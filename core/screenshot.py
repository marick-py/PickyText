"""Captures the active monitor (the one containing the mouse cursor)."""
from ctypes import byref, windll, wintypes

import mss
from PIL import Image


def capture_active_monitor() -> Image.Image:
    """Return a PIL RGB image of whichever monitor the cursor is on."""
    with mss.mss() as sct:
        monitor = _monitor_under_cursor(sct)
        raw = sct.grab(monitor)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def _monitor_under_cursor(sct) -> dict:
    """Return the mss monitor dict for the monitor containing the cursor."""
    try:
        pt = wintypes.POINT()
        windll.user32.GetCursorPos(byref(pt))
        for mon in sct.monitors[1:]:  # index 0 is the "all monitors" virtual screen
            if (
                mon["left"] <= pt.x < mon["left"] + mon["width"]
                and mon["top"] <= pt.y < mon["top"] + mon["height"]
            ):
                return mon
    except Exception:
        pass
    return sct.monitors[1]  # fallback: primary monitor
