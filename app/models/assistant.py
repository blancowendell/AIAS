from pydantic import BaseModel

class AssistantRequest(BaseModel):
    message: str
    user_id: str | None = None
    token_api: str | None = None 

class AssistantResponse(BaseModel):
    reply: str
    intent: str
