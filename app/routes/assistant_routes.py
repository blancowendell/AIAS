# app/routes/assistant_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.vector_store import search_documents
from app.services.llm import generate_answer
import logging
import traceback
import httpx
import os
import json

HRMIS_API_URL = os.environ.get("HRMIS_API_URL", "http://localhost:3005")

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    token: str = None
    history: list = []   # optional conversation history


# ---------------- Rule-based Fallback ----------------
CASUAL_GREETINGS = ["hi", "hello", "hey", "good morning", "good afternoon"]
CASUAL_CHITCHAT = ["how are you", "what's up", "how’s it going"]

def rule_based_intent(question: str):
    q = question.lower().strip()
    if any(greet in q for greet in CASUAL_GREETINGS):
        return {"action": "greeting", "reason": "Simple greeting detected"}
    if any(chat in q for chat in CASUAL_CHITCHAT):
        return {"action": "chitchat", "reason": "Small talk detected"}
    return None


# ---------------- HR Keyword Fallback ----------------
HR_KEYWORDS = ["leave", "payroll", "salary", "attendance", "holiday", "policy", "benefits"]

def looks_hr_related(question: str):
    q = question.lower()
    return any(word in q for word in HR_KEYWORDS)


# ---------------- LLM Planner ----------------
async def plan_action(question: str, history: list):
    """
    Use LLM to decide action if rule-based doesn't catch it.
    """
    prompt = f"""
You are an HR assistant that must ALWAYS respond with a JSON plan.

The user said: "{question}"
Conversation so far: {history}

Available actions:
- "greeting" → for hello/hi/etc.
- "chitchat" → casual conversation not HR-related
- "search_docs" → if question is about policies/manuals
- "api_call" → if question needs HRMIS data
- "clarify" → if ambiguous

Reply ONLY in JSON format, e.g.:
{{"action": "greeting", "reason": "User said hi"}}
"""
    try:
        plan = await generate_answer(prompt, return_json=True)
        return plan
    except Exception:
        return {"action": "clarify", "reason": "Planner failed"}


# ---------------- API Caller ----------------
async def call_hrmis_api(endpoint: str, token: str):
    full_url = f"{HRMIS_API_URL.rstrip('/')}/{endpoint.strip().lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(full_url, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ---------------- Assistant Endpoint ----------------
@router.post("/ask")
async def ask_assistant(request: QueryRequest):
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        # Step 1: Try rule-based detection first
        plan = rule_based_intent(question)
        if not plan:
            # Step 2: If not matched, ask LLM planner
            plan = await plan_action(question, request.history)

        action = plan.get("action", "clarify")

        # --- NEW: fallback to doc search if HR-related but planner says clarify ---
        if action == "clarify" and looks_hr_related(question):
            action = "search_docs"
            plan["action"] = "search_docs"
            plan["reason"] = "Fallback to doc search (HR keyword detected)"

        answer = ""
        sources = []

        # Step 3: Execute based on plan
        if action == "greeting":
            answer = "Hello! How can I help you today?"

        elif action == "chitchat":
            answer_data = generate_answer(f"Casual friendly reply to: {question}")
            answer = answer_data.get("answer", "🙂")

        elif action == "search_docs":
            results = search_documents(question, top_k=5, similarity_threshold=0.5)
            if not results:
                results = search_documents(question, top_k=5, similarity_threshold=0.0)

            if not results:
                answer = "I couldn’t find relevant information in our knowledge base."
            else:
                # Summarize with LLM
                answer_data = generate_answer(
                    question,
                    [{"text": r["text"]} for r in results],
                    style="conversational"
                )
                answer = answer_data["answer"]

                # Collect unique sources
                seen = set()
                for r in results:
                    key = (r["filename"], r["page"])
                    if key not in seen:
                        seen.add(key)
                        sources.append({"filename": r["filename"], "page": r["page"]})

        elif action == "api_call":
            endpoint = plan.get("endpoint", "employee/info")
            try:
                api_json = await call_hrmis_api(endpoint, request.token)
                answer_data = generate_answer(
                    f"Summarize this API result in a conversational helpful tone:\n{json.dumps(api_json)}"
                )
                answer = answer_data.get("answer", "Got the data, but couldn't format it.")
            except Exception as e:
                answer = f"Sorry, I couldn't fetch API data: {e}"

        elif action == "clarify":
            answer = "Could you clarify your question? For example, are you asking about leave, payroll, or policies?"

        else:
            answer = "I'm not sure how to respond to that."

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "plan": plan  # debug: shows what action was chosen
        }

    except Exception as e:
        logging.error("Error in /assistant/ask:\n%s", traceback.format_exc())
        return {
            "question": request.question,
            "answer": "Internal Server Error",
            "sources": []
        }

