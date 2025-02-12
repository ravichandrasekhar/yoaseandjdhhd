from abc import ABC, abstractmethod
from typing import List

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """Abstract method to chunk text based on strategy."""
        pass
    
    def validate_config(self, config):
        """
        Validates if the configuration provided is valid for the connector.
        :param config: The configuration settings to be validated
        """
        pass

