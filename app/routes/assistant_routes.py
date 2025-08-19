# # app/routes/assistant_routes.py
# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session

# from app.models.assistant import AssistantRequest, AssistantResponse
# from app.services.intent_classifier import classify_intent
# from app.services.hrmis_service import handle_hrmis_action
# from app.services.pdf_service import handle_pdf_question, find_relevant_chunks, generate_clarifying_questions
# from app.services.groq_service import ask_groq
# from app.dependencies import get_db 

# router = APIRouter()

# @router.post("/", response_model=AssistantResponse)
# async def process_assistant(request: AssistantRequest, db: Session = Depends(get_db)):
#     intent = classify_intent(request.message)

#     # Always check PDF relevance if intent is general or pdf-related keywords
#     pdf_relevant_chunks = find_relevant_chunks(request.message, db)
    
#     if pdf_relevant_chunks:
#         # Step 1: Try to generate clarifying questions
#         clarifying_qs = generate_clarifying_questions(request.message, db)

#         if clarifying_qs:
#             # Return clarifying questions instead of direct answer
#             reply = "I found multiple possible references. Could you clarify?\n\n" + "\n".join(
#                 [f"- {q}" for q in clarifying_qs]
#             )
#             return AssistantResponse(reply=reply, intent="clarification_needed")

#         # Step 2: If clear enough, return direct grounded answer
#         result = await handle_pdf_question(message=request.message, db=db)
#         return AssistantResponse(reply=result["reply"], intent="pdf_query")

#     # Otherwise, HRMIS-related intents
#     if intent in ["leave_request", "payslip", "attendance", "employee"]:
#         result = await handle_hrmis_action(
#             intent_name=intent,
#             message=request.message,
#             user_id=request.user_id,
#             token_api=request.token_api,
#             db=db
#         )
#         return AssistantResponse(reply=result["reply"], intent=result["intent"])

#     # Fallback to Groq AI
#     reply = await ask_groq(request.message)
#     return AssistantResponse(reply=reply, intent=intent)

# app/routes/assistant_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.vector_store import search_documents
from app.services.llm import generate_answer
import traceback
import logging

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask_assistant(request: QueryRequest):
    try:
        results = search_documents(request.question, top_k=5)
        if not results:
            raise HTTPException(status_code=404, detail="No relevant documents found")

        answer_data = generate_answer(request.question, results)
        return {
            "question": request.question,
            "answer": answer_data["answer"],
            "sources": answer_data["sources"]
        }

    except Exception as e:
        logging.error("Error in /assistant/ask:\n%s", traceback.format_exc())
        detail_message = str(e) if str(e) else "Internal Server Error"
        raise HTTPException(status_code=500, detail=detail_message)
