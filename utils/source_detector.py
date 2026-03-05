"""
source_detector.py
------------------
Detects the source type from:
  - URLs  (YouTube, Instagram, GitHub, Twitter/X, LinkedIn, Reddit, 
           Notion, Medium, Substack, HuggingFace, ArXiv, Pastebin, generic web)
  - Local file paths  (image, video, audio, document, code, data, archive)
  - Raw text / plain notes

Returns a fine-grained string tag like "youtube_video", "local_image",
"pdf_document", "plain_text", etc.
"""

import os
import re
from urllib.parse import urlparse, parse_qs


# ─────────────────────────────────────────────
# FILE EXTENSION MAPS
# ─────────────────────────────────────────────

IMAGE_EXTS    = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
                 ".tiff", ".tif", ".svg", ".ico", ".heic", ".avif"}

VIDEO_EXTS    = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv",
                 ".wmv", ".m4v", ".3gp", ".ogv"}

AUDIO_EXTS    = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
                 ".wma", ".opus", ".aiff"}

DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".odt", ".rtf",
                 ".pptx", ".ppt", ".odp",
                 ".xlsx", ".xls", ".ods", ".csv",
                 ".epub", ".mobi"}

CODE_EXTS     = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm",
                 ".css", ".scss", ".sass", ".java", ".kt", ".c", ".cpp",
                 ".h", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
                 ".sh", ".bash", ".zsh", ".ps1", ".r", ".m", ".sql",
                 ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
                 ".dockerfile", ".makefile"}

DATA_EXTS     = {".json", ".xml", ".ndjson", ".jsonl", ".parquet",
                 ".arrow", ".hdf5", ".h5", ".feather", ".db", ".sqlite"}

ARCHIVE_EXTS  = {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar",
                 ".7z", ".tgz", ".tar.gz"}

NOTEBOOK_EXTS = {".ipynb"}

TEXT_EXTS     = {".txt", ".md", ".rst", ".log"}


# ─────────────────────────────────────────────
# MAIN DETECTOR
# ─────────────────────────────────────────────

def detect_source(input_str: str) -> str:
    """
    Detects the type of a given input string.

    Args:
        input_str: a URL, local file path, or raw text

    Returns:
        A string label, e.g.:
            "youtube_video", "youtube_playlist", "youtube_shorts"
            "instagram_post", "instagram_reel", "instagram_profile", "instagram_story"
            "github_repo", "github_profile", "github_gist", "github_file"
            "twitter_tweet", "twitter_profile"
            "linkedin_post", "linkedin_profile", "linkedin_company"
            "reddit_post", "reddit_subreddit"
            "huggingface_model", "huggingface_dataset", "huggingface_space"
            "arxiv_paper"
            "medium_article"
            "substack_article"
            "notion_page"
            "pastebin"
            "web"
            "local_image", "local_video", "local_audio"
            "pdf_document", "word_document", "spreadsheet",
            "presentation", "ebook"
            "code_file", "notebook"
            "data_file", "archive"
            "plain_text_file", "plain_text"
            "unknown"
    """
    if not input_str or not isinstance(input_str, str):
        return "unknown"

    s = input_str.strip()

    # ── 1. Local file path ──────────────────────────────
    local_type = _detect_local_file(s)
    if local_type:
        return local_type

    # ── 2. URL ──────────────────────────────────────────
    if re.match(r'^https?://', s, re.IGNORECASE):
        return _detect_url(s)

    # ── 3. Raw text ─────────────────────────────────────
    return _detect_raw_text(s)


# ─────────────────────────────────────────────
# LOCAL FILE DETECTION
# ─────────────────────────────────────────────

def _detect_local_file(path: str) -> str | None:
    """Returns a type string if the path looks like a local file, else None."""

    # Must look like a path (has a separator or extension) and NOT a URL
    if re.match(r'^https?://', path, re.IGNORECASE):
        return None

    _, ext = os.path.splitext(path.lower())

    if not ext:
        # Could still be a file without extension — only classify if path exists
        if os.path.isfile(path):
            return "plain_text_file"
        return None

    # Multi-part extensions like .tar.gz
    if path.lower().endswith(".tar.gz"):
        return "archive"

    if ext in IMAGE_EXTS:       return "local_image"
    if ext in VIDEO_EXTS:       return "local_video"
    if ext in AUDIO_EXTS:       return "local_audio"
    if ext in NOTEBOOK_EXTS:    return "notebook"
    if ext in CODE_EXTS:        return "code_file"
    if ext in DATA_EXTS:        return "data_file"
    if ext in ARCHIVE_EXTS:     return "archive"
    if ext in TEXT_EXTS:        return "plain_text_file"

    if ext == ".pdf":           return "pdf_document"
    if ext in {".docx", ".doc", ".odt", ".rtf"}:
                                return "word_document"
    if ext in {".xlsx", ".xls", ".ods", ".csv"}:
                                return "spreadsheet"
    if ext in {".pptx", ".ppt", ".odp"}:
                                return "presentation"
    if ext in {".epub", ".mobi"}:
                                return "ebook"

    return None


# ─────────────────────────────────────────────
# URL DETECTION
# ─────────────────────────────────────────────

def _detect_url(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
        domain = parsed.netloc.lower().lstrip("www.")
        path   = parsed.path.lower()
        query  = parse_qs(parsed.query)

        # ── YouTube ────────────────────────────────────
        if "youtube.com" in domain or "youtu.be" in domain:
            if "playlist" in query or "playlist" in path:
                return "youtube_playlist"
            if "/shorts/" in path:
                return "youtube_shorts"
            if "/channel/" in path or "/c/" in path or "/user/" in path or "/@" in path:
                return "youtube_channel"
            if "/live/" in path or "live" in query:
                return "youtube_live"
            return "youtube_video"

        # ── Instagram ──────────────────────────────────
        if "instagram.com" in domain:
            if "/reel/"    in path: return "instagram_reel"
            if "/p/"       in path: return "instagram_post"
            if "/stories/" in path: return "instagram_story"
            if "/tv/"      in path: return "instagram_tv"
            return "instagram_profile"

        # ── GitHub ─────────────────────────────────────
        if "github.com" in domain:
            parts = [p for p in path.split("/") if p]
            if "gist.github.com" in domain:
                return "github_gist"
            if len(parts) >= 3 and parts[2] in ("blob", "tree", "raw"):
                return "github_file"
            if len(parts) >= 2:
                return "github_repo"
            return "github_profile"

        # ── Twitter / X ────────────────────────────────
        if "twitter.com" in domain or "x.com" in domain:
            if "/status/" in path:  return "twitter_tweet"
            return "twitter_profile"

        # ── LinkedIn ───────────────────────────────────
        if "linkedin.com" in domain:
            if "/posts/"   in path: return "linkedin_post"
            if "/pulse/"   in path: return "linkedin_article"
            if "/company/" in path: return "linkedin_company"
            if "/in/"      in path: return "linkedin_profile"
            return "web"

        # ── Reddit ─────────────────────────────────────
        if "reddit.com" in domain:
            if "/comments/" in path: return "reddit_post"
            if "/r/"         in path: return "reddit_subreddit"
            return "web"

        # ── HuggingFace ────────────────────────────────
        if "huggingface.co" in domain:
            if "/datasets/"  in path: return "huggingface_dataset"
            if "/spaces/"    in path: return "huggingface_space"
            return "huggingface_model"

        # ── ArXiv ──────────────────────────────────────
        if "arxiv.org" in domain:
            return "arxiv_paper"

        # ── Medium ─────────────────────────────────────
        if "medium.com" in domain:
            return "medium_article"

        # ── Substack ───────────────────────────────────
        if "substack.com" in domain:
            return "substack_article"

        # ── Notion ─────────────────────────────────────
        if "notion.so" in domain or "notion.site" in domain:
            return "notion_page"

        # ── Pastebin / similar ─────────────────────────
        if "pastebin.com" in domain or "gist.github.com" in domain:
            return "pastebin"

        # ── Loom / video hosting ───────────────────────
        if "loom.com" in domain:
            return "loom_video"
        if "vimeo.com" in domain:
            return "vimeo_video"
        if "dailymotion.com" in domain:
            return "video_url"

        # ── URL pointing to a file by extension ────────
        path_ext = os.path.splitext(path)[-1].lower()
        if path_ext in IMAGE_EXTS:    return "image_url"
        if path_ext in VIDEO_EXTS:    return "video_url"
        if path_ext in AUDIO_EXTS:    return "audio_url"
        if path_ext == ".pdf":        return "pdf_url"
        if path_ext in CODE_EXTS:     return "code_url"
        if path_ext in DATA_EXTS:     return "data_url"

        return "web"

    except Exception:
        return "unknown"


# ─────────────────────────────────────────────
# RAW TEXT DETECTION
# ─────────────────────────────────────────────

def _detect_raw_text(text: str) -> str:
    """Classify raw text that is not a URL or file path."""

    if not text:
        return "unknown"

    # Looks like code
    code_patterns = [
        r'^\s*(def |class |import |from |#!\/)',
        r'^\s*(function |const |let |var |=>)',
        r'^\s*(<html|<!DOCTYPE|<\?php)',
        r'^\s*(\{|\[)',   # JSON-like
        r'[{};]\s*$',     # C-style
    ]
    for pat in code_patterns:
        if re.search(pat, text[:300], re.IGNORECASE | re.MULTILINE):
            return "code_snippet"

    # Looks like structured data
    if re.match(r'^\s*[\{\[]', text.strip()):
        return "json_data"

    # Markdown
    if re.search(r'^#{1,6} ', text, re.MULTILINE):
        return "markdown_text"

    return "plain_text"


# ─────────────────────────────────────────────
# CONVENIENCE: detect from file object (upload)
# ─────────────────────────────────────────────

def detect_source_from_file(filename: str, mime_type: str = "") -> str:
    """
    Classify an uploaded file by its filename and optional MIME type.
    Useful for FastAPI UploadFile objects.
    """
    ext = os.path.splitext(filename.lower())[-1]

    # MIME-type overrides
    if mime_type:
        m = mime_type.lower()
        if m.startswith("image/"):       return "local_image"
        if m.startswith("video/"):       return "local_video"
        if m.startswith("audio/"):       return "local_audio"
        if m == "application/pdf":       return "pdf_document"
        if "spreadsheet" in m:           return "spreadsheet"
        if "presentation" in m:          return "presentation"
        if "wordprocessing" in m:        return "word_document"
        if m in ("application/json",
                 "application/xml",
                 "text/csv"):            return "data_file"
        if m == "text/plain":            return "plain_text_file"

    # Fall back to extension
    result = _detect_local_file(filename)
    return result if result else "unknown"


# ─────────────────────────────────────────────
# CLI TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        # YouTube
        "https://youtube.com/watch?v=abc",
        "https://youtu.be/xyz",
        "https://youtube.com/playlist?list=123",
        "https://youtube.com/shorts/abc123",
        "https://youtube.com/@fireship",
        # Instagram
        "https://instagram.com/p/abc",
        "https://instagram.com/reel/xyz",
        "https://instagram.com/stories/user/123",
        # GitHub
        "https://github.com/openai/gpt",
        "https://github.com/openai",
        "https://github.com/torvalds/linux/blob/master/README",
        "https://gist.github.com/user/abc123",
        # Social
        "https://twitter.com/elonmusk/status/123",
        "https://x.com/elonmusk",
        "https://linkedin.com/in/johndoe",
        "https://reddit.com/r/Python/comments/abc",
        # AI / Research
        "https://huggingface.co/openai/whisper",
        "https://huggingface.co/datasets/squad",
        "https://arxiv.org/abs/2303.08774",
        # Publishing
        "https://medium.com/@user/article-title",
        "https://mysite.substack.com/p/issue-1",
        "https://notion.so/My-Page-abc123",
        # Files (local)
        "/home/user/photo.jpg",
        "D:\\Downloads\\report.pdf",
        "script.py",
        "data.csv",
        "model_weights.h5",
        "notes.md",
        "project.zip",
        "analysis.ipynb",
        # Raw text
        "def hello(): print('hi')",
        '{"key": "value"}',
        "# My Notes\nThis is markdown",
        "Just some plain text note here.",
        # Generic web
        "https://example.com/article",
    ]

    for t in tests:
        print(f"{t[:60]:<60} → {detect_source(t)}")
