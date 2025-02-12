from azure.search.documents import SearchClient
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery,QueryType,QueryCaptionType,QueryAnswerType
client = AzureOpenAI(
    azure_deployment="text-embedding-ada-002",
    api_version="2023-05-15",
    azure_endpoint="",
    api_key=""
)

# Define your Azure Cognitive Search endpoint and key
service_endpoint = ""
api_key = ""

# Initialize a SearchClient
credential = AzureKeyCredential(api_key)
search_client = SearchClient(endpoint=service_endpoint, index_name="hudsonsharepointlist", credential=credential)

# Pure Vector Search
query = "Provide a brief overview of the Firm, including information on the founding, subsequent history and information on any predecessor firm and/or parent firm."
embedding = client.embeddings.create(input=query, model="text-embedding-ada-002").data[0].embedding
vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=3, fields="ContentEmbeddings")
 
results = search_client.search(  

    search_text=query,  

    vector_queries=[vector_query],

    select=["id", "question", "answer","qanda"],

    query_type='semantic', semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,

    top=1

)

for result in results:

    print(f"id:{result['id']}")

    print(f"Title: {result['question']}")

    print(f"Score: {result['@search.score']}")

    print(f"Answer: {result['answer']}")