"""
Tesseract OCR fallback via pytesseract (optional install).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

from config.defaults import TESSERACT_LANG_MAP
from models.ocr_result import OcrWord


def recognize(image: "Image.Image", language: str = "en") -> list[OcrWord]:
    """Return word-level bounding boxes using Tesseract."""
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract is not installed. "
            "Install it with: pip install pytesseract"
        ) from exc

    lang = TESSERACT_LANG_MAP.get(language, "eng")
    data = pytesseract.image_to_data(
        image, lang=lang, output_type=pytesseract.Output.DICT
    )

    words: list[OcrWord] = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text:
            continue
        conf_raw = data["conf"][i]
        confidence = max(0.0, float(conf_raw)) / 100.0
        x = data["left"][i]
        y = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]
        words.append(OcrWord(text=text, bbox=(x, y, w, h), confidence=confidence, region_id=0))

    return words
