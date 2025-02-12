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
import logging
logger = logging.getLogger(__name__)

class AzureIndex:
    def checkIndex(self, service_endpoint, admin_key, index_name):
        index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))
        try:
            # Check if the index exists
            index_client.get_index(index_name)
            logging.info(f"Index '{index_name}' already exists.")
            return True  # Index exists
        except Exception:
            logging.info(f"Index '{index_name}' not found.")
            return False  # Index does not exist
        

    def createIndex(self, service_endpoint, admin_key, index_name):
        # First check if the index exists
        if self.checkIndex(service_endpoint, admin_key, index_name):
            # If the index exists, do nothing
            return

        # Define index schema
        index_fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="content", type="Edm.String"),
            SearchField(name="content_embeddings", type="Collection(Edm.Single)", searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
            SimpleField(name="file_name", type="Edm.String", sortable=True, facetable=True),
            SimpleField(name="page_number", type="Edm.Int32", sortable=True, facetable=True),
            SearchField(name="application_name_embedding", type="Collection(Edm.Single)", searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),

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
            logging.info(f"Creating index '{index_name}'...")
            index_client.create_index(index)
            logging.info(f"Index '{index_name}' has been created successfully.")
        except Exception as e:
            logging.info(f"Error creating index '{index_name}': {e}")


    def deleteIndex(self, service_endpoint, admin_key, index_name):
        index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))
        try:
            index_client.delete_index(index_name)
            logging.info(f"Index '{index_name}' has been deleted.")
        except Exception as e:
            logging.info(f"Error deleting index '{index_name}': {e}")


    def index_document_to_azure_search(self, document, service_endpoint, admin_key, index_name):
        try:
            search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))
            search_client.upload_documents(documents=[document])
            logging.info(f"Document '{document['id']}' indexed successfully.")
        except Exception as e:
            logging.info(f"Error indexing document '{document['id']}': {str(e)}")