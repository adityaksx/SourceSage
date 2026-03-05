"""
web/app.py
----------
FastAPI application for the AI Resource Agent.

Handles:
  - GET  /       → serve chat UI
  - POST /chat   → process message (text + URLs) and uploaded images
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Resolve project root ─────────────────────
BASE_DIR   = Path(__file__).parent                        # .../web/
ROOT_DIR   = BASE_DIR.parent                              # .../ai_resource_agent/
IMAGES_DIR = ROOT_DIR / "storage" / "images"

sys.path.insert(0, str(ROOT_DIR))

# ── Project imports ──────────────────────────
from main        import process_link, process_text_input, process_image_input
from database.db import init_db

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(title="AI Resource Agent")

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

# ── Init DB once on startup ──────────────────
@app.on_event("startup")
async def startup():
    init_db()


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home():
    template = BASE_DIR / "templates" / "chat.html"
    return template.read_text(encoding="utf-8")


@app.post("/chat")
async def chat(
    message: Optional[str]             = Form(default=None),
    images:  Optional[List[UploadFile]] = File(default=None),
):
    results = []

    # ── 1. Process message text ───────────────
    if message and message.strip():
        lines     = [l.strip() for l in message.strip().splitlines() if l.strip()]
        urls      = [l for l in lines if l.startswith("http://") or l.startswith("https://")]
        plain     = [l for l in lines if l not in urls]
        plain_str = "\n".join(plain).strip()

        # Process each URL separately
        for url in urls:
            try:
                result = process_link(url)
                if result:
                    results.append(result)
            except Exception as e:
                results.append(f"Error processing '{url}': {e}")

        # Process plain text as a note
        if plain_str:
            try:
                result = process_text_input(plain_str)
                if result:
                    results.append(result)
            except Exception as e:
                results.append(f"Error processing text: {e}")

    # ── 2. Process uploaded images ────────────
    if images:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        for img in images:
            if not img or not img.filename:
                continue
            try:
                # Sanitize filename — remove spaces
                safe_name = img.filename.strip().replace(" ", "_")
                save_path = IMAGES_DIR / safe_name

                # Save file to disk
                with open(save_path, "wb") as f:
                    shutil.copyfileobj(img.file, f)

                # Route to image processor (OCR), NOT process_link
                result = process_image_input(str(save_path.resolve()))
                if result:
                    results.append(result)

            except Exception as e:
                results.append(f"Error processing image '{img.filename}': {e}")

    # ── 3. Nothing provided ───────────────────
    if not results:
        return {"response": "Nothing to process. Please provide a link, text, or image."}

    return {"response": "\n\n---\n\n".join(str(r) for r in results)}
