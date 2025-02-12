import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField
from datetime import datetime

# Constants
SHAREPOINT_SITE_ID = ""
ACCESS_TOKEN = "."
SEARCH_ENDPOINT = ""
SEARCH_ADMIN_KEY = ""
SEARCH_INDEX_NAME = ""
list_id = ""
group_id = ""
def create_search_index():
    try:
        index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))

        # Define the index schema
        index = SearchIndex(
            name=SEARCH_INDEX_NAME,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True),
                SimpleField(name="EntryID", type="Edm.String"),
                SimpleField(name="H1", type="Edm.String"),  # Alias name for _x0048_1
                SimpleField(name="H2", type="Edm.String"),  
                SimpleField(name="H3", type="Edm.String"),  
                SimpleField(name="H4", type="Edm.String"),  
                SimpleField(name="Content", type="Edm.String", searchable=True),
                SimpleField(name="FileName", type="Edm.String"),
                SimpleField(name="groupMembers", type="Collection(Edm.String)"),
                SimpleField(name="permissions", type="Collection(Edm.String)")
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
        fields_to_expand_and_index = ["EntryID", "_x0048_1", "_x0048_2", "_x0048_3", "_x0048_4", "Content", "FileName"]

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


# Function to fetch group members
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


# Function to index documents into Azure Cognitive Search
def index_documents_to_azure_search(all_documents):
    try:
        
        client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))
        
        for document in all_documents:
            document = {
                "id": document['id'],
                "EntryID": str(document.get('EntryID', '')),
                "H1": str(document.get('_x0048_1', '')),  # Using AliasName instead of _x0048_1
                "H2": str(document.get('_x0048_2', '')),  
                "H3": str(document.get('_x0048_3', '')),  
                "H4": str(document.get('_x0048_4', '')),  
                "Content": document.get('Content', ''),
                "FileName": document.get('FileName', ''),
                "Permissions": document.get('Permissions', []),
                "GroupMembers": document.get('GroupMembers', [])
            }

            # Upload document to Azure Cognitive Search
            client.upload_documents(documents=[document])
            print(f"Document 'document' indexed successfully.")
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
                        "EntryID": item.get('fields', {}).get('EntryID', ''),
                        "_x0048_1": item.get('fields', {}).get('_x0048_1', ''),  # Using _x0048_1 instead of H1
                        "_x0048_2": item.get('fields', {}).get('_x0048_2', ''),  
                        "_x0048_3": item.get('fields', {}).get('_x0048_3', ''),  
                        "_x0048_4": item.get('fields', {}).get('_x0048_4', ''),  
                        "Content": item.get('fields', {}).get('Content', ''),
                        "FileName": item.get('fields', {}).get('FileName', ''),
                        "Permissions": get_item_permissions(item['id']),
                        "GroupMembers": get_group_members(group_id)  # Pass group ID or any other identifier here
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
