# app/services/vector_store.py
import os
import faiss
import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
from fastapi import APIRouter, UploadFile, File, HTTPException

# Paths
FAISS_INDEX_PATH = "app/data/faiss_index.index"
FAISS_MAPPING_PATH = "app/data/faiss_mapping.npy"
UPLOAD_DIR = "app/uploads"
os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Text chunking
def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

# VectorStore class
class VectorStore:
    def __init__(self):
        self.index = None
        self.mapping = []  # {"text":..., "filename":..., "page":..., "tags":[...]}
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
                    "page": t.get("page", None),
                    "tags": t.get("tags", [])
                })

        if all_chunks:
            embeddings = embedding_model.encode(all_chunks).astype("float32")
            self.index.add(embeddings)
            self.mapping.extend(metadata)
            self.save_index()

    def search(self, query: str, top_k: int = 5, similarity_threshold: float = 0.5, tag_filter: Optional[str] = None) -> List[Dict]:
        if len(self.mapping) == 0:
            return []

        query_embedding = embedding_model.encode([query]).astype("float32")
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= len(self.mapping):
                continue
            similarity = 1 / (1 + float(distances[0][i]))  # L2 -> similarity 0-1
            entry = self.mapping[idx].copy()
            entry["score"] = similarity
            if similarity < similarity_threshold:
                continue
            if tag_filter and tag_filter not in entry.get("tags", []):
                continue
            results.append(entry)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

# Singleton
vector_store = VectorStore()

# Helpers
def insert_document(text: str, filename: str = "", page: Optional[int] = None, tags: Optional[List[str]] = None):
    vector_store.add_texts([{"text": text, "filename": filename, "page": page, "tags": tags or []}])

def search_documents(query: str, top_k: int = 5, similarity_threshold: float = 0.5, tag_filter: Optional[str] = None):
    return vector_store.search(query, top_k=top_k, similarity_threshold=similarity_threshold, tag_filter=tag_filter)


# PDF Upload Route
router = APIRouter()

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
                insert_document(text, filename=file.filename, page=i, tags=["document"])
                pages_processed += 1

        if pages_processed == 0:
            raise HTTPException(status_code=400, detail="No extractable text found")

        return {"message": "PDF processed successfully", "pages": pages_processed, "filename": file.filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
