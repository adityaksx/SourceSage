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
BASE_DIR   = Path(__file__).parent
ROOT_DIR   = BASE_DIR.parent
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
    message: Optional[str]              = Form(default=None),
    images:  Optional[List[UploadFile]] = File(default=None),
):
    results = []

    # ── 1. Process message text ───────────────
    if message and message.strip():
        lines     = [l.strip() for l in message.strip().splitlines() if l.strip()]
        # ✅ NEW — also catches bare URLs like github.com/user
        from utils.source_detector import _looks_like_bare_url

        urls  = [
            l for l in lines
            if l.startswith("http://") or l.startswith("https://") or _looks_like_bare_url(l)
        ]
        plain = [l for l in lines if l not in urls]
        plain_str = "\n".join(plain).strip()

        for url in urls:
            try:
                result = await process_link(url)             # ← await added
                if result:
                    results.append(result)
            except Exception as e:
                results.append(f"Error processing '{url}': {e}")

        if plain_str:
            try:
                result = await process_text_input(plain_str) # ← await added
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
                safe_name = img.filename.strip().replace(" ", "_")
                save_path = IMAGES_DIR / safe_name

                with open(save_path, "wb") as f:
                    shutil.copyfileobj(img.file, f)

                result = await process_image_input(          # ← await added
                    str(save_path.resolve())
                )
                if result:
                    results.append(result)

            except Exception as e:
                results.append(f"Error processing image '{img.filename}': {e}")

    # ── 3. Nothing provided ───────────────────
    if not results:
        return {"response": "Nothing to process. Please provide a link, text, or image."}

    return {"response": "\n\n---\n\n".join(str(r) for r in results)}
