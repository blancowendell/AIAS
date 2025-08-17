from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
    accesstype_id: str

class LoginResponse(BaseModel):
    token: str | None = None
    message: str
