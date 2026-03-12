"""
Mode B — Text Layer.

Renders OCR word bounding boxes over the screenshot. Users can click
individual words to select/deselect them, or click-drag to range-select
(like a PDF reader). Hover highlights are shown.

Coordinate mapping:
  The overlay canvas scales the screenshot (image space) into the widget.
  This layer receives a transform from the overlay so it can map between
  image-pixel coords (where OCR bboxes live) and widget coords (where the
  user clicks).
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from models.ocr_result import OcrWord
from ui.themes import ACCENT, SELECTION_FILL_ALPHA


class _WordBox:
    """Visual representation of a single OCR word on the canvas."""

    __slots__ = ("word", "widget_rect", "selected", "hovered")

    def __init__(self, word: OcrWord, widget_rect: QRectF) -> None:
        self.word = word
        self.widget_rect = widget_rect
        self.selected = False
        self.hovered = False


class TextLayer(QWidget):
    """Transparent overlay for Mode B word selection."""

    selection_changed = pyqtSignal()  # emitted when selected words change

    def __init__(self, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._theme = theme
        self._boxes: list[_WordBox] = []
        self._translations: dict[int, str] = {}  # region_id → translated text
        self._show_translation = False
        self._show_text_labels = True  # togglable OCR text over word boxes

        # Drag-select state
        self._dragging = False
        self._drag_origin = QPointF()
        self._drag_current = QPointF()

        # Image→widget transform (set by overlay)
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._scale = 1.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_words(
        self,
        words: list[OcrWord],
        img_w: int,
        img_h: int,
        widget_w: int,
        widget_h: int,
    ) -> None:
        """Load OCR results and compute widget rects from the image→widget transform."""
        self._compute_transform(img_w, img_h, widget_w, widget_h)
        self._boxes = [
            _WordBox(w, self._img_rect_to_widget(w.bbox)) for w in words
        ]
        self._translations.clear()
        self._show_translation = False
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def set_translations(self, translations: dict[int, str]) -> None:
        """Set translated text per region_id."""
        self._translations = translations
        self._show_translation = True
        self.update()

    def toggle_translation(self) -> bool:
        """Toggle visibility. Returns new state."""
        self._show_translation = not self._show_translation
        self.update()
        return self._show_translation

    def selected_text(self) -> str:
        """Return selected words joined by spaces, preserving line breaks between regions."""
        parts: dict[int, list[str]] = {}
        for b in self._boxes:
            if b.selected:
                parts.setdefault(b.word.region_id, []).append(b.word.text)
        return "\n---\n".join(" ".join(v) for v in parts.values())

    def all_text(self) -> str:
        """Return all OCR text grouped by region."""
        parts: dict[int, list[str]] = {}
        for b in self._boxes:
            parts.setdefault(b.word.region_id, []).append(b.word.text)
        return "\n---\n".join(" ".join(v) for v in parts.values())

    def toggle_text_labels(self) -> bool:
        """Toggle the OCR text labels drawn over word boxes. Returns new state."""
        self._show_text_labels = not self._show_text_labels
        self.update()
        return self._show_text_labels

    def select_all(self) -> None:
        """Select all word boxes."""
        for b in self._boxes:
            b.selected = True
        self.update()
        self.selection_changed.emit()

    def clear_selection(self) -> None:
        for b in self._boxes:
            b.selected = False
        self.update()
        self.selection_changed.emit()

    def refresh_layout(self, widget_w: int, widget_h: int, img_w: int, img_h: int) -> None:
        """Recompute widget rects after a resize."""
        self._compute_transform(img_w, img_h, widget_w, widget_h)
        for b in self._boxes:
            b.widget_rect = self._img_rect_to_widget(b.word.bbox)
        self.update()

    # ------------------------------------------------------------------
    # Coordinate mapping
    # ------------------------------------------------------------------

    def _compute_transform(self, img_w: int, img_h: int, wid_w: int, wid_h: int) -> None:
        if img_w == 0 or img_h == 0:
            self._scale, self._offset_x, self._offset_y = 1.0, 0.0, 0.0
            return
        sx = wid_w / img_w
        sy = wid_h / img_h
        self._scale = min(sx, sy)
        scaled_w = img_w * self._scale
        scaled_h = img_h * self._scale
        self._offset_x = (wid_w - scaled_w) / 2
        self._offset_y = (wid_h - scaled_h) / 2

    def _img_rect_to_widget(self, bbox: tuple[int, int, int, int]) -> QRectF:
        x, y, w, h = bbox
        return QRectF(
            x * self._scale + self._offset_x,
            y * self._scale + self._offset_y,
            w * self._scale,
            h * self._scale,
        )

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = QColor(ACCENT.get(self._theme, ACCENT["dark"]))

        # Drag-select rubber band
        if self._dragging:
            band = QRectF(self._drag_origin, self._drag_current).normalized()
            band_fill = QColor(accent)
            band_fill.setAlpha(30)
            painter.setPen(QPen(accent, 1, Qt.PenStyle.DashLine))
            painter.setBrush(band_fill)
            painter.drawRect(band)

        # Word boxes
        for box in self._boxes:
            self._paint_word_box(painter, box, accent)

        # Translation overlays
        if self._show_translation and self._translations:
            self._paint_translations(painter)

    def _paint_word_box(self, painter: QPainter, box: _WordBox, accent: QColor) -> None:
        r = box.widget_rect
        if box.selected:
            fill = QColor(accent)
            fill.setAlpha(SELECTION_FILL_ALPHA + 40)
            painter.setBrush(fill)
            painter.setPen(QPen(accent, 1.5))
            painter.drawRect(r)
            # Draw text inverted (only if text labels are on)
            if self._show_text_labels:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Segoe UI", max(7, int(r.height() * 0.55))))
                painter.drawText(r, Qt.AlignmentFlag.AlignCenter, box.word.text)
        elif box.hovered:
            fill = QColor(accent)
            fill.setAlpha(40)
            painter.setBrush(fill)
            painter.setPen(QPen(accent, 1))
            painter.drawRect(r)
            # Show text on hover too (only if text labels are on)
            if self._show_text_labels:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Segoe UI", max(7, int(r.height() * 0.55))))
                painter.drawText(r, Qt.AlignmentFlag.AlignCenter, box.word.text)
        else:
            painter.setPen(QPen(accent.lighter(150), 0.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)

    def _paint_translations(self, painter: QPainter) -> None:
        """Render translated text as a semi-transparent panel per region."""
        # Group boxes by region to find each region's bounding rect
        region_rects: dict[int, QRectF] = {}
        for b in self._boxes:
            rid = b.word.region_id
            if rid not in region_rects:
                region_rects[rid] = QRectF(b.widget_rect)
            else:
                region_rects[rid] = region_rects[rid].united(b.widget_rect)

        bg = QColor("#000000cc") if self._theme == "dark" else QColor("#ffffffcc")
        fg = QColor(Qt.GlobalColor.white) if self._theme == "dark" else QColor(Qt.GlobalColor.black)
        painter.setFont(QFont("Segoe UI", 11))

        for rid, text in self._translations.items():
            rect = region_rects.get(rid)
            if rect is None:
                continue
            # Panel slightly inset
            panel = rect.adjusted(2, 2, -2, -2)
            painter.setBrush(bg)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(panel, 6, 6)
            painter.setPen(fg)
            painter.drawText(
                panel.adjusted(6, 4, -6, -4),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                text,
            )

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        pos = ev.position()
        self._drag_origin = pos
        self._drag_current = pos
        self._dragging = True

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        pos = ev.position()

        if self._dragging:
            self._drag_current = pos
            band = QRectF(self._drag_origin, self._drag_current).normalized()
            for box in self._boxes:
                box.selected = band.intersects(box.widget_rect)
            self.update()
            return

        # Hover
        changed = False
        for box in self._boxes:
            was = box.hovered
            box.hovered = box.widget_rect.contains(pos)
            if box.hovered != was:
                changed = True
        if changed:
            self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        pos = ev.position()
        was_dragging = self._dragging
        self._dragging = False

        drag_dist = (pos - self._drag_origin).manhattanLength()

        if drag_dist < 4:
            # Single click — toggle the word under cursor
            for box in self._boxes:
                if box.widget_rect.contains(pos):
                    box.selected = not box.selected
                    break

        self.update()
        self.selection_changed.emit()
