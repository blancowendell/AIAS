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
    intent = db.query(Intent).filter(Intent.i_name == intent_name).first()
    if not intent or not intent.i_endpoint or not intent.i_method:
        logging.warning(f"Intent '{intent_name}' not found or incomplete.")
        return {"reply": "I don't know how to handle that request.", "intent": "general"}

    endpoint = intent.i_endpoint.format(user_id=user_id) if "{user_id}" in intent.i_endpoint else intent.i_endpoint
    headers = {"Authorization": f"Bearer {token_api}"} if token_api else {}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if intent.i_method.upper() == "GET":
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

            if getattr(intent, "i_response_path", None):
                value = extract_value_from_path(data, intent.i_response_path)
                if value is not None and getattr(intent, "i_response_template", None):
                    reply = intent.i_response_template.format(**{intent.i_response_path.split(".")[-1]: value})
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

