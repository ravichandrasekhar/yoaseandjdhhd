from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure configurations
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER")
AZURE_OPENAI_PREVIEW_API_VERSION = os.getenv("AZURE_OPENAI_PREVIEW_API_VERSION")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")
AZURE_SEARCH_VECTOR_COLUMNS = os.getenv("AZURE_SEARCH_VECTOR_COLUMNS")
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG = os.getenv("AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG")
AZURE_OPENAI_EMBEDDING_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_NAME")

class RagBot:
    def __init__(self):
        pass

    def generate_embeddings(self, text):
        """Generate embeddings using Azure OpenAI."""
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_EMBEDDING_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment=AZURE_OPENAI_EMBEDDING_NAME
        )
        try:
            response = client.embeddings.create(input=[text], model=AZURE_OPENAI_EMBEDDING_NAME)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise

    def get_document_information(self, question):
        """Retrieve and answer questions using Azure Cognitive Search and OpenAI."""
        try:
            question_embedding = self.generate_embeddings(question)
            search_client = SearchClient(
                endpoint=AZURE_SEARCH_SERVICE,
                index_name=AZURE_SEARCH_INDEX,
                credential=AzureKeyCredential(AZURE_SEARCH_KEY)
            )
            vector_query = VectorizedQuery(
                vector=question_embedding,
                k_nearest_neighbors=3,
                fields=AZURE_SEARCH_VECTOR_COLUMNS
            )
            results = search_client.search(
                search_text=question,
                vector_queries=[vector_query],
                top=5,
                query_type='semantic',
                semantic_configuration_name=AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG
            )
            retrieved_documents = [result.get("content", "") for result in results]
            context = "\n".join(retrieved_documents)
            filenames = [result.get("fileName", "") for result in results]

            client = AzureOpenAI(
                api_key=AZURE_OPENAI_KEY,
                api_version=AZURE_OPENAI_PREVIEW_API_VERSION,
                azure_endpoint=AZURE_OPENAI_ENDPOINT
            )
            prompt = f"""
                You are an AI assistant answering based on provided documents.
                Question: "{question}"
                Documents: {context}
                Respond in JSON: {{"answer": "string", "answer_found": "boolean"}}
            """
            messages = [{"role": "user", "content": prompt}]
            response = client.chat.completions.create(
                model=AZURE_OPENAI_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=200
            )
            resp = json.loads(response.choices[0].message.content)
            return json.dumps({
                "answer": resp["answer"],
                "citations": list(set(filenames)) if resp["answer_found"] else []
            })
        except Exception as e:
            print(f"Error: {e}")
            raise

    def get_enriched_question(self, message, conversation_history):
        """Enrich user questions based on conversation history."""
        prompt = f"""
            - History: {conversation_history}
            - Current Question: {message}
            Enrich the question with context from history and return JSON:
            {{"enriched_question": "string"}}
        """
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_PREVIEW_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        messages = [{"role": "user", "content": prompt}]
        response = client.chat.completions.create(
            model=AZURE_OPENAI_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=200
        )
        enriched_question = json.loads(response.choices[0].message.content).get("enriched_question", "")
        return enriched_question
