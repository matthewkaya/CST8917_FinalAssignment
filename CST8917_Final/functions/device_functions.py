import json
import logging
import azure.functions as func
from config.jwt_utils import authenticate_user
from azure_services.cosmosdb_services import CosmosDBService
from azure_services.iot_hub_functions import IoTHubService

def register_device(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing register_device request.")
    
    # Authenticate the user
    user_id = authenticate_user(req)
    if isinstance(user_id, func.HttpResponse):  # Check if authentication failed
        return user_id
    
    # Parse the request body
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Validate required fields
    device_id = req_body.get("deviceId")
    device_name = req_body.get("deviceName")  # Optional field
    if not device_id:
        return func.HttpResponse("deviceId is required", status_code=400)
    
    # IoT Hub: Register the device
    try:
        iot_service = IoTHubService()
        iot_service.register_device_in_iot_hub(req_body)
    except Exception as e:
        logging.exception("Failed to register device in IoT Hub.")
        return func.HttpResponse(f"Failed to register device in IoT Hub: {str(e)}", status_code=500)
    
    # CosmosDB: Add the device to the user's Devices array
    cosmos_service = CosmosDBService()
    user = cosmos_service.find_document({"_id": user_id, "type": "user"})
    if not user:
        return func.HttpResponse("User not found in CosmosDB", status_code=404)
    
    # Prepare the device object
    device_object = {
        "deviceId": device_id,
        "deviceName": device_name,
        "telemetryData": []  # Initialize with an empty telemetryData array
    }
    
    # Update the user's Devices array
    result = cosmos_service.update_document(
        {"_id": user_id, "type": "user"},
        {"$push": {"Devices": device_object}}
    )
    if result.modified_count == 0:
        return func.HttpResponse("Failed to add device to user's Devices array", status_code=400)
    
    return func.HttpResponse(json.dumps({"message": "Device registered successfully"}), status_code=201, mimetype="application/json")

def get_devices(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing get_devices request.")
    
    # Authenticate the user
    user_id = authenticate_user(req)
    if isinstance(user_id, func.HttpResponse):  # Check if authentication failed
        return user_id
    
    # Fetch the user's devices from CosmosDB
    cosmos_service = CosmosDBService()
    user = cosmos_service.find_document({"_id": user_id, "type": "user"})
    if not user:
        return func.HttpResponse("User not found in CosmosDB", status_code=404)
    
    # Get the devices array from the user document
    devices = user.get("Devices", [])
    
    return func.HttpResponse(json.dumps(devices), status_code=200, mimetype="application/json")

def update_device(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing update_device request.")
    
    # Authenticate the user
    user_id = authenticate_user(req)
    if isinstance(user_id, func.HttpResponse):  # Check if authentication failed
        return user_id
    
    # Parse the request body
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Validate required fields
    device_id = req_body.get("deviceId")
    update_data = req_body.get("update", {})
    if not device_id or not update_data:
        return func.HttpResponse("deviceId and update data are required", status_code=400)
    
    # Fetch the user's devices from CosmosDB
    cosmos_service = CosmosDBService()
    user = cosmos_service.find_document({"_id": user_id, "type": "user"})
    if not user:
        return func.HttpResponse("User not found in CosmosDB", status_code=404)
    
    # Check if the device belongs to the user
    devices = user.get("Devices", [])
    device = next((d for d in devices if d["deviceId"] == device_id), None)
    if not device:
        return func.HttpResponse("Device not found in user's Devices array", status_code=404)
    
    # Update the device in the user's Devices array
    result = cosmos_service.update_document(
        {"_id": user_id, "type": "user", "Devices.deviceId": device_id},
        {"$set": {f"Devices.$.{key}": value for key, value in update_data.items()}}
    )
    if result.modified_count == 0:
        return func.HttpResponse("Device not updated", status_code=400)
    
    return func.HttpResponse(json.dumps({"message": "Device updated successfully"}), status_code=200, mimetype="application/json")

def delete_device(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing delete_device request.")
    
    # Authenticate the user
    user_id = authenticate_user(req)
    if isinstance(user_id, func.HttpResponse):  # Check if authentication failed
        return user_id
    
    # Parse the request body
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Validate required fields
    device_id = req_body.get("deviceId")
    if not device_id:
        return func.HttpResponse("deviceId is required", status_code=400)
    
    # Fetch the user's devices from CosmosDB
    cosmos_service = CosmosDBService()
    user = cosmos_service.find_document({"_id": user_id, "type": "user"})
    if not user:
        return func.HttpResponse("User not found in CosmosDB", status_code=404)
    
    # Check if the device belongs to the user
    devices = user.get("Devices", [])
    device = next((d for d in devices if d["deviceId"] == device_id), None)
    if not device:
        return func.HttpResponse("Device not found in user's Devices array", status_code=404)
    
    # Delete the device from IoT Hub
    try:
        iot_service = IoTHubService()
        iot_service.delete_device_from_iot_hub(device_id)
    except Exception as e:
        logging.exception("Failed to delete device from IoT Hub.")
        return func.HttpResponse(f"Failed to delete device from IoT Hub: {str(e)}", status_code=500)
    
    # Remove the device from the user's Devices array
    result = cosmos_service.update_document(
        {"_id": user_id, "type": "user"},
        {"$pull": {"Devices": {"deviceId": device_id}}}
    )
    if result.modified_count == 0:
        return func.HttpResponse("Failed to remove device from user's Devices array", status_code=400)
    
    return func.HttpResponse(json.dumps({"message": "Device deleted successfully"}), status_code=200, mimetype="application/json")

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST  -> register_device (cihaz kaydı)
    GET   -> get_devices
    PUT/PATCH -> update_device
    DELETE -> delete_device
    """
    method = req.method.upper()
    if method == "POST":
        return register_device(req)
    elif method == "GET":
        return get_devices(req)
    elif method in ["PUT", "PATCH"]:
        return update_device(req)
    elif method == "DELETE":
        return delete_device(req)
    else:
        return func.HttpResponse("Method not allowed", status_code=405)
