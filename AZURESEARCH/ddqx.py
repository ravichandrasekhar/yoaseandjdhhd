import pandas as pd
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

import os  
import json  
from openai import AzureOpenAI
from dotenv import load_dotenv  
from tenacity import retry, wait_random_exponential, stop_after_attempt  
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient, SearchIndexingBufferedSender  
from azure.search.documents.indexes import SearchIndexClient  
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryCaptionResult,
    QueryAnswerResult,
    SemanticErrorMode,
    SemanticErrorReason,
    SemanticSearchResultsType,
    QueryType,
    VectorizedQuery,
    VectorQuery,
    VectorFilterMode,    
)
from azure.search.documents.indexes.models import (  
    ExhaustiveKnnAlgorithmConfiguration,
    ExhaustiveKnnParameters,
    SearchIndex,  
    SearchField,  
    SearchFieldDataType,  
    SimpleField,  
    SearchableField,  
    SearchIndex,  
    SemanticConfiguration,  
    SemanticPrioritizedFields,
    SemanticField,  
    SearchField,  
    SemanticSearch,
    VectorSearch,  
    HnswAlgorithmConfiguration,
    HnswParameters,  
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchProfile,
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    ExhaustiveKnnParameters,
    SearchIndex,  
    SearchField,  
    SearchFieldDataType,  
    SimpleField,  
    SearchableField,  
    SearchIndex,  
    SemanticConfiguration,  
    SemanticField,  
    SearchField,  
    VectorSearch,  
    HnswParameters,  
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)  

# Azure Search and Cognitive Services credentials
search_service_endpoint = ""
admin_key = ""

# Initialize Azure Search client
credential = DefaultAzureCredential()
search_client = SearchIndexClient(endpoint=search_service_endpoint, credential=credential)

# Read data from Excel file
excel_file_path = r"C:\Users\ravichandrav\Downloads\CCL_QnA_Final.xlsx"
df = pd.read_excel(excel_file_path)

# Extract questions and answers from the Excel DataFrame
questions = df["MDDQ Question"].tolist()
answers = df["Content Value"].tolist()

# Initialize OpenAI client
openai_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")

client = AzureOpenAI(
    azure_deployment="text-embedding-ada-002",
    api_version="2023-05-15",
    azure_endpoint="",
    api_key=""
)

# Generate embeddings for questions
question_embeddings = []
for question in questions:
    response = client.embeddings.create(input=[question], model="text-embedding-ada-002")
    embedding = response.data[0].embedding
    question_embeddings.append(embedding)

# Generate embeddings for questions
answer_embeddings = []
for answer in answers:
    response = client.embeddings.create(input=[answer], model="text-embedding-ada-002")
    embedding = response.data[0].embedding
    answer_embeddings.append(embedding)


# Create a search index
key = ""
# model: str = "text-embedding-ada-002" 
credential = AzureKeyCredential(key)
service_endpoint=""
index_client = SearchIndexClient(
    endpoint=service_endpoint, credential=credential)

# Configure the vector search configuration  
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

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True),
    SearchableField(name="Question", type=SearchFieldDataType.String),
    SearchableField(name="Answer", type=SearchFieldDataType.String),
    SearchField(name="question_embeddings", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
    SearchField(name="answer_embeddings", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
]

# Create the search index 
index = SearchIndex(name="indexname", fields=fields,vector_search=vector_search)
result = index_client.create_or_update_index(index)
print(f' {result.name} created')
# Upload documents with questions, answers, and embeddings to Azure Search
documents = []
for i in range(len(questions)):
    document = {
        # "@search.action": "upload",
        "id": str(i),
        "question": questions[i],
        "answer": answers[i],
        'question_embeddings': question_embeddings[i],
        'answer_embeddings':answer_embeddings[i]
    }
    documents.append(document)

    search_client = SearchClient(endpoint=service_endpoint, index_name="indexname", credential=credential)
    result = search_client.upload_documents(documents)