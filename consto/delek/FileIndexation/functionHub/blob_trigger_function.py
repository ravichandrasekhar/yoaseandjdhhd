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

blobTriggerFunc = func.Blueprint() 

# This is the main Azure Function entry point
@blobTriggerFunc.function_name(name="chatbotIndexation")
@blobTriggerFunc.blob_trigger(arg_name="myblob", path="kb-docs/{name}",connection="myBlobString") 
def chatbotIndexation(myblob: func.InputStream):
    logging.info(f"Processing File is: {myblob.name}")

    try:
        # Initialize Azure Index
        azure_index = AzureIndex()
        if not azure_index.checkIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX):
            # If the index does not exist, create it
            azure_index.createIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)

        # Extract the file name from the blob name
        file_name = myblob.name.split('/')[-1]
        logging.info(f"File name is: {file_name}")

        # Download the blob content
        azure_blob = BlobStorage()
        file_content = azure_blob.download_file_from_blob(AZURE_BLOB_CONNECTION_STRING, CONTAINER_NAME, file_name)

        # Process the file content
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

            embedding = GetEmbeddings()
            # Generate embeddings for the chunk
            document['content_embeddings'] = embedding.generate_embeddings(chunk)

            # Index document
            try:
                azure_index.index_document_to_azure_search(document, AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)
            except Exception as e:
                logging.error(f"Error indexing document '{file_name}', chunk {chunk_number}: {e}")

        logging.info("Files indexed successfully!")

    except Exception as e:
        logging.error(f"An error occurred while processing document '{file_name}': {e}")

    # Return statement should be None or omitted
    return None
