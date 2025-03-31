import jwt
import datetime
from .azure_config import get_azure_config

config = get_azure_config()
SECRET_KEY = "AlgonquinCollege" 

def generate_jwt(userId: str):
    expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    payload = {
        "userId": userId,
        "exp": expiry
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, expiry


def verify_jwt(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True, decoded.get("userId")  
    except jwt.ExpiredSignatureError:
        return False, None
    except jwt.InvalidTokenError:
        return False, None

def authenticate_request(req):
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return None, "Missing Authorization Header"
    
    token = auth_header.replace("Bearer ", "")
    is_valid, result = verify_jwt(token)
    if not is_valid:
        return None, result  # result contains error message
    return result, None  # result is userId
