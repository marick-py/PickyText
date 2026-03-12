"""
PickyText — entry point.

Launch order:
  1. Create QApplication (no visible window)
  2. Load settings
  3. Spin up tray icon
  4. Register global hotkey
  5. Enter Qt event loop (app stays alive in tray)
"""
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

import config.settings as settings_io
import ui.themes as themes
from core.hotkey import HotkeyManager
from core.screenshot import capture_active_monitor
from core.updater import UpdateChecker
from ui.history_popup import HistoryPopup
from ui.overlay import OverlayWindow
from ui.settings_window import SettingsWindow
from ui.tray import TrayIcon
from version import __version__


def main() -> None:
    # High-DPI: let Qt decide the best rounding strategy
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PickyText")
    app.setApplicationVersion(__version__)
    # Keep the process alive even when the overlay window closes
    app.setQuitOnLastWindowClosed(False)

    cfg = settings_io.load()

    tray = TrayIcon(cfg)
    hotkey = HotkeyManager(cfg.get("hotkey", "win+shift+d"))

    _overlay: OverlayWindow | None = None  # strong reference to prevent GC

    # ------------------------------------------------------------------
    # Capture handler — called from tray menu or hotkey
    # ------------------------------------------------------------------
    def on_capture() -> None:
        nonlocal _overlay
        if _overlay is not None and _overlay.isVisible():
            _overlay.activateWindow()
            return

        try:
            screenshot = capture_active_monitor()
        except Exception as exc:
            tray.show_message("PickyText", f"Screenshot failed: {exc}")
            return

        stylesheet = themes.get(cfg.get("theme", "dark"))
        _overlay = OverlayWindow(screenshot, cfg, stylesheet)
        _overlay.show()
        _overlay.activateWindow()

    # ------------------------------------------------------------------
    # Theme toggle — rebuild stylesheet on open overlay if any
    # ------------------------------------------------------------------
    def on_theme(new_theme: str) -> None:
        cfg["theme"] = new_theme
        settings_io.save(cfg)
        if _overlay is not None and _overlay.isVisible():
            _overlay.setStyleSheet(themes.get(new_theme))

    # ------------------------------------------------------------------
    # Settings window
    # ------------------------------------------------------------------
    _settings_win: SettingsWindow | None = None

    def on_settings() -> None:
        nonlocal _settings_win
        if _settings_win is not None and _settings_win.isVisible():
            _settings_win.raise_()
            _settings_win.activateWindow()
            return
        _settings_win = SettingsWindow(cfg, themes.get(cfg.get("theme", "dark")))
        _settings_win.settings_saved.connect(on_settings_saved)
        _settings_win.show()

    def on_settings_saved(new_cfg: dict) -> None:
        cfg.update(new_cfg)
        tray.update_settings(cfg)
        hotkey.update_hotkey(cfg["hotkey"])
        # Apply theme change immediately to the settings window and any open overlay
        new_stylesheet = themes.get(cfg.get("theme", "dark"))
        if _settings_win is not None:
            _settings_win.setStyleSheet(new_stylesheet)
        if _overlay is not None and _overlay.isVisible():
            _overlay.setStyleSheet(new_stylesheet)

    # ------------------------------------------------------------------
    # History popup (from tray)
    # ------------------------------------------------------------------
    def on_history() -> None:
        popup = HistoryPopup(themes.get(cfg.get("theme", "dark")))
        popup.exec()

    # ------------------------------------------------------------------
    # Manual update check
    # ------------------------------------------------------------------
    _update_checkers: list = []  # prevent GC while thread runs

    def on_check_updates() -> None:
        checker = UpdateChecker()
        _update_checkers.append(checker)

        def _cleanup():
            if checker in _update_checkers:
                _update_checkers.remove(checker)

        checker.update_available.connect(
            lambda ver, url: (
                tray.show_message(
                    "PickyText — Update available",
                    f"Version {ver} is available on GitHub.",
                ),
                _cleanup(),
            )
        )
        checker.check_failed.connect(
            lambda msg: (
                tray.show_message("PickyText", f"Update check failed: {msg}"),
                _cleanup(),
            )
        )
        tray.show_message("PickyText", "Checking for updates…")
        checker.start()

    # ------------------------------------------------------------------
    # Quit
    # ------------------------------------------------------------------
    def on_quit() -> None:
        hotkey.stop()
        settings_io.save(cfg)
        app.quit()

    # ------------------------------------------------------------------
    # Wire signals
    # ------------------------------------------------------------------
    hotkey.triggered.connect(on_capture)
    hotkey.registration_failed.connect(
        lambda msg: tray.show_message("PickyText — Hotkey Error", msg)
    )
    tray.capture_requested.connect(on_capture)
    tray.theme_toggled.connect(on_theme)
    tray.settings_requested.connect(on_settings)
    tray.history_requested.connect(on_history)
    tray.check_updates_requested.connect(on_check_updates)
    tray.quit_requested.connect(on_quit)

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------
    hotkey.start()
    tray.show_message(
        "PickyText",
        f"Running — press {cfg['hotkey']} to capture",
    )

    if cfg.get("check_updates_on_startup", True):
        updater = UpdateChecker()
        updater.update_available.connect(
            lambda ver, url: tray.show_message(
                "PickyText — Update available",
                f"Version {ver} is available on GitHub.",
            )
        )
        updater.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
