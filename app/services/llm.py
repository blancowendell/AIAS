# app/services/llm.py
import logging
from transformers import pipeline

# Initialize summarization pipeline
try:
    summarizer = pipeline(
        "summarization",
        model="facebook/bart-large-cnn",
        device=-1  # -1 for CPU
    )
except Exception as e:
    logging.error("Error initializing summarizer: %s", e)
    summarizer = None

def generate_answer(question: str, results: list) -> dict:
    """
    Generate a clean, summarized answer from vector search results.
    - Removes duplicates
    - Merges overlapping snippets
    - Summarizes each snippet
    - Combines into one coherent answer
    """
    if not results:
        return {"answer": "No relevant content found.", "sources": []}

    seen_texts = set()
    final_answer_parts = []
    sources_used = []

    for snippet in results:
        text = snippet.get("text", "").strip()
        filename = snippet.get("filename", "")
        page = snippet.get("page", None)

        if not text or text in seen_texts:
            continue  # skip duplicates
        seen_texts.add(text)

        try:
            if summarizer is None:
                summary_text = text  # fallback
            else:
                # Summarize each snippet individually
                summary = summarizer(
                    text,
                    max_length=150,
                    min_length=30,
                    do_sample=False
                )
                summary_text = summary[0]["summary_text"].strip()
        except Exception as e:
            logging.error("Error summarizing snippet: %s", e)
            summary_text = text  # fallback to raw text

        final_answer_parts.append(summary_text)
        sources_used.append({"filename": filename, "page": page})

    # Combine snippets intelligently
    combined_answer = " ".join(final_answer_parts)

    # Optional: truncate to reasonable length if too long
    if len(combined_answer) > 1000:
        combined_answer = combined_answer[:1000] + "..."

    return {
        "answer": combined_answer,
        "sources": sources_used
    }
