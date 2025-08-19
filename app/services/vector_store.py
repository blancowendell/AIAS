# app/services/vector_store.py
import os
import faiss
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader

FAISS_INDEX_PATH = "app/data/faiss_index.index"
FAISS_MAPPING_PATH = "app/data/faiss_mapping.npy"
os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """Split long text into overlapping chunks for better embedding."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

class VectorStore:
    def __init__(self):
        self.index = None
        self.mapping = []  # list of dicts: {"text":..., "filename":..., "page":...}
        self._load_index()

    def _load_index(self):
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(FAISS_MAPPING_PATH):
            self.index = faiss.read_index(FAISS_INDEX_PATH)
            self.mapping = np.load(FAISS_MAPPING_PATH, allow_pickle=True).tolist()
        else:
            self.index = faiss.IndexFlatL2(384)
            self.mapping = []

    def save_index(self):
        faiss.write_index(self.index, FAISS_INDEX_PATH)
        np.save(FAISS_MAPPING_PATH, np.array(self.mapping, dtype=object))

    def add_texts(self, texts: List[Dict]):
        all_chunks = []
        metadata = []

        for t in texts:
            text_chunks = chunk_text(t["text"])
            for chunk in text_chunks:
                all_chunks.append(chunk)
                metadata.append({
                    "text": chunk,
                    "filename": t.get("filename", ""),
                    "page": t.get("page", None)
                })

        if all_chunks:
            embeddings = embedding_model.encode(all_chunks).astype("float32")
            self.index.add(embeddings)
            self.mapping.extend(metadata)
            self.save_index()

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if len(self.mapping) == 0:
            return []

        query_embedding = embedding_model.encode([query]).astype("float32")
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.mapping):
                result = self.mapping[idx].copy()
                result["score"] = float(distances[0][i])
                results.append(result)
        return results

# Singleton instance
vector_store = VectorStore()

def insert_document(text: str, filename: str = "", page: int = None):
    vector_store.add_texts([{"text": text, "filename": filename, "page": page}])

def search_documents(query: str, top_k: int = 5):
    return vector_store.search(query, top_k)

# --- PDF upload route ---
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()
UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        reader = PdfReader(file_path)
        pages_processed = 0

        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                # Chunk the page into smaller parts for better embedding
                insert_document(text, filename=file.filename, page=i)
                pages_processed += 1

        if pages_processed == 0:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF")

        return {
            "message": "PDF uploaded and processed successfully",
            "pages": pages_processed,
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
