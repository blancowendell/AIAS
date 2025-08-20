# app/routes/assistant_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.vector_store import search_documents
from app.services.llm import generate_answer
import logging
import traceback
from collections import Counter

router = APIRouter()

class QueryRequest(BaseModel):
    question: str


CASUAL_GREETINGS = ["hi", "hello", "hey", "good morning", "good afternoon"]

def detect_intent(question: str) -> str:
    q = question.lower().strip()
    # Simple greetings
    if any(greet in q for greet in CASUAL_GREETINGS):
        return "greeting"
    # Future: add more intents (policy, reward, leave, etc.)
    return "document"  # default: search documents

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

        # Step 1: initial search (no tag filter)
        initial_results = search_documents(
            question,
            top_k=5,
            similarity_threshold=0.5
        )

        if not initial_results:
            # fallback: return most similar even if low similarity
            initial_results = search_documents(
                question,
                top_k=5,
                similarity_threshold=0.0
            )

        # Step 2: auto-detect most common tag from top results
        tags = []
        for r in initial_results:
            tags.extend(r.get("tags", []))
        tag_filter = Counter(tags).most_common(1)[0][0] if tags else None

        # Step 3: refined search with detected tag
        refined_results = search_documents(
            question,
            top_k=5,
            similarity_threshold=0.5,
            tag_filter=tag_filter
        )

        # Fallback to initial if refined returns nothing
        final_results = refined_results if refined_results else initial_results

        if not final_results:
            return {
                "question": question,
                "answer": "Sorry, I could not find relevant information.",
                "sources": []
            }

        # Step 4: generate summarized answer
        answer_data = generate_answer(question, final_results)

        return {
            "question": question,
            "answer": answer_data["answer"],
            "sources": answer_data["sources"]
        }

    except Exception as e:
        logging.error("Error in /assistant/ask:\n%s", traceback.format_exc())
        return {
            "question": request.question,
            "answer": "Internal Server Error",
            "sources": []
        }


# @router.post("/ask")
# async def ask_assistant(request: QueryRequest):
#     try:
#         question = request.question.strip()
#         if not question:
#             raise HTTPException(status_code=400, detail="Question cannot be empty")

#         # Step 1: initial search (no tag filter)
#         initial_results = search_documents(
#             question,
#             top_k=5,
#             similarity_threshold=0.5  # adjust as needed
#         )

#         if not initial_results:
#             # fallback: return most similar even if low similarity
#             initial_results = search_documents(
#                 question,
#                 top_k=5,
#                 similarity_threshold=0.0
#             )

#         # Step 2: auto-detect most common tag from top results
#         tags = []
#         for r in initial_results:
#             tags.extend(r.get("tags", []))
#         tag_filter = Counter(tags).most_common(1)[0][0] if tags else None

#         # Step 3: refined search with detected tag
#         refined_results = search_documents(
#             question,
#             top_k=5,
#             similarity_threshold=0.5,
#             tag_filter=tag_filter
#         )

#         # Fallback to initial if refined returns nothing
#         final_results = refined_results if refined_results else initial_results

#         if not final_results:
#             raise HTTPException(status_code=404, detail="No relevant documents found")

#         # Step 4: generate summarized answer
#         answer_data = generate_answer(question, final_results)

#         return {
#             "question": question,
#             "answer": answer_data["answer"],
#             "sources": answer_data["sources"]
#         }

#     except Exception as e:
#         logging.error("Error in /assistant/ask:\n%s", traceback.format_exc())
#         detail_message = str(e) if str(e) else "Internal Server Error"
#         raise HTTPException(status_code=500, detail=detail_message)
