"""
main.py
-------
Central router for the AI Resource Agent.

Handles three input types:
  1. URL / link       → detect source → run processor → clean → LLM
  2. Plain text       → text_processor → clean → LLM
  3. Uploaded image   → image_processor (OCR) → clean → LLM
  4. Mixed input      → text + images + links all together in one message
"""

from __future__ import annotations
import os
from pathlib import Path

from utils.source_detector  import detect_source
from utils.cleaner          import clean_processor_output
from llm.prompt_builder     import build_summary_prompt
from llm.summarizer         import summarize
from database.db            import save_resource, init_db

# ── Processors ──────────────────────────────
from processors.youtube_processor   import process_youtube
from processors.github_processor    import process_github
from processors.web_processor       import process_web
from processors.instagram_processor import process_instagram
from processors.text_processor      import process_text
from processors.image_processor     import process_image


# ─────────────────────────────────────────────
# SINGLE URL
# ─────────────────────────────────────────────

def process_link(url: str) -> str:
    """Process a single URL and return LLM summary."""
    source   = detect_source(url)
    raw_data = None

    try:
        if source.startswith("youtube"):
            raw_data = process_youtube(url)

        elif source.startswith("instagram"):
            raw_data = process_instagram(url)

        elif source.startswith("github"):
            raw_data = process_github(url)

        elif source in ("web", "medium_article", "substack_article",
                        "notion_page", "arxiv_paper"):
            raw_data = process_web(url)

        else:
            raw_data = process_web(url)   # best-effort fallback

        cleaned    = clean_processor_output(raw_data)
        prompt     = build_summary_prompt(cleaned)
        llm_output = summarize(prompt)

        save_resource(
            source      = source,
            url         = url,
            title       = raw_data.get("title", ""),
            raw_input   = {"url": url},
            raw_data    = raw_data,
            cleaned_data= cleaned,
            llm_output  = llm_output,
        )
        return llm_output

    except Exception as e:
        save_resource(
            source    = source,
            url       = url,
            raw_input = {"url": url},
            status    = "error",
            error     = str(e),
        )
        return f"Error processing link: {e}"


# ─────────────────────────────────────────────
# PLAIN TEXT
# ─────────────────────────────────────────────

def process_text_input(text: str) -> str:
    """Process plain user-typed/pasted text and return LLM summary."""
    if not text or not text.strip():
        return "No text provided."
    try:
        raw_data   = process_text(text)
        cleaned    = clean_processor_output(raw_data)
        prompt     = build_summary_prompt(cleaned)
        llm_output = summarize(prompt)

        save_resource(
            source       = raw_data.get("source_type", "plain_text"),
            url          = None,
            title        = raw_data.get("title", ""),
            raw_input    = {"text": text[:200]},
            raw_data     = raw_data,
            cleaned_data = cleaned,
            llm_output   = llm_output,
        )
        return llm_output

    except Exception as e:
        return f"Error processing text: {e}"


# ─────────────────────────────────────────────
# IMAGE
# ─────────────────────────────────────────────

def process_image_input(image_path: str) -> str:
    """Run OCR on an uploaded image and return LLM summary."""
    if not os.path.exists(image_path):
        return f"Image not found: {image_path}"
    try:
        raw_data   = process_image(image_path)
        cleaned    = clean_processor_output(raw_data)
        prompt     = build_summary_prompt(cleaned)
        llm_output = summarize(prompt)

        save_resource(
            source       = "local_image",
            url          = None,
            title        = raw_data.get("title", ""),
            raw_input    = {"image_path": image_path},
            raw_data     = raw_data,
            cleaned_data = cleaned,
            llm_output   = llm_output,
        )
        return llm_output

    except Exception as e:
        return f"Error processing image: {e}"


# ─────────────────────────────────────────────
# MIXED INPUT  ← this is what the FastAPI route calls
# ─────────────────────────────────────────────

def process_input(
    text:         str        = "",
    image_paths:  list[str]  = None,
) -> str:
    """
    Main entry point for the web UI.
    Accepts any combination of:
      - Free text (may contain multiple URLs on separate lines)
      - Uploaded image file paths

    Returns a single combined LLM response.
    """
    image_paths = image_paths or []
    parts       = []

    # ── 1. Split text into URLs and plain text ──
    lines     = [l.strip() for l in (text or "").splitlines() if l.strip()]
    urls      = [l for l in lines if l.startswith("http://") or l.startswith("https://")]
    plain     = [l for l in lines if not l.startswith("http")]
    plain_str = "\n".join(plain).strip()

    # ── 2. Process each URL ──────────────────────
    for url in urls:
        result = process_link(url)
        parts.append(f"[{url}]\n{result}")

    # ── 3. Process plain text ────────────────────
    if plain_str:
        result = process_text_input(plain_str)
        parts.append(f"[Text Note]\n{result}")

    # ── 4. Process each uploaded image ───────────
    for img_path in image_paths:
        result = process_image_input(img_path)
        fname  = Path(img_path).name
        parts.append(f"[Image: {fname}]\n{result}")

    if not parts:
        return "Nothing to process. Please provide a link, text, or image."

    # ── 5. If multiple inputs, ask LLM to unify ──
    if len(parts) == 1:
        return parts[0].split("\n", 1)[-1].strip()

    combined_prompt = (
        "The user provided multiple resources. "
        "Summarise each one, then give a combined insight:\n\n"
        + "\n\n---\n\n".join(parts)
    )
    try:
        return summarize(combined_prompt)
    except Exception:
        return "\n\n---\n\n".join(parts)


# ─────────────────────────────────────────────
# CLI ENTRY
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("AI Resource Agent — type a URL, paste text, or enter image path.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("Input: ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue

        # Auto-detect: image path, URL, or text
        if os.path.isfile(user_input) and Path(user_input).suffix.lower() in \
                {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}:
            result = process_image_input(user_input)
        else:
            result = process_input(text=user_input)

        print(f"\n{result}\n")
