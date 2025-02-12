import io
import PyPDF2
from docx import Document
import os
import re
class Processing:

    @staticmethod
    def get_file_extension(file_name):
        """Returns the file extension in lowercase."""
        return os.path.splitext(file_name)[1]

    @staticmethod
    def process_pdf(pdf_content):
        """
        Extracts text from a PDF and returns the extracted content as a single string.

        Args:
            pdf_content (bytes): PDF content in bytes.

        Returns:
            str: Extracted text content from the PDF or None if no content is found.
        """
        try:
            # Initialize the PDF reader
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            extracted_text = ""

            # Iterate through each page in the PDF
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                print(f"Page {i + 1} extracted.")

                if page_text:
                    extracted_text += page_text
                else:
                    print(f"Page {i + 1}: No text found (possibly scanned or image-based).")

            return extracted_text.strip() if extracted_text.strip() else None

        except Exception as e:
            print(f"Error processing PDF: {e}")
            return None

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
