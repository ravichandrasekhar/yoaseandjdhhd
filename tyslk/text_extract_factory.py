from Services.Text_Extraction.Azure_Service import AzureService
from typing import Dict, Any
from Services.Text_Extraction.Aws_Service import AwsService
from Services.Text_Extraction.Gcp_Service import GcpService
from Services.Text_Extraction.iText_Extraction import Text_Service
from Services.Text_Extraction.Opensource_Service import OpensourceService

import os
from typing import Dict, Any
from Factory.main_factory import INode
class TextExtractionFactory(INode):
    # Services available for text extraction
    _services = {
        "azure": AzureService(),
        # "gcp": GcpService(),
        "aws": AwsService(),
        "opensource": OpensourceService()
    }

    # @staticmethod
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the configuration for the selected text extraction service.
        Args:
            config (dict): Configuration for the service, including service type and settings.
        
        Returns:
            dict: Validation response, including success or failure status.
        """
        extract_type = config['type']
        
        # Check if the 'type' is provided
        if not extract_type:
            return {
                "status": "error",
                "message": "extract_type is missing",
                "error": True
            }

        # Normalize service type and check if it's supported
        extract_type = extract_type.strip().lower()
        extract_service = self._services.get(extract_type)
        
        if not extract_service:
            return {
                "status": "error",
                "message": f"Unsupported extract_type: {extract_type}",
                "error": True
            }
        
        # Validate the configuration using the appropriate service
        return extract_service.validate_config(config)

    # @staticmethod
    def create_service(self,text_extraction_type) -> Text_Service:
        """
        Create the appropriate service instance based on user-selected config.
        Args:
            config (dict): The configuration data containing service type and settings.
        
        Returns:
            Text_Service: An instance of the selected service.
        
        Raises:
            ValueError: If the service type is not supported.
        """
        service_type =text_extraction_type
        
        if not service_type:
            raise ValueError("Service type is required in configuration.")
        
        # Normalize and fetch the appropriate service instance
        service_type = service_type.strip().lower()
        extract_service: Text_Service = TextExtractionFactory()._services.get(service_type)
        
        if not extract_service:
            raise ValueError(f"Unsupported service type: {service_type}")

        # Optionally, pass the config to the service to initialize or validate specific settings
        # extract_service.configure(config) 
        return extract_service

    # @staticmethod
    #def process_text_extraction(config: Dict[str, Any], file_content: bytes) -> Dict[str, Any]:
    def process_node(self, input: Dict[str, Any]) -> Dict[str, Any]:
        print("Text extraction starting")

        text_extraction_type = os.getenv("TEXT_EXTRACTION_TYPE")
        if not text_extraction_type:
            return {
                "status": "error",
                "message": "Environment variable TEXT_EXTRACTION_TYPE is missing",
                "error": True
            }

        file_name = input.get("file_name", "")
        if not file_name:
            return {
                "status": "error",
                "message": "Input file_name is missing",
                "error": True
            }

        try:
            service = self.create_service(text_extraction_type)
            if 'file_bytes' in input:
                file_extension = f".{file_name.split('.')[-1]}"
                result = service.process(input["file_bytes"], file_extension)

                if result.get("error"):
                    return {
                        "status": "error",
                        "message": "Error processing file in text extraction service",
                        "error": True,
                    }

                updated_record = input.copy()
                updated_record["text"] = result.get("extracted_text", "")
                updated_record.pop("file_bytes", None)

                return {
                    "status": "success",
                    "error": False,
                    "record": updated_record
                }

            elif 'text' in input:
                updated_record = input.copy()
                return {
                    "status": "success",
                    "error": False,
                    "record": updated_record
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing file: {str(e)}",
                "error": True,
            }