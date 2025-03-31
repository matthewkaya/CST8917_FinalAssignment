import io
import os
import uuid
import logging
import json
import datetime
import azure.functions as func

from azure.storage.blob import BlobServiceClient
from config.azure_config import get_azure_config, get_mongo_collection
from config.jwt_utils import verify_jwt
from PIL import Image

def authenticate_request(req):
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return None, "Missing Authorization Header"
    
    token = auth_header.replace("Bearer ", "")
    is_valid, result = verify_jwt(token)
    if not is_valid:
        return None, result  # result contains error message
    return result, None  # result is userId

# HTTP Trigger – Image Upload
def upload_image(req):
    logging.info("upload_image function started")

    try:
        token = req.headers.get("Authorization", "").replace("Bearer ", "")
        logging.info(f"Extracted JWT token: {token[:10]}...")

        is_valid, userId = verify_jwt(token)  
        if not is_valid:
            logging.warning("Invalid or expired JWT token.")
            return {"status": 401, "body": "Unauthorized (invalid or expired token)."}

        logging.info(f"JWT verified. userId: {userId}")

        image_file = req.files.get("image")
        if not image_file:
            logging.error("Image file not provided.")
            return {"status": 400, "body": "Image file is required."}

        config = get_azure_config()
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])

        container_name = "user-images"
        blob_name = f"{userId}/{image_file.filename}"
        container_client = blob_service_client.get_container_client(container_name)
        container_client.upload_blob(name=blob_name, data=image_file.stream, overwrite=True)

        logging.info("Image uploaded to Blob Storage.")

        image_id = str(uuid.uuid4())
        original_image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}"

        image_doc = {
            "imageId": image_id,
            "imageName": image_file.filename,
            "originalImageUrl": original_image_url,
            "resizedImageUrl": None,
            "uploadDate": datetime.datetime.utcnow().isoformat()
        }

        users_col = get_mongo_collection("Users")
        result = users_col.update_one(
            {"userId": userId},  # ← shard key
            {"$push": {"uploadedImages": image_doc}}
        )

        if result.modified_count == 0:
            logging.warning("No matching user document found or updated.")

        response = {
            "imageId": image_id,
            "imageName": image_file.filename,
            "originalImageUrl": original_image_url,
            "uploadDate": image_doc["uploadDate"]
        }

        logging.info("Image metadata stored in MongoDB.")
        return {"status": 200, "body": json.dumps(response)}

    except Exception as e:
        logging.exception("Error occurred in upload_image")
        return {"status": 500, "body": f"Server error: {str(e)}"}
    
from config.sas_utils import generate_sas_url  
# Blob Trigger – Resize Image
def resize_image(blob: func.InputStream, userId: str, name: str):
    try:
        logging.info(f"Resizing image for userId: {userId}, file: {name}")

        if "_resized" in name:
            logging.info(f"Skipping already resized image: {name}")
            return

        config = get_azure_config()
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])

        # Orijinal resmi oku
        image_data = blob.read()
        image = Image.open(io.BytesIO(image_data))
        resized = image.resize((300, 300))

        # Buffer'a kaydet
        resized_buffer = io.BytesIO()
        resized.save(resized_buffer, format=image.format)
        resized_buffer.seek(0)

        # Blob'a yükle
        container_name = "user-images"
        resized_filename = f"{name.split('.')[0]}_resized.{name.split('.')[-1]}"
        resized_blob_path = f"{userId}/{resized_filename}"

        resized_blob_client = blob_service_client.get_blob_client(container=container_name, blob=resized_blob_path)
        resized_blob_client.upload_blob(resized_buffer, overwrite=True)

        # SAS URL üret
        secure_url = generate_sas_url(container_name, resized_blob_path)

        # MongoDB güncelle
        users_col = get_mongo_collection("Users")
        users_col.update_one(
            {"userId": userId, "uploadedImages.imageName": name},
            {"$set": {"uploadedImages.$.resizedImageUrl": secure_url}}
        )

        logging.info(f"Resized image uploaded and SAS URL generated: {secure_url}")

        # Mail bildirimi gönder
        user = users_col.find_one({"userId": userId})
        if user and "email" in user:
            send_resize_notification_to_queue(
                userId,
                name,
                user["email"],
                secure_url
            )

    except Exception as e:
        logging.error(f"[Resize Error] {str(e)}")

# Azure Service Bus 
from azure.servicebus import ServiceBusClient, ServiceBusMessage

def send_resize_notification_to_queue(userId, imageName, email, resizedImageUrl):
    try:
        config = get_azure_config()
        queue_name = config["SERVICE_BUS_QUEUE_NAME"]
        connection_str = config["SERVICE_BUS_CONNECTION_STRING"]

        servicebus_client = ServiceBusClient.from_connection_string(conn_str=connection_str)
        sender = servicebus_client.get_queue_sender(queue_name=queue_name)

        message = ServiceBusMessage(json.dumps({
            "userId": userId,
            "imageName": imageName,
            "email": email,
            "resizedImageUrl": resizedImageUrl  
        }))

        sender.send_messages(message)
        sender.close()
        servicebus_client.close()

        logging.info(f"Notification message queued for {email}")

    except Exception as e:
        logging.error(f"[Queue Error] {str(e)}")