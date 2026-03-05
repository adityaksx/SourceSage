import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


# -------------------------
# Extract video ID
# -------------------------

def get_video_id(url):

    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]

    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]

    if "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]

    return None


# -------------------------
# Get video metadata
# -------------------------

def get_video_metadata(url):

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(url, download=False)

        data = {
            "title": info.get("title"),
            "description": info.get("description"),
            "channel": info.get("uploader"),
            "views": info.get("view_count"),
            "upload_date": info.get("upload_date")
        }

        return data


# -------------------------
# Get transcript
# -------------------------

def get_transcript(url):

    video_id = get_video_id(url)

    if not video_id:
        return None

    try:

        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=["en", "hi"]
        )

        text = " ".join([t["text"] for t in transcript])

        return text

    except:
        return None


# -------------------------
# Get comments
# -------------------------

def get_comments(url, limit=100):

    ydl_opts = {
        "skip_download": True,
        "getcomments": True,
        "quiet": True
    }

    comments = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(url, download=False)

        for c in info.get("comments", [])[:limit]:

            comments.append(c.get("text"))

    return comments


# -------------------------
# Main processor
# -------------------------

def process_youtube(url):

    metadata = get_video_metadata(url)

    transcript = get_transcript(url)

    comments = get_comments(url)

    return {
        "metadata": metadata,
        "transcript": transcript,
        "comments": comments
    }