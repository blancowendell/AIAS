from pydantic import BaseModel
from typing import Optional

class AssistantRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    token_api: Optional[str] = None

class AssistantResponse(BaseModel):
    reply: str
    intent: str
