"""
Custom PyQt6 widgets for SRTFlow UI.
"""

from __future__ import annotations
import os
from typing import Optional, Callable

from PyQt6.QtCore import (
    Qt, QSize, QMimeData, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QTimer, QPoint,
)
from PyQt6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QFont, QPainter,
    QPainterPath, QPen, QBrush, QLinearGradient, QIcon, QPixmap,
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QSizePolicy, QGraphicsDropShadowEffect,
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
# Card / Surface frame
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


# ─────────────────────────────────────────────────────────────────────────────
# File Drop Zone
# ─────────────────────────────────────────────────────────────────────────────

class FileDropZone(QFrame):
    """Drag-and-drop zone for SRT files. Emits file_dropped(path) for single,
    files_dropped(list) for multiple files."""

    file_dropped = pyqtSignal(str)
    files_dropped = pyqtSignal(list)  # List[str]
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(130)
        self._hovered = False
        self._active = False
        self._file_path: Optional[str] = None
        self._file_paths: list = []

        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        self._icon_label = QLabel("↑", self)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(f"""
            font-size: 28px;
            color: {theme.TEXT_3};
            background: transparent;
            border: none;
        """)

        self._title_label = QLabel("Drop your SRT file here", self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {theme.TEXT_2};
            background: transparent;
            border: none;
        """)

        self._sub_label = QLabel("or click to browse", self)
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setStyleSheet(f"""
            font-size: 12px;
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
            font-size: 24px;
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
        """Set multiple files (batch mode)."""
        if len(paths) == 1:
            self.set_file(paths[0])
            return
        self._file_paths = paths
        self._file_path = paths[0]
        self._icon_label.setText("✓")
        self._icon_label.setStyleSheet(f"""
            font-size: 24px;
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
        self._active = False
        self._icon_label.setText("↑")
        self._icon_label.setStyleSheet(f"""
            font-size: 28px;
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
        self._sub_label.setText("or click to browse")
        self._update_style()

    def _update_style(self):
        if self._hovered or self._active:
            border_color = theme.ACCENT if self._hovered else theme.SUCCESS
            bg = theme.ACCENT_GLOW if self._hovered else theme.SUCCESS_BG
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border: 2px dashed {border_color};
                    border-radius: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.SURFACE_2};
                    border: 2px dashed {theme.BORDER};
                    border-radius: 14px;
                }}
            """)

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
# Log Panel
# ─────────────────────────────────────────────────────────────────────────────

class LogPanel(QTextEdit):
    """Read-only log panel with color-coded entries."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(140)
        self.setMaximumHeight(180)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.SURFACE};
                border: 1.5px solid {theme.BORDER};
                border-radius: 12px;
                padding: 10px 14px;
                color: {theme.TEXT_1};
                font-family: "SF Mono", "Cascadia Code", monospace;
                font-size: 12px;
                line-height: 1.5;
            }}
        """)

    def add_info(self, msg: str):
        self._append(f'<span style="color:{theme.TEXT_2}">ℹ {msg}</span>')

    def add_success(self, msg: str):
        self._append(f'<span style="color:{theme.SUCCESS}">✓ {msg}</span>')

    def add_error(self, msg: str):
        self._append(f'<span style="color:{theme.ERROR}">✗ {msg}</span>')

    def add_warning(self, msg: str):
        self._append(f'<span style="color:{theme.WARNING}">⚠ {msg}</span>')

    def add_line_result(self, index: int, original: str, translated: str):
        orig_short = (original[:40] + "…") if len(original) > 40 else original
        trans_short = (translated[:40] + "…") if len(translated) > 40 else translated
        self._append(
            f'<span style="color:{theme.TEXT_3}">[{index:03d}]</span> '
            f'<span style="color:{theme.TEXT_2}">{_esc(orig_short)}</span>'
            f'<span style="color:{theme.TEXT_3}"> → </span>'
            f'<span style="color:{theme.TEXT_1}">{_esc(trans_short)}</span>'
        )

    def clear_log(self):
        self.clear()

    def _append(self, html: str):
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.insertHtml(html + "<br>")
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.ensureCursorVisible()


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─────────────────────────────────────────────────────────────────────────────
# Animated Progress Bar
# ─────────────────────────────────────────────────────────────────────────────

class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Top row: label + count
        top_row = QHBoxLayout()
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {theme.TEXT_2}; font-size: 12px; background: transparent;")
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {theme.TEXT_3}; font-size: 12px; background: transparent;")
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

    def set_done(self, total: int):
        self._bar.setValue(100)
        self._count_label.setText(f"{total}/{total}")
        self._status_label.setText("Translation complete")
        self._status_label.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px; background: transparent;")

    def set_error(self, msg: str):
        self._bar.setValue(0)
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color: {theme.ERROR}; font-size: 12px; background: transparent;")

    def reset(self):
        self._bar.setValue(0)
        self._count_label.setText("")
        self._status_label.setText("Ready")
        self._status_label.setStyleSheet(f"color: {theme.TEXT_2}; font-size: 12px; background: transparent;")
