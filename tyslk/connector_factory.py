import os
from typing import Dict, Any
from dotenv import load_dotenv  # type: ignore # Import dotenv to load environment variables
# from ..Connectors.sharepoint_connector import SharepointConnector
from Services.Connectors.csv_connector import CsvConnector
from Services.Connectors.iconnectorservice import IConnector
from Services.Connectors.outlook_connector import OutlookConnector
from Services.Connectors.sharepoint_connector import SharepointConnector
from Services.Connectors.postgres_connector import PostgresConnector
from Services.Connectors.iconnectorservice import IConnector
import os
from .main_factory import INode
# Load environment variables from the .env file
load_dotenv()

class ConnectorFactory(INode):
    _services= {
            "sharepoint": SharepointConnector(),  # Initialize SharePoint connector,
            "csv":CsvConnector(),
            "postgres":PostgresConnector(),
            "outlook":OutlookConnector()
        }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the configuration for the selected search service.
        Args:
            config (dict): Configuration for the service, including service type and settings.

        Returns:
            dict: Validation response, including success or failure status.
        """
        service_type:str = config['type']
        service_type = service_type.strip().lower()
        extract_service: IConnector = ConnectorFactory()._services.get(service_type)
        
        if not extract_service:
            return {
                "status": "error",
                "message": f"Unsupported extract_type: {service_type}",
                "error": True
            }
        
        # Validate the configuration using the appropriate service
        return extract_service.validate_config(config)
    
    def process_node(self, Pipeline_Instance):
        print("connector node starting")
        service_type:str =os.getenv("CONNECTOR_TYPE")
        service_type = service_type.strip().lower()
        extract_service: IConnector = self._services.get(service_type)
        
        if not extract_service:
            return {
                "status": "error",
                "message": f"Unsupported extract_type: {service_type}",
                "error": True
            }
        
        return extract_service.fetch_data(Pipeline_Instance)