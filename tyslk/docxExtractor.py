from docx import Document
from pydantic import BaseModel
import io

class DocxExtractor:
    class InputSchema(BaseModel):
        InputSchema:str
    def process_docx(docx_content):
        """Extract and chunk text from a DOCX file."""
        doc = Document(io.BytesIO(docx_content))
        chunks = ''
        for paragraph in doc.paragraphs:
            chunks=chunks+paragraph.text

        return chunks
