import os
import uuid
import io
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchProfile, SearchField, SemanticConfiguration, SemanticPrioritizedFields, SemanticField, SemanticSearch
from azure.storage.blob import BlobServiceClient
from docx import Document
from openai import AzureOpenAI
import fitz
from azure.search.documents import SearchClient
# Azure Cognitive Search configuration
service_endpoint = ""
admin_key = ""
index_name = "index-blob-test"

# Azure Blob Storage configuration
blob_storage_connection_string = ""
container_name = "samplepdf"

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"

# Chunk size for embedding
chunk_size = 8000

def create_index(service_endpoint, admin_key, index_name):
    # Define index schema
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="content", type="Edm.String"),
        SearchField(name="contentEmbeddings", type="Collection(Edm.Single)", searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
        SimpleField(name="blob_file_name", type="Edm.String", sortable=True, facetable=True),
        SimpleField(name="page_number", type="Edm.Int32", sortable=True, facetable=True),
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
    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")]
        )
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(name=index_name, fields=index_fields, vector_search=vector_search, semantic_search=semantic_search)

    # Create index client
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

    try:
        # Check if the index exists
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception as e:
        print(f"Index '{index_name}' not found. Creating index...")
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")

def download_document_from_blob(storage_connection_string, container_name, blob_name, file_extension):
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    if file_extension == '.pdf':
        document_content = blob_client.download_blob().readall()
    elif file_extension == '.docx':
        docx_content = blob_client.download_blob().readall()
        document = Document(io.BytesIO(docx_content))
        document_content = '\n'.join([paragraph.text for paragraph in document.paragraphs])
    else:
        # Handle other file types if needed
        document_content = None
    return document_content

def list_blobs(storage_connection_string, container_name):
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return blob_list

def index_document_to_azure_search(document, service_endpoint, admin_key, index_name):
    try:
        # Create search client
        search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

        document_to_index = {
            "id": document["id"],
            "content": document["content"],
            "contentEmbeddings": document["contentEmbeddings"],
            "blob_file_name": document["blob_file_name"],
            "page_number": str(document["page_number"]) # Include page number in the document to index
        }
        search_client.upload_documents(documents=[document_to_index])
        print(f"Document '{document['id']}' indexed successfully.")
    except Exception as e:
        print(f"Error indexing document '{document['id']}': {str(e)}")

def main():
    try:
        # Create search index
        create_index(service_endpoint, admin_key, index_name)

        # Collect documents from Azure Blob Storage
        # List all blobs in the container
        blobs = list_blobs(blob_storage_connection_string, container_name)
        for blob in blobs:
            blob_name = blob.name
            file_extension = os.path.splitext(blob_name)[1].lower()
            if file_extension in ['.pdf', '.docx']:
                document_content = download_document_from_blob(blob_storage_connection_string, container_name, blob_name, file_extension)
                if document_content:
                    if file_extension == '.pdf':
                        doc = fitz.open(stream=io.BytesIO(document_content))
                        for page_number, page in enumerate(doc, 1):
                            page_content = page.get_text()
                            page_chunks = [page_content[i:i+chunk_size] for i in range(0, len(page_content), chunk_size)]
                            for chunk_number, chunk in enumerate(page_chunks, 1):
                                document = {
                                    "id": str(uuid.uuid4()),  # Generate unique ID
                                    "content": chunk,  # Chunk of text from the page
                                    "contentEmbeddings": [],  # Placeholder for embeddings
                                    "blob_file_name": blob_name,  # Use blob name for further processing if needed
                                    "page_number": page_number  # Page number
                                }
                                # Generate embeddings for chunk
                                try:
                                    client = AzureOpenAI(
                                        azure_endpoint=AZURE_OPENAI_ENDPOINT,
                                        api_key=azure_openai_key,
                                        api_version=azure_openai_version
                                    )
                                    combined_response = client.embeddings.create(input=chunk, model="text-embedding-ada-002")
                                    combined_embeddings = combined_response.data[0].embedding
                                    embeddings_str = [str(embedding) for embedding in combined_embeddings]
                                    document['contentEmbeddings'] = embeddings_str
                                except Exception as e:
                                    print("An error occurred:", e)
                                index_document_to_azure_search(document, service_endpoint, admin_key, index_name)
                    elif file_extension == '.docx':
                        document_chunks = [document_content[i:i+chunk_size] for i in range(0, len(document_content), chunk_size)]
                        for chunk_number, chunk in enumerate(document_chunks, 1):
                            document = {
                                "id": str(uuid.uuid4()),  # Generate unique ID
                                "content": chunk,  # Chunk of text from the entire document
                                "contentEmbeddings": [],  # Placeholder for embeddings
                                "blob_file_name": blob_name,  # Use blob name for further processing if needed
                                "page_number": 0  # Page number for entire document can be 0
                            }
                            # Generate embeddings for chunk
                            try:
                                client = AzureOpenAI(
                                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                                    api_key=azure_openai_key,
                                    api_version=azure_openai_version
                                )
                                combined_response = client.embeddings.create(input=chunk, model="text-embedding-ada-002")
                                combined_embeddings = combined_response.data[0].embedding
                                embeddings_str = [str(embedding) for embedding in combined_embeddings]
                                document['contentEmbeddings'] = embeddings_str
                            except Exception as e:
                                print("An error occurred:", e)
                            index_document_to_azure_search(document, service_endpoint, admin_key, index_name)
            else:
                print(f"Unsupported file type: {file_extension}")

    except Exception as e:
        print(f"Main process failed: {e}")

if __name__ == "__main__":
    main()
