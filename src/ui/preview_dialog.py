"""
Preview dialog — shows side-by-side original vs translated text
before committing changes to the DaVinci timeline.
User can review, then confirm or cancel.
"""

from __future__ import annotations
from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QApplication, QGraphicsDropShadowEffect,
)

from . import theme as T
from .widgets import StatusBadge


class PreviewDialog(QDialog):
    """
    Shows a table of original vs translated subtitles.
    Returns QDialog.DialogCode.Accepted if user confirms, Rejected otherwise.
    """

    def __init__(
        self,
        results: List[Tuple],  # [(item, original_text, translated_text), ...]
        source_lang: str,
        target_lang: str,
        skip_count: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self._results = results
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._skip_count = skip_count

        self._build_window()
        self._build_ui()

    def _build_window(self):
        self.setWindowTitle("SRTFlow — Preview Translation")
        self.setMinimumWidth(720)
        self.setMinimumHeight(500)
        self.setStyleSheet(T.STYLESHEET + f"""
            QDialog {{
                background-color: {T.BG};
            }}
        """)

        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(sg.center().x() - 360, sg.center().y() - 250)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        # ── Header ──
        header_row = QHBoxLayout()
        title = QLabel("Review Translation")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {T.TEXT_1};
            background: transparent;
        """)

        count = len(self._results)
        changed = sum(1 for _, orig, trans in self._results if orig != trans)
        badge = StatusBadge(f"{changed} changed", "info")

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(badge)
        root.addLayout(header_row)

        desc = QLabel(
            "Review the translations below. Click <b>Apply to Timeline</b> to write them, "
            "or <b>Cancel</b> to discard."
        )
        desc.setStyleSheet(f"color: {T.TEXT_2}; font-size: 12px; background: transparent;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        if self._skip_count > 0:
            skip_label = QLabel(f"⚠ {self._skip_count} line{'s' if self._skip_count != 1 else ''} could not be translated and will keep their original text.")
            skip_label.setStyleSheet(f"color: {T.WARNING}; font-size: 12px; background: transparent;")
            skip_label.setWordWrap(True)
            root.addWidget(skip_label)

        # ── Table ──
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["#", "Original", "Translated"])
        self._table.setRowCount(len(self._results))
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 50)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {T.SURFACE};
                border: 1.5px solid {T.BORDER};
                border-radius: 10px;
                gridline-color: {T.BORDER};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border: none;
            }}
            QTableWidget::item:alternate {{
                background-color: {T.SURFACE_2};
            }}
            QTableWidget::item:selected {{
                background-color: {T.ACCENT_GLOW};
                color: {T.TEXT_1};
            }}
            QHeaderView::section {{
                background-color: {T.SURFACE_2};
                color: {T.TEXT_2};
                border: none;
                border-bottom: 1px solid {T.BORDER};
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)

        for row, (item, original, translated) in enumerate(self._results):
            idx_item = QTableWidgetItem(str(item.index))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, idx_item)

            orig_item = QTableWidgetItem(original)
            self._table.setItem(row, 1, orig_item)

            trans_item = QTableWidgetItem(translated)
            # Highlight changed items
            if original != translated:
                trans_item.setForeground(
                    self._table.palette().text().color()
                )
            else:
                trans_item.setForeground(
                    self._table.palette().placeholderText().color()
                )
            self._table.setItem(row, 2, trans_item)

        root.addWidget(self._table, 1)

        # ── Summary stats ──
        unchanged = count - changed - self._skip_count
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        for label, value, color in [
            ("Changed", changed, T.ACCENT),
            ("Skipped", self._skip_count, T.WARNING),
            ("Unchanged", unchanged, T.TEXT_3),
        ]:
            if value > 0:
                stat = QLabel(f"<span style='color:{color}; font-weight:700;'>{value}</span>"
                              f" <span style='color:{T.TEXT_3};'>{label}</span>")
                stat.setStyleSheet("background: transparent; border: none; font-size: 12px;")
                stats_row.addWidget(stat)
        stats_row.addStretch()
        root.addLayout(stats_row)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.SURFACE_2};
                border: 1.5px solid {T.BORDER};
                border-radius: 12px;
                color: {T.TEXT_2};
                font-size: 13px;
                font-weight: 500;
                padding: 0 24px;
            }}
            QPushButton:hover {{
                border-color: {T.ERROR};
                color: {T.ERROR};
                background: {T.ERROR_BG};
            }}
        """)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        apply_btn = QPushButton(f"Apply to Timeline ({changed} changes)")
        apply_btn.setFixedHeight(48)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ba4ff, stop:1 #3d86e8);
                color: #ffffff;
                border: none;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.4px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6cb0ff, stop:1 #4f96f0);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d86e8, stop:1 #2a6dcf);
            }}
        """)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn, 1)
        root.addLayout(btn_row)
