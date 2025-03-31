import jwt
import datetime
from azure.functions import HttpRequest, HttpResponse
from .azure_config import get_azure_config

config = get_azure_config()
JWT_SECRET = config["JWT_SECRET"]
JWT_ALGORITHM = config["JWT_ALGORITHM"]

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def authenticate_user(req: HttpRequest):
    """
    Authenticates the user by checking the Authorization header and decoding the JWT token.
    Returns the user_id if authentication is successful, otherwise returns an HttpResponse with an error.
    """
    # Check for Authorization header
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return HttpResponse("Authorization header missing", status_code=401)
    
    # Decode the JWT token
    token = auth_header.split("Bearer ")[-1]
    payload = decode_token(token)
    if not payload:
        return HttpResponse("Invalid token", status_code=401)
    
    # Extract user_id from the token payload
    user_id = payload.get("user_id")
    if not user_id:
        return HttpResponse("Invalid token payload: user_id missing", status_code=401)
    
    return user_id

