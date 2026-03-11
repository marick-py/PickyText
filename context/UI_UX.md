# PickyText — UI/UX Specification

## Overlay Window (Main Interface)

### General
- Opens on hotkey trigger
- Size: **90% of active monitor** (centered)
- Always on top, frameless window
- Background: screenshot image (full monitor capture, cropped/scaled to fit window)
- Two distinct interaction modes: **Mode A (Selection)** and **Mode B (Text)**
- Smooth mode transition (no window close/reopen)
- Pressing `Escape` closes the overlay (with confirmation if regions exist)

---

## Top Bar

Fixed bar at top of overlay window. Buttons change depending on mode.

### Mode A — Selection Mode

```
[ Add Rect ] [ Add Shape ] [ Clear All ]          [ Analyze ▶ ]
```

- **Add Rect**: Next mouse drag on the canvas creates a rectangle selection
- **Add Shape**: Next mouse drag creates a freehand polygon; mouse release closes the shape
- **Clear All**: Removes all current selections
- **Analyze ▶** (right-aligned): Triggers OCR pipeline. Transforms to Mode B on completion.

### Mode B — Text Mode

```
[ ← Change Selection ] [ Copy Selected ] [ Copy All ] [ Save ] [ History ]   [ Translate ▼ ]
```

- **← Change Selection**: Returns to Mode A (clears OCR results, keeps regions)
- **Copy Selected**: Copies currently highlighted word selection to clipboard
- **Copy All**: Copies all OCR'd text from all regions (separated by `\n---\n` per region)
- **Save**: Saves screenshot + OCR text to history and optionally to disk
- **History**: Opens history popup panel
- **Translate ▼** (right-aligned, dropdown): Shows source→target language selector, then triggers translation. Becomes a toggle once translated (show/hide overlay). 

---

## Canvas — Mode A (Selection Layer)

### Rect Selection
- User clicks **Add Rect**, then drags on canvas → rubber-band rectangle drawn
- On mouse release: rect is finalized
- Each rect rendered with:
  - Semi-transparent fill (accent color, ~30% opacity)
  - Solid border (1–2px, accent color)
  - **Resize handles** at 8 corners/edges
  - **Drag handle** (whole rect is draggable when not on resize handle)
  - **Delete button** (small ✕ on top-right corner of rect)
  - **Label** (auto: "Region 1", "Region 2"…)

### Shape Selection (Freehand Polygon)
- User clicks **Add Shape**, then clicks/drags on canvas to draw freehand path
- On mouse release: path is closed (straight line back to start point)
- A **bounding box** is computed around the polygon for resize/drag handles
- Resize scales the polygon proportionally within its bounding box
- Delete button same as rect

### General Canvas Behavior (Mode A)
- Multiple selections allowed (rects and shapes can coexist)
- Selections are layered; clicking selects the topmost
- If **no selections are drawn** when Analyze is pressed → uses full screenshot

---

## Canvas — Mode B (Text Layer)

### Bounding Boxes
- Word-level bounding boxes rendered over the screenshot as transparent clickable areas
- Each box highlights on hover (light fill, accent border)
- Click: selects/deselects a word
- Click + drag: range-selects all words intersected by drag path (like PDF text selection)
- Selected words: solid accent fill, text color inverted or contrast-adjusted
- Selected text is tracked per region

### Region Separation
- Each original selection region is visually bounded (subtle border remains)
- Translated text (when toggled on) appears as a semi-transparent overlay **within each region's bounds**
  - Font: clean sans-serif, auto-sized to fit region
  - Background: dark/light panel depending on theme
  - Original OCR text is dimmed underneath (not removed)

---

## Loading State (Between Mode A → Mode B)

When Analyze is clicked:
- A **semi-transparent dark layer** (~60% opacity) covers the canvas
- A **centered spinner** (animated, themed) is shown
- Top bar buttons are disabled
- No timeout — spinner stays until OCR completes or errors

On error: spinner replaced with error message + retry button.

---

## Themes

Two themes: **Light** and **Dark**. Toggled from tray icon menu. Persisted in settings.

| Element | Dark | Light |
|---|---|---|
| Overlay background (non-image area) | `#1a1a2e` | `#f0f0f0` |
| Top bar background | `#16213e` | `#ffffff` |
| Top bar text/icon | `#e0e0e0` | `#1a1a1a` |
| Buttons (normal) | `#0f3460` | `#e8e8e8` |
| Buttons (hover) | `#533483` | `#d0d0d0` |
| Accent color | `#e94560` | `#0066cc` |
| Selection fill | accent @ 30% | accent @ 25% |
| Spinner | accent color | accent color |
| Translation overlay bg | `#000000cc` | `#ffffffcc` |

Themes defined as QSS stylesheets in `ui/themes.py`, applied app-wide.

---

## Settings Window

Opened from tray menu. Clean dialog, tabbed or single scrollable page.

### Settings Fields
| Setting | Type | Default |
|---|---|---|
| Global hotkey | Key recorder widget | `Win+Shift+D` |
| Start on Windows startup | Toggle | Off |
| Theme | Dropdown (Light/Dark) | Dark |
| History length | Number input (1–100) | 10 |
| Default source language | Dropdown | Auto-detect |
| Default target language | Dropdown | English |
| Translation endpoint | Text field | `http://[VPS_IP]:5000` |
| OCR engine | Dropdown (Windows OCR / Tesseract) | Windows OCR |
| Tesseract path | File picker (visible if Tesseract selected) | Auto-detect |
| Check for updates on startup | Toggle | On |

Save / Cancel buttons at bottom.

---

## History Popup

Opened via top bar **History** button (Mode B) or tray menu.

- List of past captures (thumbnail + timestamp + first N chars of OCR text)
- Click entry: opens it in read-only overlay (Mode B, no re-OCR)
- Delete individual entries or clear all
- History stored in `%APPDATA%\PickyText\history\`

---

## Tray Icon Menu

Right-click tray icon:

```
PickyText v1.x.x
─────────────────
🌙 Switch to Light / ☀ Switch to Dark
⚙ Settings
📋 History
─────────────────
🔄 Check for Updates
─────────────────
✕ Quit
```

Left-click tray icon: trigger screenshot immediately (same as hotkey).

---

## General UX Principles
- No modal dialogs during capture flow (everything inline)
- All heavy operations show feedback (spinner, progress)
- Keyboard shortcuts in overlay: `Ctrl+C` copies selection, `Ctrl+A` selects all text, `Esc` closes
- Window appears on the monitor where the mouse cursor was at hotkey press time
- Overlay is not taskbar-visible (tool window flag)
