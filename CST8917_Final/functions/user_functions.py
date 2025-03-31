import json
import uuid
from config.azure_config import get_mongo_collection
from config.jwt_utils import generate_jwt
from config.password_utils import hash_password, verify_password

import uuid
from config.azure_config import get_mongo_collection
from config.password_utils import hash_password

def create_user(req):
    try:
        req_body = req.get_json()
        first_name = req_body.get("firstName")
        last_name = req_body.get("lastName")
        email = req_body.get("email")
        password = req_body.get("password")

        if not all([first_name, last_name, email, password]):
            return {"status": 400, "body": "Missing required fields."}

        users_col = get_mongo_collection("Users")

        # Check if user already exists
        if users_col.find_one({"email": email}):
            return {"status": 409, "body": "User already exists."}

        hashed_pw = hash_password(password)

        userId = str(uuid.uuid4())  

        user_doc = {
            "_id": userId,
            "userId": userId, 
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "password": hashed_pw,
            "authToken": None,
            "uploadedImages": []
        }

        users_col.insert_one(user_doc)
        return {
            "status": 201,
            "body": json.dumps({
                "userId": userId,
                "message": f"User created successfully."
            })
        }

    except Exception as e:
        return {"status": 500, "body": str(e)}



def update_user(req):
    try:
        req_body = req.get_json()
        userId = req_body.get("userId")  # shard key

        # Remove fields that should not be updated
        update_fields = {
            k: v for k, v in req_body.items() 
            if k not in ["id", "userId", "_id"]
        }

        if not userId or not update_fields:
            return {
                "status": 400, 
                "body": "userId (shard key) and update fields are required."
            }

        users_col = get_mongo_collection("Users")

        result = users_col.update_one(
            {"userId": userId},  # Only shard key required
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return {"status": 404, "body": "User not found or nothing updated."}

        return {"status": 200, "body": "User updated successfully."}

    except Exception as e:
        return {"status": 500, "body": str(e)}

def delete_user(req):
    try:
        req_body = req.get_json()
        userId = req_body.get("userId")  # shard key

        if not userId:
            return {
                "status": 400,
                "body": "userId (shard key) is required."
            }

        users_col = get_mongo_collection("Users")

        result = users_col.delete_one({"userId": userId})

        if result.deleted_count == 0:
            return {"status": 404, "body": "User not found."}

        return {"status": 200, "body": "User deleted successfully."}

    except Exception as e:
        return {"status": 500, "body": str(e)}



def login_user(req):
    try:
        req_body = req.get_json()
        email = req_body.get("email")
        password = req_body.get("password")

        if not email or not password:
            return {"status": 400, "body": "Email and password required."}

        users_col = get_mongo_collection("Users")
        user = users_col.find_one({"email": email})

        if not user or not verify_password(password, user["password"]):
            return {"status": 401, "body": "Invalid credentials."}

        token, expiry = generate_jwt(user["userId"])
        users_col.update_one(
            {"userId": user["userId"]},  # Use shard key here
            {"$set": {"authToken": {"token": token, "expiryDate": expiry.isoformat()}}}
        )

        return {
            "status": 200,
            "body": json.dumps({"token": token, "expiryDate": expiry.isoformat()})
        }

    except Exception as e:
        return {"status": 500, "body": str(e)}
