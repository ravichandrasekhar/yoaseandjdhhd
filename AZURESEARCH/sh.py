from fastapi import FastAPI, HTTPException
from typing import Optional
import requests
import re
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchField, VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

app = FastAPI()

# Constants
SHAREPOINT_SITE_ID = ""
ACCESS_TOKEN = ""  # Replace with your access token
SEARCH_ENDPOINT = ""
SEARCH_ADMIN_KEY = ""
SEARCH_INDEX_NAME = "sharepoint-list"  # Replace with your search index name
group_id = ""  # Replace with your group ID
azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"

def regularexpression(field_name):
    """Sanitize the field name to comply with Azure Cognitive Search naming rules."""
    # Remove invalid characters
    expression = re.sub(r'[^a-zA-Z0-9_]', '_', field_name)
    # Ensure the name starts with a letter
    if not re.match(r'^[a-zA-Z]', expression):
        expression = 'f_' + expression
    return expression

def create_search_index(fields):
    try:
        index_fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SimpleField(name="webUrl", type="Edm.String"),
            SearchField(name="contentEmbeddings", type="Collection(Edm.String)", searchable=False, filterable=False, sortable=False),
            SimpleField(name="Permissions", type="Collection(Edm.String)"),
            SimpleField(name="accessList", type="Collection(Edm.String)")
        ]

        # Add dynamically retrieved fields
        for field in fields:
            regularxname = regularexpression(field)
            index_fields.append(SimpleField(name=regularxname, type="Edm.String"))
        
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
        index = SearchIndex(name=SEARCH_INDEX_NAME, fields=index_fields, vector_search=vector_search)
        index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))
        try:
        # Check if the index exists
            existing_index = index_client.get_index(SEARCH_INDEX_NAME)
            print(f"Index '{SEARCH_INDEX_NAME}' already exists. Deleting the existing index...")
            index_client.delete_index(SEARCH_INDEX_NAME)
            print(f"Index '{SEARCH_INDEX_NAME}' has been deleted.")
        except Exception as e:
          print(f"Index '{SEARCH_INDEX_NAME}' not found.")

        try:
            print(f"Creating index '{SEARCH_INDEX_NAME}'...")
            index_client.create_index(index)
            print(f"Index '{SEARCH_INDEX_NAME}' has been created successfully.")
        except Exception as e:
            print(f"Error creating index '{SEARCH_INDEX_NAME}': {e}")
    except Exception as e:
        print(f"Error creating index '{SEARCH_INDEX_NAME}': {e}")

    

def get_sharepoint_list_data(list_id):
    try:
        schema_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/columns"
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }
        response = requests.get(schema_url, headers=headers)
        if response.status_code == 200:
            schema_data = response.json()
            fields_to_expand_and_index = [column["name"] for column in schema_data["value"]]

            select_fields = ','.join(fields_to_expand_and_index)
            url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'value' in data:
                    return data['value'], fields_to_expand_and_index
                else:
                    print("No items found in the SharePoint list.")
                    return [], []
            else:
                print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
                return [], []
        else:
            print(f"Failed to retrieve schema from SharePoint list. Status code: {response.status_code}")
            return [], []
    except Exception as e:
        print(f"Error fetching data from SharePoint list: {str(e)}")
        return [], []
def get_item_permissions(list_id,item_id):
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

def get_group_members(group_id):
    try:
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/transitiveMembers/"
        group_members = []
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            members = response.json()["value"]
            for member in members:
                principal_name = member["userPrincipalName"]
                group_members.append(principal_name)
        return group_members
    except Exception as e:
        print(f"Error fetching group members for group {group_id}: {str(e)}")
        return []

def index_documents_to_azure_search(all_documents):
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

        client_search = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))

        for document in all_documents:
            content = document.get('Content', '')
            embeddings = []
            content_str = "\n".join(content.split('\n'))
            try:
                response = client.embeddings.create(input=content_str, model="text-embedding-ada-002")
                embeddings = response.data[0].embedding
                embeddings_str = [str(embedding) for embedding in embeddings]
                document['ContentEmbeddings'] = embeddings_str
            except Exception as e:
                print(f"Error generating embeddings for content '{content_str}': {e}")

            try:
                client_search.upload_documents(documents=[document])
                print(f"Document '{document['id']}' indexed successfully.")
            except Exception as e:
                print(f"Failed to index document '{document['id']}': {str(e)}")
    except Exception as e:
        print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")

# Define the FastAPI endpoint
@app.get("/index-lists")
async def index_lists(list_id: Optional[str] = None):
    if list_id:
        sharepoint_data= get_sharepoint_list_data(list_id)
       
        if sharepoint_data:
            
            all_documents = []
            for item in sharepoint_data:
                document = {
                    "id": str(item['id']),
                    "webUrl": item['webUrl'],
                    "Permissions": get_item_permissions(list_id,item['id']),
                    "accessList": get_group_members(group_id),
                    "ContentEmbeddings": [],
                }
                # Add dynamically retrieved fields to the document
                for field in fields:
                    rexgufield = regularexpression(field)
                    document[rexgufield] = str(item.get('fields', {}).get(field, ''))
                all_documents.append(document)
            create_search_index(fields)
            index_documents_to_azure_search(all_documents)
        return {"message": "List details indexed successfully."}
    else:
        try:
            lists_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists"
            headers = {
                "Authorization": "Bearer " + ACCESS_TOKEN,
                "Accept": "application/json"
            }
            response = requests.get(lists_url, headers=headers)
            if response.status_code == 200:
                lists_data = response.json()
                for list_item in lists_data['value']:
                    list_id = list_item['id']
                    sharepoint_data, fields = get_sharepoint_list_data(list_id)
                    if sharepoint_data:
                        
                        all_documents = []
                        for item in sharepoint_data:
                            document = {
                                "id": str(item['id']),
                                "webUrl": item['webUrl'],
                                "Permissions": get_item_permissions(list_id,item['id']),
                                "accessList": get_group_members(group_id),
                                "ContentEmbeddings": [],
                            }
                            # Add dynamically retrieved fields to the document
                            for field in fields:
                                rexgufield = regularexpression(field)
                                document[rexgufield] = str(item.get('fields', {}).get(field, ''))
                            all_documents.append(document)
                        create_search_index(fields)
                        index_documents_to_azure_search(all_documents)
                return {"message": "All lists indexed successfully."}
            else:
                return {"error": f"Failed to retrieve lists from SharePoint site. Status code: {response.status_code}"}
        except Exception as e:
             print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")
