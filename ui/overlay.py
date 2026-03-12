"""
Overlay window — main capture/OCR/translate UI.

Two modes:
  Mode A  — SelectionLayer: user draws rect/polygon regions
  Mode B  — TextLayer: shows OCR word bboxes, selection, translation

Both layers are stacked on top of the screenshot canvas.
Only one is visible at a time; a spinner overlay shows during OCR.
"""
import ctypes
import io
from datetime import datetime

from PIL import Image
from PyQt6.QtCore import QRectF, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QKeyEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Language options for the translate bar (keep in sync with ui/settings_window.py)
_TRANS_LANGS: list[tuple[str, str]] = [
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
_TRANS_LANGS_NO_AUTO = [(n, c) for n, c in _TRANS_LANGS if c != "auto"]

import core.history as history_store
from models.ocr_result import OcrWord
from ocr.engine import OcrEngine
from ui.history_popup import HistoryPopup
from ui.selection_layer import SelectionLayer
from ui.text_layer import TextLayer
from ui.themes import ACCENT


def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qimg = QImage()
    qimg.loadFromData(buf.getvalue())
    return QPixmap.fromImage(qimg)


# ------------------------------------------------------------------
# OCR worker — runs in a QThread so the UI stays responsive
# ------------------------------------------------------------------

class _OcrWorker(QThread):
    finished = pyqtSignal(list)  # list[OcrWord]
    error = pyqtSignal(str)

    def __init__(self, engine: OcrEngine, crops: list[tuple[int, Image.Image, int, int]], language: str, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._crops = crops  # list of (region_id, pil_image, crop_x, crop_y)
        self._language = language

    def run(self) -> None:
        try:
            all_words: list[OcrWord] = []
            for region_id, crop_img, crop_x, crop_y in self._crops:
                words = self._engine.recognize(crop_img, self._language)
                for w in words:
                    bx, by, bw, bh = w.bbox
                    all_words.append(OcrWord(
                        text=w.text,
                        bbox=(bx + crop_x, by + crop_y, bw, bh),
                        confidence=w.confidence,
                        region_id=region_id,
                    ))
            self.finished.emit(all_words)
        except Exception as exc:
            self.error.emit(str(exc))


# ------------------------------------------------------------------
# Overlay Window
# ------------------------------------------------------------------

class OverlayWindow(QWidget):
    """Frameless, always-on-top overlay displaying a screenshot."""

    def __init__(
        self,
        screenshot: Image.Image,
        settings: dict,
        stylesheet: str,
        parent=None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._screenshot = screenshot
        self._settings = settings
        self._pixmap = _pil_to_qpixmap(screenshot)
        self._ocr_words: list[OcrWord] = []
        self._worker: _OcrWorker | None = None
        self._theme = settings.get("theme", "dark")

        self.setStyleSheet(stylesheet)
        self._setup_geometry()
        self._setup_ui()
        self._show_mode_a()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_geometry(self) -> None:
        screen = QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        geo = screen.geometry()
        pct = self._settings.get("overlay_size_pct", 80) / 100
        w = int(geo.width() * pct)
        h = int(geo.height() * pct)
        x = geo.x() + (geo.width() - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Canvas area (created first so layers exist before bars wire signals)
        self._canvas = _ScreenshotCanvas(self._pixmap, self)
        self._selection_layer = SelectionLayer(self._theme, self._canvas)
        self._text_layer = TextLayer(self._theme, self._canvas)

        # ── Top bar (stacked: Mode-A bar vs Mode-B bar) ──────────────
        self._bar_stack = QStackedWidget()
        self._bar_a = self._build_bar_a()
        self._bar_b = self._build_bar_b()
        self._bar_stack.addWidget(self._bar_a)
        self._bar_stack.addWidget(self._bar_b)
        root.addWidget(self._bar_stack)

        # Spinner overlay (hidden by default)
        self._spinner_overlay = _SpinnerOverlay(self._theme, self._canvas)
        self._spinner_overlay.hide()

        # Add canvas after bars so visual order is: bar on top, canvas below
        root.addWidget(self._canvas, stretch=1)

    # ── Mode A bar ────────────────────────────────────────────────────

    def _build_bar_a(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._btn_add_rect = QPushButton("Add Rect")
        self._btn_add_shape = QPushButton("Add Shape")
        self._btn_clear = QPushButton("Clear All")

        self._btn_add_rect.clicked.connect(lambda: self._selection_layer.set_tool_rect())
        self._btn_add_shape.clicked.connect(lambda: self._selection_layer.set_tool_polygon())
        self._btn_clear.clicked.connect(self._selection_layer.clear_all)

        for btn in (self._btn_add_rect, self._btn_add_shape, self._btn_clear):
            layout.addWidget(btn)

        layout.addStretch()

        self._btn_analyze = QPushButton("Analyze ▶")
        self._btn_analyze.setObjectName("AccentButton")
        self._btn_analyze.clicked.connect(self._on_analyze)
        layout.addWidget(self._btn_analyze)
        return bar

    # ── Mode B bar ────────────────────────────────────────────────────

    def _build_bar_b(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._btn_back = QPushButton("← Change Selection")
        self._btn_copy_sel = QPushButton("Copy Selected")
        self._btn_copy_all = QPushButton("Copy All")
        self._btn_save = QPushButton("Save")

        self._btn_back.clicked.connect(self._back_to_mode_a)
        self._btn_copy_sel.clicked.connect(self._copy_selected)
        self._btn_copy_all.clicked.connect(self._copy_all)
        self._btn_save.clicked.connect(self._save_to_history)

        self._btn_history = QPushButton("History")
        self._btn_history.clicked.connect(self._open_history)

        for btn in (self._btn_back, self._btn_copy_sel, self._btn_copy_all, self._btn_save, self._btn_history):
            layout.addWidget(btn)

        layout.addStretch()

        self._btn_toggle_text = QPushButton("Toggle Text")
        self._btn_toggle_text.clicked.connect(self._toggle_ocr_text)
        layout.addWidget(self._btn_toggle_text)

        # Language selectors
        layout.addWidget(QLabel("From:"))
        self._src_lang_combo = QComboBox()
        for name, code in _TRANS_LANGS:
            self._src_lang_combo.addItem(name, code)
        saved_src = self._settings.get("translation_source_language", "auto")
        _src_idx = next((i for i, (_, c) in enumerate(_TRANS_LANGS) if c == saved_src), 0)
        self._src_lang_combo.setCurrentIndex(_src_idx)
        self._src_lang_combo.currentIndexChanged.connect(self._reset_translation)
        layout.addWidget(self._src_lang_combo)

        layout.addWidget(QLabel("→"))
        self._tgt_lang_combo = QComboBox()
        for name, code in _TRANS_LANGS_NO_AUTO:
            self._tgt_lang_combo.addItem(name, code)
        saved_tgt = self._settings.get("translation_target_language", "en")
        _tgt_idx = next((i for i, (_, c) in enumerate(_TRANS_LANGS_NO_AUTO) if c == saved_tgt), 0)
        self._tgt_lang_combo.setCurrentIndex(_tgt_idx)
        self._tgt_lang_combo.currentIndexChanged.connect(self._reset_translation)
        layout.addWidget(self._tgt_lang_combo)

        self._btn_translate = QPushButton("Translate")
        self._btn_translate.setObjectName("AccentButton")
        self._btn_translate.clicked.connect(self._on_translate)
        layout.addWidget(self._btn_translate)
        return bar

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _show_mode_a(self) -> None:
        self._bar_stack.setCurrentWidget(self._bar_a)
        self._selection_layer.show()
        self._text_layer.hide()
        self._spinner_overlay.hide()

    def _show_mode_b(self) -> None:
        self._bar_stack.setCurrentWidget(self._bar_b)
        self._selection_layer.hide()
        self._text_layer.show()
        self._spinner_overlay.hide()

    def _back_to_mode_a(self) -> None:
        self._text_layer.clear_selection()
        self._show_mode_a()

    # ------------------------------------------------------------------
    # Analyze (OCR)
    # ------------------------------------------------------------------

    def _on_analyze(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        # Show spinner
        self._spinner_overlay.show()
        self._spinner_overlay.raise_()
        self._btn_analyze.setEnabled(False)

        # Determine which image to OCR
        regions = self._selection_layer.get_regions_as_rects()
        img = self._screenshot
        lang = self._settings.get("ocr_source_language", "en")
        if lang == "auto":
            lang = "en"

        engine = OcrEngine(self._settings)

        if not regions:
            # Full screenshot as a single region (origin 0,0)
            crops = [(0, img, 0, 0)]
        else:
            # Crop each region from the full screenshot, recording crop origin
            crops = []
            for region_id, widget_rect in regions:
                cs = self._canvas.size()
                img_w, img_h = self._screenshot.width, self._screenshot.height
                scale = min(cs.width() / img_w, cs.height() / img_h)
                off_x = (cs.width() - img_w * scale) / 2
                off_y = (cs.height() - img_h * scale) / 2
                # Convert widget rect to image pixel coords
                ix = int((widget_rect.x() - off_x) / scale)
                iy = int((widget_rect.y() - off_y) / scale)
                iw = int(widget_rect.width() / scale)
                ih = int(widget_rect.height() / scale)
                # Clamp to image bounds
                ix = max(0, ix)
                iy = max(0, iy)
                iw = min(iw, img_w - ix)
                ih = min(ih, img_h - iy)
                if iw > 0 and ih > 0:
                    crop = img.crop((ix, iy, ix + iw, iy + ih))
                    crops.append((region_id, crop, ix, iy))
            if not crops:
                crops = [(0, img, 0, 0)]

        self._worker = _OcrWorker(engine, crops, lang, self)
        self._worker.finished.connect(self._on_ocr_done)
        self._worker.error.connect(self._on_ocr_error)
        self._worker.start()

    def _on_ocr_done(self, words: list[OcrWord]) -> None:
        self._ocr_words = words
        canvas_size = self._canvas.size()
        self._text_layer.set_words(
            words,
            self._screenshot.width,
            self._screenshot.height,
            canvas_size.width(),
            canvas_size.height(),
        )
        self._btn_analyze.setEnabled(True)
        self._show_mode_b()

    def _on_ocr_error(self, msg: str) -> None:
        self._btn_analyze.setEnabled(True)
        self._spinner_overlay.set_error(msg)

    # ------------------------------------------------------------------
    # Mode B actions
    # ------------------------------------------------------------------

    def _copy_selected(self) -> None:
        text = self._text_layer.selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def _copy_all(self) -> None:
        text = self._text_layer.all_text()
        if text:
            QApplication.clipboard().setText(text)

    def _save_to_history(self) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "label": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": self._text_layer.all_text(),
        }
        mx = self._settings.get("history_max_length", 10)
        history_store.add_entry(entry, max_length=mx)

    def _open_history(self) -> None:
        stylesheet = self.styleSheet()
        popup = HistoryPopup(stylesheet, self)
        popup.exec()

    def _toggle_ocr_text(self) -> None:
        """Toggle the text labels rendered over word boxes (not the boxes themselves)."""
        visible = self._text_layer.toggle_text_labels()
        self._btn_toggle_text.setText("Show Text" if not visible else "Toggle Text")

    def _reset_translation(self) -> None:
        """Clear cached translations so the next Translate click uses the new language pair."""
        if hasattr(self, "_text_layer"):
            self._text_layer.set_translations({})
        self._btn_translate.setText("Translate")

    def _on_translate(self) -> None:
        # If already has translations, toggle visibility
        if self._text_layer._translations:
            visible = self._text_layer.toggle_translation()
            self._btn_translate.setText("Hide Translation" if visible else "Translate")
            return

        # Run translation in a thread
        import asyncio
        from translation.engine import TranslationEngine

        src = self._src_lang_combo.currentData()
        tgt = self._tgt_lang_combo.currentData()
        all_text = self._text_layer.all_text()
        if not all_text.strip():
            return

        self._btn_translate.setEnabled(False)
        self._btn_translate.setText("Translating…")

        class _TransWorker(QThread):
            done = pyqtSignal(dict)
            error = pyqtSignal(str)

            def __init__(self, settings, texts, src, tgt, parent=None):
                super().__init__(parent)
                self._settings = settings
                self._texts = texts
                self._src = src
                self._tgt = tgt

            def run(self):
                try:
                    eng = TranslationEngine(self._settings)
                    result = asyncio.run(eng.translate(self._texts, self._src, self._tgt))
                    mapping = {i: t for i, t in enumerate(result)}
                    self.done.emit(mapping)
                except Exception as exc:
                    self.error.emit(str(exc))

        # Group text by region
        region_texts: dict[int, list[str]] = {}
        for b in self._text_layer._boxes:
            region_texts.setdefault(b.word.region_id, []).append(b.word.text)
        texts_list = [" ".join(region_texts[k]) for k in sorted(region_texts.keys())]
        region_ids = sorted(region_texts.keys())

        worker = _TransWorker(self._settings, texts_list, src, tgt, self)

        def on_done(mapping):
            translations = {region_ids[i]: t for i, t in mapping.items() if i < len(region_ids)}
            self._text_layer.set_translations(translations)
            self._btn_translate.setEnabled(True)
            self._btn_translate.setText("Hide Translation")

        def on_error(msg):
            self._btn_translate.setEnabled(True)
            self._btn_translate.setText("Translate")
            # Show error inline below the button bar
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Translation failed", msg)

        worker.done.connect(on_done)
        worker.error.connect(on_error)
        self._trans_worker = worker  # prevent GC
        worker.start()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_dwm_rounded_corners()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Keep layers sized to the canvas
        if hasattr(self, "_canvas"):
            cs = self._canvas.size()
            for layer in (self._selection_layer, self._text_layer, self._spinner_overlay):
                layer.setGeometry(0, 0, cs.width(), cs.height())
            # Refresh text layer coordinates if in Mode B
            if self._text_layer.isVisible() and self._ocr_words:
                self._text_layer.refresh_layout(
                    cs.width(), cs.height(),
                    self._screenshot.width, self._screenshot.height,
                )

    def _apply_dwm_rounded_corners(self) -> None:
        """Ask Win11 DWM to round the window corners (no-op on older OS)."""
        try:
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            hwnd = ctypes.c_void_p(int(self.winId()))
            value = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(value), ctypes.sizeof(value),
            )
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            # Confirm if user has drawn regions
            if self._selection_layer.isVisible() and self._selection_layer.region_count() > 0:
                reply = QMessageBox.question(
                    self,
                    "Close overlay?",
                    "You have active selections. Close anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.close()
        elif event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._text_layer.isVisible():
                text = self._text_layer.selected_text()
                if text:
                    QApplication.clipboard().setText(text)
        elif event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._text_layer.isVisible():
                self._text_layer.select_all()
        else:
            super().keyPressEvent(event)


# ------------------------------------------------------------------
# Screenshot canvas (draws the background image)
# ------------------------------------------------------------------

class _ScreenshotCanvas(QWidget):
    """Renders the screenshot scaled to fill the canvas while keeping aspect ratio."""

    def __init__(self, pixmap: QPixmap, parent=None) -> None:
        super().__init__(parent)
        self._pixmap = pixmap

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


# ------------------------------------------------------------------
# Spinner overlay (shown between Mode A → Mode B)
# ------------------------------------------------------------------

class _SpinnerOverlay(QWidget):
    """Semi-transparent overlay with a spinner or error message."""

    def __init__(self, theme: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._error: str | None = None
        self._angle = 0

        self._timer_id: int | None = None

    def show(self) -> None:
        self._error = None
        super().show()
        self._timer_id = self.startTimer(30)

    def hide(self) -> None:
        if self._timer_id is not None:
            self.killTimer(self._timer_id)
            self._timer_id = None
        super().hide()

    def set_error(self, msg: str) -> None:
        self._error = msg
        self.update()

    def timerEvent(self, event) -> None:
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # Dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        if self._error:
            painter.setPen(QColor("#f44336"))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                f"Error: {self._error}",
            )
            return

        # Spinning arc
        accent = QColor(ACCENT.get(self._theme, ACCENT["dark"]))
        pen = QPen(accent, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() // 2, self.height() // 2
        r = 28
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        painter.drawArc(rect, self._angle * 16, 270 * 16)
