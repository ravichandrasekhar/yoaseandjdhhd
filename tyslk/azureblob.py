from fastapi import FastAPI, HTTPException
from azure.storage.blob import BlobServiceClient
import os
import requests
import re
from datetime import datetime, timezone, timedelta
import logging
import uuid

from extractors.formats.docxExtractor import DocxExtractor
from extractors.formats.execelExtractor import ExecelExtractor
from extractors.formats.imageExtractor import ImageExtractor
from extractors.formats.jsonExtractor import JsonExtractor
from extractors.formats.pdfExtractor import PdfExtractor
from extractors.formats.presentationExtractor import PresentationExtractor
from extractors.formats.textExtractor import TextExtractor
# from extraction.extraction import ExtractionData
# from azureblob.indexation import IndexationProcess

chunk_size=8000
class AzureBlob:
  def __init__(self,config):
        self.blob_storage_connection_string =config['BLOB_STORAGE_CONNECTION_STRING']
        self.container_name=config['CONTAINER_NAME']
        # self.fileprocessor=ExtractionData
        # self.indexing=IndexationProcess(config)

    
  def download_file_from_blob(self,file_name):
    blob_service_client = BlobServiceClient.from_connection_string(self.blob_storage_connection_string)
    blob_client = blob_service_client.get_blob_client(container=self.container_name, blob=file_name)
    file_content = blob_client.download_blob().readall()
    return file_content
  def list_blobs(self, delta=False):
        # Create BlobServiceClient and get the container client
        blob_service_client = BlobServiceClient.from_connection_string(self.blob_storage_connection_string)
        container_client = blob_service_client.get_container_client(self.container_name)
        blob_list = container_client.list_blobs()

        # Get the current time and calculate the time 12 hours ago
        now = datetime.now(timezone.utc)
        twelve_hours_ago = now - timedelta(hours=12)
        
        filtered_blobs = []

        # Iterate through the blobs and filter based on the last modified time if delta is True
        for blob in blob_list:
            blob_name = blob.name
            last_modified = blob.last_modified

            if delta:
                # Filter blobs that have been modified within the last 12 hours
                if last_modified >= twelve_hours_ago:
                    filtered_blobs.append(blob)
            else:
                filtered_blobs.append(blob)

        return filtered_blobs
  def get_file_extension(self,file_name):
    return os.path.splitext(file_name)[1].lower()
  def process(self):
    file_names = self.list_blobs()

    results = []
    
    for file_name in file_names:
        try:
            file_content = self.download_file_from_blob(file_name)
            file_extension = self.get_file_extension(file_name)
            chunks = []

            if file_extension == ".pdf":
                chunks = PdfExtractor.process_pdf(file_content)
            elif file_extension in [".docx", ".doc"]:
                chunks = DocxExtractor.process_docx(file_content)
            elif file_extension == ".json":
                chunks = JsonExtractor.process_json(file_content)
            elif file_extension in [".pptx", ".ppt"]:
                chunks = PresentationExtractor.process_ppt(file_content)
            elif file_extension in [".xlsx", ".xls"]:
                chunks = ExecelExtractor.process_xlsx(file_content)
            elif file_extension == ".txt":
                chunks = TextExtractor.process_txt(file_content)
            elif file_extension in [".jpg", ".jpeg", ".png"]:
                chunks = ImageExtractor.process_image(file_content)
            else:
                logging.warning(f"Unsupported file format: {file_extension}")
                continue
            
            for chunk_number, chunk in enumerate(chunks, 1):
                    document = {
                        "id": str(uuid.uuid4()),  # Generate unique ID
                        "content": chunks,  # Chunk of text from the document
                        # "contentEmbeddings": [],  # Placeholder for embeddings
                        "blob_file_name": file_name,  # Use blob name for further processing if needed
                        # "page_number": chunk_number  # Page number
                    }
                
        
            print("file_content",chunks)
            self.indexing.index_documents(document)
                    
                
            
        except Exception as e:
            logging.error(f"An error occurred while processing document '{file_name}': {e}")
    
        

