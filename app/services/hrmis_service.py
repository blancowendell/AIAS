# import httpx
# import logging
# from app.config import settings

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

# INTENT_MAP = {
#     "leave_request": {"endpoint": "/leave/request", "method": "POST"},
#     "payslip": {"endpoint": "/payslip/{user_id}", "method": "GET"},
#     "attendance": {"endpoint": "/attendance/{user_id}", "method": "GET"},
#     "employee": {"endpoint": "/index/countactive", "method": "GET"},
# }

# def format_reply(intent: str, data: dict) -> str:
#     """
#     Enhance the API response for the AI reply.
#     """
#     if intent == "employee":
#         active_count = data.get("data", {}).get("activeCount", 0)
#         if active_count == 0:
#             return "Currently, there are no active employees in the system."
#         elif active_count == 1:
#             return "There is currently 1 active employee in the system."
#         else:
#             return f"There are currently {active_count} active employees in the system."
    
#     # Default fallback for other intents
#     return data.get("message", "Request processed successfully.")

# async def handle_hrmis_action(intent: str, message: str, user_id: str | None = None, token_api: str | None = None) -> dict:
#     """
#     Handle HRMIS API calls dynamically based on intent.
#     """
#     if intent not in INTENT_MAP:
#         return {"reply": "I don't know how to handle that request.", "intent": "general"}

#     api = INTENT_MAP[intent]
#     endpoint = api["endpoint"].format(user_id=user_id)

#     headers = {"Authorization": f"Bearer {token_api}"} if token_api else {}

#     async with httpx.AsyncClient() as client:
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


# # async def handle_hrmis_action(intent: str, message: str, user_id: str | None = None) -> dict:
# #     """
# #     Handle HRMIS API calls dynamically based on intent.
# #     """
# #     if intent not in INTENT_MAP:
# #         return {"reply": "I don't know how to handle that request.", "intent": "general"}

# #     api = INTENT_MAP[intent]
# #     endpoint = api["endpoint"].format(user_id=user_id)

# #     async with httpx.AsyncClient() as client:
# #         headers = {"Authorization": f"Bearer {settings.HRMIS_API_TOKEN}"}

# #         try:
# #             if api["method"] == "GET":
# #                 resp = await client.get(f"{settings.HRMIS_API_URL}{endpoint}", headers=headers)
# #             else:
# #                 resp = await client.post(
# #                     f"{settings.HRMIS_API_URL}{endpoint}",
# #                     json={"user_id": user_id, "message": message},
# #                     headers=headers
# #                 )

# #             data = resp.json()
# #             reply_msg = format_reply(intent, data)
# #             logger.debug(f"Reply for intent '{intent}': {reply_msg}")
# #             return {"reply": reply_msg, "intent": intent}

# #         except Exception as e:
# #             logger.error(f"HRMIS API call failed for intent '{intent}': {e}")
# #             return {"reply": f"HRMIS API call failed: {e}", "intent": intent}

# app/services/hrmis_service.py (snippet)

import httpx
from sqlalchemy.orm import Session
from app.database.models.intent import Intent
from app.config import settings
import logging

def extract_value_from_path(data: dict, path: str):
    """Extract nested value from dict using dot notation path."""
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
    return data

async def handle_hrmis_action(
    intent_name: str,
    message: str,
    user_id: str | None,
    token_api: str | None,
    db: Session
) -> dict:
    intent = db.query(Intent).filter(Intent.name == intent_name).first()
    if not intent or not intent.endpoint or not intent.method:
        logging.warning(f"Intent '{intent_name}' not found or incomplete.")
        return {"reply": "I don't know how to handle that request.", "intent": "general"}

    endpoint = intent.endpoint.format(user_id=user_id) if "{user_id}" in intent.endpoint else intent.endpoint
    headers = {"Authorization": f"Bearer {token_api}"} if token_api else {}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:  # 5s timeout
            if intent.method.upper() == "GET":
                resp = await client.get(f"{settings.HRMIS_API_URL}{endpoint}", headers=headers)
            else:
                resp = await client.post(
                    f"{settings.HRMIS_API_URL}{endpoint}",
                    json={"user_id": user_id, "message": message},
                    headers=headers
                )

            try:
                data = resp.json()
            except Exception:
                logging.error(f"Failed to parse JSON from HRMIS response: {resp.text}")
                return {"reply": "HRMIS API returned invalid response.", "intent": intent_name}

            if getattr(intent, "response_path", None):
                value = extract_value_from_path(data, intent.response_path)
                if value is not None and getattr(intent, "response_template", None):
                    reply = intent.response_template.format(**{intent.response_path.split(".")[-1]: value})
                else:
                    reply = f"Received data: {value}" if value is not None else "No data found."
            else:
                reply = data.get("message", "Request processed successfully.")

            return {"reply": reply, "intent": intent_name}

    except httpx.RequestError as e:
        logging.error(f"HRMIS API request failed: {e}")
        return {"reply": f"HRMIS API request failed: {e}", "intent": intent_name}
    except Exception as e:
        logging.error(f"Unexpected error in HRMIS handler: {e}")
        return {"reply": f"Error processing your request: {e}", "intent": intent_name}
