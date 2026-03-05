import os
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi
import whisper


MODEL = whisper.load_model("base")


# -------------------------
# Extract YouTube video ID
# -------------------------

def get_video_id(url):

    if "youtu.be" in url:
        return url.split("/")[-1]

    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]

    if "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]

    return None


# -------------------------
# YouTube transcript
# -------------------------

def youtube_transcript(url):

    video_id = get_video_id(url)

    if not video_id:
        return None

    try:

        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        text = " ".join([t["text"] for t in transcript])

        return text

    except:
        return None


# -------------------------
# Extract audio from video
# -------------------------

def extract_audio(video_path):

    audio_path = video_path + ".wav"

    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        audio_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return audio_path


# -------------------------
# Speech to text
# -------------------------

def audio_to_text(audio_path):

    result = MODEL.transcribe(audio_path)

    return result["text"]


# -------------------------
# Instagram / video transcript
# -------------------------

def video_transcript(video_path):

    audio_path = extract_audio(video_path)

    text = audio_to_text(audio_path)

    return text


# -------------------------
# Main router
# -------------------------

def get_transcript(url=None, video_path=None):

    # YouTube transcript
    if url and ("youtube.com" in url or "youtu.be" in url):

        text = youtube_transcript(url)

        if text:
            return text

    # fallback speech recognition
    if video_path:
        return video_transcript(video_path)

    return None