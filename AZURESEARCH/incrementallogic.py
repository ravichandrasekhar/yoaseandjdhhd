from fastapi import FastAPI, HTTPException
from typing import List
import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

app = FastAPI()

# Define your Azure Cognitive Search and SharePoint configuration variables here
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = "" 
SHAREPOINT_SITE_ID = ""
list_id = ""
service_endpoint = ""
admin_key = ""
index_name = "hudsonsharepointlist"
azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"
# Define your logic app endpoint path
@app.post("/incremental-indexing")
async def incremental_indexing():
    try:
        # Get data from SharePoint list
        sharepoint_data = get_sharepoint_list_data(list_id)

        # Index documents to Azure Cognitive Search
        if sharepoint_data:
            all_documents = []
            for item in sharepoint_data:
                document = {
                    "id": str(item['id']),
                    "Title": str(item.get('fields', {}).get('Title', '')),
                    "question": str(item.get('fields', {}).get('field_0', '')),
                    "answer": str(item.get('fields', {}).get('field_1', '')),
                    "Permissions": get_item_permissions(item['id']),
                    "combinedembeddings": [],
                    "webUrl": item['webUrl']
                }
                all_documents.append(document)

            index_documents_to_azure_search(all_documents, service_endpoint, admin_key, index_name)
            return {"message": "Incremental indexing completed successfully"}
        else:
            return {"message": "No data retrieved from SharePoint list"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_sharepoint_list_data(list_id):
    try:
        # Define the fields to be expanded and indexed
        fields_to_expand_and_index = ["Title", "field_0", "field_1"]

        # Construct the $select part of the URL
        select_fields = ','.join(fields_to_expand_and_index)

        # Endpoint URL to retrieve items from a SharePoint list with expanded fields
        url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"

        # Request headers
        headers = {
            "Authorization": "Bearer " + get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID),
            "Accept": "application/json"
        }

        # Send GET request
        response = requests.get(url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
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

def get_item_permissions(item_id):
    try:
        permissions_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items/{item_id}/driveItem/permissions"
        headers = {
            "Authorization": "Bearer " + get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID),
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

def index_documents_to_azure_search(all_documents, service_endpoint, admin_key, index_name):
    try:
        # Create a SearchClient instance
        client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

        # Iterate over all documents and index them
        for document in all_documents:
            # Index the document
            client.upload_documents(documents=[document])

            # Print a message indicating successful indexing
            print(f"Document '{document['id']}' indexed successfully.")

    except Exception as e:
        # Print an error message if indexing fails
        print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")

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
