import logging
import os
import azure.functions as func
from FileIndexation.functionUtils.azure_index import AzureIndex
from FileIndexation.functionUtils.blob_storage import BlobStorage
from FileIndexation.functionUtils.document_processing import Processing
from FileIndexation.functionUtils.embeddings import GetEmbeddings
import uuid

AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER")

AZURE_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

resetFunc = func.Blueprint() 

@resetFunc.function_name(name="resetChatbotIndex")
@resetFunc.route(route="resetChatbotIndex")
def resetChatbotIndex(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Initialize Azure Index
        azure_index = AzureIndex()
        if azure_index.checkIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX):
            azure_index.deleteIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)
        
        azure_index.createIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)

        # List all blobs in the container
        azure_blob = BlobStorage()
        file_names = azure_blob.list_blobs(AZURE_BLOB_CONNECTION_STRING, CONTAINER_NAME)
        # logging.info(f"Files to process: {file_names}")

        for file_name in file_names:
            try:
                logging.info(f"Processing File is: {file_names}")
                file_content = azure_blob.download_file_from_blob(AZURE_BLOB_CONNECTION_STRING, CONTAINER_NAME, file_name)
                document_process = Processing()
                file_extension = document_process.get_file_extension(file_name)
                chunks = document_process.process_file(file_content, file_extension)

                # Indexing the chunks
                for chunk_number, chunk in enumerate(chunks, 1):
                    document = {
                        "id": str(uuid.uuid4()),  # Generate unique ID
                        "content": chunk,
                        "content_embeddings": [],  # Placeholder for embeddings
                        "file_name": file_name,
                        "page_number": chunk_number
                    }

                    # Generate embeddings for chunk
                    embedding = GetEmbeddings()
                    document['content_embeddings'] = embedding.generate_embeddings(chunk)

                    # Index document
                    try:
                        azure_index.index_document_to_azure_search(document, AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)
                    except Exception as e:
                        logging.error(f"Error indexing document '{file_name}', chunk {chunk_number}: {e}")

            except Exception as e:
                logging.error(f"An error occurred while processing document '{file_name}': {e}")

        return func.HttpResponse("Files indexed successfully!", status_code=200)

    except Exception as e:
        logging.error(f"Main process failed: {e}")
        return func.HttpResponse(f"Main process failed: {e}", status_code=500)
