# app/services/intent_classifier_db.py
import string
from sqlalchemy.orm import Session
from app.models.intent import Intent

def classify_intent_db(message: str, db: Session) -> str:
    normalized = message.lower().translate(str.maketrans("", "", string.punctuation))
    intents = db.query(Intent).all()
    for it in intents:
        if it.keywords and any(k.lower() in normalized for k in it.keywords):
            return it.name
    return "general"
