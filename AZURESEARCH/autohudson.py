import datetime
import azure.cognitiveservices.search.entitysearch as entitysearch
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import Index, SimpleField, SearchableField 
import requests
# Azure Search credentials
search_service_endpoint = "..." 
search_index_name = "..."
search_admin_key = AzureKeyCredential(...)

# SharePoint list details
sharepoint_site = "..."
sharepoint_list_id = "..."

# Get last indexed timestamp
table_service = ""# Connect to Azure table storage
last_indexed = table_service.get_entity('index_state', 'sharepoint', 'last_indexed')

if not last_indexed:
    last_indexed = datetime.datetime(1900, 1, 1) 

# Build SharePoint query
filter_query = f"?$filter=LastModifiedDateTime ge {last_indexed}"
sharepoint_url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_site}/lists/{sharepoint_list_id}/items" + filter_query

# Get updated documents
updated_docs = requests.get(sharepoint_url, headers={...}).json()

# Index into Azure Search
search_client = SearchIndexClient(search_service_endpoint, search_admin_key)

for doc in updated_docs:
    # Map SharePoint fields to search index
    search_doc = {
        "id": doc["id"],
        "title": doc["title"], 
        "content": doc["content"]
    }
    
    search_client.upload_documents(documents=[search_doc])

# Update last indexed timestamp
last_indexed = datetime.datetime.now() 
table_service.update_entity('index_state', 'sharepoint', last_indexed, 'last_indexed')
