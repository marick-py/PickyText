# PickyText — OCR Pipeline

## Engine Priority

```
Windows OCR (WinRT)  ←  Primary (always available on Win11)
        ↓ fails or user override
Tesseract            ←  Optional (installed separately via installer option)
```

User can override engine preference in Settings. If Tesseract is selected but not installed, fall back to Windows OCR with a tray warning.

---

## Windows OCR (Primary)

### Why
- Built into Windows 10/11 — zero install size
- Handles CJK (Chinese, Japanese, Korean), Arabic, Hebrew, and 20+ other scripts natively
- Supports **vertical Japanese text** (`ja` language pack)
- Returns word-level bounding boxes natively
- Fast: ~100–300ms per region on average hardware
- No API key, no network, no license concerns

### Integration
Use `winrt` Python package (or `winsdk`) to call `Windows.Media.Ocr.OcrEngine`.

```python
# Simplified interface contract (windows_ocr.py)
async def recognize(image: PIL.Image, language_tag: str = "en") -> list[OcrWord]:
    # Returns list of OcrWord(text, bbox: QRect, confidence: float)
    ...
```

Language tag format: BCP-47 (`"en"`, `"ja"`, `"zh-Hans"`, `"ko"`, `"ar"`, etc.)

### Language Support (Windows OCR)
Languages available depend on installed Windows language packs. Windows 11 typically includes:
`en`, `fr`, `de`, `es`, `it`, `pt`, `ja`, `ko`, `zh-Hans`, `zh-Hant`, `ar`, `ru`, `nl`, `pl`, `sv`, `tr`, and more.

If the user's Windows doesn't have a language pack: graceful error with instructions to install via Windows Settings → Language.

### Vertical Japanese
Windows OCR handles `ja` vertically — pass the image as-is, the engine detects orientation. No preprocessing needed.

---

## Tesseract (Optional Fallback)

### When Used
- User explicitly selects Tesseract in settings
- Windows OCR unavailable (edge case)
- Future: character-level selection (Tesseract HOCR output supports it)

### Installation
Optional component in Inno Setup installer:
- Installer downloads Tesseract binary + selected language packs (`tessdata`)
- Language packs: ~4MB each; installer lets user pick languages
- Tesseract path auto-detected or manually set in settings

### Integration
Via `pytesseract` with `image_to_data()` for word-level bounding boxes.

```python
# Simplified interface contract (tesseract_ocr.py)
def recognize(image: PIL.Image, lang: str = "eng") -> list[OcrWord]:
    # Uses pytesseract.image_to_data with output_type=DataFrame
    # Returns list of OcrWord(text, bbox: QRect, confidence: float)
    ...
```

Tesseract lang codes differ from BCP-47: `eng`, `jpn`, `jpn_vert`, `chi_sim`, `chi_tra`, `kor`, `ara`, `rus`, etc.

A mapping table between BCP-47 and Tesseract lang codes is maintained in `config/defaults.py`.

---

## OCR Router (`ocr/engine.py`)

```python
class OcrEngine:
    def __init__(self, settings): ...
    
    def recognize(self, image: PIL.Image, language: str) -> list[OcrWord]:
        """
        Routes to primary/fallback engine based on settings and availability.
        language: BCP-47 tag
        Returns unified OcrWord list regardless of engine used.
        """
```

Unified output type:
```python
@dataclass
class OcrWord:
    text: str
    bbox: tuple[int, int, int, int]  # x, y, w, h in image coordinates
    confidence: float  # 0.0–1.0
    region_id: int     # which selection region this word belongs to
```

---

## OCR Flow in Application

1. User presses **Analyze** in Mode A
2. UI thread dispatches to `QThread` worker
3. Worker crops each selection region from the full screenshot (`PIL.Image.crop`)
   - If no selections: uses full screenshot as single region
4. Each region passed to `OcrEngine.recognize()` with source language setting
5. Results collected as `list[list[OcrWord]]` (one list per region)
6. Worker emits signal with results → UI thread renders bounding boxes
7. Overlay switches to Mode B

### Image Preprocessing (Optional, configurable)
Before OCR, optionally apply:
- Grayscale conversion (improves accuracy on color backgrounds)
- Contrast enhancement (PIL `ImageEnhance.Contrast`)
- Upscaling small regions (< 100px height → 2x upscale with Lanczos)

These are toggleable in advanced settings. Default: off (Windows OCR doesn't need them).

---

## Output Coordinate Mapping

OCR runs on the **cropped region image** (in region-local coordinates).
Bounding boxes must be **remapped** to the full overlay canvas coordinates for rendering.

```
canvas_x = region_offset_x + (word_bbox_x * scale_factor)
canvas_y = region_offset_y + (word_bbox_y * scale_factor)
```

Where `scale_factor` accounts for any upscaling applied during preprocessing.

---

## Error Handling

| Error | Behavior |
|---|---|
| No language pack for Windows OCR | Tray warning + link to Windows Language Settings |
| Tesseract not found | Auto-fallback to Windows OCR + settings warning |
| Region too small (< 10x10px) | Skip region, show inline warning on canvas |
| OCR returns zero words | Show "No text detected" label in region |
| General exception | Spinner replaced with error + retry button |
