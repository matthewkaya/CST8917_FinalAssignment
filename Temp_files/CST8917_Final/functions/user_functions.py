import json
import logging
import uuid
import azure.functions as func
from config.jwt_utils import create_token, decode_token
from config.password_utils import hash_password, verify_password
from azure_services.cosmosdb_services import CosmosDBService

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main function for user-related requests.
    Dispatches based on HTTP method:
      POST   -> create_user (no authorization required)
      GET    -> get_user (authorization required)
      PUT    -> update_user_put (authorization required)
      PATCH  -> If request body contains 'oldPassword' and 'newPassword', call update_password (no authorization required)
      DELETE -> delete_user (authorization required)
    """
    method = req.method.upper()
    if method == "POST":
        return create_user(req)
    elif method == "GET":
        return get_user(req)
    elif method == "PUT":
        return update_user_put(req)
    elif method == "PATCH":
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse("Invalid JSON body", status_code=400)
        # If 'oldPassword' and 'newPassword' are provided, assume this is a password change request.
        if "oldPassword" in req_body and "newPassword" in req_body:
            return update_password(req)
        else:
            return func.HttpResponse("PATCH method not used for general updates", status_code=400)
    elif method == "DELETE":
        return delete_user(req)
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

def create_user(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing create_user request.")
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Generate a unique userId using uuid (ignoring any provided userId)
    user_id = str(uuid.uuid4())
    
    # Extract required fields from the request body
    first_name = req_body.get("firstName")
    last_name = req_body.get("lastName")
    email = req_body.get("email")
    password = req_body.get("password")
    phone = req_body.get("phone")  # Optional phone field

    if not first_name or not last_name or not email or not password:
        return func.HttpResponse(
            "Missing required fields: firstName, lastName, email, password", 
            status_code=400
        )
    
    # Hash the provided password
    hashed_pw = hash_password(password)
    
    # Prepare the user document according to the specified structure.
    # The "Devices" field is an array that will hold device objects,
    # each of which can contain a telemetryData array.
    user_doc = {
        "_id": user_id,            # ShardKey (userId) generated as a UUID
        "userId": user_id,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "password": hashed_pw,
        "phone": phone,            # Optional phone field
        "authToken": None,         # Default authentication token is None
        "Devices": [],             # Devices list (each device will have a telemetryData array)
        "type": "user"             # Adding type for filtering purposes
    }
    
    cosmos_service = CosmosDBService()
    # Insert the user document into Cosmos DB
    insert_result = cosmos_service.insert_document(user_doc)
    
    # Generate an authentication token for the new user using userId as payload
    token = create_token(user_id)
    # Update the document with the generated token
    cosmos_service.update_document({"_id": user_id, "type": "user"}, {"authToken": token})
    
    response_body = {"message": "User created", "token": token}
    return func.HttpResponse(json.dumps(response_body), status_code=201, mimetype="application/json")
    logging.info("Processing create_user request.")
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Extract required fields from the request body
    user_id = req_body.get("userId")
    first_name = req_body.get("firstName")
    last_name = req_body.get("lastName")
    email = req_body.get("email")
    password = req_body.get("password")
    phone = req_body.get("phone")  # Optional phone field

    if not user_id or not first_name or not last_name or not email or not password:
        return func.HttpResponse(
            "Missing required fields: userId, firstName, lastName, email, password", 
            status_code=400
        )
    
    # Hash the provided password
    hashed_pw = hash_password(password)
    
    # Prepare the user document according to the specified structure.
    # The "Devices" field is an array that will hold device objects,
    # each of which can contain a telemetryData array.
    user_doc = {
        "_id": user_id,            # ShardKey (userId)
        "userId": user_id,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "password": hashed_pw,
        "phone": phone,            # Optional phone field
        "authToken": None,         # Default authentication token is None
        "Devices": [],             # Devices list (each device will have a telemetryData array)
        "type": "user"             # Adding type for filtering purposes
    }
    
    cosmos_service = CosmosDBService()
    # Insert the user document into Cosmos DB
    insert_result = cosmos_service.insert_document(user_doc)
    
    # Generate an authentication token for the new user using userId as payload
    token = create_token(user_id)
    # Update the document with the generated token
    cosmos_service.update_document({"_id": user_id, "type": "user"}, {"authToken": token})
    
    response_body = {"message": "User created", "token": token}
    return func.HttpResponse(json.dumps(response_body), status_code=201, mimetype="application/json")

def get_user(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing get_user request.")
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return func.HttpResponse("Authorization header missing", status_code=401)
    
    # Extract token from the Authorization header
    token = auth_header.split("Bearer ")[-1]
    payload = decode_token(token)
    if not payload:
        return func.HttpResponse("Invalid token", status_code=401)
    
    user_id = payload.get("user_id")
    cosmos_service = CosmosDBService()
    # Retrieve the user document using _id (userId) and type 'user'
    user = cosmos_service.find_document({"_id": user_id, "type": "user"})
    if not user:
        return func.HttpResponse("User not found", status_code=404)
    
    # Remove sensitive information and convert _id to string for JSON serialization
    user.pop("password", None)
    user["_id"] = str(user["_id"])
    return func.HttpResponse(json.dumps(user), status_code=200, mimetype="application/json")

def update_user_put(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing update_user_put request.")
    # This function requires authorization.
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return func.HttpResponse("Authorization header missing", status_code=401)
    
    token = auth_header.split("Bearer ")[-1]
    payload = decode_token(token)
    if not payload:
        return func.HttpResponse("Invalid token", status_code=401)
    
    user_id = payload.get("user_id")
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Allowed fields for update: firstName, lastName, email, phone
    update_data = {}
    if "firstName" in req_body:
        update_data["firstName"] = req_body["firstName"]
    if "lastName" in req_body:
        update_data["lastName"] = req_body["lastName"]
    if "email" in req_body:
        update_data["email"] = req_body["email"]
    if "phone" in req_body:
        update_data["phone"] = req_body["phone"]
    
    if not update_data:
        return func.HttpResponse("No update data provided", status_code=400)
    
    cosmos_service = CosmosDBService()
    result = cosmos_service.update_document({"_id": user_id, "type": "user"}, update_data)
    if result.modified_count == 0:
        return func.HttpResponse("User not updated", status_code=400)
    
    return func.HttpResponse(json.dumps({"message": "User info updated successfully"}), status_code=200, mimetype="application/json")

def update_password(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing update_password request.")
    # This function does NOT require an Authorization header.
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)
    
    # Expecting userId, oldPassword, and newPassword in the request body.
    user_id = req_body.get("userId")
    old_password = req_body.get("oldPassword")
    new_password = req_body.get("newPassword")
    if not user_id or not old_password or not new_password:
        return func.HttpResponse("Missing required fields: userId, oldPassword, newPassword", status_code=400)
    
    cosmos_service = CosmosDBService()
    user = cosmos_service.find_document({"_id": user_id, "type": "user"})
    if not user:
        return func.HttpResponse("User not found", status_code=404)
    
    stored_password = user.get("password")
    # Verify the provided old password with the stored hashed password
    if not verify_password(old_password, stored_password):
        return func.HttpResponse("Old password does not match", status_code=401)
    
    # Hash the new password and update the user document
    hashed_new_pw = hash_password(new_password)
    result = cosmos_service.update_document({"_id": user_id, "type": "user"}, {"password": hashed_new_pw})
    if result.modified_count == 0:
        return func.HttpResponse("Password not updated", status_code=400)
    
    return func.HttpResponse(json.dumps({"message": "Password updated successfully"}), status_code=200, mimetype="application/json")

def delete_user(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing delete_user request.")
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return func.HttpResponse("Authorization header missing", status_code=401)
    
    token = auth_header.split("Bearer ")[-1]
    payload = decode_token(token)
    if not payload:
        return func.HttpResponse("Invalid token", status_code=401)
    
    user_id = payload.get("user_id")
    cosmos_service = CosmosDBService()
    result = cosmos_service.delete_document({"_id": user_id, "type": "user"})
    if result.deleted_count == 0:
        return func.HttpResponse("User not deleted", status_code=400)
    
    return func.HttpResponse(json.dumps({"message": "User deleted"}), status_code=200, mimetype="application/json")

