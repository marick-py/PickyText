"""Full settings dialog."""
import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import config.settings as settings_io
import core.history as history_store
from version import __version__

# (display name, BCP-47 code)
_LANGUAGES: list[tuple[str, str]] = [
    ("Auto-detect", "auto"),
    ("Arabic", "ar"),
    ("Chinese (Simplified)", "zh-Hans"),
    ("Chinese (Traditional)", "zh-Hant"),
    ("Dutch", "nl"),
    ("English", "en"),
    ("French", "fr"),
    ("German", "de"),
    ("Hindi", "hi"),
    ("Indonesian", "id"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Polish", "pl"),
    ("Portuguese", "pt"),
    ("Russian", "ru"),
    ("Spanish", "es"),
    ("Swedish", "sv"),
    ("Thai", "th"),
    ("Turkish", "tr"),
    ("Ukrainian", "uk"),
    ("Vietnamese", "vi"),
]
_LANGS_NO_AUTO = [(n, c) for n, c in _LANGUAGES if c != "auto"]


def _lang_combo(langs: list[tuple[str, str]], current: str) -> QComboBox:
    combo = QComboBox()
    for name, code in langs:
        combo.addItem(name, code)
    idx = next((i for i, (_, c) in enumerate(langs) if c == current), 0)
    combo.setCurrentIndex(idx)
    return combo


class SettingsWindow(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings: dict, stylesheet: str, parent=None) -> None:
        super().__init__(parent)
        self._cfg = dict(settings)
        self.setWindowTitle("PickyText — Settings")
        self.setMinimumWidth(520)
        self.setMinimumHeight(900)
        self.resize(540, 930)
        self.setStyleSheet(stylesheet)
        self._setup_ui()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.setSpacing(0)

        # Scrollable area holds all groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 8)
        scroll.setWidget(inner)
        outer.addWidget(scroll, stretch=1)

        # Version label at top
        ver_lbl = QLabel(f"PickyText v{__version__}")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(ver_lbl)

        layout.addWidget(self._hotkey_group())
        layout.addWidget(self._ocr_group())
        layout.addWidget(self._translation_group())
        layout.addWidget(self._appearance_group())
        layout.addWidget(self._history_group())
        layout.addWidget(self._optional_features_group())
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(20, 0, 20, 0)
        btn_row.addStretch()
        btn_save = QPushButton("Save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_save)
        btn_row.addSpacing(12)
        btn_row.addWidget(btn_close)
        outer.addLayout(btn_row)

    def _hotkey_group(self) -> QGroupBox:
        g = QGroupBox("Hotkey")
        f = QFormLayout(g)
        self._hotkey = QLineEdit(self._cfg.get("hotkey", "ctrl+shift+d"))
        self._hotkey.setPlaceholderText("e.g. ctrl+shift+d")
        f.addRow("Trigger hotkey:", self._hotkey)
        note = QLabel("Tip: avoid Win+* combinations — they may need administrator rights.")
        note.setWordWrap(True)
        note.setStyleSheet("QLabel { font-size: 9pt; }")
        f.addRow("", note)
        return g

    def _ocr_group(self) -> QGroupBox:
        g = QGroupBox("OCR")
        f = QFormLayout(g)

        self._ocr_engine = QComboBox()
        self._ocr_engine.addItems(["Windows OCR", "Tesseract"])
        self._ocr_engine.setCurrentIndex(
            0 if self._cfg.get("ocr_engine", "windows") == "windows" else 1
        )
        f.addRow("Engine:", self._ocr_engine)

        self._ocr_lang = _lang_combo(_LANGUAGES, self._cfg.get("ocr_source_language", "auto"))
        f.addRow("Source language:", self._ocr_lang)

        tess_row = QHBoxLayout()
        self._tess_path = QLineEdit(self._cfg.get("tesseract_path", ""))
        self._tess_path.setPlaceholderText("Auto-detect (leave empty)")
        btn_browse = QPushButton("Browse…")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._browse_tesseract)
        tess_row.addWidget(self._tess_path)
        tess_row.addWidget(btn_browse)
        f.addRow("Tesseract path:", tess_row)
        tess_note = QLabel(
            "Tesseract must be installed separately (not bundled in the .exe). "
            "Download from <a href='https://github.com/UB-Mannheim/tesseract/wiki'>"
            "UB-Mannheim</a>, or re-run the PickyText installer and tick "
            "<i>Tesseract OCR</i>.  Windows OCR works without it."
        )
        tess_note.setWordWrap(True)
        tess_note.setOpenExternalLinks(True)
        tess_note.setStyleSheet("QLabel { font-size: 9pt; }")
        f.addRow("", tess_note)
        return g

    def _translation_group(self) -> QGroupBox:
        g = QGroupBox("Translation")
        f = QFormLayout(g)

        self._endpoint = QLineEdit(
            self._cfg.get("translation_endpoint", "http://localhost:5000")
        )
        f.addRow("Endpoint URL:", self._endpoint)

        api_row = QHBoxLayout()
        self._api_key = QLineEdit(self._cfg.get("translation_api_key", ""))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        btn_eye = QPushButton("👁")
        btn_eye.setFixedWidth(34)
        btn_eye.setCheckable(True)
        btn_eye.toggled.connect(
            lambda on: self._api_key.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        api_row.addWidget(self._api_key)
        api_row.addWidget(btn_eye)
        f.addRow("API key:", api_row)

        self._trans_src = _lang_combo(
            _LANGUAGES, self._cfg.get("translation_source_language", "auto")
        )
        f.addRow("Source language:", self._trans_src)

        self._trans_tgt = _lang_combo(
            _LANGS_NO_AUTO, self._cfg.get("translation_target_language", "en")
        )
        f.addRow("Target language:", self._trans_tgt)

        ping_row = QHBoxLayout()
        btn_ping = QPushButton("Test Connection")
        btn_ping.clicked.connect(self._ping)
        self._ping_lbl = QLabel("")
        ping_row.addWidget(btn_ping)
        ping_row.addWidget(self._ping_lbl)
        ping_row.addStretch()
        f.addRow("", ping_row)
        return g

    def _appearance_group(self) -> QGroupBox:
        g = QGroupBox("Appearance")
        f = QFormLayout(g)

        self._theme = QComboBox()
        self._theme.addItems(["Dark", "Light"])
        self._theme.setCurrentIndex(
            0 if self._cfg.get("theme", "dark") == "dark" else 1
        )
        f.addRow("Theme:", self._theme)

        self._overlay_pct = QSpinBox()
        self._overlay_pct.setRange(40, 100)
        self._overlay_pct.setValue(self._cfg.get("overlay_size_pct", 80))
        self._overlay_pct.setSuffix(" %")
        f.addRow("Overlay size:", self._overlay_pct)

        self._startup = QCheckBox("Start PickyText with Windows")
        self._startup.setChecked(self._cfg.get("start_with_windows", False))
        f.addRow("", self._startup)

        self._check_updates = QCheckBox("Check for updates on startup")
        self._check_updates.setChecked(self._cfg.get("check_updates_on_startup", True))
        f.addRow("", self._check_updates)

        return g

    def _history_group(self) -> QGroupBox:
        g = QGroupBox("History")
        f = QFormLayout(g)

        self._hist_enabled = QCheckBox("Enable history")
        self._hist_enabled.setChecked(self._cfg.get("history_enabled", True))
        f.addRow("", self._hist_enabled)

        self._hist_max = QSpinBox()
        self._hist_max.setRange(1, 100)
        self._hist_max.setValue(self._cfg.get("history_max_length", 10))
        f.addRow("Max entries:", self._hist_max)

        self._hist_images = QCheckBox("Save screenshot thumbnails")
        self._hist_images.setChecked(self._cfg.get("history_save_images", True))
        f.addRow("", self._hist_images)

        btn_clear_hist = QPushButton("Clear History Now…")
        btn_clear_hist.clicked.connect(self._clear_history)
        f.addRow("", btn_clear_hist)

        return g

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Tesseract executable", "", "Executables (*.exe)"
        )
        if path:
            self._tess_path.setText(path)

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Clear History",
            "Delete all history entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            history_store.clear()

    # ------------------------------------------------------------------
    # Optional Features group
    # ------------------------------------------------------------------

    def _optional_features_group(self) -> QGroupBox:
        from core.package_manager import (
            ARGOS_PAIRS,
            ArgosModelDownloader,
            argos_available,
            argos_installed_pairs,
        )

        g = QGroupBox("Optional Features")
        v = QVBoxLayout(g)

        # ── Argos Translate ────────────────────────────────────────────
        argos_lbl = QLabel()
        if argos_available():
            installed = argos_installed_pairs()
            installed_str = ", ".join(f"{f}→{t}" for f, t in installed) or "none"
            argos_lbl.setText(f"<b>Argos Translate</b> — installed · models: {installed_str}")
        else:
            argos_lbl.setText(
                "<b>Argos Translate</b> \u2014 <i>not installed</i>.<br>"
                "This is an optional component. If you installed PickyText via the "
                "<b>.exe installer</b>, re-run it and tick <i>Argos Translate</i> "
                "in the components list.<br>"
                "If you are running from source: "
                "<code>pip install argostranslate</code>"
            )
        argos_lbl.setWordWrap(True)
        v.addWidget(argos_lbl)

        if argos_available():
            dl_row = QHBoxLayout()
            self._argos_pair_combo = QComboBox()
            installed_set = set(argos_installed_pairs())
            for from_code, to_code, label in ARGOS_PAIRS:
                display = label if (from_code, to_code) not in installed_set else f"{label} ✓"
                self._argos_pair_combo.addItem(display, (from_code, to_code))
            dl_row.addWidget(self._argos_pair_combo, stretch=1)

            self._argos_dl_btn = QPushButton("Download Model")
            self._argos_dl_btn.clicked.connect(
                lambda: self._download_argos_model(argos_lbl, ARGOS_PAIRS, ArgosModelDownloader)
            )
            dl_row.addWidget(self._argos_dl_btn)
            v.addLayout(dl_row)

            self._argos_status_lbl = QLabel("")
            self._argos_status_lbl.setWordWrap(True)
            v.addWidget(self._argos_status_lbl)

        return g

    def _download_argos_model(
        self,
        status_lbl: QLabel,
        pairs: list,
        DownloaderClass,
    ) -> None:
        from_code, to_code = self._argos_pair_combo.currentData()
        self._argos_dl_btn.setEnabled(False)
        self._argos_status_lbl.setText("Starting…")

        worker = DownloaderClass(from_code, to_code, self)
        worker.progress.connect(self._argos_status_lbl.setText)
        worker.done.connect(self._on_argos_done)
        worker.error.connect(self._on_argos_error)
        self._argos_worker = worker  # prevent GC
        worker.start()

    def _on_argos_done(self, pair: str) -> None:
        self._argos_dl_btn.setEnabled(True)
        self._argos_status_lbl.setStyleSheet("color: #4caf50;")
        self._argos_status_lbl.setText(f"✓  {pair} installed successfully.")
        # Refresh the combo to show the checkmark
        from core.package_manager import argos_installed_pairs
        installed_set = set(argos_installed_pairs())
        for i in range(self._argos_pair_combo.count()):
            data = self._argos_pair_combo.itemData(i)
            text = self._argos_pair_combo.itemText(i).replace(" ✓", "")
            if data in installed_set or tuple(data) in installed_set:
                self._argos_pair_combo.setItemText(i, f"{text} ✓")

    def _on_argos_error(self, msg: str) -> None:
        self._argos_dl_btn.setEnabled(True)
        self._argos_status_lbl.setStyleSheet("color: #f44336;")
        self._argos_status_lbl.setText(f"✗  {msg}")

    def _ping(self) -> None:
        import asyncio
        from translation.libretranslate import LibreTranslateClient
        self._ping_lbl.setText("Pinging…")
        self._ping_lbl.setStyleSheet("")
        try:
            client = LibreTranslateClient(
                self._endpoint.text().strip(),
                self._api_key.text().strip(),
            )
            ms = asyncio.run(client.ping())
            self._ping_lbl.setText(f"✓  {ms:.0f} ms")
            self._ping_lbl.setStyleSheet("color: #4caf50;")
        except Exception as exc:
            self._ping_lbl.setText(f"✗  {exc}")
            self._ping_lbl.setStyleSheet("color: #f44336;")

    def _save(self) -> None:
        self._cfg["hotkey"] = self._hotkey.text().strip()
        self._cfg["ocr_engine"] = (
            "windows" if self._ocr_engine.currentIndex() == 0 else "tesseract"
        )
        self._cfg["ocr_source_language"] = self._ocr_lang.currentData()
        self._cfg["tesseract_path"] = self._tess_path.text().strip()
        self._cfg["translation_endpoint"] = self._endpoint.text().strip()
        self._cfg["translation_api_key"] = self._api_key.text()
        self._cfg["translation_source_language"] = self._trans_src.currentData()
        self._cfg["translation_target_language"] = self._trans_tgt.currentData()
        self._cfg["theme"] = "dark" if self._theme.currentIndex() == 0 else "light"
        self._cfg["overlay_size_pct"] = self._overlay_pct.value()
        self._cfg["start_with_windows"] = self._startup.isChecked()
        self._cfg["check_updates_on_startup"] = self._check_updates.isChecked()
        self._cfg["history_enabled"] = self._hist_enabled.isChecked()
        self._cfg["history_max_length"] = self._hist_max.value()
        self._cfg["history_save_images"] = self._hist_images.isChecked()

        settings_io.save(self._cfg)
        _apply_startup_registry(self._cfg["start_with_windows"])
        self.settings_saved.emit(self._cfg)


# ------------------------------------------------------------------
# Windows startup registry
# ------------------------------------------------------------------

def _apply_startup_registry(enable: bool) -> None:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enable:
                if getattr(sys, "frozen", False):
                    cmd = f'"{sys.executable}"'
                else:
                    cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                winreg.SetValueEx(key, "PickyText", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, "PickyText")
                except FileNotFoundError:
                    pass
    except Exception:
        pass
