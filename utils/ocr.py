"""
ocr.py
------
Extracts text from:
  - Images  (JPG, PNG, BMP, TIFF, WEBP, GIF, etc.)
  - PDFs    (each page → OCR)
  - Directories of images (batch mode)

Features:
  - PaddleOCR with optional angle/orientation correction
  - Per-line confidence scores
  - Spatial layout preserved (top-to-bottom, left-to-right sort)
  - Auto image preprocessing (grayscale, denoise, contrast boost)
  - Multi-language support (pass lang="ch", "fr", "de", etc.)
  - PDF page-by-page extraction via pdf2image
  - Structured result dataclass + plain-text fallback
  - Safe lazy init — engine only loads when first needed
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class OCRLine:
    text: str
    confidence: float           # 0.0 – 1.0
    bbox: list[list[float]]     # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    def __str__(self):
        return self.text


@dataclass
class OCRResult:
    source: str                         # original file path
    lines: list[OCRLine] = field(default_factory=list)
    page: int = 1                       # for PDFs
    error: Optional[str] = None

    @property
    def text(self) -> str:
        """Full extracted text as a plain string."""
        return "\n".join(line.text for line in self.lines)

    @property
    def text_with_confidence(self) -> str:
        """Each line annotated with confidence score."""
        return "\n".join(
            f"{line.text}  [{line.confidence:.0%}]"
            for line in self.lines
        )

    @property
    def avg_confidence(self) -> float:
        if not self.lines:
            return 0.0
        return sum(l.confidence for l in self.lines) / len(self.lines)

    def __str__(self):
        return self.text


# ─────────────────────────────────────────────
# ENGINE (lazy singleton per language)
# ─────────────────────────────────────────────

_engines: dict[str, object] = {}

def _get_engine(lang: str = "en"):
    """Return a cached PaddleOCR engine for the requested language."""
    if lang not in _engines:
        try:
            from paddleocr import PaddleOCR
            _engines[lang] = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                show_log=False,
            )
            logger.info(f"PaddleOCR engine loaded for lang='{lang}'")
        except ImportError:
            raise ImportError(
                "paddleocr is not installed. Run: pip install paddleocr"
            )
    return _engines[lang]


# ─────────────────────────────────────────────
# IMAGE PREPROCESSING
# ─────────────────────────────────────────────

def preprocess_image(
    image: Image.Image,
    grayscale: bool = False,
    denoise: bool = False,
    enhance_contrast: float = 1.0,
    enhance_sharpness: float = 1.0,
    upscale_factor: float = 1.0,
) -> Image.Image:
    """
    Optional preprocessing pipeline to improve OCR accuracy.
    All steps are off by default — enable what you need.
    """
    if upscale_factor > 1.0:
        new_w = int(image.width  * upscale_factor)
        new_h = int(image.height * upscale_factor)
        image = image.resize((new_w, new_h), Image.LANCZOS)

    if grayscale:
        image = image.convert("L").convert("RGB")

    if denoise:
        image = image.filter(ImageFilter.MedianFilter(size=3))

    if enhance_contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(enhance_contrast)

    if enhance_sharpness != 1.0:
        image = ImageEnhance.Sharpness(image).enhance(enhance_sharpness)

    return image


# ─────────────────────────────────────────────
# CORE: extract from a PIL Image object
# ─────────────────────────────────────────────

def extract_from_pil(
    image: Image.Image,
    source_label: str = "pil_image",
    lang: str = "en",
    min_confidence: float = 0.0,
    preprocess_kwargs: dict | None = None,
    page: int = 1,
) -> OCRResult:
    """Run OCR on a PIL Image and return a structured OCRResult."""

    result = OCRResult(source=source_label, page=page)

    try:
        if preprocess_kwargs:
            image = preprocess_image(image, **preprocess_kwargs)

        # Convert to numpy array (PaddleOCR accepts both file paths and arrays)
        img_array = np.array(image.convert("RGB"))

        engine = _get_engine(lang)
        raw = engine.ocr(img_array, cls=True)

        if not raw or raw[0] is None:
            return result  # blank / no text found

        # Sort lines top-to-bottom, then left-to-right by bounding box
        lines_raw = sorted(
            raw[0],
            key=lambda x: (x[0][0][1], x[0][0][0])  # (top-y, left-x)
        )

        for item in lines_raw:
            bbox, (text, conf) = item[0], item[1]
            if conf >= min_confidence and text.strip():
                result.lines.append(OCRLine(
                    text=text.strip(),
                    confidence=float(conf),
                    bbox=bbox,
                ))

    except Exception as e:
        result.error = str(e)
        logger.error(f"OCR failed on '{source_label}': {e}")

    return result


# ─────────────────────────────────────────────
# EXTRACT FROM IMAGE FILE
# ─────────────────────────────────────────────

SUPPORTED_IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff",
    ".tif", ".webp", ".gif", ".heic"
}

def extract_text(
    image_path: str,
    lang: str = "en",
    min_confidence: float = 0.0,
    preprocess_kwargs: dict | None = None,
) -> str:
    """
    Simple interface: returns extracted text as a plain string.
    Supports images and PDFs.
    """
    result = extract(image_path, lang=lang,
                     min_confidence=min_confidence,
                     preprocess_kwargs=preprocess_kwargs)

    if isinstance(result, list):
        # PDF — join all pages
        parts = []
        for r in result:
            if r.text:
                parts.append(f"[Page {r.page}]\n{r.text}")
        return "\n\n".join(parts) if parts else ""

    return result.text if not result.error else f"OCR Error: {result.error}"


def extract(
    path: str,
    lang: str = "en",
    min_confidence: float = 0.0,
    preprocess_kwargs: dict | None = None,
) -> OCRResult | list[OCRResult]:
    """
    Full interface: returns OCRResult (image) or list[OCRResult] (PDF).
    """
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = p.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(path, lang=lang,
                            min_confidence=min_confidence,
                            preprocess_kwargs=preprocess_kwargs)

    if ext in SUPPORTED_IMAGE_EXTS or ext == "":
        image = Image.open(path)
        return extract_from_pil(image, source_label=path,
                                lang=lang,
                                min_confidence=min_confidence,
                                preprocess_kwargs=preprocess_kwargs)

    raise ValueError(f"Unsupported file type: {ext}")


# ─────────────────────────────────────────────
# PDF SUPPORT
# ─────────────────────────────────────────────

def _extract_pdf(
    pdf_path: str,
    lang: str = "en",
    dpi: int = 200,
    min_confidence: float = 0.0,
    preprocess_kwargs: dict | None = None,
) -> list[OCRResult]:
    """Convert each PDF page to an image, then run OCR."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError(
            "pdf2image is not installed. Run: pip install pdf2image\n"
            "Also install poppler: https://github.com/Belval/pdf2image#windows"
        )

    pages = convert_from_path(pdf_path, dpi=dpi)
    results = []

    for page_num, page_image in enumerate(pages, start=1):
        logger.info(f"OCR: PDF '{pdf_path}' page {page_num}/{len(pages)}")
        result = extract_from_pil(
            page_image,
            source_label=f"{pdf_path}::page{page_num}",
            lang=lang,
            min_confidence=min_confidence,
            preprocess_kwargs=preprocess_kwargs,
            page=page_num,
        )
        results.append(result)

    return results


# ─────────────────────────────────────────────
# BATCH: process a whole directory
# ─────────────────────────────────────────────

def extract_directory(
    directory: str,
    lang: str = "en",
    min_confidence: float = 0.0,
    recursive: bool = False,
    preprocess_kwargs: dict | None = None,
) -> dict[str, OCRResult | list[OCRResult]]:
    """
    Run OCR on every supported file in a directory.
    Returns { filename: OCRResult } mapping.
    """
    d = Path(directory)
    if not d.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    glob = d.rglob("*") if recursive else d.glob("*")
    all_exts = SUPPORTED_IMAGE_EXTS | {".pdf"}
    results = {}

    for f in sorted(glob):
        if f.suffix.lower() in all_exts:
            try:
                results[f.name] = extract(
                    str(f), lang=lang,
                    min_confidence=min_confidence,
                    preprocess_kwargs=preprocess_kwargs
                )
                logger.info(f"Processed: {f.name}")
            except Exception as e:
                logger.warning(f"Skipped {f.name}: {e}")

    return results


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Extract text via OCR")
    parser.add_argument("path",         help="Image file, PDF, or directory")
    parser.add_argument("--lang",       default="en",  help="OCR language code (default: en)")
    parser.add_argument("--min-conf",   default=0.0,   type=float, help="Min confidence 0–1")
    parser.add_argument("--confidence", action="store_true",       help="Show confidence scores")
    parser.add_argument("--preprocess", action="store_true",       help="Auto-enhance contrast+sharpness")
    parser.add_argument("--dpi",        default=200,   type=int,   help="DPI for PDF rendering")
    args = parser.parse_args()

    pre = {"enhance_contrast": 1.4, "enhance_sharpness": 1.5} if args.preprocess else None

    path = Path(args.path)

    if path.is_dir():
        batch = extract_directory(str(path), lang=args.lang,
                                  min_confidence=args.min_conf,
                                  preprocess_kwargs=pre)
        for name, res in batch.items():
            print(f"\n{'='*50}\n{name}\n{'='*50}")
            if isinstance(res, list):
                for r in res:
                    print(f"\n--- Page {r.page} ---\n{r.text}")
            else:
                print(res.text_with_confidence if args.confidence else res.text)

    elif path.suffix.lower() == ".pdf":
        pages = _extract_pdf(str(path), lang=args.lang,
                             min_confidence=args.min_conf,
                             preprocess_kwargs=pre)
        for r in pages:
            print(f"\n--- Page {r.page} (avg conf: {r.avg_confidence:.0%}) ---")
            print(r.text_with_confidence if args.confidence else r.text)

    else:
        result = extract(str(path), lang=args.lang,
                         min_confidence=args.min_conf,
                         preprocess_kwargs=pre)
        if isinstance(result, OCRResult):
            print(result.text_with_confidence if args.confidence else result.text)
            print(f"\nAvg confidence: {result.avg_confidence:.0%} | Lines: {len(result.lines)}")
