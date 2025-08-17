import httpx
import logging
from app.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

INTENT_MAP = {
    "leave_request": {"endpoint": "/leave/request", "method": "POST"},
    "payslip": {"endpoint": "/payslip/{user_id}", "method": "GET"},
    "attendance": {"endpoint": "/attendance/{user_id}", "method": "GET"},
    "employee": {"endpoint": "/index/countactive", "method": "GET"},
}

def format_reply(intent: str, data: dict) -> str:
    """
    Enhance the API response for the AI reply.
    """
    if intent == "employee":
        active_count = data.get("data", {}).get("activeCount", 0)
        if active_count == 0:
            return "Currently, there are no active employees in the system."
        elif active_count == 1:
            return "There is currently 1 active employee in the system."
        else:
            return f"There are currently {active_count} active employees in the system."
    
    # Default fallback for other intents
    return data.get("message", "Request processed successfully.")

async def handle_hrmis_action(intent: str, message: str, user_id: str | None = None, token_api: str | None = None) -> dict:
    """
    Handle HRMIS API calls dynamically based on intent.
    """
    if intent not in INTENT_MAP:
        return {"reply": "I don't know how to handle that request.", "intent": "general"}

    api = INTENT_MAP[intent]
    endpoint = api["endpoint"].format(user_id=user_id)

    headers = {"Authorization": f"Bearer {token_api}"} if token_api else {}

    async with httpx.AsyncClient() as client:
        try:
            if api["method"] == "GET":
                resp = await client.get(f"{settings.HRMIS_API_URL}{endpoint}", headers=headers)
            else:
                resp = await client.post(
                    f"{settings.HRMIS_API_URL}{endpoint}",
                    json={"user_id": user_id, "message": message},
                    headers=headers
                )

            data = resp.json()
            reply_msg = format_reply(intent, data)
            logger.debug(f"Reply for intent '{intent}': {reply_msg}")
            return {"reply": reply_msg, "intent": intent}

        except Exception as e:
            logger.error(f"HRMIS API call failed for intent '{intent}': {e}")
            return {"reply": f"HRMIS API call failed: {e}", "intent": intent}


# async def handle_hrmis_action(intent: str, message: str, user_id: str | None = None) -> dict:
#     """
#     Handle HRMIS API calls dynamically based on intent.
#     """
#     if intent not in INTENT_MAP:
#         return {"reply": "I don't know how to handle that request.", "intent": "general"}

#     api = INTENT_MAP[intent]
#     endpoint = api["endpoint"].format(user_id=user_id)

#     async with httpx.AsyncClient() as client:
#         headers = {"Authorization": f"Bearer {settings.HRMIS_API_TOKEN}"}

#         try:
#             if api["method"] == "GET":
#                 resp = await client.get(f"{settings.HRMIS_API_URL}{endpoint}", headers=headers)
#             else:
#                 resp = await client.post(
#                     f"{settings.HRMIS_API_URL}{endpoint}",
#                     json={"user_id": user_id, "message": message},
#                     headers=headers
#                 )

#             data = resp.json()
#             reply_msg = format_reply(intent, data)
#             logger.debug(f"Reply for intent '{intent}': {reply_msg}")
#             return {"reply": reply_msg, "intent": intent}

#         except Exception as e:
#             logger.error(f"HRMIS API call failed for intent '{intent}': {e}")
#             return {"reply": f"HRMIS API call failed: {e}", "intent": intent}

