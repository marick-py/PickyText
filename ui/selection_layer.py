"""
Mode A — Selection Layer.

Renders on top of the screenshot canvas. Users draw rectangular or freehand
polygon regions. Each region can be moved, resized (8 handles for rects,
proportional scaling for polygons), and deleted.

All coordinates are in **widget space** (the canvas widget that shows the
scaled screenshot). The overlay converts them to image-pixel coords when
cropping regions for OCR.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import QWidget

from ui.themes import ACCENT, SELECTION_FILL_ALPHA


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

_HANDLE_SIZE = 8  # px, half-width of a resize handle square
_DELETE_BTN_R = 10  # radius of the ✕ circle
_MIN_REGION_SIZE = 6  # px — smaller drags are discarded


class _Tool(Enum):
    NONE = auto()
    RECT = auto()
    POLYGON = auto()


class _DragMode(Enum):
    NONE = auto()
    DRAW = auto()       # drawing a brand-new region
    MOVE = auto()       # dragging an existing region
    RESIZE = auto()     # dragging one of the 8 resize handles


class _RegionItem:
    """Internal representation of a drawn region on the canvas."""

    _next_id = 1

    def __init__(self, is_rect: bool) -> None:
        self.id = _RegionItem._next_id
        _RegionItem._next_id += 1
        self.is_rect = is_rect
        self.label = f"Region {self.id}"
        # RECT: stored as QRectF  /  POLYGON: stored as list[QPointF]
        self.rect: QRectF = QRectF()
        self.polygon: list[QPointF] = []

    def bounding_rect(self) -> QRectF:
        if self.is_rect:
            return self.rect.normalized()
        if not self.polygon:
            return QRectF()
        return QPolygonF(self.polygon).boundingRect()


# ------------------------------------------------------------------
# Selection Layer Widget
# ------------------------------------------------------------------

class SelectionLayer(QWidget):
    """Transparent overlay for Mode A region drawing."""

    regions_changed = pyqtSignal()  # emitted whenever the region list changes

    def __init__(self, theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._theme = theme
        self._tool: _Tool = _Tool.NONE
        self._regions: list[_RegionItem] = []

        # Interaction state
        self._drag_mode: _DragMode = _DragMode.NONE
        self._active_region: Optional[_RegionItem] = None
        self._handle_idx: int = -1  # which resize handle (0..7)
        self._drag_origin = QPointF()
        self._drag_last = QPointF()
        self._current_polygon_pts: list[QPointF] = []

    # ------------------------------------------------------------------
    # Public API (called by OverlayWindow)
    # ------------------------------------------------------------------

    def set_tool_rect(self) -> None:
        self._tool = _Tool.RECT

    def set_tool_polygon(self) -> None:
        self._tool = _Tool.POLYGON

    def clear_all(self) -> None:
        self._regions.clear()
        _RegionItem._next_id = 1
        self._reset_interaction()
        self.update()
        self.regions_changed.emit()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def get_regions_as_rects(self) -> list[tuple[int, QRectF]]:
        """Return (region_id, bounding_rect_in_widget) for each region."""
        return [(r.id, r.bounding_rect()) for r in self._regions]

    def region_count(self) -> int:
        return len(self._regions)

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = QColor(ACCENT.get(self._theme, ACCENT["dark"]))

        for region in self._regions:
            self._paint_region(painter, region, accent)

        # Rubber-band for current polygon drawing
        if self._tool == _Tool.POLYGON and self._current_polygon_pts:
            pen = QPen(accent, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(1, len(self._current_polygon_pts)):
                painter.drawLine(self._current_polygon_pts[i - 1], self._current_polygon_pts[i])

    def _paint_region(self, painter: QPainter, region: _RegionItem, accent: QColor) -> None:
        brect = region.bounding_rect()
        if brect.isEmpty():
            return

        # Fill
        fill = QColor(accent)
        fill.setAlpha(SELECTION_FILL_ALPHA)
        border_pen = QPen(accent, 2)
        painter.setPen(border_pen)

        if region.is_rect:
            painter.setBrush(fill)
            painter.drawRect(brect)
        else:
            painter.setBrush(fill)
            painter.drawPolygon(QPolygonF(region.polygon))

        # Label
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.drawText(
            brect.adjusted(6, 2, 0, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            region.label,
        )

        # Resize handles (8 for rects, 4 corners for polygons)
        painter.setPen(QPen(accent, 1))
        painter.setBrush(QColor(255, 255, 255, 220))
        for hpt in self._handle_points(region):
            painter.drawRect(QRectF(hpt.x() - _HANDLE_SIZE / 2, hpt.y() - _HANDLE_SIZE / 2,
                                     _HANDLE_SIZE, _HANDLE_SIZE))

        # Delete button (✕ circle at top-right)
        cx = brect.right() - 2
        cy = brect.top() - 2
        painter.setBrush(QColor(200, 50, 50, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), _DELETE_BTN_R, _DELETE_BTN_R)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        d = _DELETE_BTN_R * 0.45
        painter.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
        painter.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))

    # ------------------------------------------------------------------
    # Handle / hit-test geometry
    # ------------------------------------------------------------------

    def _handle_points(self, region: _RegionItem) -> list[QPointF]:
        """Return the 8 (rect) or 4 (polygon bbox) resize handle centres."""
        r = region.bounding_rect()
        if r.isEmpty():
            return []
        tl, tr, bl, br = r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()
        tm = QPointF(r.center().x(), r.top())
        bm = QPointF(r.center().x(), r.bottom())
        ml = QPointF(r.left(), r.center().y())
        mr = QPointF(r.right(), r.center().y())
        return [tl, tm, tr, ml, mr, bl, bm, br]

    def _hit_handle(self, region: _RegionItem, pos: QPointF) -> int:
        """Return handle index (0-7) or -1."""
        for i, hp in enumerate(self._handle_points(region)):
            if (hp - pos).manhattanLength() < _HANDLE_SIZE + 4:
                return i
        return -1

    def _hit_delete(self, region: _RegionItem, pos: QPointF) -> bool:
        br = region.bounding_rect()
        cx, cy = br.right() - 2, br.top() - 2
        return (QPointF(cx, cy) - pos).manhattanLength() < _DELETE_BTN_R + 4

    def _hit_region(self, pos: QPointF) -> Optional[_RegionItem]:
        """Return topmost region containing pos, or None."""
        for region in reversed(self._regions):
            if region.is_rect:
                if region.bounding_rect().contains(pos):
                    return region
            else:
                path = QPainterPath()
                path.addPolygon(QPolygonF(region.polygon))
                path.closeSubpath()
                if path.contains(pos):
                    return region
        return None

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        pos = ev.position()

        # Check delete button on existing regions (topmost first)
        for region in reversed(self._regions):
            if self._hit_delete(region, pos):
                self._regions.remove(region)
                self.update()
                self.regions_changed.emit()
                return

        # Check resize handles on existing regions
        for region in reversed(self._regions):
            hidx = self._hit_handle(region, pos)
            if hidx >= 0:
                self._drag_mode = _DragMode.RESIZE
                self._active_region = region
                self._handle_idx = hidx
                self._drag_origin = pos
                self._drag_last = pos
                return

        # Check move (inside an existing region)
        if self._tool == _Tool.NONE:
            hit = self._hit_region(pos)
            if hit is not None:
                self._drag_mode = _DragMode.MOVE
                self._active_region = hit
                self._drag_origin = pos
                self._drag_last = pos
                return

        # Start drawing a new region
        if self._tool == _Tool.RECT:
            r = _RegionItem(is_rect=True)
            r.rect = QRectF(pos, pos)
            self._regions.append(r)
            self._active_region = r
            self._drag_mode = _DragMode.DRAW
            self._drag_origin = pos
        elif self._tool == _Tool.POLYGON:
            self._current_polygon_pts = [pos]
            self._drag_mode = _DragMode.DRAW
            self._drag_origin = pos

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        pos = ev.position()

        if self._drag_mode == _DragMode.DRAW:
            if self._tool == _Tool.RECT and self._active_region:
                self._active_region.rect = QRectF(self._drag_origin, pos).normalized()
                self.update()
            elif self._tool == _Tool.POLYGON:
                self._current_polygon_pts.append(pos)
                self.update()

        elif self._drag_mode == _DragMode.MOVE and self._active_region:
            delta = pos - self._drag_last
            self._move_region(self._active_region, delta)
            self._drag_last = pos
            self.update()

        elif self._drag_mode == _DragMode.RESIZE and self._active_region:
            self._resize_region(self._active_region, self._handle_idx, pos)
            self._drag_last = pos
            self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            return

        if self._drag_mode == _DragMode.DRAW:
            if self._tool == _Tool.RECT and self._active_region:
                r = self._active_region.rect.normalized()
                if r.width() < _MIN_REGION_SIZE or r.height() < _MIN_REGION_SIZE:
                    self._regions.remove(self._active_region)
                self.regions_changed.emit()
            elif self._tool == _Tool.POLYGON and len(self._current_polygon_pts) > 2:
                rgn = _RegionItem(is_rect=False)
                rgn.polygon = list(self._current_polygon_pts)
                self._regions.append(rgn)
                self._current_polygon_pts.clear()
                self.regions_changed.emit()
            else:
                self._current_polygon_pts.clear()

        self._tool = _Tool.NONE
        self._reset_interaction()
        self.update()

    # ------------------------------------------------------------------
    # Move / resize logic
    # ------------------------------------------------------------------

    def _move_region(self, region: _RegionItem, delta: QPointF) -> None:
        if region.is_rect:
            region.rect.translate(delta)
        else:
            region.polygon = [p + delta for p in region.polygon]

    def _resize_region(self, region: _RegionItem, hidx: int, pos: QPointF) -> None:
        r = region.bounding_rect()
        if r.isEmpty():
            return
        new_r = QRectF(r)

        # hidx: 0=tl 1=tm 2=tr 3=ml 4=mr 5=bl 6=bm 7=br
        if hidx in (0, 3, 5):  # left edge
            new_r.setLeft(pos.x())
        if hidx in (2, 4, 7):  # right edge
            new_r.setRight(pos.x())
        if hidx in (0, 1, 2):  # top edge
            new_r.setTop(pos.y())
        if hidx in (5, 6, 7):  # bottom edge
            new_r.setBottom(pos.y())

        new_r = new_r.normalized()
        if new_r.width() < _MIN_REGION_SIZE or new_r.height() < _MIN_REGION_SIZE:
            return

        if region.is_rect:
            region.rect = new_r
        else:
            # Scale polygon proportionally to new bounding box
            old_r = r
            if old_r.width() < 1 or old_r.height() < 1:
                return
            sx = new_r.width() / old_r.width()
            sy = new_r.height() / old_r.height()
            region.polygon = [
                QPointF(
                    new_r.x() + (p.x() - old_r.x()) * sx,
                    new_r.y() + (p.y() - old_r.y()) * sy,
                )
                for p in region.polygon
            ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_interaction(self) -> None:
        self._drag_mode = _DragMode.NONE
        self._active_region = None
        self._handle_idx = -1
