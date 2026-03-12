# PickyText — Settings, Tray & Configuration

## Settings Storage

- File: `%APPDATA%\PickyText\settings.json`
- Format: JSON (human-readable, easy to hand-edit or reset)
- Loaded on startup, written on save
- If file missing or corrupt: silently reset to defaults, recreate file

---

## Default Values (`config/defaults.py`) — ✅ Implemented

```python
DEFAULTS = {
    # Hotkey
    # NOTE: win+* combos require admin on some Windows configs — use ctrl+shift+*
    "hotkey": "ctrl+shift+d",

    # Screenshot
    "capture_monitor": "active",   # always the monitor where cursor is

    # OCR
    "ocr_engine": "windows",       # "windows" | "tesseract"
    "ocr_source_language": "auto", # BCP-47 or "auto"
    "tesseract_path": "",          # auto-detected if empty

    # Translation
    "translation_endpoint": "http://localhost:5000",  # user sets their VPS URL
    "translation_api_key": "",
    "translation_source_language": "auto",
    "translation_target_language": "en",
    "translation_fallback": "argos",  # "argos" | "none"

    # UI
    "theme": "dark",               # "dark" | "light"
    "overlay_size_pct": 80,        # % of monitor (changed from 90 — feels less claustrophobic)

    # History
    "history_enabled": True,
    "history_max_length": 10,      # number of entries kept
    "history_save_images": True,   # save screenshot thumbnails with history

    # Updates
    "check_updates_on_startup": True,

    # Startup
    "start_with_windows": False,
}
```

Also in `defaults.py`: `TESSERACT_LANG_MAP` — BCP-47 → Tesseract langpack code mapping for all 21 supported languages.

---

## Settings Window (`ui/settings_window.py`) — ✅ Implemented

Single dialog, clean layout, `QFormLayout` groups.

### Sections (all implemented)

**Hotkey**
- Plain text input showing current combo (e.g. `ctrl+shift+d`)
- Tip label warning about `win+*` requiring admin
- On Save: immediately calls `hotkey.update_hotkey()` in main.py

**OCR**
- Engine: dropdown (`Windows OCR` / `Tesseract`)
- Source language: dropdown with 22 languages + "Auto-detect" (BCP-47 codes)
- Tesseract path: `QLineEdit` + Browse button (`QFileDialog`)

**Translation**
- Endpoint URL: `QLineEdit`
- API key: `QLineEdit` with password echo + eye toggle button
- Source language: dropdown + "Auto-detect"
- Target language: dropdown (no auto option)
- **[Test Connection]** → `asyncio.run(client.ping())` inline, shows latency or error in red/green

**Appearance**
- Theme: dropdown (`Dark` / `Light`)
- Overlay size: `QSpinBox` (40–100%)
- Start with Windows: `QCheckBox` → writes/removes `HKCU\...\Run\PickyText` on Save

**History**
- Enable history: `QCheckBox`
- Max entries: `QSpinBox` (1–100)
- Save screenshot thumbnails: `QCheckBox`

**Footer**: `[Save]` `[Cancel]` — Save writes JSON, emits `settings_saved` signal

### Not yet implemented in settings window
- Key recorder widget (actual keyboard capture for hotkey recording)
- Hotkey conflict detection
- [Clear History] button with confirmation
- Check for updates toggle
- Version string + manual update check

---

## System Tray (`ui/tray.py`)

### Icon — current state
- `assets/icon.svg` ✅ created (blue rounded square, document, text lines, yellow highlight, cursor arrow)
- `assets/icon.ico` 📋 not yet compiled (needs cairosvg + Pillow or Inkscape CLI)
- Fallback: programmatic Qt pixmap drawn at runtime (red circle with "PT" in white) if `.ico` not found
- Tooltip: `"PickyText — Press ctrl+shift+d to capture"`
- Processing state icon: 📋 planned

### Left Click
- Currently does nothing (📋 planned: trigger capture on left click)

### Right Click Menu

```
PickyText v1.x.x          [disabled label]
─────────────────
☀ Switch to Light          [or 🌙 Switch to Dark — toggles]
⚙ Settings...
📋 History...
─────────────────
🔄 Check for Updates
─────────────────
✕ Quit
```

"Switch to Light/Dark" applies theme immediately app-wide and saves to settings.

---

## History System (`core/history.py`)

### Storage
```
%APPDATA%\PickyText\history\
├── index.json           # list of entry metadata
└── entries\
    ├── 20250311_142301\ 
    │   ├── screenshot.webp   # compressed thumbnail (if enabled)
    │   └── data.json         # OCR text, translations, timestamp, regions
    └── ...
```

### Entry Format (`data.json`)
```json
{
  "id": "20250311_142301",
  "timestamp": "2025-03-11T14:23:01",
  "monitor": "Monitor 1 (2560x1440)",
  "regions": [
    {
      "id": 1,
      "shape": "rect",
      "bbox": [100, 200, 400, 300],
      "ocr_text": "Hello world",
      "ocr_language": "en",
      "translation": "Ciao mondo",
      "translation_language": "it"
    }
  ]
}
```

### Rotation
- On each new capture saved: if `len(entries) >= history_max_length`, delete oldest entry folder
- `index.json` updated atomically (write to temp file, rename)

### History Popup
- Accessed from top bar (Mode B) or tray menu
- Shows scrollable list: thumbnail + timestamp + first region's OCR preview
- Click entry → opens read-only Mode B overlay with that capture
- Delete button per entry, "Clear All" at bottom

---

## Startup Registration

When "Start with Windows" is enabled:

```python
import winreg

key = winreg.OpenKey(
    winreg.HKEY_CURRENT_USER,
    r"Software\Microsoft\Windows\CurrentVersion\Run",
    0, winreg.KEY_SET_VALUE
)
winreg.SetValueEx(key, "PickyText", 0, winreg.REG_SZ, str(exe_path))
winreg.CloseKey(key)
```

When disabled:
```python
winreg.DeleteValue(key, "PickyText")
```

This is the standard approach used by apps like Slack, Discord, Spotify. No Task Scheduler needed. Windows UAC doesn't flag `HKCU` registry writes.

---

## Configuration Notes

- All settings are applied **immediately** on save (no restart required)
- Hotkey is re-registered live when changed
- Theme change re-applies QSS stylesheet to all open windows instantly
- Translation endpoint change tested with [Test Connection] button before saving
- If `%APPDATA%\PickyText\` doesn't exist on first run, it's created automatically
