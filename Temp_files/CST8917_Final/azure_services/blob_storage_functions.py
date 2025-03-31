from azure.storage.blob import BlobServiceClient
import uuid
from config.azure_config import BLOB_STORAGE_CONNECTION_STRING, BLOB_CONTAINER_NAME

class BlobStorageService:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(BLOB_STORAGE_CONNECTION_STRING)
        self.container_client = self.blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

    def upload_image(self, image_bytes: bytes, filename: str = None) -> str:
        if not filename:
            filename = f"{uuid.uuid4()}.jpg"
        blob_client = self.container_client.get_blob_client(filename)
        blob_client.upload_blob(image_bytes, overwrite=True)
        return blob_client.url