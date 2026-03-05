import re
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


# -------------------------
# Extract video ID
# -------------------------

def get_video_id(url: str) -> str | None:
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    if "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return None


# -------------------------
# Clean a single comment
# -------------------------

def is_meaningful(text: str) -> bool:
    """Filter out very short, spammy, or emoji-only comments."""
    cleaned = re.sub(r"[^\w\s]", "", text).strip()
    words = cleaned.split()
    return len(words) >= 4  # At least 4 real words


def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"http\S+", "", text)          # remove URLs
    text = re.sub(r"[^\w\s,.!?'-]", "", text)    # remove emojis/junk but keep punctuation
    text = re.sub(r"\s+", " ", text).strip()
    return text


# -------------------------
# yt-dlp metadata + comments
# -------------------------

def get_youtube_metadata(url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,       # must be False to get full metadata
        "getcomments": True,
        "extractor_args": {
            "youtube": {
                "comment_sort": ["top"],     # fetch top comments first
                "max_comments": ["30"],      # fetch 30, we'll filter down to 10-15
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    raw_comments = []
    for c in (info.get("comments") or []):
        text = (c.get("text") or "").strip()
        if text:
            raw_comments.append(text)

    return {
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "raw_comments": raw_comments,
    }


# -------------------------
# Get transcript / subtitles
# -------------------------

def get_transcript(url: str) -> str:
    video_id = get_video_id(url)
    if not video_id:
        return ""

    # Priority: manual captions first, then auto-generated
    language_options = [
        (["en", "hi"], False),   # manual captions
        (["en", "hi"], True),    # auto-generated subtitles
    ]

    for langs, auto in language_options:
        try:
            if auto:
                transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript_obj = transcripts.find_generated_transcript(langs)
                data = transcript_obj.fetch()
            else:
                data = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)

            return " ".join(t["text"] for t in data).strip()
        except Exception:
            continue

    return ""


# -------------------------
# Filter top meaningful comments
# -------------------------

def get_top_comments(raw_comments: list, max_count: int = 12) -> list:
    seen = set()
    result = []

    for comment in raw_comments:
        cleaned = clean_text(comment)
        key = cleaned.lower()

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


# -------------------------
# Main processor
# -------------------------

def process_youtube(url: str) -> dict:
    data = get_youtube_metadata(url)

    title = data.get("title", "")
    description = clean_text(data.get("description", ""))
    raw_comments = data.get("raw_comments", [])

    transcript = get_transcript(url)
    top_comments = get_top_comments(raw_comments, max_count=12)

    return {
        "title": title,
        "description": description,
        "transcript": transcript,           # empty string if not available
        "top_comments": top_comments,       # 10–15 meaningful, unique, top comments
    }
