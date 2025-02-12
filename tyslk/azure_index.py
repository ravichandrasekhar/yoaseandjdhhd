from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models import (
    SimpleField, SearchableField, HnswAlgorithmConfiguration,
    VectorSearch, VectorSearchProfile, SearchField,
    SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch
)

class AzureIndex:
    def createIndex(self, service_endpoint, admin_key, index_name):
        # First check if the index exists
    

        # Define index schema
        index_fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="content", type="Edm.String"),
            SearchField(name="contentVector", type="Collection(Edm.Single)", searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
            SimpleField(name="fileName", type="Edm.String", sortable=True, facetable=True),
            SimpleField(name="page_number", type="Edm.Int32", sortable=True, facetable=True),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
            profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
        )

        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(content_fields=[SemanticField(field_name="content")])
        )

        semantic_search = SemanticSearch(configurations=[semantic_config])

        index = SearchIndex(name=index_name, fields=index_fields, vector_search=vector_search, semantic_search=semantic_search)

        # Create index client
        index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

        try:
         if index_client.get_index(index_name):
          print(f"Index '{index_name}' exists. Deleting... ")
          index_client.delete_index(index_name)
          print("Deleted.")
        except Exception as e:
          print(f"Index '{index_name}' does not exist or other error: {e}")
        try:
            print(f"Creating index '{index_name}'...")
            index_client.create_index(index)
            print(f"Index '{index_name}' has been created successfully.")
        except Exception as e:
            print(f"Error creating index '{index_name}': {e}")


    
    def index_document_to_azure_search(self, document, service_endpoint, admin_key, index_name):
        try:
            search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))
            search_client.upload_documents(documents=[document])
            print(f"Document '{document['id']}' indexed successfully.")
        except Exception as e:
            print(f"Error indexing document '{document['id']}': {str(e)}")
