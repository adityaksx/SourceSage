"""
llm/summarizer.py
-----------------
Calls the local Ollama LLM and returns structured knowledge output.

- Uses build_summary_prompt() / build_merge_prompt() from prompt_builder.py.
- No prompt logic lives here — all prompts are in prompt_builder.py.
- Different models are selected automatically based on source_type.
"""

import requests
from llm.prompt_builder import build_summary_prompt, build_merge_prompt

OLLAMA_URL = "http://localhost:11434/api/generate"


# ─────────────────────────────────────────────────────────────────────────────
# Model routing
# ─────────────────────────────────────────────────────────────────────────────

_CODE_TYPES = {
    "github_repo",
    "github_file",
    "code_snippet",
}

_DEEP_ANALYSIS_TYPES = {
    "arxiv_paper",
    "pdf_document",
    "substack_article",
}

_DEFAULT_MODEL = "qwen2.5:7b-instruct"
_CODE_MODEL    = "deepseek-coder:6.7b"
_DEEP_MODEL    = "qwen2.5:14b"


def get_model(source_type: str) -> str:
    if source_type in _CODE_TYPES:
        return _CODE_MODEL
    if source_type in _DEEP_ANALYSIS_TYPES:
        return _DEEP_MODEL
    return _DEFAULT_MODEL


# ─────────────────────────────────────────────────────────────────────────────
# LLM options per model
# ─────────────────────────────────────────────────────────────────────────────

_MODEL_OPTIONS = {
    "deepseek-coder:6.7b":  {"temperature": 0.2, "num_predict": 1200, "top_p": 0.9},
    "qwen2.5:14b":          {"temperature": 0.3, "num_predict": 2000, "top_p": 0.9},
    "qwen2.5:7b-instruct":  {"temperature": 0.3, "num_predict": 1500, "top_p": 0.9},
}

_DEFAULT_OPTIONS = {"temperature": 0.3, "num_predict": 1500, "top_p": 0.9}


# ─────────────────────────────────────────────────────────────────────────────
# Core LLM call
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(prompt: str, source_type: str = "") -> str:
    """
    Send a ready-built prompt string to Ollama.
    Model is chosen from source_type automatically.
    """
    model   = get_model(source_type)
    options = _MODEL_OPTIONS.get(model, _DEFAULT_OPTIONS)

    print(f"  [LLM] model={model}  source={source_type or 'default'}")

    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False, "options": options},
            timeout=240,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "[ERROR] Ollama is not running. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return f"[ERROR] Ollama timed out (model: {model})."
    except Exception as e:
        return f"[ERROR] LLM call failed: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Paragraph-aware chunking
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks:  list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = (current + " " + sent).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = sent.strip()
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [text]


# ─────────────────────────────────────────────────────────────────────────────
# Main summarization entry points
# ─────────────────────────────────────────────────────────────────────────────

def summarize_data(data: dict) -> str:
    """
    Main entry point. Accepts a cleaned processor output dict.
    Builds prompt internally and calls the correct model.
    Handles chunking for long fields automatically.
    """
    source_type = data.get("source_type", "")

    long_fields     = ["transcript", "content", "body", "text", "readme", "ocr_text"]
    needs_chunking  = any(
        isinstance(data.get(f), str) and len(data.get(f, "")) > 3000
        for f in long_fields
    )

    if not needs_chunking:
        prompt = build_summary_prompt(data)
        return call_llm(prompt, source_type)

    # Find longest field to chunk
    target_field = max(
        (f for f in long_fields if isinstance(data.get(f), str) and data.get(f)),
        key=lambda f: len(data.get(f, "")),
        default=None,
    )

    if not target_field:
        return call_llm(build_summary_prompt(data), source_type)

    chunks = chunk_text(data[target_field])
    print(f"  [LLM] Chunking '{target_field}' into {len(chunks)} parts")

    partial_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        print(f"  [LLM] Summarizing chunk {i + 1}/{len(chunks)}...")
        chunk_data = {**data, target_field: chunk}
        partial_summaries.append(call_llm(build_summary_prompt(chunk_data), source_type))

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    print("  [LLM] Merging chunks...")
    return call_llm(build_merge_prompt(partial_summaries), source_type="")


def summarize_text(text: str, source_type: str = "plain_text") -> str:
    """Convenience wrapper for raw string input."""
    return summarize_data({"source_type": source_type, "content": text})


# ─────────────────────────────────────────────────────────────────────────────
# Legacy alias — FIXED: now calls call_llm directly, not summarize_text
# Use only for pre-built prompt strings (e.g. multi-input combine in main.py)
# ─────────────────────────────────────────────────────────────────────────────

def summarize(prompt: str) -> str:
    """
    Legacy alias kept for backwards compatibility.
    Treats input as a ready-built prompt and calls LLM directly.
    Does NOT wrap it in another prompt.
    """
    return call_llm(prompt, source_type="")
