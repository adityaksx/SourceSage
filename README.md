# 🤖 AI Resource Agent

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green)
![LLM](https://img.shields.io/badge/LLM-Ollama-orange)
![Database](https://img.shields.io/badge/Database-SQLite-lightgrey)
![License](https://img.shields.io/badge/License-MIT-purple)

> **Turn any link, text, or image into structured AI knowledge.**

AI Resource Agent is an **async multi-source intelligence pipeline** that accepts URLs, text, or files — automatically detects their type, extracts useful data, enriches it using an LLM, and stores everything in a searchable resource vault.

It acts like a **personal AI knowledge ingestion engine**.

---

# ✨ What Makes It Cool

🧠 **Smart Input Understanding**
Paste almost anything:

* YouTube video
* GitHub repository
* Research paper
* Blog article
* Instagram post
* Local image or file
* Plain text notes

The agent **figures out what it is automatically.**

---

⚡ **Async End-to-End Pipeline**

No blocking calls. Everything runs with `async/await`:

```
detect → extract → clean → enrich → summarize → store
```

Fast and scalable.

---

🧩 **Modular Architecture**

Each content type has its own processor:

```
YouTube → youtube_processor
GitHub → github_processor
Web → web_processor
Image → OCR pipeline
Text → text processor
```

Easy to extend with new sources.

---

🗄 **Local Knowledge Vault**

Every processed resource is stored in SQLite with:

* title
* summary
* source type
* cleaned data
* enriched LLM insights

Your personal **AI knowledge database**.

---

🌐 **Two Ways to Use It**

**Web Interface**

```
FastAPI chat interface
```

Paste links and instantly get structured insights.

**CLI Mode**

```
python main.py
```

Simple terminal REPL.

---

# 🧠 System Architecture

```
User Input
(URL / Text / Image)
        │
        ▼
┌───────────────────────────────┐
│ Source Detection              │
│ 1️⃣ Regex rules               │
│ 2️⃣ LLM fallback classifier   │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ Source Processor              │
│ YouTube | GitHub | Web        │
│ Instagram | Text | Image OCR  │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ LLM Processing Pipeline       │
│ classify → clean → enrich     │
│ summarize                     │
└───────────────────────────────┘
        │
        ▼
SQLite Database
        │
        ▼
Web UI / CLI Output
```

---

# 🌍 Supported Sources

| Category    | Supported                         |
| ----------- | --------------------------------- |
| 🎥 Video    | YouTube videos, shorts, playlists |
| 💻 Code     | GitHub repos, files, gists        |
| 📱 Social   | Instagram posts, Reddit           |
| 📰 Articles | Medium, Substack, Notion          |
| 📚 Research | ArXiv papers                      |
| 🤖 AI Tools | HuggingFace models & datasets     |
| 🌐 Web      | Any webpage                       |
| 📂 Files    | Images, PDFs, notebooks           |
| 📝 Text     | Plain text notes                  |

⚠️ Login-protected sources (LinkedIn etc.) are not supported — paste the text instead.

---

# 📂 Project Structure

```
ai_resource_agent
│
├── main.py                # Entry point & async router
├── config.py              # Configuration
├── .env                   # API keys
│
├── processors/            # Source processors
│   ├── youtube_processor.py
│   ├── github_processor.py
│   ├── web_processor.py
│   ├── instagram_processor.py
│   ├── text_processor.py
│   └── image_processor.py
│
├── llm/                   # LLM pipeline
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

## 1️⃣ Clone Repo

```bash
git clone https://github.com/adityaksx/ai_resource_agent.git
cd ai_resource_agent
```

---

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Setup Environment

Create `.env`

```
OLLAMA_MODEL=llama3
```

---

## 4️⃣ Run Web Interface

```bash
uvicorn web.app:app --reload
```

Open:

```
http://localhost:8000
```

---

## 5️⃣ Run CLI

```
python main.py
```

Paste any:

* URL
* text
* file path
* image

---

# 🧩 Key Components

## `main.py`

Central async router.

Responsibilities:

* detect input type
* call correct processor
* run LLM pipeline
* save results to database

---

## `llm/pipeline.py`

Core LLM workflow.

```
classify()
extract_guidance()
clean()
enrich()
summarize()
```

---

## `processors/`

Extract raw data from sources.

Examples:

```
youtube_processor → metadata + transcript
github_processor → repo structure + README
web_processor → article extraction
image_processor → OCR text
```

---

## `database/db.py`

SQLite resource vault.

Stores:

```
vault_title
vault_snippet
source
raw_data
cleaned_data
llm_output
status
```

---

# 🛠 Design Philosophy

✔ Fully async architecture
✔ Modular processors
✔ Local-first AI workflow
✔ Extendable source support
✔ Structured knowledge storage

---

# 🧪 Example Use Cases

• Build a **personal AI research vault**
• Save and summarize **GitHub repos instantly**
• Extract knowledge from **YouTube tutorials**
• Organize **AI/ML resources automatically**
• Create your own **AI knowledge ingestion system**

---

# 🔮 Future Ideas

* Vector search over stored resources
* RAG chat over your vault
* Browser extension for one-click ingestion
* Semantic clustering of resources
* Automatic tagging

---

# 📜 License

MIT License

---

# 👤 Author

**Aditya Kumar**

Building tools around **AI agents, automation, and knowledge systems.**

GitHub
[https://github.com/adityaksx](https://github.com/adityaksx)
