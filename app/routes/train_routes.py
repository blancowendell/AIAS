# app/routes/train_routes.py
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.vector_store import insert_document

router = APIRouter()

# Updated Pydantic model
class TrainMetadata(BaseModel):
    filename: Optional[str] = ""
    page: Optional[int] = None
    tags: Optional[List[str]] = Field(default_factory=list)

class TrainRequest(BaseModel):
    text: str = Field(..., description="The content to train the AI on")
    metadata: TrainMetadata

@router.post("/train")
async def train_text(request: TrainRequest = Body(...)):
    """
    Add new text to the vector store for training/updating knowledge base.
    Expects metadata with optional filename, page, and tags.
    """
    try:
        filename = request.metadata.filename
        page = request.metadata.page
        tags = request.metadata.tags

        # Insert the document into the vector store
        insert_document(request.text, filename=filename, page=page, tags=tags)

        return {
            "message": "Text successfully added to vector store",
            "text_preview": request.text[:100] + ("..." if len(request.text) > 100 else ""),
            "tags": tags
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error training vector store: {str(e)}")
