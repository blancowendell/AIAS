# # app/routes/assistant_routes.py
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from app.services.vector_store import search_documents
# from app.services.llm import generate_answer
# import logging
# import traceback
# from collections import Counter

# router = APIRouter()

# class QueryRequest(BaseModel):
#     question: str

# CASUAL_GREETINGS = ["hi", "hello", "hey", "good morning", "good afternoon"]

# def detect_intent(question: str) -> str:
#     q = question.lower().strip()
#     if any(greet in q for greet in CASUAL_GREETINGS):
#         return "greeting"
#     return "document"

# @router.post("/ask")
# async def ask_assistant(request: QueryRequest):
#     try:
#         question = request.question.strip()
#         if not question:
#             raise HTTPException(status_code=400, detail="Question cannot be empty")

#         # Step 0: detect intent
#         intent = detect_intent(question)
#         if intent == "greeting":
#             return {
#                 "question": question,
#                 "answer": "Hello! How can I help you today?",
#                 "sources": []
#             }

#         # Step 1: query vector store (no static keyword filter)
#         initial_results = search_documents(
#             question,
#             top_k=5,
#             similarity_threshold=0.5
#         )

#         if not initial_results:
#             # fallback with no similarity filter
#             initial_results = search_documents(
#                 question,
#                 top_k=5,
#                 similarity_threshold=0.0
#             )

#         if not initial_results:
#             return {
#                 "question": question,
#                 "answer": "Sorry, I could not find relevant information.",
#                 "sources": []
#             }

#         # Step 2: auto-detect most common tag in retrieved results
#         tags = []
#         for r in initial_results:
#             tags.extend(r.get("tags", []))
#         tag_filter = Counter(tags).most_common(1)[0][0] if tags else None

#         # Step 3: refine search with detected tag (if any)
#         refined_results = search_documents(
#             question,
#             top_k=5,
#             similarity_threshold=0.5,
#             tag_filter=tag_filter
#         )

#         final_results = refined_results if refined_results else initial_results

#         # Step 4: if the top chunk looks like a requirements/attachments list, shortcut
#         top_text = final_results[0]["text"]
#         if tag_filter == "attachment" and (
#             top_text.strip().startswith("1.") or "-" in top_text or "\n" in top_text
#         ):
#             answer = top_text.strip()
#         else:
#             # Otherwise, use LLM to generate answer
#             answer_data = generate_answer(question, final_results)
#             answer = answer_data["answer"]

#         # Deduplicate sources
#         unique_sources = []
#         seen = set()
#         for r in final_results:
#             key = (r["filename"], r["page"])
#             if key not in seen:
#                 seen.add(key)
#                 unique_sources.append({"filename": r["filename"], "page": r["page"]})

#         return {
#             "question": question,
#             "answer": answer,
#             "sources": unique_sources
#         }

#     except Exception as e:
#         logging.error("Error in /assistant/ask:\n%s", traceback.format_exc())
#         return {
#             "question": request.question,
#             "answer": "Internal Server Error",
#             "sources": []
#         }


# app/routes/assistant_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.vector_store import search_documents
from app.services.llm import generate_answer, api_json_to_text
import logging
import traceback
from collections import Counter
import httpx
import os
import re
import json

HRMIS_API_URL = os.environ.get("HRMIS_API_URL", "http://localhost:3005")

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    token: str = None

CASUAL_GREETINGS = ["hi", "hello", "hey", "good morning", "good afternoon"]

def detect_intent(question: str) -> str:
    q = question.lower().strip()
    if any(greet in q for greet in CASUAL_GREETINGS):
        return "greeting"
    return "document"

@router.post("/ask")
async def ask_assistant(request: QueryRequest):
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        # Step 0: detect intent
        intent = detect_intent(question)
        if intent == "greeting":
            return {
                "question": question,
                "answer": "Hello! How can I help you today?",
                "sources": []
            }

        # Step 1: query vector store
        initial_results = search_documents(question, top_k=5, similarity_threshold=0.5)
        if not initial_results:
            initial_results = search_documents(question, top_k=5, similarity_threshold=0.0)
        if not initial_results:
            return {
                "question": question,
                "answer": "No relevant content found.",
                "sources": []
            }

        # Step 2: detect most common tag
        tags = []
        for r in initial_results:
            tags.extend(r.get("tags", []))
        tag_filter = Counter(tags).most_common(1)[0][0] if tags else None

        # Step 3: refine search
        refined_results = search_documents(question, top_k=5, similarity_threshold=0.5, tag_filter=tag_filter)
        final_results = refined_results if refined_results else initial_results

        # Step 4: process API entries and normal text
        answer_parts = []
        seen_apis = set()

        def extract_api_data(api_json: dict) -> str:
            """
            Build a human-friendly summary from API JSON.
            """
            try:
                msg = api_json.get("msg", "")
                data = api_json.get("data", [])

                summary = f"{msg.capitalize()}. " if msg else ""
                if data:
                    for i, item in enumerate(data):
                        val = item.get("Result") or item.get("result") or "N/A"
                        summary += f"{i+1}. Result: {val}\n"
                else:
                    summary += "No results found."

                return summary.strip()
            except Exception:
                return "Could not parse API response."

        for r in final_results:
            api_tags = [t for t in r.get("tags", []) if t.startswith("api")]
            endpoint = r.get("endpoint")
            api_identifier = r.get("api_id") or "dynamic_api"

            if api_tags and endpoint:
                api_key = api_identifier.lower()
                if api_key in seen_apis:
                    continue
                seen_apis.add(api_key)

                full_url = f"{HRMIS_API_URL.rstrip('/')}/{endpoint.strip().lstrip('/')}"
                headers = {"Authorization": f"Bearer {request.token}"} if request.token else {}

                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(full_url, headers=headers)
                        resp.raise_for_status()
                        api_answer_json = resp.json()

                        # Extract and clean API data
                        cleaned_text = r["text"] + " " + extract_api_data(api_answer_json)
                        answer_parts.append(cleaned_text)

                except Exception as e:
                    answer_parts.append(f"[API {api_identifier} failed]: {e}")
            else:
                answer_parts.append(r["text"])


        # Step 5: remove duplicate answer parts
        unique_answer_parts = []
        seen_parts = set()
        for part in answer_parts:
            if part not in seen_parts:
                seen_parts.add(part)
                unique_answer_parts.append(part)

        # Step 6: shortcut for attachments
        top_text = final_results[0]["text"]
        if tag_filter == "attachment" and (
            top_text.strip().startswith("1.") or "-" in top_text or "\n" in top_text
        ):
            answer = top_text.strip()
        else:
            # Step 7: generate coherent, human-friendly summary
            answer_data = generate_answer(question, [{"text": part} for part in unique_answer_parts])
            answer = answer_data["answer"]

        # Deduplicate sources
        unique_sources = []
        seen = set()
        for r in final_results:
            key = (r["filename"], r["page"])
            if key not in seen:
                seen.add(key)
                unique_sources.append({"filename": r["filename"], "page": r["page"]})

        return {
            "question": question,
            "answer": answer,
            "sources": unique_sources
        }

    except Exception as e:
        logging.error("Error in /assistant/ask:\n%s", traceback.format_exc())
        return {
            "question": request.question,
            "answer": "Internal Server Error",
            "sources": []
        }
