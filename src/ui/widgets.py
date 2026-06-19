"""
Custom PyQt6 widgets for SRTFlow UI.
Includes animated, polished components for a premium feel.
"""

from __future__ import annotations
import math
import os
from typing import Optional, Callable

from PyQt6.QtCore import (
    Qt, QSize, QMimeData, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QTimer, QPoint, QRect, QRectF,
    QParallelAnimationGroup, QSequentialAnimationGroup,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QFont, QPainter,
    QPainterPath, QPen, QBrush, QLinearGradient, QIcon, QPixmap,
    QConicalGradient,
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QSizePolicy, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QProgressBar, QTextEdit, QScrollArea,
)

from . import theme


# ─────────────────────────────────────────────────────────────────────────────
# Divider
# ─────────────────────────────────────────────────────────────────────────────

class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {theme.BORDER}; border: none;")


# ─────────────────────────────────────────────────────────────────────────────
# Section label
# ─────────────────────────────────────────────────────────────────────────────

class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"""
            color: {theme.TEXT_3};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.2px;
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Card / Surface frame with shadow
# ─────────────────────────────────────────────────────────────────────────────

class Card(QFrame):
    def __init__(self, parent=None, elevated: bool = False):
        super().__init__(parent)
        bg = theme.SURFACE_3 if elevated else theme.SURFACE_2
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1.5px solid {theme.BORDER};
                border-radius: 12px;
            }}
        """)
        if elevated:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(16)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 4)
            self.setGraphicsEffect(shadow)


# ─────────────────────────────────────────────────────────────────────────────
# Animated Spinner (circular loading indicator)
# ─────────────────────────────────────────────────────────────────────────────

class Spinner(QWidget):
    """Smooth circular loading spinner. Call start()/stop() to control."""

    def __init__(self, size: int = 24, color: str = theme.ACCENT, stroke: int = 3, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._size = size
        self._color = QColor(color)
        self._stroke = stroke
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._running = False

    def start(self):
        if not self._running:
            self._running = True
            self._timer.start(16)  # ~60fps
            self.setVisible(True)

    def stop(self):
        self._running = False
        self._timer.stop()
        self.setVisible(False)

    def _rotate(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        if not self._running:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = self._stroke + 1
        rect = QRectF(margin, margin, self._size - 2 * margin, self._size - 2 * margin)

        pen = QPen(QColor(self._color.red(), self._color.green(), self._color.blue(), 50))
        pen.setWidth(self._stroke)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)

        pen.setColor(self._color)
        p.setPen(pen)
        start_angle = int(self._angle * 16)
        span = 90 * 16
        p.drawArc(rect, start_angle, span)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# Toast Notification
# ─────────────────────────────────────────────────────────────────────────────

class Toast(QFrame):
    """Animated popup notification. Auto-dismisses after duration_ms."""

    _ICONS = {"success": "✓", "error": "✗", "warning": "!", "info": "i"}
    _COLORS = {
        "success": (theme.SUCCESS, theme.SUCCESS_BG),
        "error": (theme.ERROR, theme.ERROR_BG),
        "warning": (theme.WARNING, theme.WARNING_BG),
        "info": (theme.ACCENT, theme.INFO_BG),
    }

    def __init__(self, message: str, kind: str = "info", duration_ms: int = 3000, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setMinimumWidth(280)
        self.setMaximumWidth(500)

        color, bg = self._COLORS.get(kind, self._COLORS["info"])
        icon = self._ICONS.get(kind, "i")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.SURFACE_3};
                border: 1px solid {color};
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(22, 22)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background: {bg};
            color: {color};
            border-radius: 11px;
            font-size: 12px;
            font-weight: 700;
            border: none;
        """)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"""
            color: {theme.TEXT_1};
            font-size: 12px;
            font-weight: 500;
            background: transparent;
            border: none;
        """)

        layout.addWidget(icon_lbl)
        layout.addWidget(msg_lbl, 1)

        # Fade-in opacity
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(shadow)  # shadow takes priority, opacity via animation

        # Auto dismiss
        QTimer.singleShot(duration_ms, self._dismiss)

        # Slide-in animation
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(theme.ANIM_NORMAL)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_toast(self):
        """Position and animate in from the top-right of parent."""
        if not self.parent():
            return
        pw = self.parent().width()
        start = QPoint(pw - self.width() - 16, -50)
        end = QPoint(pw - self.width() - 16, 12)
        self._slide_anim.setStartValue(start)
        self._slide_anim.setEndValue(end)
        self.show()
        self.raise_()
        self._slide_anim.start()

    def _dismiss(self):
        if not self.parent():
            self.deleteLater()
            return
        pw = self.parent().width()
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(theme.ANIM_NORMAL)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.setStartValue(self.pos())
        anim.setEndValue(QPoint(pw - self.width() - 16, -60))
        anim.finished.connect(self.deleteLater)
        anim.start()
        self._dismiss_anim = anim  # prevent GC


class ToastManager:
    """Manages toast notifications for a parent widget."""

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._toasts: list = []

    def show(self, message: str, kind: str = "info", duration_ms: int = 3000):
        toast = Toast(message, kind, duration_ms, parent=self._parent)
        toast.show_toast()
        self._toasts.append(toast)


# ─────────────────────────────────────────────────────────────────────────────
# File Drop Zone (enhanced with glow animation)
# ─────────────────────────────────────────────────────────────────────────────

class FileDropZone(QFrame):
    """Drag-and-drop zone for SRT files with animated hover effects."""

    file_dropped = pyqtSignal(str)
    files_dropped = pyqtSignal(list)  # List[str]
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(140)
        self._hovered = False
        self._active = False
        self._file_path: Optional[str] = None
        self._file_paths: list = []

        # Glow effect for hover
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(0)
        self._glow.setColor(QColor(79, 156, 249, 0))
        self._glow.setOffset(0, 0)
        self.setGraphicsEffect(self._glow)

        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon_label = QLabel("", self)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(f"""
            font-size: 32px;
            color: {theme.TEXT_3};
            background: transparent;
            border: none;
        """)
        self._icon_label.setText("⬆")

        self._title_label = QLabel("Drop your SRT file here", self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {theme.TEXT_2};
            background: transparent;
            border: none;
        """)

        self._sub_label = QLabel("or click to browse  ·  Ctrl+O", self)
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setStyleSheet(f"""
            font-size: 11px;
            color: {theme.TEXT_3};
            background: transparent;
            border: none;
        """)

        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._sub_label)

    def set_file(self, path: str):
        self._file_path = path
        self._file_paths = [path]
        name = os.path.basename(path)
        self._icon_label.setText("✓")
        self._icon_label.setStyleSheet(f"""
            font-size: 26px;
            color: {theme.SUCCESS};
            background: transparent;
            border: none;
        """)
        self._title_label.setText(name)
        self._title_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {theme.TEXT_1};
            background: transparent;
            border: none;
        """)
        self._sub_label.setText("Click to change file")
        self._active = True
        self._update_style()

    def set_files(self, paths: list):
        if len(paths) == 1:
            self.set_file(paths[0])
            return
        self._file_paths = paths
        self._file_path = paths[0]
        self._icon_label.setText("✓")
        self._icon_label.setStyleSheet(f"""
            font-size: 26px;
            color: {theme.SUCCESS};
            background: transparent;
            border: none;
        """)
        self._title_label.setText(f"{len(paths)} SRT files selected")
        self._title_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {theme.TEXT_1};
            background: transparent;
            border: none;
        """)
        names = ", ".join(os.path.basename(p) for p in paths[:3])
        if len(paths) > 3:
            names += f" +{len(paths) - 3} more"
        self._sub_label.setText(names)
        self._active = True
        self._update_style()

    def clear(self):
        self._file_path = None
        self._file_paths = []
        self._active = False
        self._icon_label.setText("⬆")
        self._icon_label.setStyleSheet(f"""
            font-size: 32px;
            color: {theme.TEXT_3};
            background: transparent;
            border: none;
        """)
        self._title_label.setText("Drop your SRT file here")
        self._title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {theme.TEXT_2};
            background: transparent;
            border: none;
        """)
        self._sub_label.setText("or click to browse  ·  Ctrl+O")
        self._update_style()

    def _update_style(self):
        if self._hovered:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(79,156,249,0.08);
                    border: 2px dashed {theme.ACCENT};
                    border-radius: 14px;
                }}
            """)
            self._animate_glow(30)
        elif self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.SUCCESS_BG};
                    border: 2px solid {theme.SUCCESS};
                    border-radius: 14px;
                }}
            """)
            self._animate_glow(0)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.SURFACE_2};
                    border: 2px dashed {theme.BORDER};
                    border-radius: 14px;
                }}
            """)
            self._animate_glow(0)

    def _animate_glow(self, target_blur: int):
        anim = QPropertyAnimation(self._glow, b"blurRadius")
        anim.setDuration(theme.ANIM_NORMAL)
        anim.setStartValue(self._glow.blurRadius())
        anim.setEndValue(float(target_blur))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._glow_anim = anim  # prevent GC
        if target_blur > 0:
            self._glow.setColor(QColor(79, 156, 249, 80))
        else:
            self._glow.setColor(QColor(0, 0, 0, 0))

    def mousePressEvent(self, event):
        self.clicked.emit()

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".srt") for u in urls):
                event.acceptProposedAction()
                self._hovered = True
                self._update_style()

    def dragLeaveEvent(self, event):
        self._hovered = False
        self._update_style()

    def dropEvent(self, event: QDropEvent):
        self._hovered = False
        urls = event.mimeData().urls()
        srt_paths = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith(".srt")]
        if len(srt_paths) == 1:
            self.set_file(srt_paths[0])
            self.file_dropped.emit(srt_paths[0])
        elif len(srt_paths) > 1:
            self.set_files(srt_paths)
            self.files_dropped.emit(srt_paths)
        self._update_style()


# ─────────────────────────────────────────────────────────────────────────────
# Status Badge
# ─────────────────────────────────────────────────────────────────────────────

class StatusBadge(QLabel):
    """Small colored pill badge. kind: 'success' | 'error' | 'warning' | 'info' | 'neutral'"""

    _COLORS = {
        "success": (theme.SUCCESS,     theme.SUCCESS_BG),
        "error":   (theme.ERROR,       theme.ERROR_BG),
        "warning": (theme.WARNING,     theme.WARNING_BG),
        "info":    (theme.ACCENT,      theme.INFO_BG),
        "neutral": (theme.TEXT_2,      theme.SURFACE_2),
    }

    def __init__(self, text: str, kind: str = "neutral", parent=None):
        super().__init__(text, parent)
        color, bg = self._COLORS.get(kind, self._COLORS["neutral"])
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }}
        """)
        self.setFixedHeight(20)


# ─────────────────────────────────────────────────────────────────────────────
# Log Panel (with empty state)
# ─────────────────────────────────────────────────────────────────────────────

class LogPanel(QWidget):
    """Read-only log panel with color-coded entries and empty state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Empty state
        self._empty_state = QLabel(
            "Translation log will appear here\n"
            "Drop an SRT file above to get started"
        )
        self._empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state.setMinimumHeight(100)
        self._empty_state.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_3};
                font-size: 12px;
                background-color: {theme.SURFACE};
                border: 1.5px solid {theme.BORDER};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        # Log text area
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(140)
        self._log.setMaximumHeight(200)
        self._log.setVisible(False)
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.SURFACE};
                border: 1.5px solid {theme.BORDER};
                border-radius: 12px;
                padding: 10px 14px;
                color: {theme.TEXT_1};
                font-family: {theme.FONT_MONO};
                font-size: 12px;
                line-height: 1.5;
            }}
        """)

        layout.addWidget(self._empty_state)
        layout.addWidget(self._log)

        self._has_content = False

    def _ensure_visible(self):
        if not self._has_content:
            self._has_content = True
            self._empty_state.setVisible(False)
            self._log.setVisible(True)

    def add_info(self, msg: str):
        self._ensure_visible()
        self._append(f'<span style="color:{theme.TEXT_2}">ℹ  {msg}</span>')

    def add_success(self, msg: str):
        self._ensure_visible()
        self._append(f'<span style="color:{theme.SUCCESS}">✓  {msg}</span>')

    def add_error(self, msg: str):
        self._ensure_visible()
        self._append(f'<span style="color:{theme.ERROR}">✗  {msg}</span>')

    def add_warning(self, msg: str):
        self._ensure_visible()
        self._append(f'<span style="color:{theme.WARNING}">⚠  {msg}</span>')

    def add_line_result(self, index: int, original: str, translated: str):
        self._ensure_visible()
        orig_short = (original[:40] + "…") if len(original) > 40 else original
        trans_short = (translated[:40] + "…") if len(translated) > 40 else translated
        self._append(
            f'<span style="color:{theme.TEXT_3}">[{index:03d}]</span> '
            f'<span style="color:{theme.TEXT_2}">{_esc(orig_short)}</span>'
            f'<span style="color:{theme.TEXT_3}">  →  </span>'
            f'<span style="color:{theme.TEXT_1}">{_esc(trans_short)}</span>'
        )

    def clear_log(self):
        self._log.clear()
        self._has_content = False
        self._empty_state.setVisible(True)
        self._log.setVisible(False)

    def _append(self, html: str):
        self._log.moveCursor(self._log.textCursor().MoveOperation.End)
        self._log.insertHtml(html + "<br>")
        self._log.moveCursor(self._log.textCursor().MoveOperation.End)
        self._log.ensureCursorVisible()


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─────────────────────────────────────────────────────────────────────────────
# Animated Progress Panel (with spinner)
# ─────────────────────────────────────────────────────────────────────────────

class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Top row: spinner + label + count
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._spinner = Spinner(size=16, stroke=2)
        self._spinner.setVisible(False)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {theme.TEXT_2}; font-size: 12px; background: transparent;")
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {theme.TEXT_3}; font-size: 12px; background: transparent;")

        top_row.addWidget(self._spinner)
        top_row.addWidget(self._status_label)
        top_row.addStretch()
        top_row.addWidget(self._count_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.SURFACE_2};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3d86e8, stop:1 #5ba4ff);
                border-radius: 3px;
            }}
        """)

        layout.addLayout(top_row)
        layout.addWidget(self._bar)

    def set_progress(self, current: int, total: int):
        pct = int((current / total) * 100) if total else 0
        self._bar.setValue(pct)
        self._count_label.setText(f"{current}/{total}")
        self._status_label.setText(f"Translating… {pct}%")
        self._spinner.start()

    def set_done(self, total: int):
        self._spinner.stop()
        self._bar.setValue(100)
        self._count_label.setText(f"{total}/{total}")
        self._status_label.setText("Translation complete")
        self._status_label.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px; background: transparent;")

    def set_error(self, msg: str):
        self._spinner.stop()
        self._bar.setValue(0)
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {theme.ERROR}; font-size: 12px; background: transparent;")

    def reset(self):
        self._spinner.stop()
        self._bar.setValue(0)
        self._count_label.setText("")
        self._status_label.setText("Ready")
        self._status_label.setStyleSheet(f"color: {theme.TEXT_2}; font-size: 12px; background: transparent;")


# ─────────────────────────────────────────────────────────────────────────────
# Keyboard Shortcut Help Dialog
# ─────────────────────────────────────────────────────────────────────────────

class ShortcutHelpOverlay(QFrame):
    """Floating overlay showing all keyboard shortcuts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.SURFACE_3};
                border: 1px solid {theme.BORDER};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(6)

        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {theme.TEXT_1};
            background: transparent;
            border: none;
            margin-bottom: 8px;
        """)
        layout.addWidget(title)

        shortcuts = [
            ("Ctrl + O", "Open SRT file(s)"),
            ("Ctrl + T", "Start translation"),
            ("Ctrl + E", "Export to other formats"),
            ("Ctrl + Shift + T", "Quick Translate (timeline)"),
            ("Escape", "Cancel translation"),
            ("Ctrl + Z", "Undo last timeline edit"),
            ("Ctrl + /", "Show this help"),
        ]

        for keys, desc in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(12)

            key_lbl = QLabel(keys)
            key_lbl.setFixedWidth(140)
            key_lbl.setStyleSheet(f"""
                background: {theme.SURFACE};
                color: {theme.ACCENT};
                font-size: 11px;
                font-weight: 600;
                font-family: {theme.FONT_MONO};
                padding: 4px 8px;
                border-radius: 5px;
                border: 1px solid {theme.BORDER};
            """)

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"""
                color: {theme.TEXT_2};
                font-size: 12px;
                background: transparent;
                border: none;
            """)

            row.addWidget(key_lbl)
            row.addWidget(desc_lbl, 1)
            layout.addLayout(row)

        # Dismiss hint
        hint = QLabel("Press Escape or Ctrl+/ to close")
        hint.setStyleSheet(f"""
            color: {theme.TEXT_3};
            font-size: 10px;
            margin-top: 10px;
            background: transparent;
            border: none;
        """)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.adjustSize()
        self.setVisible(False)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            if self.parent():
                pw = self.parent().width()
                ph = self.parent().height()
                self.move((pw - self.width()) // 2, (ph - self.height()) // 2)
            self.show()
            self.raise_()


# ─────────────────────────────────────────────────────────────────────────────
# Collapsible Panel Wrapper (smooth animation)
# ─────────────────────────────────────────────────────────────────────────────

class AnimatedCollapsible(QWidget):
    """Wraps a widget with smooth expand/collapse animation."""

    def __init__(self, title: str, icon_collapsed: str = "▸", icon_expanded: str = "▾",
                 badge_text: str = "", parent=None):
        super().__init__(parent)
        self._expanded = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self._toggle_btn = QPushButton(f"{icon_collapsed}  {title}")
        self._toggle_btn.setProperty("role", "ghost")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {theme.TEXT_3};
                font-size: 12px;
                font-weight: 500;
                text-align: left;
                padding: 4px 0;
            }}
            QPushButton:hover {{
                color: {theme.TEXT_2};
                background: transparent;
            }}
        """)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self.toggle)

        self._badge = QLabel(badge_text)
        self._badge.setStyleSheet(f"""
            color: {theme.TEXT_3};
            font-size: 10px;
            background: {theme.SURFACE_2};
            border-radius: 8px;
            padding: 1px 6px;
            border: none;
        """)
        self._badge.setVisible(bool(badge_text))

        header_row.addWidget(self._toggle_btn)
        header_row.addWidget(self._badge)
        header_row.addStretch()

        # Content area
        self._content = QWidget()
        self._content.setMaximumHeight(0)

        root.addLayout(header_row)
        root.addWidget(self._content)

        self._title = title
        self._icon_collapsed = icon_collapsed
        self._icon_expanded = icon_expanded

    def set_content_layout(self, layout):
        """Set the layout for the collapsible content area."""
        self._content.setLayout(layout)

    def content_widget(self) -> QWidget:
        return self._content

    def set_badge(self, text: str):
        self._badge.setText(text)
        self._badge.setVisible(bool(text))

    def toggle(self):
        self._expanded = not self._expanded
        icon = self._icon_expanded if self._expanded else self._icon_collapsed
        self._toggle_btn.setText(f"{icon}  {self._title}")

        anim = QPropertyAnimation(self._content, b"maximumHeight")
        anim.setDuration(theme.ANIM_NORMAL)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if self._expanded:
            self._content.setVisible(True)
            anim.setStartValue(0)
            anim.setEndValue(self._content.sizeHint().height() + 100)
        else:
            anim.setStartValue(self._content.maximumHeight())
            anim.setEndValue(0)
            anim.finished.connect(lambda: self._content.setVisible(False) if not self._expanded else None)

        anim.start()
        self._anim = anim  # prevent GC

    @property
    def expanded(self) -> bool:
        return self._expanded
