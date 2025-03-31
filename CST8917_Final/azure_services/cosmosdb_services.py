import logging
from config.azure_config import get_azure_config
from pymongo import MongoClient


class CosmosDBService:
    def __init__(self):
        """
        Initializes the CosmosDBService with the specified collection name.
        """
        try:

            config = get_azure_config()
            client = MongoClient(config["COSMOS_DB_CONNECTION_STRING"])
            db = client[config["COSMOS_DB_NAME"]]
            self.collection_name = config["COLLECTION_NAME"] 

            # Get the MongoDB collection from config
            self.collection = db[self.collection_name]

            logging.info(f"[CosmosDBService] MongoDB collection '{self.collection_name}' initialized successfully.")
        except Exception as ex:
            logging.exception(f"[CosmosDBService] MongoDB collection '{self.collection_name}' initialization failed.")
            raise ex

    def insert_document(self, document: dict):
        """
        Inserts a document into the collection.
        """
        return self.collection.insert_one(document)

    def find_document(self, query: dict):
        """
        Finds a single document in the collection based on the query.
        """
        return self.collection.find_one(query)

    def update_document(self, query: dict, update: dict):
        """
        Updates a document in the collection based on the query.
        """
        return self.collection.update_one(query, {"$set": update})

    def delete_document(self, query: dict):
        """
        Deletes a document from the collection based on the query.
        """
        return self.collection.delete_one(query)

    def find_documents(self, query: dict):
        """
        Finds multiple documents in the collection based on the query.
        """
        return list(self.collection.find(query))