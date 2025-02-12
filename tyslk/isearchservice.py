# isearch_service.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class ISearchService(ABC):
    @abstractmethod
    def create_index(self, config: Dict[str, Any], dimensions: int, additional_metadata: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    def store_records(self, config: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def retrieve_records(self, config: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass
