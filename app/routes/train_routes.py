# app/routes/train_routes.py
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.vector_store import insert_document

router = APIRouter()

class TrainMetadata(BaseModel):
    filename: Optional[str] = ""
    page: Optional[int] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    api_id: Optional[str] = None
    endpoint: Optional[str] = None

class TrainRequest(BaseModel):
    text: str = Field(..., description="The content to train the AI on")
    metadata: TrainMetadata

@router.post("/train")
async def train_text(request: TrainRequest = Body(...)):
    """
    Add new text to the vector store for training/updating knowledge base.
    Optional metadata: filename, page, tags, api_id, endpoint.
    """
    try:
        filename = request.metadata.filename
        page = request.metadata.page
        tags = request.metadata.tags
        api_id = request.metadata.api_id
        endpoint = request.metadata.endpoint

        if api_id:
            tags.append(f"api:{api_id}")

        insert_document(request.text, filename=filename, page=page, tags=tags, endpoint=endpoint)

        return {
            "message": "Text successfully added to vector store",
            "text_preview": request.text[:100] + ("..." if len(request.text) > 100 else ""),
            "tags": tags,
            "endpoint": endpoint
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error training vector store: {str(e)}")

