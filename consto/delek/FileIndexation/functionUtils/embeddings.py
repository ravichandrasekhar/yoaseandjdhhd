from openai import AzureOpenAI
import os
import logging

# Load environment variables
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")

class GetEmbeddings():
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version=EMBEDDING_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment="text-embedding-ada-002"
        )

    def generate_embeddings(self, chunk):
        try:
            response = self.client.embeddings.create(input=[chunk], model="text-embedding-ada-002")
            # logging.info("Response: %s", response.data)
            logging.info("Embedding generated successfully..!!")
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise
