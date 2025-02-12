import chardet
from pydantic import BaseModel

class TextExtractor:
    class InputSchema(BaseModel):
        InputSchema:str
    def process_txt(txt_content):
        """Process and chunk text file content."""
        detected_encoding = chardet.detect(txt_content)
        encoding = detected_encoding['encoding'] or 'utf-8'
        text = txt_content.decode(encoding, errors='ignore')
        # chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        return text