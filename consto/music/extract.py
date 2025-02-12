import os
from PyPDF2 import PdfReader
import pdfplumber
from pdf2image import convert_from_path
from dotenv import load_dotenv
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import openai
import re
from io import BytesIO
import base64
from pathlib import Path

# Load environment variables
load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = "https://ngloflopenai.openai.azure.com/"
AZURE_OPENAI_KEY = "090c8f8e9f724b7eb47bf8a9e30db65b"
AZURE_EMBEDDING_MODEL_NAME = "text-embedding-ada-002"  # This is your deployment ID
AZURE_OPENAI_VERSION = "2023-05-15"

# Local database to store documents, embeddings, and extracted content
database = {"documents": [], "embeddings": [], "keywords": [], "images": [], "tables": []}
DB_FILE = "local_database.json"

# Load or initialize the database
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r") as f:
            database = json.load(f)
    except json.JSONDecodeError:
        print("Error loading local_database.json. The file may be corrupted. Initializing a new database.")
        database = {"documents": [], "embeddings": [], "keywords": [], "tables": []}
else:
    with open(DB_FILE, "w") as f:
        json.dump(database, f)

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    text = ""
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function to convert image to base64
def convert_image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")  # Save the image in PNG format
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Function to extract tables from PDF
def extract_tables_from_pdf(file_path):
    tables = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables += page.extract_tables()
    return tables

# Function to extract images from PDF and save them locally
def save_images_to_folder(images, folder_path, base_filename):
    # Ensure the directory exists
    Path(folder_path).mkdir(parents=True, exist_ok=True)
    
    for idx, img in enumerate(images):
        # Create a unique filename for each image
        image_filename = f"{base_filename}_image_{idx + 1}.png"
        image_path = os.path.join(folder_path, image_filename)
        
        # Save the image as a PNG file
        img.save(image_path, format="PNG")
        print(f"Image saved as {image_path}")

# Function to extract images from PDF
def extract_images_from_pdf(file_path, save_folder):
    images = []
    # Convert PDF pages to images
    image_list = convert_from_path(file_path)
    
    # Save images locally
    save_images_to_folder(image_list, save_folder, os.path.basename(file_path).split('.')[0])
    
    return images  # You can return images if you need them for further processing

# Function to compute embeddings using Azure OpenAI
def compute_embedding(text):
    openai.api_type = "azure"
    openai.api_base = AZURE_OPENAI_ENDPOINT
    openai.api_key = AZURE_OPENAI_KEY
    openai.api_version = AZURE_OPENAI_VERSION

    # Specify the deployment_id instead of model
    response = openai.Embedding.create(
        input=text,
        deployment_id=AZURE_EMBEDDING_MODEL_NAME  # Use the deployment_id here
    )
    return response["data"][0]["embedding"]

# Function to extract keywords dynamically from the document text
def extract_keywords(text):
    # Using a simple approach to extract keywords by finding most frequent words
    words = re.findall(r'\w+', text.lower())
    word_freq = {}
    for word in words:
        if word not in word_freq:
            word_freq[word] = 1
        else:
            word_freq[word] += 1
    # Sort words by frequency and return top 10 keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, freq in sorted_words[:10]]
    return keywords

# Index PDF documents (Split each document into sections/paragraphs)
def index_documents(folder_path, save_image_folder):
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".pdf"):
            file_path = os.path.join(folder_path, file_name)
            print(f"Indexing {file_name}...")

            # Extract and save images to the local folder
            extract_images_from_pdf(file_path, save_image_folder)

            text = extract_text_from_pdf(file_path)
            
            # Extract keywords dynamically from the document text
            keywords = extract_keywords(text)
            
            # Extract tables from the PDF
            tables = extract_tables_from_pdf(file_path)

            # Split the document into sections (for simplicity, split by paragraphs)
            sections = text.split("\n\n")
            
            for section in sections:
                embedding = compute_embedding(section)
                
                # Append the document, embedding, keywords, tables, and images to the database
                database["documents"].append({"file_name": file_name, "text": section})
                database["embeddings"].append(embedding)  # No .tolist() needed
                database["keywords"].append(keywords)
                database["tables"].append(tables)  # Storing extracted tables

    # Save the database to the file
    with open(DB_FILE, "w") as f:
        json.dump(database, f)

# Query documents (return relevant snippet based on query)
def query_documents(query):
    query_embedding = compute_embedding(query)
    embeddings = np.array(database["embeddings"])
    similarities = cosine_similarity([query_embedding], embeddings)[0]
    
    # Retrieve the most relevant snippet
    best_match_idx = np.argmax(similarities)
    similarity_score = similarities[best_match_idx]

    # Check if the similarity is above a relevance threshold (0.5 in this case)
    if similarity_score > 0.5:  
        relevant_snippet = database["documents"][best_match_idx]["text"]
        
        # Optionally, we can return only the first sentence or paragraph for more concise responses
        return relevant_snippet
    else:
        return "Sorry, I couldn't find relevant information in the indexed documents."

# Main chatbot function
def chatbot():
    print("Chatbot initialized. Ask your questions or type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Exiting chatbot. Goodbye!")
            break

        document = query_documents(user_input)
        if document:
            print("Bot:", document)  # Return the most relevant document snippet
        else:
            print("Bot: Sorry, I couldn't find relevant information in the indexed documents.")

# Main execution
if __name__ == "__main__":
    PDF_FOLDER_PATH = "Data"
    IMAGE_SAVE_FOLDER = "Extracted_Images"  # Folder to save extracted images
    poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
    tesseract_path = r'D:\\configurations\\test\\tesseract.exe'
    os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
    os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'

    # Step 1: Index the PDF files and save images
    index_documents(PDF_FOLDER_PATH, IMAGE_SAVE_FOLDER)

    # Step 2: Run the chatbot
    chatbot()
