# # app/routes/pdf_routes.py
# from fastapi import APIRouter, UploadFile, File, Depends
# from sqlalchemy.orm import Session
# from app.database.database import SessionLocal
# from app.database.models.pdf import PDFDocument, PDFChunk
# from datetime import datetime
# from typing import List
# import os
# import uuid
# import fitz  # PyMuPDF for PDF text extraction
# import re
# from collections import Counter

# router = APIRouter()

# # Dependency to get DB session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # Normalize text for tokenization
# def normalize_text(text: str) -> str:
#     return re.sub(r'[^\w\s]', '', text.lower())

# # Extract keywords (top N frequent words)
# def extract_keywords(text: str, top_n: int = 10):
#     words = [w.lower() for w in re.findall(r"\b\w+\b", text) if len(w) > 2]
#     most_common = [w for w, _ in Counter(words).most_common(top_n)]
#     return most_common

# # Split text into word-based chunks
# def split_text_into_chunks(text: str, chunk_size: int = 200) -> List[str]:
#     words = text.split()
#     chunks = []
#     for i in range(0, len(words), chunk_size):
#         chunks.append(" ".join(words[i:i+chunk_size]))
#     return chunks

# # Detect headings and bullets in page text
# def detect_headings_and_sections(text: str):
#     """
#     Returns list of (section_title, section_text)
#     Splits by headings (ALL CAPS or numbered) and groups bullets under headings
#     """
#     lines = [line.strip() for line in text.split("\n") if line.strip()]
#     sections = []
#     current_title = "Introduction"
#     current_text = []

#     heading_pattern = re.compile(r"(^\d+\..+)|(^[A-Z\s]{3,100}$)")

#     for line in lines:
#         if heading_pattern.match(line):
#             if current_text:
#                 sections.append((current_title, " ".join(current_text)))
#             current_title = line
#             current_text = []
#         else:
#             current_text.append(line)
#     if current_text:
#         sections.append((current_title, " ".join(current_text)))
#     return sections

# @router.post("/upload-pdf/")
# async def upload_pdf(
#     file: UploadFile = File(...),
#     uploaded_by: str | None = None,
#     db: Session = Depends(get_db)
# ):
#     os.makedirs("uploads/pdfs", exist_ok=True)
#     file_path = f"uploads/pdfs/{uuid.uuid4()}_{file.filename}"

#     with open(file_path, "wb") as f:
#         f.write(await file.read())

#     # Open PDF
#     doc = fitz.open(file_path)

#     # Insert PDF metadata
#     pdf_doc = PDFDocument(
#         pd_title=file.filename,
#         pd_file_path=file_path,
#         pd_uploaded_by=uploaded_by,
#         pd_uploaded_at=datetime.utcnow()
#     )
#     db.add(pdf_doc)
#     db.commit()
#     db.refresh(pdf_doc)

#     chunk_index = 0
#     total_chunks = 0

#     # Heuristics patterns
#     heading_pattern = re.compile(r"(^\d+\..+)|(^[A-Z\s]{3,100}$)")
#     bullet_pattern = re.compile(r"^[-*•]\s+")
#     attachment_pattern = re.compile(r"attachment\s+[A-Z]", re.IGNORECASE)

#     # Iterate per page
#     for page_num, page in enumerate(doc, start=1):
#         lines = [line.strip() for line in page.get_text().split("\n") if line.strip()]
#         current_section = "Introduction"
#         parent_section = None
#         current_text = []

#         for line in lines:
#             # Detect heading
#             if heading_pattern.match(line):
#                 if current_text:
#                     # Chunk previous section
#                     chunks = split_text_into_chunks(" ".join(current_text), chunk_size=200)
#                     for chunk_text in chunks:
#                         tokens = normalize_text(chunk_text).split()
#                         keywords = extract_keywords(chunk_text)
#                         chunk = PDFChunk(
#                             pc_pdf_id=pdf_doc.pd_id,
#                             pc_chunk_text=chunk_text,
#                             pc_page_number=page_num,
#                             pc_chunk_index=chunk_index,
#                             pc_section_title=current_section,
#                             pc_parent_section_title=parent_section,
#                             pc_is_list=False,
#                             pc_is_table=False,
#                             pc_has_attachment_ref=bool(attachment_pattern.search(chunk_text)),
#                             pc_keywords=keywords,
#                             pc_tokens=tokens,
#                             pc_created_at=datetime.utcnow()
#                         )
#                         db.add(chunk)
#                         chunk_index += 1
#                         total_chunks += 1
#                 # Update section titles
#                 parent_section = current_section
#                 current_section = line
#                 current_text = []
#             else:
#                 current_text.append(line)

#         # Add remaining text as chunks
#         if current_text:
#             chunks = split_text_into_chunks(" ".join(current_text), chunk_size=200)
#             for chunk_text in chunks:
#                 tokens = normalize_text(chunk_text).split()
#                 keywords = extract_keywords(chunk_text)
#                 is_list = bool(bullet_pattern.search(chunk_text))
#                 chunk = PDFChunk(
#                     pc_pdf_id=pdf_doc.pd_id,
#                     pc_chunk_text=chunk_text,
#                     pc_page_number=page_num,
#                     pc_chunk_index=chunk_index,
#                     pc_section_title=current_section,
#                     pc_parent_section_title=parent_section,
#                     pc_is_list=is_list,
#                     pc_is_table=False,
#                     pc_has_attachment_ref=bool(attachment_pattern.search(chunk_text)),
#                     pc_keywords=keywords,
#                     pc_tokens=tokens,
#                     pc_created_at=datetime.utcnow()
#                 )
#                 db.add(chunk)
#                 chunk_index += 1
#                 total_chunks += 1

#     db.commit()

#     return {
#         "message": "PDF uploaded and intelligently processed",
#         "pdf_id": pdf_doc.pd_id,
#         "chunks": total_chunks
#     }

# app/routes/pdf_routes.py
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from PyPDF2 import PdfReader
from app.services.vector_store import insert_document

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
