from pymongo import MongoClient, ASCENDING
from config.azure_config import COSMOS_DB_URI, COSMOS_DB_NAME, COSMOS_COLLECTION

class CosmosDBService:
    def __init__(self):
        self.client = MongoClient(COSMOS_DB_URI)
        self.db = self.client[COSMOS_DB_NAME]
        self.collection = self.db[COSMOS_COLLECTION]
        # Indexler: type, sensorType ve deviceId üzerinden sorgulama için
        self.collection.create_index([("type", ASCENDING)])
        self.collection.create_index([("sensorType", ASCENDING)])
        self.collection.create_index([("deviceId", ASCENDING)])

    def insert_document(self, document: dict):
        return self.collection.insert_one(document)

    def find_document(self, query: dict):
        return self.collection.find_one(query)

    def update_document(self, query: dict, update: dict):
        return self.collection.update_one(query, {"$set": update})

    def delete_document(self, query: dict):
        return self.collection.delete_one(query)

    def find_documents(self, query: dict):
        return list(self.collection.find(query))