"""
utils/ocr.py
------------
OCR text extraction from images.

Priority:
  1. PaddleOCR  (if available and working)
  2. pytesseract (fallback — currently active on this machine)

PaddleOCR is skipped permanently for the session if it fails on first use
due to DLL/dependency errors (common when PyTorch is also installed on Windows).
"""

from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)

# ── Env flags ────────────────────────────────
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_use_mkldnn", "0")

# Session-level flag — set True if PaddleOCR fails with a hard error
# so we stop retrying it on every image
_paddle_disabled: bool = False
_paddle_instance        = None


def _get_paddle_ocr():
    """
    Lazy-init PaddleOCR. Returns None and permanently disables PaddleOCR
    for this session if a DLL / import error is encountered.
    """
    global _paddle_instance, _paddle_disabled

    if _paddle_disabled:
        return None
    if _paddle_instance is not None:
        return _paddle_instance

    # Silence paddle's own logging
    try:
        import paddle
        paddle.disable_signal_handler()
    except Exception:
        pass

    try:
        from paddleocr import PaddleOCR

        try:
            _paddle_instance = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,
                show_log=False,
            )
        except TypeError:
            # PaddleOCR v3+ removed show_log
            _paddle_instance = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,
            )

        return _paddle_instance

    except OSError as e:
        # WinError 127 = DLL dependency missing (common PyTorch+Paddle conflict)
        logger.warning(
            f"PaddleOCR disabled for this session — DLL error: {e}\n"
            f"  → Using Tesseract as primary OCR engine."
        )
        _paddle_disabled = True
        return None

    except ImportError:
        logger.info("PaddleOCR not installed — using Tesseract.")
        _paddle_disabled = True
        return None

    except Exception as e:
        logger.warning(f"PaddleOCR init failed: {e} — using Tesseract.")
        _paddle_disabled = True
        return None


def _paddle_extract(image_path: str) -> str:
    """Extract text using PaddleOCR."""
    ocr = _get_paddle_ocr()
    if ocr is None:
        raise RuntimeError("PaddleOCR unavailable")

    result = ocr.ocr(image_path, cls=True)
    lines  = []

    for page in (result or []):
        if not page:
            continue
        for item in page:
            try:
                text, confidence = item[1]
                if confidence >= 0.5:
                    lines.append(text.strip())
            except (IndexError, TypeError):
                pass

    return "\n".join(lines)


def _tesseract_extract(image_path: str) -> str:
    """Extract text using pytesseract (Tesseract-OCR)."""
    try:
        import pytesseract
        from PIL import Image

        img  = Image.open(image_path).convert("RGB")
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text.strip()

    except ImportError:
        raise RuntimeError(
            "pytesseract not installed. Run: pip install pytesseract pillow\n"
            "Also install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
        )


def extract_text(image_path: str) -> str:
    """
    Extract text from an image file.

    Tries PaddleOCR first (skipped if previously failed),
    then falls back to pytesseract.

    Returns:
        Extracted text string, or empty string if all methods fail.
    """
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return ""

    # ── 1. PaddleOCR ─────────────────────────────
    if not _paddle_disabled:
        try:
            text = _paddle_extract(image_path)
            if text.strip():
                logger.info(f"PaddleOCR: {len(text)} chars from '{os.path.basename(image_path)}'")
                return text
        except Exception as e:
            logger.warning(f"PaddleOCR failed on '{os.path.basename(image_path)}': {e}")

    # ── 2. Tesseract fallback ─────────────────────
    try:
        text = _tesseract_extract(image_path)
        if text.strip():
            logger.info(f"Tesseract: {len(text)} chars from '{os.path.basename(image_path)}'")
            return text
    except Exception as e:
        logger.error(f"Tesseract failed on '{os.path.basename(image_path)}': {e}")

    logger.error(f"All OCR methods failed for '{os.path.basename(image_path)}'")
    return ""
