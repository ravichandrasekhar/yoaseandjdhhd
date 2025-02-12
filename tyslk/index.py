import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from azure.search.documents import SearchClient
import os
from azure.search.documents.indexes.models import SearchIndex, SimpleField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration, VectorSearchProfile, SearchableField, SearchField, SearchFieldDataType
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
import re
import json
import uuid
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import numpy as np
from sklearn.decomposition import TruncatedSVD

# Load environment variables from .env file
load_dotenv("./.env")

# Retrieve username, password, and API URL from environment variables
username = os.getenv("USER")
password = os.getenv("PASSWORD")
api_url = ""  # Replace with your actual API URL
service_endpoint = ""
admin_key = ""
index_name = "kb-knowledge1"
azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"

def get_all_records():
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    try:
        response = requests.get(api_url, headers=headers, auth=HTTPBasicAuth(username, password))
        response.raise_for_status()

        data = response.json()
        results = data.get('result', [])
        print("Data retrieved successfully.", data)
        print("Number of records retrieved: ", len(results))
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def create_index(service_endpoint, admin_key, index_name):
    # Define index schema
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True, searchable=True, sortable=True, filterable=True, facetable=True),
        SimpleField(name="short_description", type="Edm.String"),
        SimpleField(name="sys_id", type="Edm.String", searchable=True, sortable=True, filterable=True, facetable=True),
        SimpleField(name="text", type="Edm.String"),
        SearchableField(name="content", type="Edm.String"),  # this field for remove html
        SearchField(name="ContentEmbeddings", type="Collection(Edm.Single)", searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
        SimpleField(name="sys_updated_on", type="Edm.String"),
        SimpleField(name="number", type="Edm.String"),
        SimpleField(name="sys_updated_by", type="Edm.String"),
        SimpleField(name="workflow_state", type="Edm.String"),
        SimpleField(name="sys_created_on", type="Edm.String"),
        SimpleField(name="meta_description", type="Edm.String"),
        SimpleField(name="meta", type="Edm.String"),
        SimpleField(name="topic", type="Edm.String"),
        SimpleField(name="display_number", type="Edm.String"),
        SimpleField(name="related_products", type="Edm.String"),
        SimpleField(name="article_id", type="Edm.String"),
        SimpleField(name="active", type="Edm.String"),
        SimpleField(name="description", type="Edm.String"),
        SimpleField(name="sys_created_by", type="Edm.String"),
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

    # Create index client
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

    try:
        # Check if the index exists
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists. Deleting the existing index...")
        index_client.delete_index(index_name)
        print(f"Index '{index_name}' has been deleted.")
    except Exception as e:
        print(f"Index '{index_name}' not found.")

    try:
        print(f"Creating index '{index_name}'...")
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")
    except Exception as e:
        print(f"Error creating index '{index_name}': {e}")

def upload_documents(documents, service_endpoint, admin_key, index_name):
    try:
        search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))
        
        # Debug prints
        print("Number of documents to upload:", len(documents))
        print("Sample document:", documents[0] if documents else "No documents")
        
        if documents:
            result = search_client.upload_documents(documents=documents)
            print("Documents uploaded successfully.")
        else:
            print("No documents to upload.")
    except Exception as e:
        print(f"Error uploading documents: {e}")

if __name__ == "__main__":
    try:
        # Example usage:
        openai_credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_deployment=azure_openai_embedding_deployment,
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            azure_ad_token_provider=token_provider if not azure_openai_key else None,
            api_version=azure_openai_version
        ) 
        all_records = get_all_records()

        # Call create_index function
        create_index(service_endpoint, admin_key, index_name)

        # Convert records to documents with SimpleField schema
        documents = []
        for record in all_records:
            if isinstance(record, dict):
                descriptions = record.get("text", "")
                content_data = remove_html_tags(descriptions)
                
                # Generate a new unique ID if 'id' is not present
                record_id = str(record.get("id", "")) if "id" in record else str(uuid.uuid4())
                # Inside the loop where you generate embeddings for content
                embeddings = []  # Initialize list to store embeddings

                # Inside the loop where you generate embeddings for content
                # print("content_data:", content_data)
                chunk_size = 8000  # Define chunk size as needed
                content_chunks = [content_data[i:i + chunk_size] for i in range(0, len(content_data), chunk_size)]

                for chunk in content_chunks:
                    try:
                        # Generate embeddings for content chunk
                        response = client.embeddings.create(input=chunk, model=embedding_model_name)
                        if response.data and response.data[0].embedding:  # Check if response and embedding exist
                            # Extract embeddings and ensure the correct dimensionality
                            embeddings_chunk = response.data[0].embedding[:1536]  # Limit to 1536 dimensions
                            embeddings.append(embeddings_chunk)
                        else:
                            print("Error: Embedding data not found in response.")
                    except Exception as e:
                        print(f"Error generating embeddings for content chunk: {e}")

                # Convert embeddings to numpy array
                embeddings_array = np.array(embeddings)

                # Convert embeddings array to list for JSON serialization
                embeddings_list = embeddings_array.tolist()

                document = {
                    "id": str(record_id),
                    "short_description": str(record.get('short_description', '')),
                    "text": str(descriptions),
                    "sys_id": str(record.get("sys_id", "")),
                    "content": str(content_data),  # Wrap content in a list
                    "ContentEmbeddings": embeddings_list[0] if embeddings_list else [],
                    "sys_updated_by": str(record.get('sys_updated_by', " ")),
                    "sys_updated_on": str(record.get('sys_updated_on', '')),
                    "number": str(record.get('number', ' ')),
                    "sys_created_on": str(record.get('sys_created_on', '')),
                    "workflow_state": str(record.get('workflow_state', '')),
                    "sys_created_by": str(record.get('sys_created_by', '')),
                    "meta_description": str(record.get('meta_description', '')),
                    "meta": str(record.get('meta', '')),
                    "topic": str(record.get('topic', '')),
                    "display_number": str(record.get('display_number', '')),
                    
                    "related_products": str(record.get('related_products', '')),
                    "article_id": str(record.get('article_id', '')),
                    "active": str(record.get('active', '')),
                    "description": str(record.get('description', ''))
                }
                # print("Documents:", document)
                documents.append(document)
                # print("documents append", documents)

        # Upload documents to the index
        try:
            upload_documents(documents, service_endpoint, admin_key, index_name)
        except Exception as e:
            print(f"Error uploading documents: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")
