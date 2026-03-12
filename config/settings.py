"""Settings loader / saver. Stored at %APPDATA%\\PickyText\\settings.json."""
import json
import os
from pathlib import Path

from config.defaults import DEFAULTS

_APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PickyText"
_SETTINGS_FILE = _APPDATA_DIR / "settings.json"


def load() -> dict:
    """Load settings from disk, merging with defaults for any missing keys."""
    if not _SETTINGS_FILE.exists():
        return dict(DEFAULTS)
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save(settings: dict) -> None:
    """Persist settings to disk."""
    _APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def appdata_dir() -> Path:
    return _APPDATA_DIR
