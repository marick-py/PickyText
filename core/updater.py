"""Auto-update check via GitHub Releases API. Runs in a daemon thread."""
import threading

import httpx
from packaging.version import Version
from PyQt6.QtCore import QObject, pyqtSignal

from version import __version__

GITHUB_REPO = "marick-py/PickyText"


class UpdateChecker(QObject):
    update_available = pyqtSignal(str, str)  # (latest_version, release_url)
    check_failed = pyqtSignal(str)           # error message

    def start(self) -> None:
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self) -> None:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            with httpx.Client(timeout=5.0) as client:
                r = client.get(url, headers={"Accept": "application/vnd.github+json"})
                r.raise_for_status()
                data = r.json()
            latest = data.get("tag_name", "").lstrip("v")
            release_url = data.get("html_url", "")
            if latest and Version(latest) > Version(__version__):
                self.update_available.emit(latest, release_url)
        except Exception as exc:
            self.check_failed.emit(str(exc))
