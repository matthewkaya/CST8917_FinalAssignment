import jwt
import datetime
from config.azure_config import get_azure_config

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
