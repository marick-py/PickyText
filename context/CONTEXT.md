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
| Feature | Status |
|---|---|
| Global hotkey (configurable) | ✅ Core |
| Screenshot of active monitor | ✅ Core |
| Overlay preview window (90% screen) | ✅ Core |
| Rect + freehand polygon region selection | ✅ Core |
| Per-region OCR (Windows OCR primary) | ✅ Core |
| Word-level selectable bounding boxes | ✅ Core |
| Per-region translation (LibreTranslate) | ✅ Core |
| Translation overlay toggle | ✅ Core |
| Copy selected / copy all text | ✅ Core |
| Save screenshot + OCR result | ✅ Core |
| History (configurable length, default 10) | ✅ Core |
| System tray icon + menu | ✅ Core |
| Light / Dark theme (tray toggle) | ✅ Core |
| Settings window (from tray) | ✅ Core |
| Start on Windows startup (registry) | ✅ Core |
| Installer (Inno Setup) | ✅ Core |
| Auto-update via GitHub Releases | ✅ Core |
| Optional local components (Tesseract, Argos) | ⚙️ Optional install |
| Character-level selection | 🔮 Future |
| Multi-rect single API request (separator trick) | ✅ Core |
| Docker LibreTranslate on VPS | ✅ Infrastructure |

## Name
**PickyText** — from "picking text" off the screen. Intuitive for non-technical users, memorable, and available as a GitHub repo name.

## Project Repo
- GitHub: `github.com/[user]/PickyText`
- Versioning: SemVer (`MAJOR.MINOR.PATCH`), git tags (`v1.0.0`)
- Releases: GitHub Releases with compiled `.exe` installer attached
- CI: GitHub Actions — auto-build installer on tag push

## Language & Runtime
- Python 3.13 (verify all deps are compatible before locking; fallback to 3.11 if needed)
- Windows 11 only (uses WinRT APIs for OCR)
- Packaged via PyInstaller → Inno Setup installer
