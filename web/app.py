import os
import sys
import shutil

from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import process_link

app = FastAPI()

app.mount("/static", StaticFiles(directory="web/static"), name="static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# -------------------------
# Serve UI
# -------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    # FIXED: use absolute path + utf-8 encoding
    template_path = os.path.join(BASE_DIR, "templates", "chat.html")
    with open(template_path, encoding="utf-8") as f:
        return f.read()


# -------------------------
# Chat endpoint
# -------------------------

@app.post("/chat")
async def chat(
    message: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None)
):
    results = []

    # Handle text / URLs (one per line)
    if message:
        lines = [l.strip() for l in message.strip().splitlines() if l.strip()]
        for line in lines:
            try:
                result = process_link(line)
                if result:
                    results.append(result)
            except Exception as e:
                results.append(f"Error processing '{line}': {e}")

    # Handle uploaded images → save → OCR pipeline
    if images:
        images_dir = os.path.join(BASE_DIR, "..", "storage", "images")
        os.makedirs(images_dir, exist_ok=True)

        for img in images:
            try:
                save_path = os.path.join(images_dir, img.filename)
                with open(save_path, "wb") as f:
                    shutil.copyfileobj(img.file, f)

                # Route through process_link as local image path
                result = process_link(save_path)
                if result:
                    results.append(result)
            except Exception as e:
                results.append(f"Error processing image '{img.filename}': {e}")

    if not results:
        return {"response": "Nothing could be processed. Please try a different link or image."}

    return {"response": "\n\n---\n\n".join(str(r) for r in results)}
