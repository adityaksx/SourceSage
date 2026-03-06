import re
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO ID EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def get_video_id(url: str) -> str | None:
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    if "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^\w\s,.!?'-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_meaningful(text: str) -> bool:
    cleaned = re.sub(r"[^\w\s]", "", text).strip()
    return len(cleaned.split()) >= 4


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — METADATA ONLY (no comments — fast and reliable)
# ─────────────────────────────────────────────────────────────────────────────

def get_youtube_metadata(url: str) -> dict:
    """
    Fetches title, description, duration, view count, channel.
    Comments are intentionally excluded here — they are fetched
    separately in get_youtube_comments() so a comment failure
    never blocks metadata.
    """
    ydl_opts = {
        "quiet":         True,
        "skip_download": True,
        "extract_flat":  False,
        "getcomments":   False,       # ← KEY FIX: no comments here
        "no_warnings":   False,       # keep warnings visible for debugging
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {}

        return {
            "title":       info.get("title",        ""),
            "description": info.get("description",  ""),
            "duration":    info.get("duration",      0),     # seconds
            "view_count":  info.get("view_count",    0),
            "channel":     info.get("channel",       ""),
            "upload_date": info.get("upload_date",   ""),    # YYYYMMDD
            "tags":        info.get("tags",          []),
        }

    except yt_dlp.utils.DownloadError as e:
        print(f"[youtube_processor] yt-dlp download error: {e}")
        return {}
    except Exception as e:
        print(f"[youtube_processor] Metadata fetch failed: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — COMMENTS (separate call — failure is non-fatal)
# ─────────────────────────────────────────────────────────────────────────────

def get_youtube_comments(url: str, max_fetch: int = 30) -> list[str]:
    """
    Separate comment fetch — isolated so failures don't affect metadata.
    Returns empty list on any error (non-fatal).
    """
    ydl_opts = {
        "quiet":         True,
        "skip_download": True,
        "extract_flat":  False,
        "getcomments":   True,
        "no_warnings":   True,        # suppress "Incomplete data" warnings here
        "extractor_args": {
            "youtube": {
                "comment_sort": ["top"],
                "max_comments": [str(max_fetch)],
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return []

        raw = []
        for c in (info.get("comments") or []):
            text = (c.get("text") or "").strip()
            if text:
                raw.append(text)
        return raw

    except Exception as e:
        # Comment fetch failure is not an error — just skip comments
        print(f"[youtube_processor] Comments unavailable (non-fatal): {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — TRANSCRIPT
# ─────────────────────────────────────────────────────────────────────────────

def get_transcript(url: str) -> str:
    """
    Priority order:
      1. Manual English captions
      2. Manual Hindi captions
      3. Auto-generated English
      4. Auto-generated Hindi
      5. Any available auto-generated language (translated to English)
    Returns empty string if nothing available.
    """
    video_id = get_video_id(url)
    if not video_id:
        return ""

    # Try manual captions first
    try:
        data = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "hi"]
        )
        return " ".join(t["text"] for t in data).strip()
    except Exception:
        pass

    # Try auto-generated captions
    try:
        transcripts    = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript_obj = transcripts.find_generated_transcript(["en", "hi"])
        data           = transcript_obj.fetch()
        return " ".join(t["text"] for t in data).strip()
    except Exception:
        pass

    # Last resort — take any available transcript, translate to English
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        for t in transcripts:
            try:
                data = t.translate("en").fetch()
                return " ".join(item["text"] for item in data).strip()
            except Exception:
                continue
    except Exception:
        pass

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# COMMENT FILTER
# ─────────────────────────────────────────────────────────────────────────────

def get_top_comments(raw_comments: list, max_count: int = 12) -> list:
    seen   = set()
    result = []

    for comment in raw_comments:
        cleaned = clean_text(comment)
        key     = cleaned.lower()

        if not cleaned:
            continue
        if key in seen:
            continue
        if not is_meaningful(cleaned):
            continue

        seen.add(key)
        result.append(cleaned)

        if len(result) >= max_count:
            break

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

def process_youtube(url: str) -> dict:
    """
    3-stage fetch — each stage is independent.
    A failure in comments or transcript never blocks the metadata.

    Stage 1: Metadata  (title, description, views, channel) — fast, reliable
    Stage 2: Comments  (top 12 meaningful comments)         — optional, non-fatal
    Stage 3: Transcript (manual → auto → translated)        — best-effort
    """
    # Stage 1 — always run, required
    metadata     = get_youtube_metadata(url)

    if not metadata:
        print(f"[youtube_processor] Metadata fetch failed entirely for: {url}")
        return {}

    # Stage 2 — optional, never crashes the pipeline
    raw_comments = get_youtube_comments(url)
    top_comments = get_top_comments(raw_comments, max_count=12)

    # Stage 3 — best effort
    transcript   = get_transcript(url)

    if transcript:
        print(f"[youtube_processor] Transcript: {len(transcript.split())} words")
    else:
        print(f"[youtube_processor] No transcript available — using description only")

    return {
        "title":        metadata.get("title",       ""),
        "description":  clean_text(metadata.get("description", "")),
        "channel":      metadata.get("channel",     ""),
        "view_count":   metadata.get("view_count",  0),
        "duration":     metadata.get("duration",    0),
        "upload_date":  metadata.get("upload_date", ""),
        "tags":         metadata.get("tags",        []),
        "transcript":   transcript,
        "top_comments": top_comments,
    }
