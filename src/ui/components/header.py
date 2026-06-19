"""
Header bar component — logo, title, DaVinci connection badge, shortcut hint.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsDropShadowEffect

from .. import theme as T
from ..widgets import StatusBadge


def build_header(resolve_available: bool, timeline_name: str | None = None) -> QWidget:
    """Create the top header bar with logo, title, and connection status."""
    bar = QWidget()
    bar.setFixedHeight(56)
    bar.setStyleSheet(f"""
        QWidget {{
            background-color: {T.SURFACE};
            border-bottom: 1px solid {T.BORDER};
        }}
    """)

    # Subtle bottom shadow for depth
    shadow = QGraphicsDropShadowEffect(bar)
    shadow.setBlurRadius(12)
    shadow.setColor(QColor(0, 0, 0, 60))
    shadow.setOffset(0, 2)
    bar.setGraphicsEffect(shadow)

    layout = QHBoxLayout(bar)
    layout.setContentsMargins(24, 0, 16, 0)

    # Logo — accent colored diamond
    logo = QLabel("◈")
    logo.setStyleSheet(f"font-size: 20px; color: {T.ACCENT}; background: transparent; border: none;")

    title = QLabel("SRTFlow")
    title.setStyleSheet(f"""
        font-size: 15px;
        font-weight: 700;
        color: {T.TEXT_1};
        letter-spacing: -0.3px;
        background: transparent;
        border: none;
    """)

    subtitle = QLabel("Subtitle Translator")
    subtitle.setStyleSheet(f"""
        font-size: 11px;
        color: {T.TEXT_3};
        background: transparent;
        border: none;
    """)

    # Shortcut hint
    shortcut_hint = QLabel("Ctrl+/  shortcuts")
    shortcut_hint.setStyleSheet(f"""
        font-size: 10px;
        color: {T.TEXT_3};
        background: {T.SURFACE_2};
        border: 1px solid {T.BORDER};
        border-radius: 4px;
        padding: 2px 6px;
    """)

    if resolve_available:
        badge = StatusBadge("DaVinci Connected", "success")
    else:
        badge = StatusBadge("Standalone", "neutral")

    layout.addWidget(logo)
    layout.addSpacing(8)
    layout.addWidget(title)
    layout.addSpacing(6)
    layout.addWidget(subtitle)
    layout.addStretch()
    layout.addWidget(shortcut_hint)
    layout.addSpacing(8)
    layout.addWidget(badge)

    return bar
