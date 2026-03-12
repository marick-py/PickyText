"""
Optional package/feature manager — downloads Argos Translate language model pairs
at runtime without requiring a reinstall.

Argos models live in the user's AppData, not the install directory, so this works
whether the app was installed or run from source.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal


# Language pairs available for download (from_code, to_code, display label)
ARGOS_PAIRS: list[tuple[str, str, str]] = [
    ("en", "ar", "English → Arabic"),
    ("en", "zh", "English → Chinese"),
    ("en", "nl", "English → Dutch"),
    ("en", "fr", "English → French"),
    ("en", "de", "English → German"),
    ("en", "hi", "English → Hindi"),
    ("en", "id", "English → Indonesian"),
    ("en", "it", "English → Italian"),
    ("en", "ja", "English → Japanese"),
    ("en", "ko", "English → Korean"),
    ("en", "pl", "English → Polish"),
    ("en", "pt", "English → Portuguese"),
    ("en", "ru", "English → Russian"),
    ("en", "es", "English → Spanish"),
    ("en", "sv", "English → Swedish"),
    ("en", "tr", "English → Turkish"),
    ("en", "uk", "English → Ukrainian"),
    ("en", "vi", "English → Vietnamese"),
    ("ar", "en", "Arabic → English"),
    ("zh", "en", "Chinese → English"),
    ("fr", "en", "French → English"),
    ("de", "en", "German → English"),
    ("ja", "en", "Japanese → English"),
    ("ko", "en", "Korean → English"),
    ("ru", "en", "Russian → English"),
    ("es", "en", "Spanish → English"),
]


def argos_available() -> bool:
    """Return True if argostranslate is importable."""
    try:
        import argostranslate  # noqa: F401
        return True
    except ImportError:
        return False


def argos_installed_pairs() -> list[tuple[str, str]]:
    """Return list of (from_code, to_code) for installed Argos models."""
    if not argos_available():
        return []
    try:
        from argostranslate.translate import get_installed_languages
        langs = get_installed_languages()
        pairs = []
        for lang in langs:
            for tl in lang.translations_to:
                pairs.append((lang.code, tl.to_lang.code))
        return pairs
    except Exception:
        return []


class ArgosModelDownloader(QThread):
    """Download and install one Argos language-pair model in a background thread."""

    progress = pyqtSignal(str)   # status text updates
    done = pyqtSignal(str)       # emits "from_code→to_code" on success
    error = pyqtSignal(str)      # emits error message

    def __init__(self, from_code: str, to_code: str, parent=None) -> None:
        super().__init__(parent)
        self._from = from_code
        self._to = to_code

    def run(self) -> None:
        try:
            from argostranslate import package
        except ImportError:
            self.error.emit(
                "argostranslate is not installed.\n"
                "Install it with:  pip install argostranslate"
            )
            return

        try:
            self.progress.emit("Updating package index…")
            package.update_package_index()

            available = package.get_available_packages()
            pkg = next(
                (
                    p for p in available
                    if p.from_code == self._from and p.to_code == self._to
                ),
                None,
            )
            if pkg is None:
                self.error.emit(
                    f"No Argos model found for {self._from} → {self._to}.\n"
                    "It may not be available yet upstream."
                )
                return

            self.progress.emit(f"Downloading {pkg.from_name} → {pkg.to_name} ({pkg.package_version})…")
            path = pkg.download()
            self.progress.emit("Installing…")
            package.install_from_path(path)
            self.done.emit(f"{self._from}→{self._to}")

        except Exception as exc:
            self.error.emit(str(exc))
