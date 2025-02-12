import io
import PyPDF2
from docx import Document
import os

class Processing:
    @staticmethod
    def get_file_extension(file_name):
        """Returns the file extension in lowercase."""
        return os.path.splitext(file_name)[1]

    @staticmethod
    def process_pdf(pdf_content):
        """Extracts text from PDF and returns it as a list of paragraphs."""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        chunks = []
        
        # Iterate through each page in the PDF
        for page in pdf_reader.pages:
            page_content = page.extract_text()
            
            if page_content:  # Check if there is content on the page
                # Split the page content into paragraphs based on double newlines
                paragraphs = page_content.split('\n\n')
                
                # Add paragraphs to chunks, avoiding empty paragraphs
                for paragraph in paragraphs:
                    if paragraph.strip():
                        chunks.append(paragraph.strip())
        
        return chunks

    @staticmethod
    def process_docx(docx_content):
        """Extracts text from DOCX and returns it as a list of non-empty paragraphs."""
        doc = Document(io.BytesIO(docx_content))
        paragraphs = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Avoid empty paragraphs
                paragraphs.append(paragraph.text)

        return paragraphs

    @staticmethod
    def process_file(file_content, file_extension):
        """Processes a file based on its extension and returns extracted text as chunks."""
        if file_extension == ".pdf":
            return Processing.process_pdf(file_content)
        elif file_extension in [".docx", ".doc"]:
            return Processing.process_docx(file_content)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
