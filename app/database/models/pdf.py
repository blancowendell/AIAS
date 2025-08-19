from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class PDFDocument(Base):
    __tablename__ = "pdf_documents"

    pd_id = Column(Integer, primary_key=True, index=True)
    pd_title = Column(String(255), nullable=False)
    pd_file_path = Column(String(255), nullable=False)
    pd_uploaded_by = Column(String(50), nullable=True)
    pd_uploaded_at = Column(DateTime, default=datetime.utcnow)
    pd_description = Column(Text, nullable=True)
    pd_is_active = Column(Boolean, default=True)

    chunks = relationship("PDFChunk", back_populates="pdf", cascade="all, delete-orphan")


class PDFChunk(Base):
    __tablename__ = "pdf_chunks"

    pc_id = Column(Integer, primary_key=True, index=True)
    pc_pdf_id = Column(Integer, ForeignKey("pdf_documents.pd_id"), nullable=False)
    pc_chunk_text = Column(Text, nullable=False)
    pc_page_number = Column(Integer, nullable=True)
    pc_chunk_index = Column(Integer, nullable=True)
    pc_section_title = Column(String(255), nullable=True)       # section heading
    pc_subsection_title = Column(String(255), nullable=True)    # subsection heading
    pc_parent_section_title = Column(String(255), nullable=True) # parent section for context
    pc_is_list = Column(Boolean, default=False)                # bullet / numbered list
    pc_is_table = Column(Boolean, default=False)               # table-like content
    pc_has_attachment_ref = Column(Boolean, default=False)     # mentions attachments
    pc_keywords = Column(JSON, nullable=True)                  # extracted keywords
    pc_tokens = Column(JSON, nullable=True)                    # tokenized words
    pc_created_at = Column(DateTime, default=datetime.utcnow)

    pdf = relationship("PDFDocument", back_populates="chunks")



class PDFEmbedding(Base):
    __tablename__ = "pdf_embeddings"

    pe_id = Column(Integer, primary_key=True, index=True)
    pe_chunk_id = Column(Integer, ForeignKey("pdf_chunks.pc_id"), nullable=False)
    pe_embedding = Column(JSON, nullable=False)
    pe_created_at = Column(DateTime, default=datetime.utcnow)
