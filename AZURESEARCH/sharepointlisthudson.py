import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration, VectorSearchProfile
from datetime import datetime
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import numpy as np
# Define your client ID and client secret
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = "" 
# Define your SharePoint site ID and list ID
SHAREPOINT_SITE_ID = ""
list_id= ""
SEARCH_ENDPOINT = ""
SEARCH_ADMIN_KEY = ""
SEARCH_INDEX_NAME = "sharepointlist"

azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"
def get_access_token(client_id, client_secret, tenant_id):
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Failed to retrieve access token: {response.text}")
        return None
# Retrieve access token
ACCESS_TOKEN = get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID)
def create_search_index():
    try:
        index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))

        # Define the index schema
        index = SearchIndex(
            name=SEARCH_INDEX_NAME,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True),  
                SimpleField(name="Content", type="Edm.String", searchable=True),
                SimpleField(name="FileName", type="Edm.String"),
                SimpleField(name="permissions", type="Collection(Edm.String)"),
                SimpleField(name="ContentEmbeddings", type="Collection(Edm.String)", searchable=False, filterable=False, sortable=False, facetable=False, key=False, retrievable=True, index_analyzer=None, search_analyzer=None, synonym_maps=None, fields=None, suggester=None, analyzer=None, searchable_tree=None, vector_search_dimensions=32, vector_search_similarity_function=None, vector_search_algorithm=None, vector_search_ranking_function=None, vector_search_profile=None)

            ]
        )
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

        # Create the index
        index_client.create_index(index)
        print(f"Search index '{SEARCH_INDEX_NAME}' created successfully.")
    except Exception as e:
        print(f"Error creating search index: {str(e)}")

# Function to get data from SharePoint list using list ID
def get_sharepoint_list_data(list_id):
    try:
        # Define the fields to be expanded and indexed
        fields_to_expand_and_index = ["id", "field_0", "field_1", "field_3", "_x0048_4", "Content", "FileName"]

        # Construct the $select part of the URL
        select_fields = ','.join(fields_to_expand_and_index)
        print("Select_field value:", select_fields)

        # Endpoint URL to retrieve items from a SharePoint list with expanded fields
        url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"

        # Request headers
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }

        # Send GET request
        response = requests.get(url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            print("Retrieved SharePoint data:", data)  # Print the retrieved data
            if 'value' in data:
                return data['value']
            else:
                print("No items found in the SharePoint list.")
                return []
        else:
            print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching data from SharePoint list: {str(e)}")
        return []


# Function to fetch permissions for a specific item
def get_item_permissions(item_id):
    try:
        permissions_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items/{item_id}/driveItem/permissions"
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }
        response = requests.get(permissions_url, headers=headers)
        permissions = []
        if response.status_code == 200:
            permissions_data = response.json().get("value", [])
            for permission_data in permissions_data:
                granted_to = permission_data.get("grantedTo", None)
                if granted_to:
                    if "user" in granted_to:
                        user_or_group = granted_to["user"].get("displayName", "N/A")
                        permissions.append(user_or_group)
                    elif "group" in granted_to:
                        user_or_group = granted_to["group"].get("displayName", "N/A")
                        permissions.append(user_or_group)

        return permissions
    except Exception as e:
        print(f"Error fetching permissions for item {item_id}: {str(e)}")
        return []

# Function to index documents into Azure Cognitive Search
def index_documents_to_azure_search(all_documents):
    try:
        # Azure OpenAI client initialization
        openai_credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_deployment=azure_openai_embedding_deployment,
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            azure_ad_token_provider=token_provider if not azure_openai_key else None,
            api_version=azure_openai_version
        )

        client_search = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))

        for document in all_documents:
            document = {
                "id": document['id'],
                "Content": document.get('Content', ''),
                "FileName": document.get('FileName', ''),
                "Permissions": document.get('Permissions', []),
                "ContentEmbeddings": []  # Initialize content embedding field
            }

            content = document.get('Content', '')  # Get the content from the document
            embeddings = []
            content_str = "\n".join(content.split('\n'))  # Concatenate content lines into a single string
            try:
                # Generate embeddings for content
                response = client.embeddings.create(input=content_str, model="text-embedding-ada-002")
                embeddings = response.data[0].embedding  # Access embeddings directly, assuming response is in the correct format
                embeddings_str = [str(embedding) for embedding in embeddings]
                document['ContentEmbeddings'] = embeddings_str
            except Exception as e:
                print(f"Error generating embeddings for content '{content_str}': {e}")

            try:
                # Upload document to Azure Cognitive Search
                client_search.upload_documents(documents=[document])
                print(f"Document '{document['id']}' indexed successfully.")
            except Exception as e:
                print(f"Failed to index document '{document['id']}': {str(e)}")
    except Exception as e:
        print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")

if __name__ == "__main__":
    try:
        # Create search index
        create_search_index()

        # Get list ID from SharePoint site ID
        if list_id:
            # Retrieve data from SharePoint list using list ID
            sharepoint_data = get_sharepoint_list_data(list_id)
            if sharepoint_data:
                # Collect all documents
                all_documents = []
                for item in sharepoint_data:
                    document = {
                        "id": str(item['id']),  # Use the SharePoint item ID as the unique identifier for the document
                        "EntryID": str(item.get('fields', {}).get('EntryID', '')),  # Ensure correct property names
                        "_x0048_1": str(item.get('fields', {}).get('_x0048_1', '')),  # Using _x0048_1 instead of H1
                        "_x0048_2": str(item.get('fields', {}).get('_x0048_2', '')),  
                        "_x0048_3": str(item.get('fields', {}).get('_x0048_3', '')),  
                        "_x0048_4": str(item.get('fields', {}).get('_x0048_4', '')),  
                        "Content": item.get('fields', {}).get('Content', ''),
                        "FileName": item.get('fields', {}).get('FileName', ''),
                        "Permissions": get_item_permissions(item['id']),
                        
                        "ContentEmbeddings": []  # Initialize content embedding field
                        # Add other fields to index as needed
                    }
                    all_documents.append(document)

                # Index all documents into Azure Cognitive Search
                index_documents_to_azure_search(all_documents)
            else:
                print("No data retrieved from SharePoint list.")
        else:
            print("Failed to retrieve list ID from SharePoint site.")
    except Exception as e:
        print(f"Main process failed: {str(e)}")
