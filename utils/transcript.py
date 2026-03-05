"""
transcript.py
-------------
Extracts transcripts/speech from:
  - YouTube videos, Shorts, Playlists
  - Local video files  (mp4, mkv, mov, avi, webm …)
  - Local audio files  (mp3, wav, ogg, flac, m4a …)
  - Direct audio URLs  (http/https .mp3, .wav, etc.)
  - Instagram / Loom / Vimeo (via yt-dlp download → Whisper)

Strategy per source:
  1. YouTube  → YouTubeTranscriptApi (fast, free, no model needed)
               → multi-language + preferred language fallback
               → yt-dlp auto-caption fallback
               → Whisper STT final fallback
  2. Video file / URL → ffmpeg extract audio → Whisper STT
  3. Audio file → Whisper STT directly

Returns a structured TranscriptResult dataclass.
"""

from __future__ import annotations

import os
import re
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")  # tiny/base/small/medium/large
PREFERRED_LANGS    = ["en", "en-US", "en-GB"]            # order matters for YouTube fallback

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".aac",
              ".m4a", ".wma", ".opus", ".aiff", ".webm"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm",
              ".flv", ".wmv", ".m4v", ".3gp", ".ogv"}

# ─────────────────────────────────────────────
# LAZY MODEL LOADER
# ─────────────────────────────────────────────

_whisper_model = None

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            logger.info(f"Loading Whisper model '{WHISPER_MODEL_SIZE}'…")
            _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
        except ImportError:
            raise ImportError("openai-whisper not installed. Run: pip install openai-whisper")
    return _whisper_model


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class TranscriptSegment:
    text: str
    start: float = 0.0   # seconds
    end:   float = 0.0
    lang:  str   = "en"

    def __str__(self):
        return self.text


@dataclass
class TranscriptResult:
    source:   str
    method:   str                                   # "youtube_api" | "whisper" | "ytdlp_caption"
    language: str = "en"
    segments: list[TranscriptSegment] = field(default_factory=list)
    error:    Optional[str] = None

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip())

    @property
    def timestamped(self) -> str:
        """Human-readable transcript with timestamps."""
        lines = []
        for s in self.segments:
            ts = f"[{_fmt_time(s.start)} → {_fmt_time(s.end)}]"
            lines.append(f"{ts}  {s.text.strip()}")
        return "\n".join(lines)

    def __str__(self):
        return self.text


def _fmt_time(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ─────────────────────────────────────────────
# VIDEO ID EXTRACTION
# ─────────────────────────────────────────────

def get_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from any YouTube URL format."""
    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/live/([a-zA-Z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def get_playlist_id(url: str) -> Optional[str]:
    qs = parse_qs(urlparse(url).query)
    return qs.get("list", [None])[0]


# ─────────────────────────────────────────────
# YOUTUBE — API TRANSCRIPT
# ─────────────────────────────────────────────

def _youtube_api_transcript(
    video_id: str,
    preferred_langs: list[str] = PREFERRED_LANGS,
) -> Optional[TranscriptResult]:
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
        )

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try preferred languages first
        transcript = None
        for lang in preferred_langs:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except Exception:
                continue

        # Fall back to any manually created transcript
        if not transcript:
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    transcript_list._manually_created_transcripts.keys()
                )
            except Exception:
                pass

        # Fall back to any auto-generated
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(
                    transcript_list._generated_transcripts.keys()
                )
            except Exception:
                pass

        if not transcript:
            return None

        data = transcript.fetch()
        lang_code = transcript.language_code

        segments = [
            TranscriptSegment(
                text  = entry["text"],
                start = entry["start"],
                end   = entry["start"] + entry.get("duration", 0),
                lang  = lang_code,
            )
            for entry in data
        ]

        return TranscriptResult(
            source   = f"https://youtube.com/watch?v={video_id}",
            method   = "youtube_api",
            language = lang_code,
            segments = segments,
        )

    except Exception as e:
        logger.warning(f"YouTube API transcript failed for {video_id}: {e}")
        return None


# ─────────────────────────────────────────────
# YT-DLP CAPTION FALLBACK
# ─────────────────────────────────────────────

def _ytdlp_caption(url: str) -> Optional[TranscriptResult]:
    """Download auto-subtitle via yt-dlp and parse the .vtt file."""
    try:
        import yt_dlp
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = {
                "skip_download": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-orig"],
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            vtt_files = list(Path(tmpdir).glob("*.vtt"))
            if not vtt_files:
                return None

            raw = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
            text = _parse_vtt(raw)
            if not text:
                return None

            return TranscriptResult(
                source   = url,
                method   = "ytdlp_caption",
                language = "en",
                segments = [TranscriptSegment(text=text)],
            )
    except Exception as e:
        logger.warning(f"yt-dlp caption fallback failed: {e}")
        return None


def _parse_vtt(vtt_text: str) -> str:
    """Strip VTT headers and tags, return clean text."""
    lines = vtt_text.splitlines()
    result = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        if re.match(r"^\d+$", line):
            continue
        # Remove HTML tags like <c>, <00:00:01.000>
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in result[-1:]:  # deduplicate consecutive
            result.append(clean)
    return " ".join(result)


# ─────────────────────────────────────────────
# AUDIO EXTRACTION (ffmpeg)
# ─────────────────────────────────────────────

def extract_audio(
    source_path: str,
    output_path: Optional[str] = None,
    sample_rate: int = 16000,
) -> str:
    """
    Extract mono 16kHz PCM WAV from a video or audio file.
    If output_path is None, creates a temp file.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_path = tmp.name
        tmp.close()

    cmd = [
        "ffmpeg", "-y",
        "-i", source_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        output_path
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        err = result.stderr.decode(errors="ignore")
        raise RuntimeError(f"ffmpeg failed: {err[-300:]}")

    return output_path


# ─────────────────────────────────────────────
# WHISPER STT
# ─────────────────────────────────────────────

def _whisper_transcribe(
    audio_path: str,
    source_label: str = "",
    language: Optional[str] = None,
) -> TranscriptResult:
    """Run Whisper on an audio file, return structured result."""
    model = _get_whisper()

    kwargs = {"verbose": False}
    if language:
        kwargs["language"] = language

    raw = model.transcribe(audio_path, **kwargs)

    segments = [
        TranscriptSegment(
            text  = seg["text"].strip(),
            start = seg["start"],
            end   = seg["end"],
            lang  = raw.get("language", "en"),
        )
        for seg in raw.get("segments", [])
        if seg.get("text", "").strip()
    ]

    # Fallback if segments missing
    if not segments and raw.get("text"):
        segments = [TranscriptSegment(text=raw["text"].strip())]

    return TranscriptResult(
        source   = source_label or audio_path,
        method   = "whisper",
        language = raw.get("language", "en"),
        segments = segments,
    )


# ─────────────────────────────────────────────
# YT-DLP DOWNLOAD (non-YouTube video URLs)
# ─────────────────────────────────────────────

def _download_audio_ytdlp(url: str, output_dir: str) -> Optional[str]:
    """Download best audio from any URL via yt-dlp."""
    try:
        import yt_dlp
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        files = list(Path(output_dir).glob("audio.*"))
        return str(files[0]) if files else None
    except Exception as e:
        logger.warning(f"yt-dlp download failed: {e}")
        return None


# ─────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────

def get_transcript(
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    language: Optional[str] = None,
    whisper_fallback: bool = True,
    keep_temp: bool = False,
) -> TranscriptResult:
    """
    Universal transcript extractor.

    Args:
        url:              Any URL (YouTube, Instagram, Loom, Vimeo, direct audio)
        file_path:        Local video or audio file path
        language:         Force Whisper to use this language ('en', 'hi', 'fr' …)
        whisper_fallback: Use Whisper if API transcript unavailable
        keep_temp:        Don't delete temp audio files (for debugging)

    Returns:
        TranscriptResult with .text, .timestamped, .segments, .method
    """

    # ── Local audio file ────────────────────────────────────
    if file_path:
        p = Path(file_path)
        ext = p.suffix.lower()

        if ext in AUDIO_EXTS:
            logger.info(f"Transcribing audio file: {file_path}")
            return _whisper_transcribe(file_path, source_label=file_path,
                                       language=language)

        if ext in VIDEO_EXTS:
            logger.info(f"Extracting audio from video: {file_path}")
            tmp_audio = extract_audio(file_path)
            try:
                return _whisper_transcribe(tmp_audio, source_label=file_path,
                                           language=language)
            finally:
                if not keep_temp and os.path.exists(tmp_audio):
                    os.remove(tmp_audio)

    # ── YouTube URL ─────────────────────────────────────────
    if url and re.search(r"youtube\.com|youtu\.be", url, re.I):
        video_id = get_video_id(url)

        if video_id:
            # 1. YouTube Transcript API
            result = _youtube_api_transcript(video_id)
            if result:
                logger.info(f"YouTube API transcript OK ({result.language}) for {video_id}")
                return result

            # 2. yt-dlp auto-caption
            result = _ytdlp_caption(url)
            if result:
                logger.info(f"yt-dlp caption fallback OK for {video_id}")
                return result

            # 3. Whisper STT
            if whisper_fallback:
                logger.info(f"Falling back to Whisper for {video_id}")
                with tempfile.TemporaryDirectory() as tmpdir:
                    audio = _download_audio_ytdlp(url, tmpdir)
                    if audio:
                        return _whisper_transcribe(audio, source_label=url,
                                                   language=language)

        return TranscriptResult(
            source=url, method="failed",
            error="Could not extract transcript from YouTube URL."
        )

    # ── Any other URL (Instagram, Loom, Vimeo, direct mp3 …) ──
    if url:
        logger.info(f"Downloading audio from URL via yt-dlp: {url}")
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = _download_audio_ytdlp(url, tmpdir)
            if audio:
                return _whisper_transcribe(audio, source_label=url,
                                           language=language)

        return TranscriptResult(
            source=url, method="failed",
            error="Could not download or transcribe from URL."
        )

    return TranscriptResult(
        source="", method="failed",
        error="No url or file_path provided."
    )


# ─────────────────────────────────────────────
# CONVENIENCE: plain text shortcut
# ─────────────────────────────────────────────

def transcribe(url: Optional[str] = None,
               file_path: Optional[str] = None,
               language: Optional[str] = None) -> str:
    """Returns plain text transcript string. Simpler alias for get_transcript()."""
    result = get_transcript(url=url, file_path=file_path, language=language)
    return result.text if not result.error else f"Transcript Error: {result.error}"


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract transcript from video/audio")
    parser.add_argument("source",         help="URL or local file path")
    parser.add_argument("--lang",         default=None,  help="Force language (e.g. en, hi, fr)")
    parser.add_argument("--timestamps",   action="store_true", help="Show timestamped output")
    parser.add_argument("--no-whisper",   action="store_true", help="Disable Whisper fallback")
    parser.add_argument("--model",        default=None,  help="Whisper model size (tiny/base/small/medium/large)")
    args = parser.parse_args()

    if args.model:
        WHISPER_MODEL_SIZE = args.model

    is_url = args.source.startswith("http")
    result = get_transcript(
        url       = args.source if is_url  else None,
        file_path = args.source if not is_url else None,
        language  = args.lang,
        whisper_fallback = not args.no_whisper,
    )

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(result.timestamped if args.timestamps else result.text)
        print(f"\nMethod: {result.method} | Language: {result.language} | Segments: {len(result.segments)}")
