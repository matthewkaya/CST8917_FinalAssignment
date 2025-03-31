import logging
import json
import azure.functions as func
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import Device
from config.azure_config import get_azure_config, get_mongo_collection

config = get_azure_config()
collection = get_mongo_collection("Devices")

def get_registred_devices(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("[get_registered_devices] Fetching registered devices with query parameters...")

    try:
        device_id = req.params.get("device_id")
        sensor_type = req.params.get("sensor_type")
        location = req.params.get("location")

        query = {}
        if device_id:
            query["device_id"] = device_id
        if sensor_type:
            query["sensor_type"] = sensor_type
        if location:
            query["location"] = location

        logging.info(f"[get_registered_devices] Query: {query}")

        collection = get_mongo_collection("Devices")
        devices = list(collection.find(query, {"_id": 0}))  # _id hariç getir

        return func.HttpResponse(
            json.dumps(devices),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[get_registered_devices] Error: {str(e)}")
        return func.HttpResponse(
            "Failed to retrieve registered devices.",
            status_code=500
        )

def register_device(data: dict):
    device_id = data.get("device_id")
    userId = data.get("userId")

    if not device_id or not userId:
        raise ValueError("Both 'device_id' and 'userId' are required.")

    registry_manager = IoTHubRegistryManager(config["IOTHUB_CONNECTION_STRING"])

    try:
        registry_manager.get_device(device_id)
        logging.info(f"Device '{device_id}' already exists in IoT Hub for user '{userId}'.")
    except Exception:
        registry_manager.create_device_with_sas(device_id, "", "", "enabled")
        logging.info(f"Device '{device_id}' created in IoT Hub for user '{userId}'.")

    collection.insert_one(data)
    logging.info(f"Device '{device_id}' registered in MongoDB for user '{userId}'.")

# Function: Delete Device
def delete_device(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("[delete_device] Starting device deletion process.")
    device_id = req.params.get("device_id")

    if not device_id:
        return func.HttpResponse("Missing 'device_id' parameter.", status_code=400)

    try:
        # Delete from IoT Hub
        registry_manager = IoTHubRegistryManager(config["IOTHUB_CONNECTION_STRING"])
        registry_manager.delete_device(device_id)
        logging.info(f"[delete_device] Device '{device_id}' deleted from IoT Hub.")

        # Delete from Cosmos DB
        collection = get_mongo_collection("Devices")
        result = collection.delete_one({"device_id": device_id})
        logging.info(f"[delete_device] Deleted {result.deleted_count} document(s) from Cosmos DB for device_id '{device_id}'.")

        return func.HttpResponse(f"Device '{device_id}' deleted successfully.", status_code=200)

    except Exception as e:
        logging.error(f"[delete_device] Error: {str(e)}")
        return func.HttpResponse(f"Error deleting device: {str(e)}", status_code=500)

def validate_device_data(data: dict) -> bool:
    required_fields = {
        "device_id": str,
        "sensor_type": str,
        "timestamp": str,
        "value": (int, float, dict)
    }
    for field, expected_type in required_fields.items():
        if field not in data or not isinstance(data[field], expected_type):
            logging.warning(f"Validation failed: '{field}' missing or invalid type in data: {data}")
            return False
    logging.info("Telemetry data validation succeeded.")
    return True    