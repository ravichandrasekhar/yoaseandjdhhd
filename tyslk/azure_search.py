# azure_search_service.py
from typing import Any, Dict, List
from Services.Search.isearchservice import ISearchService

class AzureSearchService(ISearchService):
    DEFAULT_VECTOR_DIMENSION = 512  # Config-based default value if vector_dimension is missing

    def create_index(self, config: Dict[str, Any], additional_metadata: Dict[str, Any]) -> Dict[str, Any]:
        # Extract essential details from the config
        index_name = config.get("index_name")
        api_key = config.get("api_key")
        endpoint = config.get("endpoint")
        vector_dimension = config.get("vector_dimension", self.DEFAULT_VECTOR_DIMENSION)  # Default if not provided

        # Validate essential details
        missing_fields = []
        if not index_name:
            missing_fields.append("index_name")
        if not api_key:
            missing_fields.append("api_key")
        if not endpoint:
            missing_fields.append("endpoint")

        # Return error if essential details are missing
        if missing_fields:
            return {
                "status": "error",
                "message": f"Missing essential config fields: {', '.join(missing_fields)}",
                "error": True
            }

        print(f"Creating index: {index_name} with vector dimension {vector_dimension}")
        
        # Dynamically create index schema based on additional metadata
        index_schema = self._generate_index_schema(additional_metadata)
        print(f"Generated index schema: {index_schema}")
        
        # Placeholder code: Actual Azure Search API logic to create index
        # Logic to create index with provided schema in Azure Search
        print(f"Index {index_name} created successfully with schema: {index_schema}")

        return {
            "status": "success",
            "message": f"Index {index_name} created successfully",
            "error": None
        }
    
    def store_records(self, config: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Extract essential details from the config
        index_name = config.get("index_name")
        api_key = config.get("api_key")
        endpoint = config.get("endpoint")

        # Validate essential details
        missing_fields = []
        if not index_name:
            missing_fields.append("index_name")
        if not api_key:
            missing_fields.append("api_key")
        if not endpoint:
            missing_fields.append("endpoint")

        # Return error if essential details are missing
        if missing_fields:
            return {
                "status": "error",
                "message": f"Missing essential config fields: {', '.join(missing_fields)}",
                "error": True
            }

        print(f"Storing records in index: {index_name} at {endpoint}")
        
        # Process each record and push it to Azure Search
        for record in records:
            embeddings = record["embeddings"]
            metadata = record["metadata"]

            # Convert metadata types dynamically
            dynamic_metadata = self._process_metadata(metadata)
            print(f"Storing record with embeddings {embeddings} and metadata {dynamic_metadata}")
            
            # Placeholder code: Actual Azure Search API to store the records
            # Insert data into Azure Search

        return {
            "status": "success",
            "message": f"Records stored successfully in {index_name}",
            "error": None
        }

    def _generate_index_schema(self, additional_metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate the schema for the index based on the additional metadata types.
        """
        schema = {}
        for key, value in additional_metadata.items():
            schema[key] = self._infer_type(value)
        return schema

    def _infer_type(self, value: Any) -> str:
        """
        Infers the type of the metadata value to define the schema.
        """
        if isinstance(value, str):
            return "Edm.String"
        elif isinstance(value, int):
            return "Edm.Int32"
        elif isinstance(value, float):
            return "Edm.Double"
        elif isinstance(value, list):
            return "Collection(Edm.String)"  # Assuming it's a collection of strings for simplicity
        elif isinstance(value, dict):
            return "ComplexType"  # Placeholder for complex objects, needs more detail
        else:
            return "Edm.String"  # Default type if unsure

    def _process_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically process metadata by inferring types and ensuring correct formatting.
        """
        processed_metadata = {}
        for key, value in metadata.items():
            processed_metadata[key] = self._infer_value(value)
        return processed_metadata

    def _infer_value(self, value: Any) -> Any:
        """
        Infers the value and transforms it appropriately if needed (e.g., complex types).
        """
        if isinstance(value, dict):
            # Process nested dicts or complex objects
            return {k: self._infer_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            # Ensure lists are processed appropriately
            return [self._infer_value(v) for v in value]
        else:
            return value
