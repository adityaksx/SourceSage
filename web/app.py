
"""
web/app.py
----------
FastAPI application for the AI Resource Agent (DEPLOY-SAFE VERSION)

- LLM / heavy processing disabled for deployment
- Only viewing stored resources works
"""

import os
import sys
import shutil
import time
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────

BASE_DIR   = Path(__file__).parent
ROOT_DIR   = BASE_DIR.parent
IMAGES_DIR = ROOT_DIR / "storage" / "images"
PDFS_DIR   = ROOT_DIR / "storage" / "pdfs"

sys.path.insert(0, str(ROOT_DIR))

# ─────────────────────────────────────────────
# INIT APP
# ─────────────────────────────────────────────

app = FastAPI(title="AI Resource Agent")

# ✅ CORS (must be AFTER app init)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# IMPORTS (after path setup)
# ─────────────────────────────────────────────

from database.db import init_db, get_resources, get_resource, delete_resource

# ─────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)

    app.mount(
        "/storage/images",
        StaticFiles(directory=str(IMAGES_DIR)),
        name="images",
    )

# ─────────────────────────────────────────────
# HTML ROUTES
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "templates" / "chat.html").read_text(encoding="utf-8")


@app.get("/resources", response_class=HTMLResponse)
def resources_page():
    return (BASE_DIR / "templates" / "resources.html").read_text(encoding="utf-8")


# ─────────────────────────────────────────────
# API: LIST RESOURCES
# ─────────────────────────────────────────────

@app.get("/api/resources")
def api_list_resources(limit: int = 500):
    rows = get_resources(limit=limit)

    items = []
    for row in rows:
        items.append({
            "id":            row[0],
            "source":        row[1],
            "url":           row[2],
            "title":         row[3],
            "llm_output":    row[7],
            "status":        row[9],
            "created_at":    row[11],
            "vault_title":   row[12],
            "vault_snippet": row[13],
            "session_id":    row[14],
        })

    return {"resources": items}


# ─────────────────────────────────────────────
# API: SINGLE RESOURCE
# ─────────────────────────────────────────────

@app.get("/api/resources/{resource_id}")
def api_get_resource(resource_id: int):
    row = get_resource(resource_id)

    if not row:
        raise HTTPException(status_code=404, detail="Resource not found")

    return {
        "id":            row[0],
        "source":        row[1],
        "url":           row[2],
        "title":         row[3],
        "raw_input":     row[4],
        "raw_data":      row[5],
        "cleaned_data":  row[6],
        "llm_output":    row[7],
        "files":         row[8],
        "status":        row[9],
        "error":         row[10],
        "created_at":    row[11],
        "vault_title":   row[12],
        "vault_snippet": row[13],
    }


# ─────────────────────────────────────────────
# API: DELETE RESOURCE
# ─────────────────────────────────────────────

@app.delete("/api/resources/{resource_id}")
def api_delete_resource(resource_id: int):
    row = get_resource(resource_id)

    if not row:
        raise HTTPException(status_code=404, detail="Resource not found")

    delete_resource(resource_id)
    return {"ok": True, "deleted_id": resource_id}


# ─────────────────────────────────────────────
# CHAT (DISABLED FOR DEPLOYMENT)
# ─────────────────────────────────────────────

@app.post("/chat")
async def chat(
    message: Optional[str] = Form(default=None),
    images: Optional[List[UploadFile]] = File(default=None),
    session_id: Optional[str] = Form(default=None),
):
    return {
        "response": "Processing is disabled in the deployed version. "
                    "This demo only shows previously stored resources."
    }


# ─────────────────────────────────────────────
# UPDATE ANSWER
# ─────────────────────────────────────────────

@app.patch("/api/resources/{resource_id}/answer")
async def api_update_answer(resource_id: int, payload: dict):
    row = get_resource(resource_id)

    if not row:
        raise HTTPException(status_code=404, detail="Resource not found")

    from database.db import update_resource_answer
    update_resource_answer(resource_id, payload.get("llm_output", ""))

    return {"ok": True}
```
