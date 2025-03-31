import logging
import logging
import json
import azure.functions as func

from .device_functions import validate_device_data
from azure_services.notification_functions import forward_event, trigger_notification
from azure_services.cosmosdb_functions import store_data_in_cosmosdb
from config.azure_config import get_mongo_collection, get_azure_config
from config.jwt_utils import verify_jwt, authenticate_request

config = get_azure_config()
telemetry_col = get_mongo_collection(config["TELEMETRY_COLLECTION_NAME"])


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main function to handle HTTP requests and route them to the appropriate function
    based on the HTTP method and request path.
    """
    method = req.method.upper()
    path = req.route_params.get("path", "").lower()  # Extract path if available

    try:
        user_id = authenticate_request(req)  # Extract userId from token
        if method == "GET" and "telemetry" in path:
            # Handle GET requests for telemetry data
            query_params = req.params
            results = get_telemetry_data(query_params, user_id)
            return func.HttpResponse(json.dumps(results), status_code=200, mimetype="application/json")

        elif method == "POST" and "telemetry" in path:
            # Handle POST requests for telemetry data
            body = req.get_json()
            body["userId"] = user_id  # Add userId to the telemetry data
            post_telemetry_data(body)
            return func.HttpResponse("Telemetry data processed successfully.", status_code=201)

        elif method == "DELETE" and "telemetry" in path:
            # Handle DELETE requests for telemetry data
            return delete_telemetry_data(req, user_id)

        else:
            # Return 405 for unsupported methods or paths
            return func.HttpResponse("Method not allowed.", status_code=405)

    except ValueError as ve:
        logging.error(f"[main] ValueError: {str(ve)}")
        return func.HttpResponse(str(ve), status_code=400)

    except Exception as e:
        logging.error(f"[main] Unexpected error: {str(e)}")
        return func.HttpResponse("Internal server error.", status_code=500)

def get_telemetry_data(query_params, user_id):
    logging.info("[get_telemetry_data] Fetching telemetry data with filters...")

    query = {"userId": user_id}  # Use userId from token
    device_id = query_params.get("device_id")
    sensor_type = query_params.get("sensor_type")
    value = query_params.get("value")

    if device_id:
        query["device_id"] = device_id
    if sensor_type:
        query["sensor_type"] = sensor_type
    if value:
        try:
            query["value"] = json.loads(value)
        except:
            logging.warning("[get_telemetry_data] Could not parse 'value' as JSON. Ignoring.")

    logging.info(f"[get_telemetry_data] Query: {query}")

    collection = get_mongo_collection("TelemetryData")
    results = list(collection.find(query, {"_id": 0}))
    return results


def delete_telemetry_data(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    logging.info("[delete_telemetry_data] Processing telemetry data deletion...")

    try:
        body = req.get_json()
        required_keys = ["device_id", "sensor_type", "timestamp", "dataId"]
        if not all(k in body for k in required_keys):
            return func.HttpResponse("Missing required telemetry fields.", status_code=400)

        query = {
            "userId": user_id,  # Use userId from token
            "device_id": body["device_id"],
            "sensor_type": body["sensor_type"],
            "timestamp": body["timestamp"],
            "dataId": body["dataId"]
        }

        logging.info(f"[delete_telemetry_data] Query: {query}")

        collection = get_mongo_collection("TelemetryData")
        result = collection.delete_one(query)

        if result.deleted_count == 1:
            return func.HttpResponse("Telemetry data deleted successfully.", status_code=200)
        else:
            return func.HttpResponse("No matching telemetry data found.", status_code=404)

    except Exception as e:
        logging.error(f"[delete_telemetry_data] Error: {str(e)}")
        return func.HttpResponse("Internal server error.", status_code=500)

def post_telemetry_data(data: dict):
    logging.info(f"[process_telemetry_data] Received telemetry data: {data}")

    # 1. Validation
    if not validate_device_data(data):
        logging.warning("[process_telemetry_data] Validation failed for telemetry data.")
        raise ValueError("Invalid telemetry data.")
    logging.info("[process_telemetry_data] Telemetry data passed validation.")

    # 2. Store to Cosmos DB
    try:
        store_data_in_cosmosdb(data)
        logging.info("[process_telemetry_data] Data stored in Cosmos DB successfully.")
    except Exception as ex:
        logging.error(f"[process_telemetry_data] Error while storing data: {ex}")
        raise

    # 3. Forward event to Event Grid
    try:
        forward_event(data)
        logging.info("[process_telemetry_data] Data forwarded to Event Grid successfully.")
    except Exception as ex:
        logging.error(f"[process_telemetry_data] Error while forwarding event: {ex}")
        raise

    # 4. Optional: trigger notification if it's a health sensor and value is abnormal
    try:
         if data.get("sensor_type") == "health" and isinstance(data.get("value"), dict):
             heart_rate = data["value"].get("heart_rate", 0)
             logging.info(f"[process_telemetry_data] Checking heart rate: {heart_rate}")
             if heart_rate > 100:
                userId = data.get("userId", "unknown")
                message = f"High heart rate detected: {heart_rate}"
                trigger_notification(userId, message)
                logging.info(f"[process_telemetry_data] Notification triggered for user {userId}")
    except Exception as ex:
         logging.error(f"[process_telemetry_data] Error in notification logic: {ex}")
         raise

    #logging.info("[process_telemetry_data] Telemetry data processing complete.")
