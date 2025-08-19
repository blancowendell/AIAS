# app/services/llm.py
# app/services/llm.py
import logging
from transformers import pipeline
from app.services.vector_store import search_documents

# Initialize summarization pipeline
try:
    summarizer = pipeline(
        "summarization",
        model="facebook/bart-large-cnn",  # you can change to any HF summarization model
        device=-1  # -1 for CPU, or 0 for GPU
    )
except Exception as e:
    logging.error("Error initializing summarizer: %s", e)
    summarizer = None

def generate_answer(question: str, results: list) -> dict:
    """
    Generate a clean, summarized answer from vector search results.
    Each snippet is summarized individually, then combined.
    """
    if not results:
        return {"answer": "No relevant content found.", "sources": []}

    final_answer_parts = []
    sources_used = []

    for snippet in results:
        text = snippet.get("text", "")
        filename = snippet.get("filename", "")
        page = snippet.get("page", None)

        if not text.strip():
            continue

        try:
            if summarizer is None:
                summary_text = text  # fallback: use raw text if summarizer failed
            else:
                summary = summarizer(
                    text,
                    max_length=150,
                    min_length=30,
                    do_sample=False
                )
                summary_text = summary[0]["summary_text"].strip()
        except Exception as e:
            logging.error("Error summarizing snippet: %s", e)
            summary_text = f"Error summarizing snippet: {str(e)}"

        final_answer_parts.append(summary_text)
        sources_used.append({"filename": filename, "page": page})

    final_answer = " ".join(final_answer_parts)
    return {
        "answer": final_answer,
        "sources": sources_used
    }
