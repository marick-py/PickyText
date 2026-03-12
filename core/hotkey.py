"""
Global hotkey listener.

The `keyboard` library runs callbacks in its own daemon OS thread.
PyQt6 signal emission is thread-safe: when a signal emitted from a non-Qt
thread is connected to a slot that lives on the main thread, PyQt6
automatically posts the invocation to the main thread's event queue
(AutoConnection behaves like QueuedConnection across threads).
"""
import keyword as _kw  # noqa: F401 — stdlib, just to avoid name clash

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    """Emits `triggered` on the Qt main thread when the hotkey fires."""

    triggered = pyqtSignal()
    registration_failed = pyqtSignal(str)  # emits error message

    def __init__(self, hotkey_str: str, parent=None) -> None:
        super().__init__(parent)
        self._hotkey_str = hotkey_str
        self._registered = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Register the hotkey with the OS. Safe to call multiple times."""
        if self._registered:
            return
        try:
            keyboard.add_hotkey(self._hotkey_str, self._fire, suppress=True)
            self._registered = True
        except Exception as exc:
            self.registration_failed.emit(
                f"Could not register hotkey '{self._hotkey_str}': {exc}\n"
                "Try running as administrator or change the hotkey in Settings."
            )

    def stop(self) -> None:
        """Unregister the hotkey."""
        if not self._registered:
            return
        try:
            keyboard.remove_hotkey(self._hotkey_str)
        except (KeyError, ValueError):
            pass
        self._registered = False

    def update_hotkey(self, new_str: str) -> None:
        """Replace the registered hotkey without restarting the listener."""
        self.stop()
        self._hotkey_str = new_str
        self.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fire(self) -> None:
        # Called from keyboard library's daemon thread — signal emission
        # is thread-safe; Qt will deliver it to the main thread.
        self.triggered.emit()
