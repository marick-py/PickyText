"""Light / Dark QSS stylesheets applied app-wide."""

DARK = """
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QCheckBox,
QGroupBox, QRadioButton, QDialogButtonBox, QMenu, QMenuBar {
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QWidget#TopBar {
    background-color: #16213e;
    border-bottom: 1px solid #0f3460;
}
QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #533483;
}
QPushButton:pressed {
    background-color: #e94560;
}
QPushButton:disabled {
    background-color: #0a1e3a;
    color: #606080;
}
QPushButton#AccentButton {
    background-color: #e94560;
}
QPushButton#AccentButton:hover {
    background-color: #ff6b81;
}
QToolTip {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #533483;
    padding: 4px;
}
"""

LIGHT = """
QWidget {
    background-color: #f5f5f5;
    color: #1a1a1a;
}
QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QCheckBox,
QGroupBox, QRadioButton, QMenu, QMenuBar {
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}
QDialog {
    background-color: #f0f0f0;
}
QWidget#TopBar {
    background-color: #e8ecf0;
    border-bottom: 1px solid #c0c8d0;
}
QGroupBox {
    border: 1px solid #c0c8d0;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 6px;
    background-color: #fafafa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    color: #333333;
    font-weight: bold;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #b0b8c0;
    border-radius: 4px;
    padding: 4px 8px;
    color: #1a1a1a;
    selection-background-color: #0066cc;
    selection-color: #ffffff;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #0066cc;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #b0b8c0;
    selection-background-color: #0066cc;
    selection-color: #ffffff;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #999;
    border-radius: 3px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #0066cc;
    border-color: #0066cc;
}
QScrollBar:vertical {
    background: #e8e8e8;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #b0b8c0;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #0066cc;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollArea { border: none; background: transparent; }
QSplitter::handle { background: #c0c8d0; }
QListWidget {
    background-color: #ffffff;
    border: 1px solid #c0c8d0;
    border-radius: 4px;
}
QListWidget::item:hover { background: #e4eef8; }
QListWidget::item:selected { background: #0066cc; color: #ffffff; }
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #c0c8d0;
    border-radius: 4px;
    color: #1a1a1a;
}
QPushButton {
    background-color: #e0e4e8;
    color: #1a1a1a;
    border: 1px solid #c0c8d0;
    border-radius: 4px;
    padding: 6px 14px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #d0d8e4;
    border-color: #0066cc;
}
QPushButton:pressed {
    background-color: #0066cc;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #ebebeb;
    color: #aaaaaa;
    border-color: #d8d8d8;
}
QPushButton#AccentButton {
    background-color: #0066cc;
    color: #ffffff;
    border: none;
}
QPushButton#AccentButton:hover {
    background-color: #0052a3;
}
QToolTip {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #c0c8d0;
    padding: 4px;
}
"""

# Accent colours for use in QPainter code (must stay in sync with QSS above)
ACCENT = {
    "dark":  "#e94560",
    "light": "#0066cc",
}

SELECTION_FILL_ALPHA = 77   # ~30% of 255


def get(theme_name: str) -> str:
    return DARK if theme_name == "dark" else LIGHT
