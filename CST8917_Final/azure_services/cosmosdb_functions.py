import logging
import uuid
from config.azure_config import get_mongo_collection

try:
    # Get the MongoDB collection from config
    collection = get_mongo_collection("TelemetryData")
    logging.info("[store_data_in_cosmosdb] MongoDB collection initialized successfully.")
except Exception as ex:
    logging.exception("[store_data_in_cosmosdb] MongoDB collection initialization failed.")
    raise ex

def store_data_in_cosmosdb(data: dict):
    """
    Inserts telemetry data into the CosmosDB collection with a required shard key 'dataId'.
    """
    try:
        # Ensure shard key exists
        if "dataId" not in data:
            data["dataId"] = str(uuid.uuid4())
            logging.info(f"[store_data_in_cosmosdb] Generated new dataId: {data['dataId']}")

        logging.info(f"[store_data_in_cosmosdb] Attempting to insert document: {data}")
        result = collection.insert_one(data)
        logging.info(f"[store_data_in_cosmosdb] Inserted document with _id: {result.inserted_id}")
    except Exception as ex:
        logging.exception(f"[store_data_in_cosmosdb] Failed to store data in MongoDB: {ex}")
        raise ex