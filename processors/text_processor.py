"""
text_processor.py
-----------------
Processes plain text / notes / markdown / code snippets / JSON
passed directly by the user (not a URL).
"""

from __future__ import annotations
from utils.source_detector import _detect_raw_text


def process_text(text: str) -> dict:
    """
    Accepts raw user-typed or pasted text.
    Detects sub-type (plain_text, code_snippet, markdown, json_data)
    and returns a structured dict ready for cleaning + LLM.
    """
    if not text or not text.strip():
        return {"error": "Empty text input"}

    text = text.strip()
    subtype = _detect_raw_text(text)

    return {
        "source_type": subtype,
        "content":     text,
        "title":       text[:80].replace("\n", " "),   # first line as title
        "char_count":  len(text),
        "word_count":  len(text.split()),
    }
