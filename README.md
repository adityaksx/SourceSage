# 🤖 AI Resource Agent

> Turn any URL, text, or file into structured AI knowledge.

AI Resource Agent is a **fully async multi-source ingestion system** that accepts links, text, and images, detects their type automatically, extracts useful information, enriches it using an LLM, and stores everything in a local knowledge database.

Think of it as a **personal AI-powered resource vault**.

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

The agent **automatically detects the source type**.

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

This becomes your **personal AI knowledge database**.

---

### 🌐 Web Interface + CLI

Two ways to use the agent.

**Web Interface**

FastAPI-based chat UI.

```
uvicorn web.app:app --reload
```

Open:

```
http://localhost:8000
```

---

**CLI Mode**

Run the terminal interface:

```
python main.py
```

Paste URLs, text, or file paths directly.

---

# 🧠 System Architecture

```
User Input
(URL / Text / Image)
        │
        ▼
Source Detection
│
├─ Stage 1: Regex Rules
└─ Stage 2: LLM Classifier
        │
        ▼
Source Processor
│
├─ YouTube
├─ GitHub
├─ Web
├─ Instagram
├─ Text
└─ Image (OCR)
        │
        ▼
LLM Processing Pipeline
│
├─ classify()
├─ extract_guidance()
├─ clean()
├─ enrich()
└─ summarize()
        │
        ▼
SQLite Database
        │
        ▼
Web UI / CLI Output
```

---

# 🌍 Supported Sources

| Category | Examples |
|--------|--------|
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
ai_resource_agent/
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
└── web/
    ├── app.py
    ├── templates/
    └── static/
```

---

# 🚀 Getting Started

## 1. Clone the Repository

```
git clone https://github.com/adityaksx/ai_resource_agent.git
cd ai_resource_agent
```

---

## 2. Install Dependencies

```
pip install -r requirements.txt
```

---

## 3. Setup Environment Variables

Create a `.env` file:

```
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```
---

## 4. Run Web Interface

```
uvicorn web.app:app --reload
```

Then open:

```
http://localhost:8000
```

---

## 5. Run CLI Mode

```
python main.py
```

Type any:

- URL
- text
- image path
- file path

Type `exit` to quit.

---

## 🧱 System Dependencies

- ffmpeg (required for audio/video processing)
- tesseract-ocr (required for OCR fallback)
- ollama (must be running locally)

Example:

ollama serve

---

## 🤖 Ollama Models

- ollama pull qwen2.5:7b-instruct
- ollama pull deepseek-coder:6.7b
- ollama pull mistral:7b

---

## ⚠️ Deployment Note (Important)

To ensure smooth deployment on platforms like Render or Railway, some heavy dependencies are excluded:

- paddleocr
- pytesseract
- pillow

These libraries require system-level dependencies (Rust, Tesseract, etc.) that are not supported in most free hosting environments.

### 🔹 Current Deployment Mode

The hosted version runs in **demo mode**:
- OCR processing is disabled
- AI processing is disabled
- Only previously stored resources are displayed

### 🔹 For Full Local Setup

If you want full functionality (OCR + AI processing), install:

pip install paddleocr pytesseract pillow

Also install system dependencies:

- Tesseract OCR
- ffmpeg
- Ollama (for local LLM)

---
  
# 🧩 Key Modules

### `main.py`

Central async router that:

- detects input type  
- routes to processor  
- runs the LLM pipeline  
- saves results to the database  

---

### `llm/pipeline.py`

Implements the AI processing pipeline:

```
classify()
extract_guidance()
clean()
enrich()
summarize()
```

---

### `llm/prompt_builder.py`

Builds **source-specific prompts** for better LLM responses.

---

### `processors/`

Each processor extracts structured data from its source.

Examples:

```
youtube_processor → metadata + transcript
github_processor → repo structure + README
web_processor → article extraction
image_processor → OCR text
```

---

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

• Personal AI research vault  
• Automatic GitHub repo summarization  
• Knowledge extraction from YouTube tutorials  
• Organizing AI/ML resources  
• Building your own AI knowledge ingestion system  

---

# 📜 License

MIT License

---

# 👤 Author

**Aditya Kumar**

GitHub  
https://github.com/adityaksx
