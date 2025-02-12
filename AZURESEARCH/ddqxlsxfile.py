import pandas as pd
from datetime import datetime
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchField, HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration, VectorSearchProfile,SearchableField,SearchFieldDataType,SemanticConfiguration,SemanticPrioritizedFields,SemanticField,SemanticSearch
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


service_endpoint = ""
admin_key = ""
index_name = "DDQxlsx"
file_path = r"C:\Users\ravichandrav\Downloads\CCL_QnA_Final.xlsx"
# Define Azure OpenAI configuration
azure_openai_endpoint = "" # Your Azure OpenAI endpoint
azure_openai_key = "" # Your Azure OpenAI key
azure_openai_embedding_deployment = "text-embedding-ada-002"
embedding_model_name = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"
def create_index(service_endpoint, admin_key, index_name):
    # Define index schema
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SimpleField(name="Title", type="Edm.String"),
        SearchableField(name="question", type="Edm.String"),  # Alias name for field_0
        SearchableField(name="answer", type="Edm.String"),  # Alias name for field_1
        SearchField(name="ContentEmbeddings", type="Collection(Edm.Single)",searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
        
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

def read_excel_data(file_path):
    try:
        # Read data from Excel file
        excel_data = pd.read_excel(file_path)
        return excel_data
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return None

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

        index_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

        for document in all_documents:
           

            # Concatenate question and answer into a single string
            
            document = {
                "id": document['id'],
                "question": str(document.get('field_0', '')),
                "answer": str(document.get('field_1', '')),
                "ContentEmbeddings": [] ,# Initialize both question and answer embedding field
                
               
                
            }
    
            # # Get the content from the document
            # answerembed = document.get('answer', '')  
            # questionembed = document.get('question', '')

            # # Concatenate question and answer into a single string
            # combined_text = questionembed + "-" + answerembed
            # # print("Combined text:", combined_text)
            # # Generate embeddings for combined text
            try:
                # Generate embeddings for combined text
                combined_response = client.embeddings.create(input="question", model="text-embedding-ada-002")
                combined_embeddings = combined_response.data[0].embedding
                
                # Convert embeddings to string format
                embeddings_str = [str(embedding) for embedding in combined_embeddings]
                
                # Store embeddings in the document
                document['combinedembeddings'] = embeddings_str
            
            except Exception as e:
                print("An error occurred during embedding generation:", e)

            try:
                index_client.upload_documents(documents=[document])
                print(f"Document '{document['id']}' indexed successfully.")
            except Exception as e:
                print(f"Failed to index document '{document['id']}': {str(e)}")
        
    except Exception as e:
        print(f"Failed to index documents to Azure Cognitive Search. Error: {str(e)}")

if __name__ == "__main__":
    try:
        # Create search index
        create_index(service_endpoint, admin_key, index_name)

        # Read data from Excel file
        excel_data = read_excel_data(file_path)
        
        if excel_data is not None:
            # Process Excel data into documents
            all_documents = []
            for index, row in excel_data.iterrows():
                document = {
                    "id": str(row['id']),  # Use a unique identifier from the Excel file
                    "field_0": str(row.get('field_0', '')),  
                    "field_1": str(row.get('field_1', '')),   
                    "Title": str(row.get('Title', '')),  
                    "Permissions": [],  # You may need to adjust this based on Excel data
                    "combinedembeddings": [],  # Initialize content embedding field
                    "webUrl": ""  # Initialize webUrl
                    # Add other fields to index as needed
                }
                all_documents.append(document)

            # Index documents into Azure Cognitive Search
            index_documents_to_azure_search(all_documents)
        else:
            print("No data retrieved from Excel file.")
    except Exception as e:
        print(f"Main process failed: {str(e)}")
