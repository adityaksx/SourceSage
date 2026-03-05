# AI Resource Agent 🧠📚

A **local AI-powered knowledge collector** that helps developers save, analyze, and organize learning resources from the internet.

Instead of bookmarking links and never revisiting them, this agent **extracts meaningful knowledge from resources** such as:

* YouTube videos
* GitHub repositories
* Articles / blogs
* Screenshots / images
* Instagram dev posts (planned)

It processes the content locally and creates structured summaries that can be searched later.

The goal is to build a **personal developer knowledge archive powered by local AI models.**

---

# 🚀 Motivation

Every day developers discover useful resources like:

* GitHub projects
* AI tools
* tutorials
* courses
* dev articles
* social media posts
* YouTube videos

Most of these get saved as **bookmarks or screenshots and are forgotten**.

This project solves that problem by creating a **personal AI ingestion pipeline** that:

1. Collects raw resources
2. Extracts useful information
3. Summarizes the content using local LLMs
4. Stores the knowledge for future search

Everything runs **locally** using models from **Ollama**.

---

# 🎯 Goals

The system should:

* Work **locally without cloud APIs**
* Use **different LLMs for different tasks**
* Extract **maximum information before sending to LLM** (token efficient)
* Save **raw resources + processed knowledge**
* Support **multiple resource types**

---

# 📥 Supported Resource Types (Current / Planned)

### Video

* YouTube videos
* YouTube Shorts
* Instagram Reels

Videos are **not analyzed visually**.

Instead the agent extracts:

* transcript
* title
* description
* comments

---

### GitHub Repositories

The agent can:

* clone repositories
* read README
* analyze project description
* summarize project purpose

---

### Web Articles

The system can:

* scrape article content
* remove HTML clutter
* summarize the content

---

### Images / Screenshots

Useful for:

* dev roadmaps
* diagrams
* cheat sheets

Pipeline:

```
image
↓
OCR (Tesseract)
↓
text extraction
↓
LLM summary
```

---

### Social Media Posts (Planned)

Examples:

* Instagram dev posts
* Twitter threads
* LinkedIn posts

The agent will extract:

* captions
* hashtags
* images
* external links

---

# 🧠 Core Idea

Instead of building a **chatbot**, this project builds a **task-specific AI agent** whose only job is:

> **Ingest developer resources and convert them into structured knowledge.**

Pipeline:

```
Raw Resource
↓
Python Processing
↓
Content Extraction
↓
LLM Analysis
↓
Structured Knowledge
↓
Local Storage
```

---

# 🧩 Architecture

The system separates **data processing** and **LLM reasoning**.

```
INPUT
(link / image / notes)
        ↓
Source Detection
        ↓
Processor
(YouTube / GitHub / Web / OCR)
        ↓
Clean Context
        ↓
LLM Analysis
        ↓
Structured Output
        ↓
Local Storage
```

---

# ⚙️ Technology Stack

### AI

* Ollama
* Local LLM models (Mistral / Qwen / Llama)

### Processing

* Python
* yt-dlp
* youtube-transcript-api
* trafilatura
* pytesseract

### Tools

* Git
* Tesseract OCR

---

# 📁 Project Structure

```
ai_resource_agent/

main.py
config.py

processors/
    youtube_processor.py
    github_processor.py
    web_processor.py
    instagram_processor.py

utils/
    source_detector.py
    downloader.py
    transcript.py
    ocr.py
    cleaner.py

llm/
    summarizer.py
    prompt_builder.py

database/
    db.py

storage/
    raw/
    processed/
    images/
    videos/
    repos/
```

---

# 🔄 Processing Pipeline

Example for YouTube:

```
YouTube link
↓
extract video ID
↓
fetch transcript
↓
send transcript to LLM
↓
generate summary
↓
store results
```

Example for GitHub:

```
GitHub repo
↓
clone repository
↓
read README
↓
summarize project
```

Example for images:

```
image
↓
OCR extraction
↓
text cleaning
↓
LLM summary
```

---

# 📦 Installation

### 1. Install Python dependencies

```
pip install yt-dlp youtube-transcript-api trafilatura pytesseract pillow requests
```

---

### 2. Install Ollama

https://ollama.com

Pull a model:

```
ollama pull mistral
```

Start server:

```
ollama serve
```

---

### 3. Install Git

```
winget install Git.Git
```

---

### 4. Install Tesseract OCR

```
winget install UB-Mannheim.TesseractOCR
```

---

# ▶️ Running the Agent

```
python main.py
```

Paste a resource link:

```
https://youtube.com/...
https://github.com/...
https://blog.example.com/article
```

The agent will:

1. detect source
2. extract content
3. summarize with LLM
4. display results

---

# 🔮 Future Improvements

Planned upgrades:

### Knowledge Database

Store summaries in searchable database.

### Vector Search

Allow semantic search of saved resources.

### Automatic Tagging

Detect technologies automatically.

### Instagram Integration

Download dev posts and reels.

### Resource Scoring

Evaluate usefulness of resources.

### Knowledge Graph

Connect related resources automatically.

---

# 🧠 Vision

The long-term goal is to build a **personal AI knowledge system** for developers.

Instead of collecting random bookmarks, the system builds a **structured learning archive** that grows smarter over time.

Eventually it will allow queries like:

* "Show AI agent tutorials I saved"
* "Find Docker courses"
* "List GitHub repos about RAG"

---

# 📜 License

MIT License

---

# 🤝 Contributions

Ideas, improvements, and suggestions are welcome.

This project is an experiment toward building **local AI-powered developer tools**.
