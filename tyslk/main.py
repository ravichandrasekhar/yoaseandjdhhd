import logging
import os
import uuid


from azure_index import AzureIndex
from embeddings import GetEmbeddings
from extraction import Processing
from dotenv import load_dotenv
load_dotenv()
# Environment Variables for Azure Search
AZURE_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")


def chatbot_indexation_from_directory(directory_path):
    """
    Main entry point for processing and indexing all files in a directory.

    :param directory_path: Local directory path containing the files to be processed.
    """
    logging.info(f"Processing files from directory: {directory_path}")

    try:
        # Initialize Azure Index
        azure_index = AzureIndex()
        
            # If the index does not exist, create it
        azure_index.createIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)

        # Iterate through all files in the directory
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                logging.info(f"Processing file: {file_path}")

                try:
                    # Read the file content
                    with open(file_path, "rb") as file:
                        file_content = file.read()

                    # Process the file content
                    document_process = Processing()
                    file_extension = document_process.get_file_extension(file_name)
                    chunks = document_process.process_file(file_content, file_extension)
                    print(chunks)
                    # Index the chunks
                    for chunk_number, chunk in enumerate(chunks, 1):
                        document = {
                            "id": str(uuid.uuid4()),  # Generate unique ID
                            "content": chunk,
                            "contentVector": [],  # Placeholder for embeddings
                            "file_name": file_name,
                            "page_number": chunk_number
                        }

                        embedding = GetEmbeddings()
                        # Generate embeddings for the chunk
                        document['contentVector'] = embedding.generate_embeddings(chunk)

                        # Index document
                        try:
                            azure_index.index_document_to_azure_search(
                                document,
                                AZURE_SERVICE_ENDPOINT,
                                AZURE_SEARCH_KEY,
                                AZURE_SEARCH_INDEX
                            )
                        except Exception as e:
                            logging.error(f"Error indexing document '{file_name}', chunk {chunk_number}: {e}")

                    logging.info(f"File '{file_name}' indexed successfully!")

                except Exception as e:
                    logging.error(f"Error processing file '{file_path}': {e}")

    except Exception as e:
        logging.error(f"An error occurred while processing the directory '{directory_path}': {e}")


# Example Usage
if __name__ == "__main__":
    # Path to the local directory containing files to be processed
    local_directory_path = r"Data2"  # Update this with your directory path
    chatbot_indexation_from_directory(local_directory_path)
