import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField
from azure.search.documents import SearchClient
from datetime import datetime
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import numpy as np
SHAREPOINT_SITE_ID = ""
ACCESS_TOKEN = ""
group_id = ""
search_service_endpoint = ""
search_api_key = ""
index_name = "sharepointpages"
azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"

# Function to retrieve SharePoint pages
def get_sharepoint_pages(site_id, access_token):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/pages"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        print(f"Failed to retrieve SharePoint pages data: {response.text}")
        return []

# Function to fetch group members
def get_group_members(group_id, access_token):
    try:
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/transitiveMembers/"
        group_members = []
        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            members = response.json()["value"]

            for member in members:
                principal_name = member["userPrincipalName"]
                group_members.append({"id": member["id"], "name": principal_name})

        return group_members
    except Exception as e:
        print(f"Error fetching group members for group {group_id}: {str(e)}")
        return []

# Function to create an index if it does not exist
def create_search_index(service_endpoint, index_name, api_key):
    try:
        index_client = SearchIndexClient(endpoint=service_endpoint, credential=AzureKeyCredential(api_key))

        # Define the index schema
        index = SearchIndex(
            name=index_name,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True),
                SimpleField(name="title", type="Edm.String"),
                SimpleField(name="groupMembers", type="Collection(Edm.String)"),
                SimpleField(name="description", type="Edm.String"),
                SimpleField(name="webUrl", type="Edm.String"),
                SimpleField(name="ContentEmbeddings", type="Collection(Edm.String)")
            ]
        )
        
        # Create the index
        index_client.create_index(index)
        print(f"Search index '{index_name}' created successfully.")
        return True
    except Exception as e:
        print(f"Error creating search index: {str(e)}")
        return False

# Function to index SharePoint pages
def index_sharepoint_pages(service_endpoint, index_name, api_key, site_id, access_token, group_id):
    try:
        openai_credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_deployment=azure_openai_embedding_deployment,
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            azure_ad_token_provider=token_provider if not azure_openai_key else None,
            api_version=azure_openai_version
        )

        pages = get_sharepoint_pages(site_id, access_token)
        group_members = get_group_members(group_id, access_token)

        documents = []
        for page in pages:
            document = {
                "id": str(page["id"]),
                "title": page.get("title", ""),
                "description": page.get("description", ""),
                "webUrl":page.get("webUrl",""),
                "groupMembers": [member["name"] for member in group_members],
                "ContentEmbeddings":[]
            }
            content = document.get('description', '')  # Get the content from the description
            embeddings = []
            content_str = "\n".join(content.split('\n'))  # Concatenate content lines into a single string
            try:
                # Generate embeddings for content
                response = client.embeddings.create(input=content_str, model=embedding_model_name)
                embeddings = response.data[0].embedding  # Access embeddings directly, assuming response is in the correct format
                embeddings_str = [str(embedding) for embedding in embeddings]
                document['ContentEmbeddings'] = embeddings_str
            except Exception as e:
                print(f"Error generating embeddings for content '{content_str}': {e}")

            documents.append(document)
        
        client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(api_key))
        result = client.upload_documents(documents=documents)
        print("Indexed SharePoint pages:", result)
    except Exception as e:
        print(f"Error indexing SharePoint pages: {str(e)}")

# Check and create the index if it does not exist
index_created = create_search_index(search_service_endpoint, index_name, search_api_key)

# Index SharePoint pages
if index_created:
    index_sharepoint_pages(search_service_endpoint, index_name, search_api_key, SHAREPOINT_SITE_ID, ACCESS_TOKEN, group_id)