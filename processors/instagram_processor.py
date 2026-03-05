import yt_dlp
import re


# -------------------------
# Extract instagram metadata
# -------------------------

def get_instagram_metadata(url):

    ydl_opts = {
        "quiet": True,
        "skip_download": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(url, download=False)

        data = {
            "caption": info.get("description"),
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "comments": []
        }

        # collect comments if available
        if "comments" in info and info["comments"]:

            for c in info["comments"]:
                if c.get("text"):
                    data["comments"].append(c["text"])

        return data


# -------------------------
# Clean comments
# -------------------------

def clean_comments(comments):

    cleaned = []

    for comment in comments:

        c = comment.strip()

        if len(c) < 5:
            continue

        # remove emojis / junk
        c = re.sub(r"[^\w\s]", "", c)

        cleaned.append(c)

    return cleaned


# -------------------------
# AI-style unique filtering
# -------------------------

def unique_comments(comments):

    seen = set()
    unique = []

    for comment in comments:

        key = comment.lower()

        if key not in seen:
            seen.add(key)
            unique.append(comment)

    return unique


# -------------------------
# Main processor
# -------------------------

def process_instagram(url):

    data = get_instagram_metadata(url)

    caption = data.get("caption", "")
    title = data.get("title", "")

    comments = data.get("comments", [])

    comments = clean_comments(comments)

    comments = unique_comments(comments)

    return {
        "title": title,
        "caption": caption,
        "description": caption,
        "unique_comments": comments[:50]
    }