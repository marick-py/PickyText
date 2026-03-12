"""History browser popup."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import core.history as history_store


class HistoryPopup(QDialog):
    def __init__(self, stylesheet: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PickyText — History")
        self.setMinimumSize(680, 420)
        self.setStyleSheet(stylesheet)
        self._entries: list[dict] = []
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: entry list ──────────────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Captures"))
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        ll.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        btn_delete = QPushButton("Delete Entry")
        btn_delete.clicked.connect(self._delete_selected)
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self._clear)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_clear)
        ll.addLayout(btn_row)
        splitter.addWidget(left)

        # ── Right: OCR text preview ───────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("OCR text"))
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        rl.addWidget(self._text, stretch=1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        # ── Bottom bar ────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bar.addWidget(btn_close)
        root.addLayout(bar)

    def _load(self) -> None:
        self._entries = history_store.load()
        self._list.clear()
        for entry in self._entries:
            ts = entry.get("timestamp", "")
            label = entry.get("label", ts or "Untitled")
            self._list.addItem(QListWidgetItem(label))
        self._text.clear()

    def _on_select(self, row: int) -> None:
        if 0 <= row < len(self._entries):
            self._text.setPlainText(self._entries[row].get("text", ""))
        else:
            self._text.clear()

    def _delete_selected(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        history = history_store.load()
        if row < len(history):
            del history[row]
            history_store.save(history)
        self._load()

    def _clear(self) -> None:
        reply = QMessageBox.question(
            self, "Clear History",
            "Delete all history entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            history_store.clear()
            self._load()
