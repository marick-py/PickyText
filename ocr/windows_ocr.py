"""
Windows OCR via WinRT (winsdk).

The WinRT OcrEngine exposes async methods. We run them inside
`asyncio.run()` which is called from a worker thread (QThread)
— never from the Qt main thread.
"""
from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

from models.ocr_result import OcrWord

if TYPE_CHECKING:
    from PIL import Image


# ------------------------------------------------------------------
# Internal async helpers
# ------------------------------------------------------------------

async def _pil_to_software_bitmap(img: "Image.Image"):
    """Convert a PIL Image to a WinRT SoftwareBitmap via an in-memory PNG."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)          # type: ignore[arg-type]
    writer.write_bytes(png_bytes)        # type: ignore[arg-type]
    await writer.store_async()
    await writer.flush_async()
    stream.seek(0)

    decoder = await BitmapDecoder.create_async(stream)  # type: ignore[arg-type]
    return await decoder.get_software_bitmap_async()


async def _recognize_async(img: "Image.Image", language: str) -> list[OcrWord]:
    bitmap = await _pil_to_software_bitmap(img)

    engine = OcrEngine.try_create_from_language(Language(language))
    if engine is None:
        raise RuntimeError(
            f"Windows OCR engine not available for language '{language}'. "
            "Make sure the language pack is installed in Windows Settings → Language."
        )

    result = await engine.recognize_async(bitmap)

    words: list[OcrWord] = []
    if result.lines:
        for line in result.lines:
            if not line.words:
                continue
            for word in line.words:
                r = word.bounding_rect
                words.append(
                    OcrWord(
                        text=word.text,
                        bbox=(int(r.x), int(r.y), int(r.width), int(r.height)),
                        confidence=1.0,  # WinRT OCR does not expose per-word confidence
                        region_id=0,
                    )
                )
    return words


# ------------------------------------------------------------------
# Public sync API  (call from QThread worker, never from main thread)
# ------------------------------------------------------------------

def recognize(img: "Image.Image", language: str = "en") -> list[OcrWord]:
    """
    Run Windows OCR synchronously.

    Creates a fresh event loop each call — this is fine because the caller
    is a QThread worker whose only job is to run OCR.
    """
    return asyncio.run(_recognize_async(img, language))
