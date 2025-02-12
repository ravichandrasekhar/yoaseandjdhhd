import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration, VectorSearchProfile,SearchableField,SearchFieldDataType,SemanticConfiguration,SemanticPrioritizedFields,SemanticField,SemanticSearch
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from datetime import datetime

# Define your client ID, client secret, and tenant ID for Azure Active Directory
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = "" 

# Define SharePoint site ID and list ID
SHAREPOINT_SITE_ID = ""
list_id = ""

# Define Azure Cognitive Search configuration
service_endpoint = ""  # Your Azure Cognitive Search endpoint
admin_key = ""  # Your Azure Cognitive Search admin key
index_name = "hudsonsharepointlist"  # Name of your search index

# Define Azure OpenAI configuration
azure_openai_endpoint = ""  # Your Azure OpenAI endpoint
azure_openai_key = ""  # Your Azure OpenAI key
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"
LOGIC_APP_ENDPOINT = "--"

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

def create_index(service_endpoint, admin_key, index_name):
    # Define index schema
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SimpleField(name="Title", type="Edm.String"),
        SearchableField(name="question", type="Edm.String"),  # Alias name for field_0
        SearchableField(name="answer", type="Edm.String"),  # Alias name for field_1
        SimpleField(name="permissions", type="Collection(Edm.String)"),
        SearchField(name="ContentEmbeddings", type="Collection(Edm.Single)",searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
        SearchableField(name="qanda",type="SearchFieldDataType.String"),
        SimpleField(name="webUrl",type="Edm.String"),
        SimpleField(name="modified_timestamp",type="Edm.DateTimeOffset")
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
    
    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="qanda")]
        )
    )
    
    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    index = SearchIndex(name=index_name, fields=index_fields,vector_search=vector_search,semantic_search=semantic_search)

    # Create index client
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

    try:
        # Check if the index exists
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception as e:
        print(f"Index '{index_name}' not found. Creating index...")
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")

def get_sharepoint_list_data_and_handle_deletions(list_id):
    try:
        # Define the fields to be expanded and indexed
        fields_to_expand_and_index = ["Title", "field_0", "field_1", "Modified"]

        # Construct the $select part of the URL
        select_fields = ','.join(fields_to_expand_and_index)

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
            if 'value' in data:
                sharepoint_items = data['value']
                return sharepoint_items
            else:
                print("No items found in the SharePoint list.")
                return []
        else:
            print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching data from SharePoint list: {str(e)}")
        return []

def handle_deleted_items(sharepoint_items, all_documents):
    try:
        azure_search_document_ids = [document['id'] for document in all_documents]
        for sharepoint_item in sharepoint_items:
            item_id = sharepoint_item.get('id')
            if item_id not in azure_search_document_ids:
                trigger_logic_app(item_id)
    except Exception as e:
        print(f"Error handling deleted items: {str(e)}")

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

def index_documents_to_azure_search(all_documents, service_endpoint, admin_key, index_name):
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

        client_search = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

        for document in all_documents:
            document_id = document['id']
            if is_document_updated_or_modified(document_id):
                modifiedtime = document.get('modified_timestamp')
                modified_timestamp = datetime.fromisoformat(modifiedtime[:-1]) if modifiedtime else None
                formatted_modified_timestamp = modified_timestamp.isoformat() + 'Z' if modified_timestamp else None
                document = {
                    "id": document_id,
                    "Title": str(document.get('Title', '')),
                    "question": str(document.get('field_0', '')),
                    "answer": str(document.get('field_1', '')),
                    "combinedtext":"",
                    "Permissions": document.get('Permissions', []),
                    "combinedembeddings": [],
                    "webUrl":document['webUrl'],
                    "modified_timestamp":formatted_modified_timestamp
                }

                answerembed = document.get('answer', '')  
                questionembed = document.get('question', '')

                combined_text = questionembed + "-" + answerembed
                document['combinedtext'] = combined_text

                try:
                    combined_response = client.embeddings.create(input=combined_text, model="text-embedding-ada-002")
                    combined_embeddings = combined_response.data[0].embedding
                    embeddings_str = [str(embedding) for embedding in combined_embeddings]
                    document['combinedembeddings'] = embeddings_str
                except Exception as e:
                    print("An error occurred:", e)

                try:
                    client_search.upload_documents(documents=[document])
                    print(f"Document '{document['id']}' indexed successfully.")
                except Exception as e:
                    print(f"Failed to index document '{document['id']}': {str(e)}")
            else:
                print(f"Document '{document_id}' is not updated or modified. Skipping indexing.")
    except Exception as e:
        print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")

def is_document_updated_or_modified(document_id):
    try:
        sharepoint_timestamp = get_sharepoint_document_timestamp_or_version(document_id)
        azure_search_timestamp = get_azure_search_document_timestamp_or_version(document_id)
        print(f"Document '{document_id}' has SharePoint timestamp '{sharepoint_timestamp}' and Azure Cognitive Search timestamp '{azure_search_timestamp}'")

        if sharepoint_timestamp > azure_search_timestamp:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking document update status: {str(e)}")
        return False

def get_sharepoint_document_timestamp_or_version(document_id):
    try:
        sharepoint_data = get_sharepoint_list_data_and_handle_deletions(list_id)

        for item in sharepoint_data:
            if item.get('id') == document_id:
                print(f"Document '{document_id}' found in the SharePoint list.")
                print("modiifed",item.get('fields', {}).get('Modified'))
                return item.get('fields', {}).get('Modified')
        else:
            print(f"Document '{document_id}' not found in the SharePoint list.")
            return None
    except Exception as e:
        print(f"Error fetching timestamp or version number from SharePoint for document '{document_id}': {str(e)}")
        return None

def get_azure_search_document_timestamp_or_version(document_id):
    try:
        search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))
        result = search_client.get_document(document_id)
        modified_timestamp = result.get("modified_timestamp")
        print(f"Document '{document_id}' has Azure Cognitive Search timestamp '{modified_timestamp}'")
        return modified_timestamp
    except Exception as e:
        print(f"Error fetching timestamp or version number from Azure Cognitive Search for document '{document_id}': {str(e)}")
        return None

def trigger_logic_app(item_id):
    try:
        # Implement your logic app trigger code here
        print(f"Triggering Logic App for deleted item with ID: {item_id}")
    except Exception as e:
        print(f"Error triggering Logic App: {str(e)}")
def trigger_logic_app(item_id):
    try:
        logic_app_endpoint = "<your-logic-app-endpoint>"
        payload = {
            "itemId": item_id
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(logic_app_endpoint, json=payload, headers=headers)
        
        if response.status_code == 200:
            print(f"Logic App triggered successfully for deleted item with ID: {item_id}")
        else:
            print(f"Failed to trigger Logic App for deleted item with ID: {item_id}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error triggering Logic App: {str(e)}")
# Create Azure Cognitive Search index
create_index(service_endpoint, admin_key, index_name)

# Get SharePoint list data and handle deletions
sharepoint_data = get_sharepoint_list_data_and_handle_deletions(list_id)

# Collect all documents
all_documents = []
for item in sharepoint_data:
    document = {
        "id": str(item['id']),
        "field_0": str(item.get('fields', {}).get('field_0', '')),  
        "field_1": str(item.get('fields', {}).get('field_1', '')),   
        "Title": str(item.get('fields', {}).get('Title', '')),  
        "Permissions": get_item_permissions(item['id']),
        "combinedembeddings": [],
        "webUrl": item['webUrl'],
        "modified_timestamp": item.get('fields', {}).get('Modified'),
    }
    all_documents.append(document)

# Index documents into Azure Cognitive Search
index_documents_to_azure_search(all_documents, service_endpoint, admin_key, index_name)
handle_deleted_items(sharepoint_data, all_documents)