import os
import datetime

from azure.storage.blob import BlobServiceClient
from config.azure_config import get_azure_config, get_mongo_collection

def scheduled_cleanup(timer_info):
    try:
        config = get_azure_config()
        blob_service_client = BlobServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )
        container_name = "user-images"
        container_client = blob_service_client.get_container_client(container_name)

        # Get current UTC time
        now = datetime.datetime.utcnow()

        # Access MongoDB collection
        users_col = get_mongo_collection("Users")
        users = users_col.find({})

        for user in users:
            updated_images = []
            for image in user.get("uploadedImages", []):
                upload_date = datetime.datetime.fromisoformat(image["uploadDate"])
                age = now - upload_date

                # Check if image is older than 1 day
                if age.total_seconds() > 86400:
                    # Delete original and resized images from blob storage
                    try:
                        blob_name_original = f"{user['_id']}/{image['imageName']}"
                        blob_name_resized = f"{user['_id']}/{image['imageName'].split('.')[0]}_resized.{image['imageName'].split('.')[-1]}"
                        container_client.delete_blob(blob_name_original)
                        container_client.delete_blob(blob_name_resized)
                        print(f"Deleted blobs: {blob_name_original}, {blob_name_resized}")
                    except Exception as e:
                        print(f"Failed to delete blob(s): {str(e)}")
                else:
                    updated_images.append(image)

            # Update user document with only fresh images
            users_col.update_one(
                {"_id": user["_id"]},
                {"$set": {"uploadedImages": updated_images}}
            )

    except Exception as e:
        print(f"[Cleanup Error] {str(e)}")

import logging

def handle_error(error: Exception, context: dict = None):
    source = context.get("source", "Unknown")
    logging.exception(f"Error in {source}: {str(error)}")