"""System tray icon and context menu."""
import io

from PIL import Image, ImageDraw
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from version import __version__


def _build_icon() -> QIcon:
    """Generate a simple 'PT' tray icon programmatically."""
    from pathlib import Path
    ico_path = Path(__file__).parent.parent / "assets" / "icon.ico"
    if ico_path.exists():
        return QIcon(str(ico_path))

    # Fallback: red circle drawn with Qt (no PIL font needed)
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(233, 69, 96))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(2, 2, 60, 60)
    painter.setPen(QColor(255, 255, 255))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(22)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "PT")  # AlignHCenter | AlignVCenter
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    quit_requested = pyqtSignal()
    capture_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    theme_toggled = pyqtSignal(str)  # emits new theme name: "dark" | "light"
    history_requested = pyqtSignal()
    check_updates_requested = pyqtSignal()

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._tray = QSystemTrayIcon(_build_icon())
        self._build_menu()
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_message(self, title: str, body: str) -> None:
        self._tray.showMessage(
            title, body, QSystemTrayIcon.MessageIcon.Information, 3000
        )

    def update_settings(self, settings: dict) -> None:
        self._settings = settings
        self._build_menu()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        version_action = menu.addAction(f"PickyText v{__version__}")
        version_action.setEnabled(False)

        menu.addSeparator()

        capture_action = menu.addAction("Capture now")
        capture_action.triggered.connect(self.capture_requested)

        menu.addSeparator()

        theme = self._settings.get("theme", "dark")
        theme_label = "Switch to Light theme" if theme == "dark" else "Switch to Dark theme"
        self._theme_action = menu.addAction(theme_label)
        self._theme_action.triggered.connect(self._toggle_theme)

        menu.addSeparator()

        settings_action = menu.addAction("Settings…")
        settings_action.triggered.connect(self.settings_requested)

        history_action = menu.addAction("History…")
        history_action.triggered.connect(self.history_requested)

        menu.addSeparator()

        updates_action = menu.addAction("Check for Updates")
        updates_action.triggered.connect(self.check_updates_requested)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_requested)

        self._tray.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.capture_requested.emit()

    def _toggle_theme(self) -> None:
        current = self._settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self._settings["theme"] = new_theme
        label = "Switch to Light theme" if new_theme == "dark" else "Switch to Dark theme"
        self._theme_action.setText(label)
        self.theme_toggled.emit(new_theme)
