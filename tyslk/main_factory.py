from abc import ABC, abstractmethod

class INode(ABC):
    @abstractmethod
    def process_node(self, record: dict) -> dict:
        """
        Standard method to process a record.
        """
        pass
