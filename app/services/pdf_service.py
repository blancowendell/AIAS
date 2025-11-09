from sqlalchemy.orm import Session
from app.database.models.pdf import PDFChunk
import logging
import string
from collections import Counter
import re

def normalize_text(text: str) -> str:
    """Lowercase, remove punctuation, and collapse whitespace for matching."""
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()

def compute_overlap_score(
    query_words: list[str],
    chunk_words: list[str],
    chunk_keywords: list[str],
    section_title: str,
    subsection_title: str | None = None
) -> float:
    """
    Count overlap between query and chunk, with extra weight for keywords,
    section, and subsection matches.
    """
    counter = Counter(chunk_words)
    score = sum((counter & Counter(query_words)).values())
    
    score += sum(2 for w in query_words if w in chunk_keywords)
    
    section_words = normalize_text(section_title).split()
    score += sum(1.5 for w in query_words if w in section_words)

    if subsection_title:
        subsection_words = normalize_text(subsection_title).split()
        score += sum(1 for w in query_words if w in subsection_words)
    
    return score

def find_relevant_chunks(message: str, db: Session, top_n: int = 5):
    """
    Find PDF chunks most relevant to the user message, considering keywords,
    section, and subsection. Searches across ALL PDFs since pdf_id is removed.
    """
    normalized_msg = normalize_text(message)
    query_words = normalized_msg.split()

    chunks = db.query(PDFChunk).all()

    scored_chunks = []
    for chunk in chunks:
        chunk_words = normalize_text(chunk.pc_chunk_text).split()
        chunk_keywords = chunk.pc_keywords if chunk.pc_keywords else []
        section_title = chunk.pc_section_title or ""
        subsection_title = getattr(chunk, "pc_subsection_title", None)  # optional
        score = compute_overlap_score(query_words, chunk_words, chunk_keywords, section_title, subsection_title)
        if score > 0:
            scored_chunks.append({
                "score": score,
                "section": section_title,
                "subsection": subsection_title,
                "text": chunk.pc_chunk_text,
                "page": chunk.pc_page_number
            })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)

    return scored_chunks[:top_n]

def extract_snippet(chunk_text: str, query_words: list[str], window: int = 50) -> str:
    """Return a snippet of the chunk around the first matched keyword, highlighting matches."""
    chunk_lower = chunk_text.lower()
    for word in query_words:
        idx = chunk_lower.find(word)
        if idx != -1:
            start = max(0, idx - window)
            end = min(len(chunk_text), idx + window)
            while start > 0 and chunk_text[start] != " ":
                start -= 1
            while end < len(chunk_text) and chunk_text[end] != " ":
                end += 1
            snippet = chunk_text[start:end].strip()
            for w in query_words:
                snippet = re.sub(fr"\b({re.escape(w)})\b", r"**\1**", snippet, flags=re.IGNORECASE)
            return snippet
    return chunk_text[:200]

async def handle_pdf_question(message: str, db: Session) -> dict:
    """
    Respond strictly based on stored PDF chunks.
    Uses sections, subsections, page numbers, and keyword highlighting.
    """
    try:
        chunks_info = find_relevant_chunks(message, db)
        if not chunks_info:
            return {"reply": "I could not find relevant information in the PDF.", "source": "pdf", "chunks_found": 0}
        
        normalized_msg = normalize_text(message)
        query_words = normalized_msg.split()
        
        snippets = []
        for c in chunks_info:
            snippet = extract_snippet(c["text"], query_words)
            section_info = f"Section: {c['section']}" if c['section'] else ""
            subsection_info = f"Subsection: {c['subsection']}" if c.get("subsection") else ""
            page_info = f"Page: {c['page']}" if c['page'] else ""
            context = " | ".join(filter(None, [section_info, subsection_info, page_info]))
            snippets.append(f"{context}\n{snippet}")

        reply = "\n\n---\n\n".join(snippets)
        
        return {"reply": reply, "source": "pdf", "chunks_found": len(chunks_info)}
    
    except Exception as e:
        logging.error(f"Error in PDF QA service: {e}")
        return {"reply": f"Error processing PDF question: {e}", "source": "pdf", "chunks_found": 0}

def generate_clarifying_questions(message: str, db: Session, max_q: int = 5):
    """
    Generate clarifying questions based on candidate PDF chunks.
    Useful when the user query is vague (e.g., 'What are the attachments?').
    """
    chunks_info = find_relevant_chunks(message, db)
    if not chunks_info:
        return []

    keywords_of_interest = ["attachment", "form", "document", "policy", "procedure"]
    
    questions = []
    for c in chunks_info:
        text = normalize_text(c["text"])
        for kw in keywords_of_interest:
            if kw in text and len(questions) < max_q:
                section = c["section"] or "this section"
                page = f" (Page {c['page']})" if c["page"] else ""
                q = f"Do you mean the {kw} mentioned in {section}{page}?"
                if q not in questions:
                    questions.append(q)

    # Fallback if no keyword-based questions found
    if not questions:
        for c in chunks_info[:max_q]:
            section = c["section"] or "this section"
            q = f"Are you asking about details in {section} (Page {c['page']})?"
            if q not in questions:
                questions.append(q)

    return questions
