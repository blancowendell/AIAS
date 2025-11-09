# app/services/llm.py
import logging
from transformers import pipeline
import json

try:
    summarizer = pipeline(
        "summarization",
        model="facebook/bart-large-cnn",
        device=-1
    )
except Exception as e:
    logging.error("Error initializing summarizer: %s", e)
    summarizer = None


def generate_answer(question: str, results: list, style: str = "default") -> dict:
    """
    Generate a clean, summarized answer from vector search results.

    Args:
        question (str): User's query.
        results (list): List of dicts with keys like {"text", "filename", "page"}.
        style (str): Controls answer tone:
            - "default": Neutral summarization.
            - "conversational": Friendly, assistant-like tone.
            - "formal": Polished, professional tone.
            - "bullet": Structured list style.

    Returns:
        dict: { "answer": str, "sources": list }
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
            continue
        seen_texts.add(text)

        try:
            if summarizer is None:
                summary_text = text
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
            summary_text = text

        final_answer_parts.append(summary_text)
        sources_used.append({"filename": filename, "page": page})

    # Combine answers
    combined_answer = " ".join(final_answer_parts)
    if len(combined_answer) > 1000:
        combined_answer = combined_answer[:1000] + "..."

    # === Apply Styles ===
    if style == "conversational":
        combined_answer = f"Here’s what I found regarding your question: {combined_answer}"
    elif style == "formal":
        combined_answer = f"Based on the available documentation, the following information may be relevant: {combined_answer}"
    elif style == "bullet":
        combined_answer = "Here’s a breakdown:\n" + "\n".join(
            [f"- {part}" for part in final_answer_parts]
        )

    return {"answer": combined_answer.strip(), "sources": sources_used}


def api_json_to_text(api_id: str, api_json: dict) -> str:
    """
    Convert API JSON to plain values.
    Tries to extract human-readable info from API responses.
    """
    try:
        if isinstance(api_json, dict):
            # Common API response structures
            if "Result" in api_json:
                return str(api_json["Result"])
            if "result" in api_json:
                return str(api_json["result"])
            if "data" in api_json:
                return json.dumps(api_json["data"], indent=2)
            if "msg" in api_json:
                return api_json["msg"]

        if isinstance(api_json, list):
            return json.dumps(api_json, indent=2)

        return str(api_json)

    except Exception as e:
        logging.error("Error parsing API JSON for %s: %s", api_id, e)
        return "Could not parse API response."
