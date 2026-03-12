# PickyText — Project Context

## What Is It
PickyText is a lightweight Windows 11 desktop utility that lives in the system tray. It lets the user trigger a screenshot via a global hotkey, select regions of that screenshot, run OCR on them, interactively select the recognized text (like a PDF reader), and translate it — all in a clean, fast overlay UI.

## Target User
- Primary: Riccardo (developer + power user)
- Secondary: GitHub open-source audience (Windows 11 users who need quick screen OCR + translation)
- Assumed technical level of end user: non-technical (UI must be self-explanatory)

## Core Use Case
> "I'm reading something on screen in a foreign language. I press a hotkey, select the area, and instantly get the text + translation — without leaving the window I'm in."

## Feature Summary

Legend: ✅ Done · 🔨 Stub/skeleton · 📋 Planned · 🔮 Future

| Feature | Status |
|---|---|
| Global hotkey (`ctrl+shift+d`, configurable) | ✅ Done |
| Screenshot of active monitor | ✅ Done |
| Overlay preview window (80% screen, rounded corners) | ✅ Done |
| Tray icon + menu (capture, theme, settings, quit) | ✅ Done |
| Light / Dark theme (tray toggle, live apply) | ✅ Done |
| Settings window (all sections, Test Connection, registry) | ✅ Done |
| History store (JSON, rotating) | ✅ Done |
| History popup (list + text preview, clear) | ✅ Done |
| Auto-update check via GitHub Releases | ✅ Done |
| Start on Windows startup (registry write) | ✅ Done |
| OCR router (engine.py, tesseract_ocr.py) | ✅ Done |
| Translation router + batching + LibreTranslate client | ✅ Done |
| Argos Translate fallback wrapper | ✅ Done |
| Windows OCR (`windows_ocr.py`) | ✅ Done (WinRT async, tested) |
| Rect + freehand polygon region selection (Mode A canvas) | ✅ Done (`selection_layer.py`) |
| Word-level selectable bounding boxes (Mode B canvas) | ✅ Done (`text_layer.py`) |
| Per-region OCR + Mode A→B transition | ✅ Done (`overlay.py` mode switching + OCR worker thread) |
| Translation overlay toggle | ✅ Done (translation worker thread in overlay.py) |
| Copy selected / copy all text | ✅ Done (overlay.py Mode B bar) |
| Save screenshot + OCR result to history | ✅ Done (overlay.py Save button) |
| Loading spinner between modes | ✅ Done (`_SpinnerOverlay` in overlay.py) |
| Installer (Inno Setup + PyInstaller) | 📋 Planned |
| icon.ico (compiled from icon.svg) | ✅ Done (multi-size: 16–256px) |
| Optional local components (Tesseract, Argos) | ⚙️ Optional install |
| Character-level selection | 🔮 Future |
| Docker LibreTranslate on VPS | ✅ Infrastructure (spec ready) |

## Name
**PickyText** — from "picking text" off the screen. Intuitive for non-technical users, memorable, and available as a GitHub repo name.

## Project Repo
- GitHub: `github.com/[user]/PickyText`
- Versioning: SemVer (`MAJOR.MINOR.PATCH`), git tags (`v1.0.0`)
- Releases: GitHub Releases with compiled `.exe` installer attached
- CI: GitHub Actions — auto-build installer on tag push

## Language & Runtime
- Python 3.14 (active dev environment; all current deps confirmed compatible)
- Windows 11 only (uses WinRT APIs for OCR)
- Packaged via PyInstaller → Inno Setup installer
- `winsdk==1.0.0b10` used for WinRT bindings (not `winrt`)
