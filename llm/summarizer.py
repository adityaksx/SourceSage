"""
llm/summarizer.py
-----------------
Calls the local Ollama LLM and returns structured knowledge output.

Responsibilities (this file ONLY):
  - Model selection by source_type
  - Raw HTTP call to Ollama API  (now ASYNC via httpx)
  - Paragraph-aware chunking for long content
  - Multi-chunk merge via build_merge_prompt()

Does NOT:
  - Build prompts          → llm/prompt_builder.py
  - Run multi-stage flow   → llm/pipeline.py
  - Classify input type    → llm/llm_classifier.py
  - Clean text             → utils/cleaner.py

Public API consumed by other files:
  main.py      → call_llm(), summarize_data()
  pipeline.py  → call_llm()
"""

from __future__ import annotations

import asyncio
import logging
import httpx

from llm.prompt_builder import build_summary_prompt, build_merge_prompt

try:
    from config import OLLAMA_URL  # type: ignore
except ImportError:
    OLLAMA_URL = "http://localhost:11434/api/generate"

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SEMAPHORE — only 1 Ollama request at a time, prevents HTTP 500 on concurrency
# ─────────────────────────────────────────────────────────────────────────────
_ollama_semaphore = asyncio.Semaphore(1)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL ROUTING
# ─────────────────────────────────────────────────────────────────────────────

_CODE_TYPES: set[str] = {
    "github_repo", "github_file", "github_gist",
    "code_snippet", "notebook",
}

_DEEP_ANALYSIS_TYPES: set[str] = {
    "arxiv_paper", "pdf_document",
    "substack_article", "medium_article",
}

_DEFAULT_MODEL = "qwen2.5:7b-instruct"
_CODE_MODEL    = "deepseek-coder:6.7b"
_DEEP_MODEL    = "qwen2.5:14b"

_MODEL_OPTIONS: dict[str, dict] = {
    _CODE_MODEL:    {"temperature": 0.2, "num_predict": 1200, "top_p": 0.9},
    _DEEP_MODEL:    {"temperature": 0.3, "num_predict": 2000, "top_p": 0.9},
    _DEFAULT_MODEL: {"temperature": 0.3, "num_predict": 1500, "top_p": 0.9},
}

_DEFAULT_OPTIONS: dict = {"temperature": 0.3, "num_predict": 1500, "top_p": 0.9}


def get_model(source_type: str) -> str:
    if source_type in _CODE_TYPES:
        return _CODE_MODEL
    if source_type in _DEEP_ANALYSIS_TYPES:
        return _DEEP_MODEL
    return _DEFAULT_MODEL


# ─────────────────────────────────────────────────────────────────────────────
# OLLAMA HEALTH CHECK  (now async)
# ─────────────────────────────────────────────────────────────────────────────

async def check_ollama() -> tuple[bool, str]:
    """
    Async check whether Ollama is running and reachable.
    Returns (is_running: bool, message: str).
    """
    try:
        base_url = OLLAMA_URL.replace("/api/generate", "")
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{base_url}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return True, f"Ollama running. Available models: {models}"
            return False, f"Ollama returned status {r.status_code}"
    except httpx.ConnectError:
        return False, "Ollama is not running. Start it with: ollama serve"
    except Exception as e:
        return False, f"Ollama health check failed: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# CORE LLM CALL  (now async + semaphore + retry)
# ─────────────────────────────────────────────────────────────────────────────

async def call_llm(prompt: str, source_type: str = "") -> str:
    """
    Async HTTP call to Ollama. Semaphore ensures only 1 call runs at a time.
    Retries up to 3 times on HTTP 500 with backoff.

    Called by:
      - summarize_data()    (Stage 4 final answer)
      - pipeline.py         (Stage 1, 2, 3 intermediate calls)
      - main.py             (multi-input merge)
    """
    model   = get_model(source_type)
    options = _MODEL_OPTIONS.get(model, _DEFAULT_OPTIONS)

    logger.info(f"[LLM] model={model}  source={source_type or 'default'}")
    print(f"  [LLM] model={model}  source={source_type or 'default'}")

    payload = {
        "model":   model,
        "prompt":  prompt,
        "stream":  False,
        "options": options,
    }

    async with _ollama_semaphore:                        # ← KEY FIX: no concurrent calls
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=240) as client:
                    r = await client.post(OLLAMA_URL, json=payload)
                    r.raise_for_status()

                response = r.json().get("response", "").strip()
                if not response:
                    logger.warning(f"[LLM] Empty response from {model}")
                    return "[ERROR] LLM returned an empty response. Try again."

                return response

            except httpx.ConnectError:
                msg = "[ERROR] Ollama is not running. Start it with: ollama serve"
                logger.error(msg)
                return msg                               # no retry — Ollama is off

            except httpx.TimeoutException:
                msg = f"[ERROR] Ollama timed out after 240s (model: {model})."
                logger.error(msg)
                return msg

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    msg = (
                        f"[ERROR] Model '{model}' not found in Ollama.\n"
                        f"Run: ollama pull {model}"
                    )
                    logger.error(msg)
                    return msg                           # no retry — model missing

                if status == 500 and attempt < 2:
                    wait = 2 * (attempt + 1)
                    logger.warning(f"[LLM] HTTP 500, retry {attempt+1}/3 in {wait}s...")
                    await asyncio.sleep(wait)            # ← backoff before retry
                    continue

                msg = f"[ERROR] Ollama HTTP error: {e}"
                logger.error(msg)
                return msg

            except Exception as e:
                msg = f"[ERROR] LLM call failed: {e}"
                logger.error(msg)
                return msg

    return "[ERROR] LLM call failed after 3 retries."


# ─────────────────────────────────────────────────────────────────────────────
# PARAGRAPH-AWARE CHUNKING  (unchanged — no async needed here)
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split text into chunks ≤ max_chars at paragraph/sentence boundaries."""
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text]

    chunks:  list[str] = []
    current: str       = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
                current = ""

            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = (current + " " + sent).strip() if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [text]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SUMMARIZATION ENTRY POINTS  (now async)
# ─────────────────────────────────────────────────────────────────────────────

async def summarize_data(data: dict) -> str:
    """
    Async entry point. Accepts cleaned + enriched processor output dict.
    Handles chunking automatically.

    Called by: main.py → _run_pipeline()
    """
    source_type = data.get("source_type", "")

    _LONG_FIELDS = ["transcript", "content", "body", "text", "readme", "ocr_text"]

    needs_chunking = any(
        isinstance(data.get(f), str) and len(data.get(f, "")) > 3000
        for f in _LONG_FIELDS
    )

    if not needs_chunking:
        prompt = build_summary_prompt(data)
        return await call_llm(prompt, source_type)          # ← await

    target_field = max(
        (f for f in _LONG_FIELDS if isinstance(data.get(f), str) and data.get(f)),
        key=lambda f: len(data.get(f, "")),
        default=None,
    )

    if not target_field:
        return await call_llm(build_summary_prompt(data), source_type)

    chunks = chunk_text(data[target_field])
    logger.info(f"[LLM] Chunking '{target_field}' into {len(chunks)} parts")
    print(f"  [LLM] Chunking '{target_field}' into {len(chunks)} parts")

    partial_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        print(f"  [LLM] Summarizing chunk {i + 1}/{len(chunks)}...")
        chunk_data = {**data, target_field: chunk}
        partial = await call_llm(build_summary_prompt(chunk_data), source_type)  # ← await
        if not partial.startswith("[ERROR]"):
            partial_summaries.append(partial)

    if not partial_summaries:
        return "[ERROR] All chunk summaries failed."
    if len(partial_summaries) == 1:
        return partial_summaries[0]

    print("  [LLM] Merging chunks into final answer...")
    return await call_llm(build_merge_prompt(partial_summaries), source_type="")  # ← await


async def summarize_text(text: str, source_type: str = "plain_text") -> str:
    """Async convenience wrapper for raw string input."""
    if not text or not text.strip():
        return "No text provided."
    return await summarize_data({"source_type": source_type, "content": text})


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY ALIAS
# ─────────────────────────────────────────────────────────────────────────────

async def summarize(prompt: str) -> str:
    """Legacy alias — kept for backwards compatibility."""
    return await call_llm(prompt, source_type="")


# ─────────────────────────────────────────────────────────────────────────────
# CLI  (python -m llm.summarizer)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def main():
        print("Checking Ollama...")
        ok, msg = await check_ollama()
        print(f"  {'✅' if ok else '❌'} {msg}\n")

        if ok:
            print("Quick test — summarizing plain text:")
            result = await summarize_text(
                "FastAPI is a modern Python web framework for building APIs. "
                "It uses type hints for validation and generates OpenAPI docs automatically.",
                source_type="plain_text"
            )
            print(result)

    asyncio.run(main())
