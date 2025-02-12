from PyPDF2 import PdfReader# PyMuPDF
from PIL import Image
import pdfplumber
import io
import os
import re
import uuid
import camelot
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
import fitz
# Load environment variables
load_dotenv()

# Configuration Paths
poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
tesseract_path = r'D:\\configurations\\test\\tesseract.exe'
os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'

# Directory Paths
pdf_directory = r"Data"
output_folder = r"extraction_images23"

# Ensure the output folder exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Function to extract text content from PDF
def extraction_content_from_pdf(pdf_path):
    text_contents = []
    loader = PyPDFLoader(pdf_path, extract_images=True)
    documents = loader.load()
    for document in documents:
        page_content = getattr(document, 'content', None) or str(document)
        if page_content:
            page_content = page_content.strip()
            if page_content.startswith('page_content='):
                page_content = page_content[len('page_content='):].strip()
                page_content = re.sub(r"metadata=\{.*?\}", "", page_content)
                page_content = re.sub(r"^metadata=.*$", "", page_content, flags=re.MULTILINE)
                page_content = re.sub(r"\n+", "\n", page_content).strip()
            text_contents.append(page_content)
    return text_contents

# Function to extract tables from PDF
def extract_tables_from_pdf(file_path):
    tables = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables += page.extract_tables()
    return tables


# Function to extract images from PDF

# Function to process PDFs in directory
def process_pdfs_in_directory(directory_path, output_folder):
    pdf_paths = [os.path.join(directory_path, file) for file in os.listdir(directory_path) if file.lower().endswith('.pdf')]
    image_counter = 1

    for pdf_path in pdf_paths:
        print(f"Processing PDF: {pdf_path}")
        
        # Extract images
     
        
        # Extract tables
        table_content = extract_tables_from_pdf(pdf_path)
        print("table-content",table_content)
        
        # Extract text
        text_contents = extraction_content_from_pdf(pdf_path)
        print("text-content",text_contents)
        
        # Process extracted data (you can modify this part to store or index the data)
       
            
            # Add any further processing, such as indexing, here.
            # For example, you could save the extracted data to a file or database.

# Main function to initiate processing
def main():
    process_pdfs_in_directory(pdf_directory, output_folder)

if __name__ == "__main__":
    main()
