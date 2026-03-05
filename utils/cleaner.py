"""
cleaner.py
----------
Cleans and normalises raw text extracted from any source before
it is passed to the LLM.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CleanConfig:
    remove_urls:       bool  = True
    remove_hashtags:   bool  = True
    remove_emojis:     bool  = False
    remove_html_tags:  bool  = True
    fix_unicode:       bool  = True
    normalize_spaces:  bool  = True
    normalize_quotes:  bool  = True
    dedupe_lines:      bool  = True
    dedupe_threshold:  float = 0.85
    min_sentence_len:  int   = 15
    max_sentences:     int   = 100
    max_comments:      int   = 30
    min_comment_len:   int   = 10
    max_tokens:        Optional[int] = None
    mode:              str   = "prose"


CONFIGS = {
    "prose":      CleanConfig(mode="prose"),
    "transcript": CleanConfig(mode="transcript", remove_urls=True,
                              remove_hashtags=False, max_sentences=200),
    "code":       CleanConfig(mode="code", remove_urls=False,
                              remove_hashtags=False, remove_emojis=False,
                              dedupe_lines=False),
    "ocr":        CleanConfig(mode="ocr", remove_urls=True,
                              min_sentence_len=5, dedupe_threshold=0.9),
    "social":     CleanConfig(mode="social", remove_urls=True,
                              remove_hashtags=True, remove_emojis=True,
                              max_sentences=50),
}


# ─────────────────────────────────────────────────────────────────────────────
# RESULT DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CleanResult:
    text:               str
    mode:               str
    original_chars:     int
    cleaned_chars:      int
    sentences:          int
    duplicates_removed: int   = 0
    truncated:          bool  = False

    @property
    def compression_ratio(self) -> float:
        if self.original_chars == 0:
            return 0.0
        return round(1 - self.cleaned_chars / self.original_chars, 3)

    def __str__(self):
        return self.text


# ─────────────────────────────────────────────────────────────────────────────
# LOW-LEVEL CLEANERS
# ─────────────────────────────────────────────────────────────────────────────

def _fix_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text

def _normalize_quotes(text: str) -> str:
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "--",
        "\u2026": "...",
    }
    for smart, straight in replacements.items():
        text = text.replace(smart, straight)
    return text

def _remove_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&apos;": "'", "&nbsp;": " ", "&#39;": "'",
    }
    for ent, char in entities.items():
        text = text.replace(ent, char)
    return text

def _remove_urls(text: str) -> str:
    return re.sub(r"https?://\S+|www\.\S+", "", text)

def _remove_hashtags(text: str) -> str:
    return re.sub(r"#\w+", "", text)

def _remove_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text)

def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()

def _remove_vtt_artifacts(text: str) -> str:
    text = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}", "", text)
    text = re.sub(r"^\d+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^WEBVTT.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[^>]+>", "", text)
    return text

def _remove_boilerplate(text: str) -> str:
    patterns = [
        r"cookie[s]? policy", r"accept all cookies", r"privacy policy",
        r"terms of (service|use)", r"all rights reserved",
        r"subscribe (to our newsletter|now)",
        r"click here to (read|view|see)", r"advertisement",
        r"skip to (main )?content", r"share this (article|post|story)",
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def _jaccard(a: str, b: str) -> float:
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)

def deduplicate(lines: list[str], threshold: float = 0.85) -> tuple[list[str], int]:
    seen:   list[str] = []
    result: list[str] = []
    removed = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue
        if any(_jaccard(stripped, s) >= threshold for s in seen):
            removed += 1
        else:
            seen.append(stripped)
            result.append(line)
    return result, removed


# ─────────────────────────────────────────────────────────────────────────────
# SENTENCE SPLITTING
# ─────────────────────────────────────────────────────────────────────────────

def split_sentences(text: str, min_len: int = 15) -> list[str]:
    if not text:
        return []
    ABBREVS = [
        "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr",
        "vs", "etc", "approx", "est", "vol", "fig",
        "no", "p", "pp", "e.g", "i.e", "Jan", "Feb",
        "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct",
        "Nov", "Dec", "U.S", "U.K",
    ]
    PLACEHOLDER = "<DOT>"
    protected = text
    for abbr in ABBREVS:
        protected = protected.replace(f"{abbr}.", f"{abbr}{PLACEHOLDER}")
    parts = re.split(r"(?<=[.!?])\s+", protected)
    sentences = []
    for part in parts:
        restored = part.replace(PLACEHOLDER, ".").strip()
        if len(restored) >= min_len:
            sentences.append(restored)
    return sentences


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN BUDGET
# ─────────────────────────────────────────────────────────────────────────────

def trim_to_token_budget(text: str, max_tokens: int) -> tuple[str, bool]:
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text, False
    chunk      = text[:max_chars]
    last_break = max(chunk.rfind(". "), chunk.rfind(".\n"))
    if last_break > max_chars * 0.7:
        chunk = chunk[:last_break + 1]
    return chunk.strip(), True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLEAN FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text: str, config: CleanConfig | None = None) -> CleanResult:
    if not text or not isinstance(text, str):
        return CleanResult(text="", mode="prose",
                           original_chars=0, cleaned_chars=0, sentences=0)

    cfg           = config or CleanConfig()
    original_chars = len(text)

    if cfg.fix_unicode:
        text = _fix_unicode(text)
    if cfg.normalize_quotes:
        text = _normalize_quotes(text)
    if cfg.mode == "transcript":
        text = _remove_vtt_artifacts(text)
    if cfg.remove_html_tags:
        text = _remove_html(text)

    # Code mode — skip destructive cleaning
    if cfg.mode == "code":
        if cfg.normalize_spaces:
            text = _normalize_whitespace(text)
        return CleanResult(
            text=text, mode=cfg.mode,
            original_chars=original_chars, cleaned_chars=len(text),
            sentences=len(text.splitlines()),
        )

    if cfg.remove_urls:
        text = _remove_urls(text)
    if cfg.remove_hashtags:
        text = _remove_hashtags(text)
    if cfg.remove_emojis:
        text = _remove_emojis(text)
    if cfg.mode in ("prose", "social"):
        text = _remove_boilerplate(text)
    if cfg.normalize_spaces:
        text = _normalize_whitespace(text)

    sentences = split_sentences(text, min_len=cfg.min_sentence_len)
    duplicates_removed = 0
    if cfg.dedupe_lines and sentences:
        sentences, duplicates_removed = deduplicate(sentences, threshold=cfg.dedupe_threshold)

    sentences = sentences[:cfg.max_sentences]
    text      = " ".join(sentences)

    truncated = False
    if cfg.max_tokens:
        text, truncated = trim_to_token_budget(text, cfg.max_tokens)

    return CleanResult(
        text=text, mode=cfg.mode,
        original_chars=original_chars, cleaned_chars=len(text),
        sentences=len(sentences),
        duplicates_removed=duplicates_removed,
        truncated=truncated,
    )


def clean(text: str, mode: str = "prose", max_tokens: Optional[int] = None, **overrides) -> CleanResult:
    cfg = CleanConfig(**{
        **CONFIGS.get(mode, CONFIGS["prose"]).__dict__,
        **({"max_tokens": max_tokens} if max_tokens else {}),
        **overrides,
    })
    return clean_text(text, config=cfg)


# ─────────────────────────────────────────────────────────────────────────────
# COMMENTS CLEANER
# ─────────────────────────────────────────────────────────────────────────────

def clean_comments(comments: list[str], config: CleanConfig | None = None) -> list[str]:
    cfg     = config or CONFIGS["social"]
    cleaned = []
    for c in comments:
        if not c or not isinstance(c, str):
            continue
        result = clean_text(c.strip(), config=cfg)
        if result.cleaned_chars >= cfg.min_comment_len:
            cleaned.append(result.text)
    deduped, _ = deduplicate(cleaned, threshold=cfg.dedupe_threshold)
    return deduped[:cfg.max_comments]


# ─────────────────────────────────────────────────────────────────────────────
# PROCESSOR OUTPUT CLEANER
# ─────────────────────────────────────────────────────────────────────────────

# Metadata fields — pass through unchanged, never clean these
# FIXED: source_type="github_repo" was being filtered out (only 10 chars, below min_sentence_len=15)
_SKIP_CLEAN_FIELDS = {
    "source_type", "url", "video_id", "channel",
    "author", "date", "source", "title",
}

# Maps field name → cleaning mode
_FIELD_MODES: dict[str, str] = {
    "content":         "prose",
    "transcript":      "transcript",
    "caption":         "social",
    "overview":        "prose",
    "description":     "prose",
    "readme":          "prose",
    "ocr_text":        "ocr",
    "code":            "code",
    "comments":        "social",
    "unique_comments": "social",
    "summary":         "prose",
    "article":         "prose",
    "text":            "prose",
    "body":            "prose",
}

def clean_processor_output(data: dict, max_tokens: Optional[int] = None) -> dict:
    """
    Takes raw output dict from any processor and returns a cleaned,
    LLM-ready dict. Preserves all keys; cleans text values by field type.
    Metadata fields (source_type, url, title, etc.) are never cleaned.
    """
    result = {}

    for key, value in data.items():
        if not value:
            continue

        # ── FIXED: never clean metadata fields ────────────────────────────
        if key in _SKIP_CLEAN_FIELDS:
            result[key] = value
            continue

        if isinstance(value, list):
            if key in ("comments", "unique_comments"):
                result[key] = clean_comments(value)
            else:
                joined     = "\n".join(str(v) for v in value if v)
                r          = clean(joined, mode="prose", max_tokens=max_tokens)
                result[key] = r.text

        elif isinstance(value, str):
            mode        = _FIELD_MODES.get(key, "prose")
            r           = clean(value, mode=mode, max_tokens=max_tokens)
            result[key] = r.text

        elif isinstance(value, dict):
            result[key] = clean_processor_output(value, max_tokens=max_tokens)

        else:
            result[key] = value   # numbers, booleans — pass through

    return result
