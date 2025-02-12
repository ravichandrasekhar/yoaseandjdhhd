import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration, VectorSearchProfile, SearchField, SearchFieldDataType, SemanticConfiguration, SemanticPrioritizedFields, SemanticField, SemanticSearch
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import time
# Global variable to store the last synchronization time
last_sync_time = None
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
        SearchField(name="combinedembeddings", type="Collection(Edm.Single)",searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
        SearchableField(name="combinedtext",type="SearchFieldDataType.String"),
        SimpleField(name="webUrl",type="Edm.String")          
        
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
        content_fields=[SemanticField(field_name="combinedtext")]
    )
)
    print("semantic config",semantic_config)
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

# Function to get data from SharePoint list using list ID
def get_sharepoint_list_data(list_id):
    try:
        # Define the fields to be expanded and indexed
        fields_to_expand_and_index = ["Title", "field_0", "field_1"]

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

def index_documents_to_azure_search(all_documents, service_endpoint, admin_key, index_name):
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

        client_search = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))
        
        # Retrieve existing document IDs from the search index
        existing_document_ids = set()
        result = client_search.search(search_text="*", top=1000)  # Adjust 'top' as per your index size
        for doc in result:
            existing_document_ids.add(doc["id"])
            
        # Track processed document IDs
        processed_document_ids = set()

        for document in all_documents:
            document_id = document['id']

            # Check if the document is already processed
            if document_id in processed_document_ids:
                continue

            # Get the content from the document
            answerembed = document.get('answer', '')  
            questionembed = document.get('question', '')

            # Concatenate question and answer into a single string
            combined_text = questionembed + "-" + answerembed

            # Generate embeddings for combined text
            try:
                # Generate embeddings for combined text
                combined_response = client.embeddings.create(input=combined_text, model="text-embedding-ada-002")
                combined_embeddings = combined_response.data[0].embedding
                
                # Convert embeddings to string format
                embeddings_str = [str(embedding) for embedding in combined_embeddings]
                
                # Store embeddings in the document
                document['combinedembeddings'] = embeddings_str
            
            except Exception as e:
                print("An error occurred during embedding generation:", e)

            try:
                # Upload document to Azure Cognitive Search if it's not in the existing index
                if document_id not in existing_document_ids:
                    document_to_upload = {
                        "id": document_id,
                        "Title": str(document.get('Title', '')),
                        "question": str(document.get('field_0', '')),
                        "answer": str(document.get('field_1', '')),
                        "combinedtext": combined_text,
                        "Permissions": document.get('Permissions', []),
                        "combinedembeddings": document.get('combinedembeddings', []),
                        "webUrl": document['webUrl']
                    }

                    client_search.upload_documents(documents=[document_to_upload])
                    print(f"Document '{document['id']}' indexed successfully.")
                else:
                    # Document exists, check for changes
                    existing_document = client_search.get_document(key=document_id)
                    existing_combined_text = existing_document["combinedtext"]
                    if combined_text != existing_combined_text:
                        # Update document in Azure Cognitive Search
                        document_to_update = {
                            "id": document_id,
                            "Title": str(document.get('Title', '')),
                            "question": str(document.get('field_0', '')),
                            "answer": str(document.get('field_1', '')),
                            "combinedtext": combined_text,
                            "Permissions": document.get('Permissions', []),
                            "combinedembeddings": document.get('combinedembeddings', []),
                            "webUrl": document['webUrl']
                        }
                        client_search.upload_documents(documents=[document_to_update])
                        print(f"Document '{document['id']}' updated successfully.")
                
                # Add document ID to the processed set
                processed_document_ids.add(document_id)

            except Exception as e:
                print(f"Failed to index document '{document['id']}': {str(e)}")

        # Check for documents in the search index that are not present in the SharePoint list and delete them
        for doc_id in existing_document_ids - processed_document_ids:
            try:
                client_search.delete_document(key=doc_id)
                print(f"Document '{doc_id}' deleted successfully.")
            except Exception as e:
                print(f"Failed to delete document '{doc_id}': {str(e)}")

    except Exception as e:
        print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")

def synchronize_sharepoint_data():
    global last_sync_time

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
                    # Ensure correct property names
                    "field_0": str(item.get('fields', {}).get('field_0', '')),  # Using _x0048_1 instead of H1
                    "field_1": str(item.get('fields', {}).get('field_1', '')),   
                    "Title": str(item.get('fields', {}).get('Title', '')),  
                    "Permissions": get_item_permissions(item['id']),
                    "combinedembeddings": [] ,
                    "webUrl":item['webUrl']  # Initialize content embedding field
                    # Add other fields to index as needed
                }
                all_documents.append(document)

            # Index only updated or new documents into Azure Cognitive Search
            index_documents_to_azure_search(all_documents, service_endpoint, admin_key, index_name)
        else:
            print("No data retrieved from SharePoint list.")
    else:
        print("Failed to retrieve list ID from SharePoint site.")

    # Update last synchronization time
    last_sync_time = time.time()

if __name__ == "__main__":
    try:
        # Create search index
        create_index(service_endpoint, admin_key, index_name)

        while True:
            # Synchronize SharePoint data if last synchronization time is None or more than 1 hour has passed
            if last_sync_time is None or time.time() - last_sync_time >= 3600:
                synchronize_sharepoint_data()

            # Sleep for a certain period before the next synchronization
            time.sleep(60)  # Sleep for 1 minute

    except Exception as e:
        print(f"Main process failed: {str(e)}")