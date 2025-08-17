from fastapi import APIRouter
from app.models.assistant import AssistantRequest, AssistantResponse
from app.services.intent_classifier import classify_intent
from app.services.hrmis_service import handle_hrmis_action
from app.services.groq_service import ask_groq 

router = APIRouter()

@router.post("/", response_model=AssistantResponse)
async def process_assistant(request: AssistantRequest):
    """
    Process a user's message, classify the intent, and call the appropriate HRMIS API.
    Falls back to Groq AI if the intent is not recognized.
    """
    intent = classify_intent(request.message)

    if intent in ["leave_request", "payslip", "attendance", "employee"]:
        result = await handle_hrmis_action(
            intent,
            request.message,
            request.user_id,
            token_api=request.token_api
        )
        return AssistantResponse(reply=result["reply"], intent=result["intent"])
    
        # result = await handle_hrmis_action(intent, request.message, request.user_id)
        # return AssistantResponse(reply=result["reply"], intent=result["intent"])

    reply = await ask_groq(request.message)
    return AssistantResponse(reply=reply, intent=intent)
