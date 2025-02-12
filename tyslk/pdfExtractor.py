import fitz
import io
from pydantic import BaseModel
class PdfExtractor:
    class InputSchema(BaseModel):
        pass
    def process_pdf(pdf_content):
        """Extract and chunk text from a PDF file."""
        doc = fitz.open(stream=io.BytesIO(pdf_content))
        page_content = ''
        for page in doc:
            page_content += page.get_text()
        return page_content