from typing import Dict, Any
import uuid
import os
from Services.Search.aws_search import AwsSearchService
from Services.Search.azure_search import AzureSearchService
from Services.Search.elastic_search import ElasticSearchService
# from Services.Search.gcp_search import GcpSearchService
from Services.Search.isearchservice import ISearchService
from Factory.main_factory import INode
import json

class SearchFactory(INode):
    _services = {
        "elastic":ElasticSearchService(),
        "azure":AzureSearchService(),
         "aws":AwsSearchService(),
        # "gcp":GcpSearchService()
    }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the configuration for the selected search service.
        Args:
            config (dict): Configuration for the service, including service type and settings.

        Returns:
            dict: Validation response, including success or failure status.
        """
        service_type: str = config['type']
        service_type = service_type.strip().lower()
        extract_service: ISearchService = self._services.get(service_type)

        if not extract_service:
            return {
                "status": "error",
                "message": f"Unsupported extract_type: {service_type}",
                "error": True
            }

        # Validate the configuration using the appropriate service
        return extract_service.validate_config(config)

    def process_search_request(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method to process search requests and return the results.
        """
        search_type = os.getenv("SEARCH_TYPE")
        search_service = self._services.get(search_type)

        if not search_service:
            return {
                "status": "error",
                "message": f"Unsupported connector_type: {search_type}",
                "error": True
            }

        query = input_data.get("query", "")
        results = search_service.retrieve_records(query)
        return results

    def create_index(self, config: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        This method would be used to create an index, but it's not implemented here.
        """
        pass

    def process_node(self, record) -> Dict[str, Any]:
        """
        Stores records in the specified search service.
        """
        try:
            search_type = os.getenv("SEARCH_TYPE")
            search_service = self._services.get(search_type)

            if not search_service:
                return {
                    "status": "error",
                    "message": f"Unsupported connector_type: {search_type}",
                    "error": True
                }
            mapping_properties = os.getenv("FIELD_DEFINITIONS")
            if mapping_properties:
                mapping = json.loads(mapping_properties)
                
            embeddings = record.get("embeddings", [])
            chunks = record.get("chunks", [])
            del record["embeddings"]
            del record["chunks"]
            documents = []
            def get_value(record, field_name):
                fields = field_name.split(".")
                value = record
                for i in fields:
                    value = value.get(i, None)
                return value
            for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
                document = {
                    "id": str(uuid.uuid4()),
                    "embeddings": embedding,
                    "chunks": chunk
                }
                
                for i, mapping_properties in enumerate(mapping):
                    # print("properties_mapping_1",mapping_properties)
                    document[mapping_properties["Target_name"]] = get_value(record,mapping_properties["source_name"])
                documents.append(document)
            

            # Store filtered records
            result = search_service.store_records(documents)
            if not result:
                return {
                    "status": "failed",
                    "error": "Failed to store records",
                }

            return {
                "status": "success",
                "record": record,
                "error": None
            }
        except Exception as e:
            print(str(e))
            return {
                "status": "failed",
                "error": True,
                "message": str(e),
            }

    def retrieve_records(self, query: str) -> Dict[str, Any]:
        """
        Retrieves records from the specified search service based on the search query.
        """
        search_type = os.getenv("SEARCH_TYPE")
        search_service = self._services.get(search_type)

        if not search_service:
            return {
                "status": "error",
                "message": f"Unsupported connector_type: {search_type}",
                "error": True
            }

        # Retrieve records using the search service
        results = search_service.retrieve_records(query)
        return {
            "status": "success",
            "records": results
        }