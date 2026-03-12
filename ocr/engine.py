"""
OCR router — selects Windows OCR (primary) or Tesseract (fallback).
Stub: full implementation requires Opus session for WinRT/QThread bridge.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image
    from models.ocr_result import OcrWord


class OcrEngine:
    def __init__(self, settings: dict) -> None:
        self._settings = settings

    def recognize(self, image: "Image.Image", language: str) -> list["OcrWord"]:
        """
        Route to the configured engine and return a unified OcrWord list.
        language: BCP-47 tag (e.g. "en", "ja", "zh-Hans")
        """
        engine = self._settings.get("ocr_engine", "windows")
        if engine == "windows":
            from ocr.windows_ocr import recognize as win_recognize
            return win_recognize(image, language)
        from ocr.tesseract_ocr import recognize as tess_recognize
        return tess_recognize(image, language)
