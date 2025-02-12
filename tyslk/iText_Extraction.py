from abc import ABC, abstractmethod
from typing import Any, Dict, List
class Text_Service(ABC):
    @abstractmethod
    def validate_config(self):
        pass
    
    @abstractmethod
    def process(self, file_content, file_extension,metadata):
        pass