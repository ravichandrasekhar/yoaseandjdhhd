import io
import fitz
from azure.storage.blob import BlobServiceClient

def download_pdf_from_blob(storage_connection_string, container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    pdf_content = blob_client.download_blob().readall()
    return pdf_content

def convert_pdf_to_chunks(pdf_content, chunk_size):
    chunks = []
    doc = fitz.open(stream=io.BytesIO(pdf_content))
    for page in doc:
        page_content = page.get_text()
        page_chunks = [page_content[i:i+chunk_size] for i in range(0, len(page_content), chunk_size)]
        chunks.extend(page_chunks)
    return chunks

def list_pdf_blobs(storage_connection_string, container_name):
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return [blob.name for blob in blob_list if blob.name.endswith('.pdf')]

def main():
    storage_connection_string = ""
    container_name = ""
    chunk_size = 8000

    pdf_blobs = list_pdf_blobs(storage_connection_string, container_name)

    for blob_name in pdf_blobs:
        pdf_content = download_pdf_from_blob(storage_connection_string, container_name, blob_name)
        chunks = convert_pdf_to_chunks(pdf_content, chunk_size)
        
        # Do something with the chunks, e.g., print them
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1} of {blob_name}: {chunk}")

if __name__ == "__main__":
    main()
