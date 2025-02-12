from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict
import requests
import uvicorn
import pdfplumber
from docx import Document
import io
import os
import csv
import openpyxl
import base64
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchField,SearchableField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration, VectorSearchProfile,SearchFieldDataType
from azure.core.credentials import AzureKeyCredential

app = FastAPI()
search_service_endpoint = ""
admin_key = ""
index_name = "sharepoint"
group_id = ""
azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"

# Define request models
class SharePointItem(BaseModel):
    ACCESS_TOKEN: Optional[str] = Field(None, description="Access token for SharePoint API")
    CLIENT_ID: Optional[str] = Field(None, description="Client ID for SharePoint API")
    CLIENT_SECRET: Optional[str] = Field(None, description="Client secret for SharePoint API")
    TENANT_ID: Optional[str] = Field(None, description="Tenant ID for SharePoint API")
    configuration: str = Field(..., description="Configuration type: 'list', 'drive', or 'pages'")
    SHAREPOINT_DRIVE_ID: Optional[str] = Field(None, description="ID of the SharePoint drive (optional)")
    list_id: Optional[str] = Field(None, description="ID of the SharePoint list (optional)")
    sharepoint_site_id: Optional[str] = Field(None, description="ID of the SharePoint site (optional)")
    folder_id: Optional[str] = Field(None, description="ID of the SharePoint folder (optional)")
def sanitize_field_names(fields):
    return [sanitize_field_name(field) for field in fields]

def sanitize_field_name(field_name):
    if field_name.startswith('_'):
        return field_name[1:]
    return field_name    

def create_or_update_index(search_service_endpoint, admin_key, index_name, fields):
    client = SearchIndexClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(admin_key))
    field_schemas = [
        SearchableField(name=sanitize_field_name(field), type=SearchFieldDataType.String, searchable=True, filterable=True)
        for field in fields
    ]
    field_schemas.append(SimpleField(name="id", type=SearchFieldDataType.String, key=True)),
    field_schemas.append(SimpleField(name="accessList", type="Collection(Edm.String)")),
    field_schemas.append(SimpleField(name="permissions", type="Collection(Edm.String)")),
    field_schemas.append(SearchField(name="contentEmbeddings", type="Collection(Edm.Single)",vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"))
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

    index = SearchIndex(name=index_name, fields=field_schemas,vector_search=vector_search)
    index_client = SearchIndexClient(search_service_endpoint, AzureKeyCredential(admin_key))
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
    client.create_or_update_index(index)
    print(f"Search Index successfully created {index_name}")
def get_item_permissions(item_id,access_token,sharepoint_site_id,list_id):
    try:
        permissions_url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{list_id}/items/{item_id}/driveItem/permissions"
        headers = {
            "Authorization": "Bearer " + access_token,
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


# Function to fetch group members
def get_group_members(group_id,access_token):
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
                group_members.append(principal_name)

        return group_members
    except Exception as e:
        print(f"Error fetching group members for group {group_id}: {str(e)}")
        return []


def upload_documents(search_service_endpoint, admin_key, index_name, documents):
    client = SearchClient(endpoint=search_service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))
    
    # Convert numerical values to strings in document data
    for document in documents:
        for key, value in document.items():
            if isinstance(value, (int, float)):
                document[key] = str(value)
    
    client.upload_documents(documents)

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

def get_sharepoint_list_data(list_id, access_token, sharepoint_site_id):
    try:
        schema_url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{list_id}/columns"
        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json"
        }
        response = requests.get(schema_url, headers=headers)
        if response.status_code == 200:
            schema_data = response.json()
            fields_to_expand_and_index = [column["name"] for column in schema_data["value"]]

            select_fields = ','.join(fields_to_expand_and_index)
            url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists/{list_id}/items?expand=fields(select={select_fields})"
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

def get_all_sharepoint_lists(access_token, sharepoint_site_id):
    try:
        lists_url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site_id}/lists"
        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json"
        }
        response = requests.get(lists_url, headers=headers)
        if response.status_code == 200:
            lists_data = response.json().get("value", [])
            all_lists_data = []
            for list_item in lists_data:
                list_id = list_item.get("id")
                list_data, fields = get_sharepoint_list_data(list_id, access_token, sharepoint_site_id)
                all_lists_data.append({"list_id": list_id, "list_data": list_data, "fields": fields})
            return all_lists_data
        else:
            print(f"Failed to retrieve lists from SharePoint site. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching lists from SharePoint site: {str(e)}")
        return []

def get_sharepoint_items(access_token, folder_id, SHAREPOINT_DRIVE_ID):
    try:
        if folder_id:
            url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{folder_id}/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/root/children"

        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data['value']
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to retrieve items from SharePoint drive.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching items from SharePoint drive: {str(e)}")

def download_sharepoint_file(file_id, SHAREPOINT_DRIVE_ID, access_token):
    try:
        content_url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{file_id}/content"
        headers = {
            "Authorization": "Bearer " + access_token,
        }
        response = requests.get(content_url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to download file with ID '{file_id}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file from SharePoint drive: {str(e)}")
def index_folder_to_azure_search(folder_name, folder_id):
    client = SearchClient(endpoint=search_service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

    document = {
        "id": str(folder_id),  # Unique identifier for the folder
        "folderName": folder_name
        # Add more fields as needed
    }
    try:
        result = client.upload_documents(documents=[document])
        print(f"Folder '{folder_name}' indexed successfully.")
    except Exception as e:
        print(
            f"Failed to index folder '{folder_name}' to Azure Search. Error: {str(e)}")
def get_permissions(SHAREPOINT_DRIVE_ID,file_id, access_token):
    permissions_url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{file_id}/permissions"
    headers = {
        "Authorization": "Bearer " + access_token,
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
                elif "group" in granted_to:
                    user_or_group = granted_to["group"].get("displayName", "N/A")
                if user_or_group != "N/A":  # Filter out "N/A" values
                    permissions.append(f" {user_or_group}")

    return permissions


def download_sharepoint_file(file_id, SHAREPOINT_DRIVE_ID, access_token):
    try:
        content_url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{file_id}/content"
        headers = {
            "Authorization": "Bearer " + access_token,
        }
        response = requests.get(content_url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to download file with ID '{file_id}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file from SharePoint drive: {str(e)}")
def extract_text_from_pdf(file_content):
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages)

def extract_text_from_word(file_content):
    return "\n".join(paragraph.text for paragraph in Document(io.BytesIO(file_content)).paragraphs)

def extract_text_from_excel(file_content):
    file_str = ""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_content))
        for sheet in wb:
            file_str += " ".join(str(cell.value) for row in sheet.iter_rows() for cell in row if cell.value)
    except Exception as e:
        file_str = f"Error extracting text from Excel file: {str(e)}"
    return file_str

def extract_text_from_text(file_content):
    try:
        return file_content.decode('utf-8')
    except UnicodeDecodeError:
        return str(file_content, errors='ignore')

def extract_text_from_csv(file_content):
    try:
        return " ".join(" ".join(row) for row in csv.reader(io.StringIO(file_content.decode('utf-8'))))
    except Exception as e:
        return f"Error extracting text from CSV file: {str(e)}"

def extract_text_from_other(file_content):
    return "Unsupported file type"

def extract_text(file_name, file_content):
    ext = os.path.splitext(file_name)[-1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_content)
    elif ext in [".doc", ".docx"]:
        return extract_text_from_word(file_content)
    elif ext in [".xls", ".xlsx"]:
        return extract_text_from_excel(file_content)
    elif ext == ".txt":
        return extract_text_from_text(file_content)
    elif ext == ".csv":
        return extract_text_from_csv(file_content)
    else:
        return extract_text_from_other(file_content)
def index_drive_folder(SHAREPOINT_DRIVE_ID, access_token, folder_id=None):
    drive_items = get_sharepoint_items(access_token, folder_id, SHAREPOINT_DRIVE_ID)
    for item in drive_items:
        item_name = item['name']
        item_id = item['id']
        web_url = item['webUrl']
        if 'folder' in item:
            # If item is a folder, recursively index its contents
            index_folder_to_azure_search(item_name, item_id)
            index_drive_folder(SHAREPOINT_DRIVE_ID, access_token, item_id)
        else:
            # If item is a file, index its content
            file_content = download_sharepoint_file(item_id, SHAREPOINT_DRIVE_ID, access_token)
            permissions = get_permissions(SHAREPOINT_DRIVE_ID, item_id, access_token)
            group_members = get_group_members(group_id, access_token)
            if file_content:
                # Extract text based on file type
                if item_name.endswith('.pdf'):
                    content_str = extract_text_from_pdf(file_content)
                elif item_name.endswith('.docx'):
                    content_str = extract_text_from_word(file_content)
                elif item_name.endswith('.xlsx') or item_name.endswith('.xls'):
                    content_str = extract_text_from_excel(file_content)
                else:
                    content_str = extract_text_from_other(file_content)
                
                # Generate content embeddings using Azure OpenAI
                index_document_to_azure_search(item_name, file_content, item_id, permissions, group_members, web_url)
def index_document_to_azure_search(file_name, file_content, file_id, permissions, group_members, web_url):
    file_extension = os.path.splitext(file_name)[1].lower()
    content_str = ""

    try:
        if file_extension == ".docx" or file_extension == ".doc":
            content_str = extract_text_from_word(file_content)
        elif file_extension == ".pdf":
            content_str = extract_text_from_pdf(file_content)
        elif file_extension == ".txt":
            content_str = extract_text_from_text(file_content)
        elif file_extension == ".xlsx" or file_extension == ".xls":
            content_str = extract_text_from_excel(file_content)
        elif file_extension == ".csv":
            content_str = extract_text_from_csv(file_content)
        else:
            content_str = extract_text_from_other(file_content)

    except Exception as e:
        print(f"Error extracting text from '{file_name}': {str(e)}")
        return
    client = SearchClient(endpoint=search_service_endpoint,
                              index_name=index_name,
                              credential=AzureKeyCredential(admin_key))

    document = {
            "id": str(file_id),  # Unique identifier for the document
            "fileName": file_name,
            "content": content_str,
            "permissions": permissions,
            "accessList": [str(member) for member in group_members],
            "webUrl": web_url,
            # "contentEmbeddings": []
        }
        # document['contentEmbeddings'] = content_embedding_strs
    result = client.upload_documents(documents=[document])
    print(f"Document '{file_name}' indexed successfully.")


@app.post("/sharepoint/get-details/")
def get_sharepoint_details(item: SharePointItem):
    if not item.ACCESS_TOKEN:
        if not (item.CLIENT_ID and item.CLIENT_SECRET and item.TENANT_ID):
            raise HTTPException(status_code=400, detail="Access token or client credentials must be provided.")
        item.ACCESS_TOKEN = get_access_token(item.CLIENT_ID, item.CLIENT_SECRET, item.TENANT_ID)

    if item.configuration == "list":
        if item.list_id and item.sharepoint_site_id:
            list_data, fields = get_sharepoint_list_data(item.list_id, item.ACCESS_TOKEN, item.sharepoint_site_id)
            if not list_data:
                raise HTTPException(status_code=404, detail="No items found in the SharePoint list.")
            create_or_update_index(search_service_endpoint, admin_key, index_name, fields)
            all_documents = []
            for list_item in list_data:
                document = {"id": str(list_item["id"])}
                for field in fields:
                    field_name = sanitize_field_name(field)
                    document[field_name] = str(list_item.get('fields', {}).get(field, ''))
                all_documents.append(document)
            
            upload_documents(search_service_endpoint, admin_key, index_name, all_documents)
            return {"list_data": list_data, "fields": fields}
        elif item.sharepoint_site_id:
            all_lists_data = get_all_sharepoint_lists(item.ACCESS_TOKEN, item.sharepoint_site_id)
            if not all_lists_data:
                raise HTTPException(status_code=404, detail="No lists found in the SharePoint site.")
            for list_data_info in all_lists_data:
                list_id = list_data_info["list_id"]
                list_data = list_data_info["list_data"]
                fields = list_data_info["fields"]
                create_or_update_index(search_service_endpoint, admin_key, index_name, fields)
                all_documents = []
                for list_item in list_data:
                    document = {"id": str(list_item["id"])}
                    for field in fields:
                        field_name = sanitize_field_name(field)
                        document[field_name] = str(list_item.get('fields', {}).get(field, ''))
                    all_documents.append(document)
                upload_documents(search_service_endpoint, admin_key, index_name, all_documents) 
            return {"all_lists_data": all_documents}
        else:
            raise HTTPException(status_code=400, detail="SharePoint site ID is required to retrieve lists.")
            
    elif item.configuration == "drive":
        if item.SHAREPOINT_DRIVE_ID:
            if item.folder_id:
                drive_items = get_sharepoint_items(item.ACCESS_TOKEN, item.folder_id, item.SHAREPOINT_DRIVE_ID)
            else:
                drive_items = get_sharepoint_items(item.ACCESS_TOKEN, None, item.SHAREPOINT_DRIVE_ID)
            
            # Extract fields dynamically from the files in the drive
            fields = ["content", "weburl", "fileName","folderName"]
            create_or_update_index(search_service_endpoint, admin_key, index_name, fields)
            index_drive_folder(item.SHAREPOINT_DRIVE_ID, item.ACCESS_TOKEN)
            
            return {"drive_items": drive_items}
        else:
            raise HTTPException(status_code=400, detail="Drive ID is required for 'drive' configuration.")
    elif item.configuration == "pages":
        raise HTTPException(status_code=400, detail="Pages configuration not implemented yet.")
    else:
        raise HTTPException(status_code=400, detail="Invalid configuration type. Must be 'list', 'drive', or 'pages'.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)