# blob_storage.py
from azure.storage.blob import BlobServiceClient

class BlobStorage():
    def container_list(self,storage_connection_string):
        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)

        # List containers
        try:
            containers = blob_service_client.list_containers()
            containers_list = [container.name for container in containers]
            if not containers_list:
                print("No containers found.")
            else:
                print("List of containers:", containers_list)
        except Exception as e:
            print(f"An error occurred: {e}")
    
        return containers_list


    def list_blobs(self,storage_connection_string, container_name):
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        return [blob.name for blob in container_client.list_blobs()]


    def download_file_from_blob(self,storage_connection_string, container_name, file_name):
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        return blob_client.download_blob().readall()
