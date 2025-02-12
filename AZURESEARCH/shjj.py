import requests
import pdfplumber
from docx import Document
import io
import openpyxl
import os
import csv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField
)
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

Site_url=""
ACCESS_TOKEN = "e"
SEARCH_ENDPOINT = ""
SEARCH_ADMIN_KEY = ""
SEARCH_INDEX_NAME = "sharepointfolder"
group_id = ""
azure_openai_endpoint = ""
azure_openai_key = ""
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version="2023-05-15"
def get_drive_id(site_url, access_token):
    # Extract hostname and site-relative path from the site URL
    parts = site_url.split('/')
    hostname = parts[2]  # This will be "mouritechpvtltd.sharepoint.com"
    site_path = '/'.join(parts[4:])  # This will be "sites/MTEnterpriseSearch"

    # Construct the Microsoft Graph API URL
    graph_url = f'https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_path}'
    print("Graph URL:", graph_url)

    # Headers with authorization
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    # Send GET request to retrieve site information
    response = requests.get(graph_url, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        site_info = response.json()
        site_id = site_info['id']
        print("Site ID:", site_id)
        
        # Construct the URL to get drives
        drive_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        print("Drive endpoint:", drive_endpoint)
        drive_response = requests.get(drive_endpoint, headers=headers)

        if drive_response.status_code == 200:
            drives_data = drive_response.json()["value"]
            if drives_data:
                # Print all drive IDs
                for drive in drives_data:
                    drive_id = drive["id"]
                    print("Drive ID:", drive_id)
                return drives_data  # Return all drive data
            else:
                print("No drives found.")
                return None
        else:
            print("Failed to retrieve drives information:", drive_response.text)
            return None
    else:
        print("Failed to retrieve site information:", response.text)
        return None


def get_sharepoint_items(access_token,SHAREPOINT_DRIVE_ID,site_url, folder_id=None,):
    if SHAREPOINT_DRIVE_ID:
        drive_id=get_drive_id(site_url, access_token)
    if folder_id:
        url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{folder_id}/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/root/children"
    headers = {
        "Authorization": "Bearer " + access_token, 
        "Accept": "application/json"
        }
    response = requests.get(url, headers=headers)
    data = response.json()
    return data

def download_sharepoint_file(file_id, access_token):
    content_url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(content_url, headers=headers)
    return response.content if response.status_code == 200 else None

def get_permissions(file_id, access_token):
    permissions_url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{file_id}/permissions"
    headers ={
        "Authorization": "Bearer " + access_token, 
        "Accept": "application/json"
        }
    response = requests.get(permissions_url, headers=headers)
    permissions = []
    if response.status_code == 200:
        for permission_data in response.json().get("value", []):
            granted_to = permission_data.get("grantedTo", {})
            user_or_group = granted_to.get("user", {}).get("displayName") or granted_to.get("group", {}).get("displayName")
            if user_or_group: permissions.append(user_or_group)
    return permissions

def get_group_members(group_id, access_token):
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

    else:
        print(f"Failed to retrieve the group members: {response.text}")

    return group_members
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
    try: return file_content.decode('utf-8')
    except UnicodeDecodeError: return str(file_content, errors='ignore')

def extract_text_from_csv(file_content):
    try:
        return " ".join(" ".join(row) for row in csv.reader(io.StringIO(file_content.decode('utf-8'))))
    except Exception as e:
        return f"Error extracting text from CSV file: {str(e)}"

def extract_text_from_other(file_content):
    return "Unsupported file type"

def index_folder_to_azure_search(folder_name, folder_id):
    client = SearchClient(endpoint=SEARCH_ENDPOINT,
                          index_name=SEARCH_INDEX_NAME,
                          credential=AzureKeyCredential(SEARCH_ADMIN_KEY))

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

def index_document_to_azure_search(file_name, file_content, file_id, permissions, group_members, web_url):
    file_extension = os.path.splitext(file_name)[1].lower()
    extractors = {".docx": extract_text_from_word, ".pdf": extract_text_from_pdf, ".txt": extract_text_from_text, ".xlsx": extract_text_from_excel, ".xls": extract_text_from_excel, ".csv": extract_text_from_csv}
    content_str = extractors.get(file_extension, extract_text_from_other)(file_content)
    
    try:
        openai_credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(azure_deployment=azure_openai_embedding_deployment, azure_endpoint=azure_openai_endpoint, api_key=azure_openai_key, azure_ad_token_provider=token_provider if not azure_openai_key else None, api_version=azure_openai_version)
        content_response = client.embeddings.create(input=content_str, model=embedding_model_name)
        combined_embeddings = content_response.data[0].embedding

        search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))
        document = {"id": str(file_id), "fileName": file_name, "content": content_str, "permissions": permissions, "accessList": [str(member) for member in group_members], "webUrl": web_url, "contentEmbeddings": combined_embeddings}
        search_client.upload_documents(documents=[document])
        print(f"Document '{file_name}' indexed successfully.")
    
    except Exception as e:
        print(f"Error indexing document '{file_name}': {str(e)}")

def index_sharepoint_items(access_token, parent_folder_id=None):
    items = get_sharepoint_items(access_token, parent_folder_id)
    for item in items:
        item_name, item_id, web_url = item['name'], item['id'], item['webUrl']
        if 'folder' in item:
            index_folder_to_azure_search(item_name, item_id)
            index_sharepoint_items(access_token, item_id)
        else:
            file_content = download_sharepoint_file(item_id, access_token)
            if file_content:
                permissions = get_permissions(item_id, access_token)
                group_members = get_group_members(group_id, ACCESS_TOKEN)
                index_document_to_azure_search(item_name, file_content, item_id, permissions, group_members, web_url)

def create_index():
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True, filterable=True, sortable=True),
        SearchableField(name="fileName", type="Edm.String", filterable=True),
        SimpleField(name="content", type="Edm.String", filterable=True),
        SimpleField(name="permissions", type="Collection(Edm.String)"),
        SimpleField(name="folderName", type="Edm.String"),
        SimpleField(name="accessList", type="Collection(Edm.String)", filterable=True),
        SimpleField(name="webUrl", type="Edm.String"),
        SearchField(name="contentEmbeddings", type="Collection(Edm.Single)", vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile")
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
    )
    index = SearchIndex(name=SEARCH_INDEX_NAME, fields=index_fields, vector_search=vector_search)
    client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))
    client.create_index(index)
    print("Index created successfully.")

def main():
    create_index()
    index_sharepoint_items(ACCESS_TOKEN, None)

if __name__ == "__main__":
    main()
