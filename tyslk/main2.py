import uuid
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from datetime import datetime, timezone
from docx import Document
from dotenv import load_dotenv
import os
from langchain_community.document_loaders import PyPDFLoader
import re
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchProfile, SearchField
import uuid
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from datetime import datetime, timezone
from openai import AzureOpenAI
load_dotenv()

poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
tesseract_path = r'D:\\configurations\\test\\tesseract.exe'
os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'
pdf_directory = r"Data2"
search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
search_api_key = os.getenv("AZURE_SEARCH_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_embedding_deployment = os.getenv("azure_openai_embedding_deployment")
embedding_model_name = os.getenv("azure_openai_embedding_deployment")
azure_openai_version = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")
def extraction_content_from_pdf(pdf_directory):
    text_contents = []
    for file_name in os.listdir(pdf_directory):
        if file_name.endswith('.pdf'):
            file_path = os.path.join(pdf_directory, file_name)
            
            loader = PyPDFLoader(file_path, extract_images=True)
            documents = loader.load()

            for document in documents:
                page_content = getattr(document, 'content', None) or str(document)
                if page_content:
                    page_content = page_content.strip()
                    if page_content.startswith('page_content='):
                        page_content = page_content[len('page_content='):]
                        page_content = re.sub(r"metadata=\{.*?\}", "", page_content)
                        page_content = re.sub(r"^metadata=.*$", "", page_content, flags=re.MULTILINE)
                        page_content = re.sub(r"\n+", "\n", page_content).strip()
                    text_contents.append(page_content)
    return text_contents


def create_index(search_endpoint, search_api_key, index_name):
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="content", type="Edm.String"),
        SearchField(name="contentVector", type="Collection(Edm.Single)", searchable=True, stored=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
        SimpleField(name="indexationTime", type="Edm.DateTimeOffset", filterable=True, retrievable=True, stored=True, sortable=True, facetable=True),
    ]
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
            )
        ]
    )
    index = SearchIndex(name=index_name, fields=index_fields, vector_search=vector_search)

    index_client = SearchIndexClient(search_endpoint, AzureKeyCredential(search_api_key))

    try:
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists. Deleting the existing index...")
        index_client.delete_index(index_name)
        print(f"Index '{index_name}' has been deleted.")
    except Exception as e:
        print(f"Index '{index_name}' not found or another error occurred: {e}")

    try:
        print(f"Creating index '{index_name}'...")
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")
    except Exception as e:
        print(f"Error creating index '{index_name}': {e}")


def index_document_to_azure_search(document, service_endpoint, admin_key, index_name):
    try:
        search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

        document_to_index = {
            "id": document["id"],
            "content": document['content'],
            "contentVector": document["contentVector"],
            "indexationTime": document["indexationTime"]
        }
        search_client.upload_documents(documents=[document_to_index])
        print(f"Indexing document '{document_to_index}'...")
        print(f"Document '{document['id']}' indexed successfully.")
    except Exception as e:
        print(f"Error indexing document '{document['id']}': {str(e)}")


def process_and_index_pdfs(pdf_directory):
    create_index(search_endpoint, search_api_key, index_name)
    pdfs = []

    # Extract content
    text_contents = extraction_content_from_pdf(pdf_directory)
    # Extract tables and summaries
    for file_name in os.listdir(pdf_directory):
        if file_name.endswith('.pdf'):
            pdf_path = os.path.join(pdf_directory, file_name)
            # Extract tables
          
            
            # Extract images and generate image descriptions
            image_counter = 1
            
            
            # Process each page of the PDF
            for page_content in zip(text_contents):
                document = {
                    "id": str(uuid.uuid4()),  # Generate unique ID
                    "content": page_content,
                    "contentVector": [],  # Placeholder for embeddings
                    "indexationTime": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                }

                # Generate embeddings
                try:
                    client = AzureOpenAI(
                        azure_endpoint=azure_openai_endpoint,
                        api_key=azure_openai_key,
                        api_version=azure_openai_version
                    )
                    combined_response = client.embeddings.create(input=[page_content], model=embedding_model_name)
                    combined_embeddings = combined_response.data[0].embedding
                    document['contentVector'] = combined_embeddings
                except Exception as e:
                    print(f"An error occurred while generating embeddings: {e}")
                    continue

                # Index the document
                try:
                    index_document_to_azure_search(document, search_endpoint, search_api_key, index_name)
                except Exception as e:
                    print(f"Error indexing document '{document['id']}': {str(e)}")
                try:
                    index_document_to_azure_search(document, search_endpoint, search_api_key, index_name)
                except Exception as e:
                    print(f"Error indexing document '{document['id']}': {str(e)}")
            
if __name__ == "__main__":
    try:
        # Process PDFs and extract images
        process_pdfs_in_directory(pdf_directory)

        # Process and index PDFs
        process_and_index_pdfs(pdf_directory)
    except Exception as e:
        print(f"An error occurred: {e}")
