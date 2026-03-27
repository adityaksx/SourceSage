# 🔮 SourceSage

> Turn any URL, text, or file into structured AI knowledge.

SourceSage is a **fully async multi-source ingestion system** that accepts links, text, and images, detects their type automatically, extracts useful information, enriches it using an LLM, and stores everything in a knowledge database.

Think of it as a **personal AI-powered resource vault**.

---

## 🌐 Live Demo

| Page | URL |
|------|-----|
| 🏠 Landing Page | https://ai-resource-agent.vercel.app/ |
| 💬 Chat Interface | https://ai-resource-agent.vercel.app/chat |
| 🗄 Resource Vault | https://ai-resource-agent.vercel.app/resources |

> **Demo mode:** The hosted version displays previously saved resources from the demo database.
> Full AI processing (OCR, LLM, Whisper) requires a local install — see [Getting Started](#-getting-started).

---

## ✨ Features

### 🧠 Multi-Source Input
Paste almost anything:

- YouTube videos / playlists
- GitHub repositories / files / gists
- Blog posts & articles
- Instagram posts
- Research papers (ArXiv)
- HuggingFace models
- Local images or files
- Plain text notes

SourceSage **automatically detects the source type**.

---

### ⚡ Async Processing Pipeline

End-to-end asynchronous architecture.

```
detect → extract → clean → enrich → summarize → store
```

No blocking I/O. Everything runs with `async/await`.

---

### 🔎 Smart Source Detection

Two-stage detection system:

1. **Fast rule-based detection** using regex
2. **LLM fallback classifier** for ambiguous inputs

This keeps detection both **fast and intelligent**.

---

### 🧩 Modular Processors

Each source type has its own processor.

```
processors/
├── youtube_processor.py
├── github_processor.py
├── web_processor.py
├── instagram_processor.py
├── text_processor.py
└── image_processor.py
```

Easy to extend with new sources.

---

### 🗄 Persistent Knowledge Vault

Every processed resource is saved in **SQLite** with structured metadata.

Stored fields include:

- title
- snippet
- source type
- raw extracted data
- cleaned data
- LLM summary
- processing status

---

### 🌐 Web Interface + CLI

**Web Interface** — FastAPI-based UI with 3 pages:

```
uvicorn web.app:app --reload
```

```
http://localhost:8000            ← Landing page
http://localhost:8000/chat       ← Chat interface
http://localhost:8000/resources  ← Resource vault
```

**CLI Mode:**

```
python main.py
```

---

# 🧠 System Architecture

```
User Input (URL / Text / Image)
        │
        ▼
Source Detection
├─ Stage 1: Regex Rules
└─ Stage 2: LLM Classifier
        │
        ▼
Source Processor
├─ YouTube  ├─ GitHub  ├─ Web
├─ Instagram  ├─ Text  └─ Image (OCR)
        │
        ▼
LLM Processing Pipeline
├─ classify()  ├─ extract_guidance()
├─ clean()  ├─ enrich()  └─ summarize()
        │
        ▼
SQLite Database → Web UI / CLI Output
```

---

# 🌍 Supported Sources

| Category | Examples |
|----------|----------|
| Video | YouTube videos, playlists |
| Code | GitHub repositories, files, gists |
| Social | Instagram posts, Reddit |
| Articles | Medium, Substack, blogs |
| Research | ArXiv papers |
| AI | HuggingFace models & datasets |
| Web | Any webpage |
| Files | PDFs, images, notebooks |
| Text | Plain text notes |

⚠ Login-protected platforms (LinkedIn etc.) are not supported.

---

# 📁 Project Structure

```
sourcesage/
│
├── main.py
├── config.py
├── .env
│
├── processors/
│   ├── youtube_processor.py
│   ├── github_processor.py
│   ├── web_processor.py
│   ├── instagram_processor.py
│   ├── text_processor.py
│   └── image_processor.py
│
├── llm/
│   ├── pipeline.py
│   ├── summarizer.py
│   ├── prompt_builder.py
│   ├── llm_classifier.py
│   ├── ollama_client.py
│   └── embeddings.py
│
├── utils/
│   ├── source_detector.py
│   └── cleaner.py
│
├── database/
│   └── db.py
│
├── frontend/                ← HTML pages served by FastAPI
│   ├── index.html           ← Landing page (/)
│   ├── chat.html            ← Chat UI (/chat)
│   ├── resources.html       ← Resource vault (/resources)
│   └── static/              ← CSS, JS assets
│
└── web/
    └── app.py               ← FastAPI backend
```

---

# 🚀 Getting Started

## 1. Clone the Repository

```
git clone https://github.com/adityaksx/ai_resource_agent.git
cd ai_resource_agent
```

## 2. Install Dependencies

```
pip install -r requirements.txt
```

## 3. Setup Environment Variables

Create a `.env` file:

```
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

## 4. Run Web Interface

```
uvicorn web.app:app --reload
```

Open `http://localhost:8000`

## 5. Run CLI Mode

```
python main.py
```

Type any URL, text, image path, or file path. Type `exit` to quit.

---

## 🧱 System Dependencies (Full Local Setup)

These are **not required** for the hosted demo but needed locally:

```bash
# Linux / WSL
sudo apt install tesseract-ocr ffmpeg

# Start Ollama
ollama serve
```

## 🤖 Ollama Models

```bash
ollama pull qwen2.5:7b-instruct
ollama pull deepseek-coder:6.7b
ollama pull mistral:7b
```

---

## ⚠️ Deployment Note

Deployed on **Render** (backend) + **Vercel** (frontend).

The following are **excluded** from the hosted version — they require system binaries unavailable on Render's free plan:

| Package | Reason |
|---------|--------|
| `torch` / `torchvision` | Too large (>1 GB), no GPU |
| `pytesseract` | Requires Tesseract binary |
| `paddleocr` | Requires PaddlePaddle + Tesseract |
| `openai-whisper` | Requires ffmpeg + heavy torch |
| `pillow` | Compiled C extensions |
| `ollama` | Requires a running local server |

### Hosted demo limitations
- OCR processing disabled
- AI/LLM processing disabled
- Shows only previously saved demo database resources

### For full local setup

```bash
pip install pillow pytesseract paddleocr openai-whisper torch
```

---

# 🧩 Key Modules

### `main.py`
Central async router — detects input type, routes to processor, runs LLM pipeline, saves to database.

### `llm/pipeline.py`
Implements: `classify()` → `extract_guidance()` → `clean()` → `enrich()` → `summarize()`

### `llm/prompt_builder.py`
Builds source-specific prompts for better LLM responses.

### `processors/`

```
youtube_processor  → metadata + transcript
github_processor   → repo structure + README
web_processor      → article extraction
image_processor    → OCR text
```

### `database/db.py`
Handles SQLite storage and resource queries.

---

# 🛠 Design Principles

- Fully async architecture
- Modular processors
- Clean separation of concerns
- Local-first AI workflow
- Easy extensibility

---

# 💡 Example Use Cases

- Personal AI research vault
- Automatic GitHub repo summarization
- Knowledge extraction from YouTube tutorials
- Organizing AI/ML resources
- Building your own AI knowledge ingestion system

---

# 📜 License

MIT License

---

# 👤 Author

**Aditya Kumar**
GitHub: https://github.com/adityaksx
