import os
# from extraction.extraction import ExtractionData
# from fileshare.indexation import IndexationProcessing
import uuid
import logging
from pydantic import BaseModel

from extractors.formats.execelExtractor import ExecelExtractor
from extractors.formats.csvExtractor import CsvExtractor
from extractors.formats.docxExtractor import DocxExtractor
from extractors.formats.imageExtractor import ImageExtractor
from extractors.formats.jsonExtractor import JsonExtractor
from extractors.formats.pdfExtractor import PdfExtractor
from extractors.formats.presentationExtractor import PresentationExtractor
from extractors.formats.textExtractor import TextExtractor
class FileShare:
    class Inputschema(BaseModel):
        InputStream: str
    def __init__(self,config):
        self.local_directory =config['local_directory']
    
        # self.indexing=IndexationProcessing(config)

    
    def list_files(self):
            # List all files in the local directory
            return [os.path.join(self.local_directory, file_name) for file_name in os.listdir(self.local_directory) if os.path.isfile(os.path.join(self.local_directory, file_name))]
    def get_file_extension(self,file_name):
            return os.path.splitext(file_name)[1].lower()
    def read_file_content(self,file_path):
            """Read the file content in binary mode."""
            with open(file_path, 'rb') as file:
                return file.read()
    def process(self):
            file_names = self.list_files()
            results = []

            for file_name in file_names:
             try:
                file_content = self.read_file_content(file_name)
                file_extension = self.get_file_extension(file_name)
                chunks = []

                # Handle different file types
                if file_extension == ".pdf":
                    chunks = PdfExtractor.process_pdf(file_content)  # Ensure method can handle binary data
                elif file_extension in [".docx", ".doc"]:
                    chunks = DocxExtractor.process_docx(file_content)  # Ensure method can handle binary data
                elif file_extension == ".json":
                    # Decode JSON files from binary to text
                    file_content = file_content.decode('utf-8')
                    chunks = JsonExtractor.process_json(file_content)
                elif file_extension in [".pptx", ".ppt"]:
                    chunks = PresentationExtractor.process_ppt(file_content)  # Ensure method can handle binary data
                elif file_extension in [".xlsx", ".xls"]:
                    chunks = ExecelExtractor.process_xlsx(file_content)  # Ensure method can handle binary data
                elif file_extension== ".csv":
                    chunks=CsvExtractor.extract_content(file_content)
                elif file_extension == ".txt":
                    # Decode text files from binary to text
                    file_content = file_content.decode('utf-8')
                    chunks = TextExtractor.process_txt(file_content)
                elif file_extension in [".jpg", ".jpeg", ".png"]:
                    chunks = ImageExtractor.process_image(file_content)  # Ensure method can handle binary data
                else:
                    logging.warning(f"Unsupported file format: {file_extension}")
                    continue

                # Iterate over chunks and index each document
                for chunk_number, chunk in enumerate(chunks, 1):
                    document = {
                        "id": str(uuid.uuid4()),  # Generate unique ID
                        "content": chunks,  # Chunk of text from the document
                        # "contentEmbeddings": [],  # Placeholder for embeddings
                        "file_name": file_name,
                    }
                self.indexing.index_documents(document)

             except Exception as e:
                logging.error(f"An error occurred while processing document '{file_name}': {e}")
