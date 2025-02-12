from pydantic import BaseModel
import json


class JsonExtractor:
    class InputSchema(BaseModel):
        inputSchema:str
    def process_json(json_content):
        """Pretty print and chunk JSON content."""
        data = json.loads(json_content)
        text = json.dumps(data, indent=4)
        return text
 