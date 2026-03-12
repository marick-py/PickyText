# PickyText — Architecture

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.14 | Developer familiarity, ecosystem |
| GUI Framework | PyQt6 | Native-feeling widgets, tray support, full theming, performance |
| Global Hotkey | `keyboard` library | Cross-process hotkey registration on Windows |
| Screenshot | `mss` | Fastest multi-monitor screenshot lib in Python |
| OCR Primary | Windows OCR (WinRT via `winsdk` or `winrt`) | Built-in Win11, zero deps, CJK/vertical support |
| OCR Fallback | Tesseract (`pytesseract`) | Optional install, wider language model support |
| Translation | LibreTranslate (self-hosted VPS) | Free, private, supports 30+ langs incl. CJK |
| Translation Fallback | Argos Translate (local) | Optional install, same engine as LibreTranslate |
| Tray Icon | PyQt6 `QSystemTrayIcon` | Native integration |
| Installer | Inno Setup | Professional, Windows-native, uninstall support |
| Packaging | PyInstaller | Single-folder or onefile `.exe` |
| Auto-update | GitHub Releases API | Lightweight, no service required |
| History Storage | JSON file (rotating, configurable length) | Simple, human-readable, light |
| Settings Storage | JSON (`config/settings.py`) | Lightweight, easy to hand-edit, at `%APPDATA%\PickyText\settings.json` |

## Module Structure

Layout is **flat at repo root** (no `pickytext/` wrapper package).

Status: ✅ implemented · 🔨 stub · 📋 not yet created

```
main.py                      ✅ Entry point, tray + hotkey init, Qt event loop
core/
    screenshot.py            ✅ Active-monitor detection (ctypes cursor pos), mss capture
    hotkey.py                ✅ keyboard lib daemon thread → Qt signal bridge
    history.py               ✅ JSON rotating store at %APPDATA%\PickyText\history.json
    updater.py               ✅ daemon thread, GitHub Releases API, semver compare
ocr/
    engine.py                ✅ Router: windows → tesseract fallback
    windows_ocr.py           ✅ WinRT async (winsdk), asyncio.run() in QThread worker
    tesseract_ocr.py         ✅ pytesseract.image_to_data wrapper (requires optional install)
translation/
    engine.py                ✅ Router + separator-trick batching
    libretranslate.py        ✅ httpx async client + ping()
    argos.py                 ✅ argostranslate wrapper (requires optional install)
ui/
    tray.py                  ✅ QSystemTrayIcon, programmatic fallback icon, context menu
    overlay.py               ✅ Mode switching (A↔B), OCR worker QThread, spinner, dual top bars
    selection_layer.py       ✅ Mode A: rect + polygon drawing, resize handles, drag, delete
    text_layer.py            ✅ Mode B: word bbox rendering, click/drag selection, translation overlay
    settings_window.py       ✅ Full form: hotkey, OCR, translation, appearance, history
    history_popup.py         ✅ Splitter list/preview, clear all
    themes.py                ✅ Dark + Light QSS, ACCENT dict, SELECTION_FILL_ALPHA
models/
    region.py                ✅ Region dataclass (RECT | POLYGON, geometry, ocr_words, translation)
    ocr_result.py            ✅ OcrWord dataclass (text, bbox, confidence, region_id)
config/
    settings.py              ✅ JSON load/save at %APPDATA%\PickyText\settings.json
    defaults.py              ✅ DEFAULTS dict + TESSERACT_LANG_MAP (BCP-47 → tessdata codes)
assets/
    icon.svg                 ✅ Blue rounded square, document, text lines, cursor arrow
    icon.ico                 ✅ Multi-size (16–256px) compiled from icon.svg via cairosvg
installer/
    pickytext.iss            📋 Inno Setup script
pickytext.spec               📋 PyInstaller spec
```

## Data Flow

```
[Global Hotkey: ctrl+shift+d]
    → screenshot.py captures active monitor (mss, cursor-based monitor detection)
    → overlay.py opens at 80% screen size (DWM rounded corners)
    → MODE A: selection_layer.py (draw rects / polygons)
        → user clicks Analyze
        → each region cropped from screenshot
        → ocr/engine.py processes each region → list of (word, bbox) per region
        → overlay switches to MODE B
    → MODE B: text_layer.py renders word bboxes over image
        → user selects words (mouse drag over bboxes)
        → user clicks Translate
        → translation/engine.py called with separator-batched regions
        → translated text rendered as overlay on image
        → Copy / Save / History actions available
```

## Thread Model

- **Main thread**: Qt event loop (UI)
- **Hotkey thread**: `keyboard` library listener (daemon thread)
- **OCR thread**: `QThread` or `concurrent.futures.ThreadPoolExecutor` — keeps UI responsive during analysis
- **Translation thread**: Same executor — async HTTP to VPS
- **Updater**: Runs once at startup in background thread, posts tray notification if update available

## RAM Budget (Sleep Mode)
Target: **< 50MB RSS** when idle in tray

Achieved by:
- Overlay window destroyed (not just hidden) after use
- No background polling except update check at startup
- History kept as JSON on disk, not in memory
- PyQt6 app loop is near-zero CPU when no window is open

## Performance Notes
- `mss` screenshot: ~15–30ms for 1080p/4K
- Windows OCR: ~100–300ms per region (WinRT async, run in thread)
- LibreTranslate VPS: ~100–400ms per request (network dependent)
- All heavy ops run off main thread; UI shows spinner during wait
