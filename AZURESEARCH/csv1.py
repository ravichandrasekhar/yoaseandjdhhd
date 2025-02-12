import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticPrioritizedFields, SemanticField,
    SemanticSearch
)
from openai import AzureOpenAI
from azure.identity import get_bearer_token_provider,DefaultAzureCredential


service_endpoint = ""
admin_key = ""
index_name = "ddqxlsx"
file_path = r"C:\Users\ravichandrav\Downloads\CCL_QnA_Final.xlsx"
# Define Azure OpenAI configuration
azure_openai_endpoint = "https://ngloflopenai.openai.azure.com/" # Your Azure OpenAI endpoint
azure_openai_key = "090c8f8e9f724b7eb47bf8a9e30db65b" # Your Azure OpenAI key
azure_openai_embedding_deployment = "text-embedding-ada-002"
azure_openai_version = "2023-05-15"

def create_index(service_endpoint, admin_key, index_name):
    index_fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="question", type="Edm.String"),  
        SearchableField(name="answer", type="Edm.String"),  
        SearchField(name="ContentEmbeddings", type="Collection(Edm.Single)", searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
    ]
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="myHnsw")
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
            content_fields=[
                SemanticField(field_name="question"),
                SemanticField(field_name="answer")
            ]
        )
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(name=index_name, fields=index_fields, vector_search=vector_search, semantic_search=semantic_search)
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

    try:
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception as e:
        print(f"Index '{index_name}' not found. Creating index...")
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")

def read_data(file_path):
    if file_path.endswith(".xlsx"):
        data = pd.read_excel(file_path)
    elif file_path.endswith(".csv"):
        data = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file format. Only CSV and XLSX files are supported.")
    return data

def index_documents_to_azure_search(all_questions, all_answers):
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

        for idx, (question, answer) in enumerate(zip(all_questions, all_answers)):
            document = {
                "id": str(idx),
                "question": str(question),
                "answer": str(answer),
                "ContentEmbeddings": []  # Initialize embeddings field
            }

            try:
                response = client.embeddings.create(input=question, model="text-embedding-ada-002")
                embeddings = response.data[0].embedding
                embeddings_str = [str(embedding) for embedding in embeddings]
                document['ContentEmbeddings'] = embeddings_str
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
        create_index(service_endpoint, admin_key, index_name)
        data = read_data(file_path)
        
        if data is not None:
            questions = data["MDDQ Question"].tolist()
            answers = data["Content Value"].tolist()
            if questions and answers:
                index_documents_to_azure_search(questions, answers)
            else:
                print("No data retrieved from file.")
        else:
            print("No data retrieved from file.")
    except Exception as e:
        print(f"Main process failed: {str(e)}")
