"""Rotating JSON history store at %APPDATA%\\PickyText\\history.json."""
import json
import os
from pathlib import Path
from typing import Any

_APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PickyText"
_HISTORY_FILE = _APPDATA_DIR / "history.json"


def load() -> list[dict]:
    if not _HISTORY_FILE.exists():
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save(history: list[dict]) -> None:
    _APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_entry(entry: dict[str, Any], max_length: int = 10) -> None:
    """Prepend a new entry and trim to `max_length`."""
    history = load()
    history.insert(0, entry)
    save(history[:max_length])


def clear() -> None:
    if _HISTORY_FILE.exists():
        _HISTORY_FILE.unlink()
