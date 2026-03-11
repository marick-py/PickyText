# PickyText — Architecture

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.13 | Developer familiarity, ecosystem |
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
| Settings Storage | JSON or INI (via `configparser`) | Lightweight, easy to hand-edit |

## Module Structure

```
pickytext/
├── main.py                  # Entry point, tray init, hotkey registration
├── core/
│   ├── screenshot.py        # Monitor detection, mss capture
│   ├── hotkey.py            # Global hotkey listener (background thread)
│   ├── history.py           # History read/write, rotation
│   └── updater.py           # GitHub Releases version check
├── ocr/
│   ├── engine.py            # OCR router (Windows OCR → Tesseract fallback)
│   ├── windows_ocr.py       # WinRT OCR wrapper, returns word bounding boxes
│   └── tesseract_ocr.py     # Optional Tesseract wrapper (same output format)
├── translation/
│   ├── engine.py            # Translation router (LibreTranslate → Argos fallback)
│   ├── libretranslate.py    # HTTP client for VPS LibreTranslate instance
│   └── argos.py             # Optional local Argos Translate wrapper
├── ui/
│   ├── tray.py              # QSystemTrayIcon, context menu
│   ├── overlay.py           # Main 90% screen overlay window
│   ├── selection_layer.py   # Rect + polygon drawing canvas (Mode A)
│   ├── text_layer.py        # Word bounding box overlay, mouse selection (Mode B)
│   ├── settings_window.py   # Settings dialog
│   ├── history_popup.py     # History browser popup
│   └── themes.py            # Light/dark QSS stylesheets
├── models/
│   ├── region.py            # Region dataclass (shape, bbox, OCR result, translation)
│   └── ocr_result.py        # Word + bounding box dataclass
├── config/
│   ├── settings.py          # Settings loader/saver
│   └── defaults.py          # All default values in one place
└── assets/
    ├── icon.svg             # Placeholder tray/app icon
    └── icon.ico             # Compiled icon for Windows
```

## Data Flow

```
[Global Hotkey] 
    → screenshot.py captures active monitor (mss)
    → overlay.py opens at 90% screen size
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
