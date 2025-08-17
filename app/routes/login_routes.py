# app/routes/login_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import logging
from app.config import settings

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str
    accesstype_id: int

class LoginResponse(BaseModel):
    token: str | None
    message: str

# Router
router = APIRouter(tags=["Login"])

@router.post("/get-token", response_model=LoginResponse)
async def get_token(login_request: LoginRequest):
    """
    Call Node.js /login API and return the token.
    """
    url = f"{settings.HRMIS_API_URL}/login"
    payload = {
        "username": login_request.username,
        "password": login_request.password,
        "accesstypeid": login_request.accesstype_id
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, json=payload)
            
            # Log raw response for debugging
            logger.debug(f"Node.js login response: {response.text}")

            # Try to get token from cookies first
            token_cookie = response.cookies.get("token")
            if token_cookie:
                return LoginResponse(token=token_cookie, message="Login successful")

            # Fallback: check 'token' in JSON response
            data = response.json()
            token = data.get("token") or data.get("data", [{}])[0].get("token")

            if token:
                return LoginResponse(token=token, message="Login successful")
            else:
                return LoginResponse(token=None, message="Login failed or incorrect credentials")

    except Exception as e:
        logger.error(f"Login API call failed: {e}")
        return LoginResponse(token=None, message=f"Login failed: {e}")
