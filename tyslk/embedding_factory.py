from typing import Any, Dict
from Factory.main_factory import INode
from Services.Embeddings.IEmbedding_service import IEmbeddingService
from Services.Embeddings.gcp_embedding_service import GcpEmbeddingService
from Services.Embeddings.azure_embedding_service import AzureEmbeddingService
from Services.Embeddings.aws_embedding_service import AwsEmbeddingService
from Services.Embeddings.opensource_embedding_service import OpensourceEmbeddingService

 # type: ignore 
import os
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingFactory(INode):
    # Mapping of service type to the corresponding embedding service class
    service_type = {
        "gcp": GcpEmbeddingService(),
        "azure": AzureEmbeddingService(),
        "aws": AwsEmbeddingService(),
        "opensource": OpensourceEmbeddingService()
    }

    def get_embedding_service(self, service_type: str) -> IEmbeddingService:
        # Retrieve the service class from the dictionary, or raise an error if not found
        service_class = self.service_type.get(service_type)
       
        if service_class is None:
            raise ValueError(f"Invalid service_type: {service_type}")
        
        return service_class  
    

    def validate_config(self, config:Dict[str, Any]) -> Dict[str, Any]:
        
        """
        Validate the configuration of the embedding service based on the provided service type.
        """
        service_type = config['type']
        embedding_service = self.get_embedding_service(service_type)
        if not service_type:
            return {
            "status": "error",
            "message": f"Unsupported service_type{embedding_service}",
            "error": True
        }
        return embedding_service.validate_config(config)
    
    def process_node(self, record: dict):
        # Choose service type from environment 
        service_type = os.getenv("EMBEDDING_TYPE").strip()
        if not service_type:
            return {
                "status": "error",
                "message": "Environment variable EMBEDDING_TYPE  is missing",
                "error": True
            }
        print("embedding node is starting")

        embedding_service = self.get_embedding_service(service_type)
        chunks = record.get('chunks')
  
        try:
        # Generate embeddings with the chosen service
            embeddings=embedding_service.generate_embeddings(chunks)
        # Combine embeddings with metadata
            updated_record = record.copy()
            updated_record["embeddings"] = embeddings
            return {
                "status": "success",
                "record": updated_record,
                "error": None
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }

