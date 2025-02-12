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


# Define Azure Cognitive Search configuration
service_endpoint = ""  # Your Azure Cognitive Search endpoint
admin_key = ""  # Your Azure Cognitive Search admin key
index_name = "hudsonsharepointlist"  # Name of your search index
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
    print("semantic config",semantic_config)
    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])
    print("semantic-search",semantic_search)
    
    index = SearchIndex(name=index_name, fields=index_fields,vector_search=vector_search,semantic_search=semantic_search)

    # Create index client
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

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




