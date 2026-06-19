"""
Glossary editor — add, remove, search custom term replacements.
Terms are applied post-translation (source term → replacement).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLabel,
)

from .. import theme as T
from ..widgets import SectionLabel, Card

_GLOSSARY_PATH = Path(__file__).parent.parent.parent.parent / "glossary.json"


class GlossaryEditor(QWidget):
    """Collapsible glossary editor panel with add/remove/search."""

    glossary_changed = pyqtSignal(dict)  # emits updated terms dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._terms: Dict[str, str] = {}
        self._load_glossary()
        self._setup_ui()

    def _load_glossary(self):
        try:
            data = json.loads(_GLOSSARY_PATH.read_text(encoding="utf-8"))
            self._terms = data.get("terms", {})
        except Exception:
            self._terms = {}

    def _save_glossary(self):
        try:
            data = {"_comment": "Custom glossary — terms are applied after translation", "terms": self._terms}
            _GLOSSARY_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
        self.glossary_changed.emit(self._terms)

    def get_terms(self) -> Dict[str, str]:
        return dict(self._terms)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toggle header
        self._toggle_btn = QPushButton("▸  Glossary", self)
        self._toggle_btn.setProperty("role", "ghost")
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {T.TEXT_3};
                font-size: 12px;
                font-weight: 500;
                text-align: left;
                padding: 4px 0;
            }}
            QPushButton:hover {{
                color: {T.TEXT_2};
                background: transparent;
            }}
        """)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)

        # Content
        self._content = QWidget(self)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 10, 0, 0)
        content_layout.setSpacing(10)

        card = Card(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        desc = QLabel("Custom terms applied after translation (find → replace).")
        desc.setStyleSheet(f"color: {T.TEXT_3}; font-size: 11px; background: transparent;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        # Empty state hint
        self._empty_hint = QLabel("No glossary terms yet — add your first term below")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setStyleSheet(f"""
            color: {T.TEXT_3}; font-size: 11px; background: {T.SURFACE};
            border: 1px dashed {T.BORDER}; border-radius: 8px; padding: 16px;
        """)
        card_layout.addWidget(self._empty_hint)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search glossary…")
        self._search.textChanged.connect(self._filter_table)
        card_layout.addWidget(self._search)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Find", "Replace With"])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(120)
        self._table.setMaximumHeight(200)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {T.SURFACE};
                border: 1.5px solid {T.BORDER};
                border-radius: 8px;
                gridline-color: {T.BORDER};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {T.ACCENT_GLOW};
                color: {T.TEXT_1};
            }}
            QHeaderView::section {{
                background-color: {T.SURFACE_2};
                color: {T.TEXT_3};
                border: none;
                border-bottom: 1px solid {T.BORDER};
                padding: 6px 8px;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        card_layout.addWidget(self._table)

        # Add row
        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self._find_edit = QLineEdit()
        self._find_edit.setPlaceholderText("Find term…")
        self._repl_edit = QLineEdit()
        self._repl_edit.setPlaceholderText("Replace with…")

        add_btn = QPushButton("Add")
        add_btn.setFixedWidth(60)
        add_btn.setFixedHeight(32)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.ACCENT};
                border: none;
                border-radius: 6px;
                color: #fff;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {T.ACCENT_HOVER}; }}
        """)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_term)

        add_row.addWidget(self._find_edit, 1)
        add_row.addWidget(self._repl_edit, 1)
        add_row.addWidget(add_btn)
        card_layout.addLayout(add_row)

        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setFixedHeight(28)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {T.BORDER};
                border-radius: 6px;
                color: {T.TEXT_3};
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {T.ERROR};
                color: {T.ERROR};
                background: {T.ERROR_BG};
            }}
        """)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self._remove_selected)
        card_layout.addWidget(remove_btn)

        content_layout.addWidget(card)

        root.addWidget(self._toggle_btn)
        root.addWidget(self._content)
        self._content.setVisible(False)

        self._refresh_table()

    def _toggle(self):
        self._expanded = not self._expanded
        icon = "▾" if self._expanded else "▸"
        self._toggle_btn.setText(f"{icon}  Glossary")

        # Update badge
        count = len(self._terms)
        if count and not self._expanded:
            self._toggle_btn.setText(f"▸  Glossary  ({count} term{'s' if count != 1 else ''})")

        if self._expanded:
            self._content.setVisible(True)
            self._content.setMaximumHeight(0)
            anim = QPropertyAnimation(self._content, b"maximumHeight")
            anim.setDuration(T.ANIM_NORMAL)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(0)
            anim.setEndValue(self._content.sizeHint().height() + 100)
            anim.start()
            self._anim = anim
        else:
            anim = QPropertyAnimation(self._content, b"maximumHeight")
            anim.setDuration(T.ANIM_NORMAL)
            anim.setEasingCurve(QEasingCurve.Type.InCubic)
            anim.setStartValue(self._content.maximumHeight())
            anim.setEndValue(0)
            anim.finished.connect(lambda: self._content.setVisible(False) if not self._expanded else None)
            anim.start()
            self._anim = anim

    def _refresh_table(self, filter_text: str = ""):
        ft = filter_text.lower()
        items = [(k, v) for k, v in sorted(self._terms.items())
                 if not ft or ft in k.lower() or ft in v.lower()]

        has_terms = len(self._terms) > 0
        self._empty_hint.setVisible(not has_terms)
        self._table.setVisible(has_terms)
        self._search.setVisible(has_terms)

        self._table.setRowCount(len(items))
        for row, (find, repl) in enumerate(items):
            self._table.setItem(row, 0, QTableWidgetItem(find))
            self._table.setItem(row, 1, QTableWidgetItem(repl))

    def _filter_table(self, text: str):
        self._refresh_table(text)

    def _add_term(self):
        find = self._find_edit.text().strip()
        repl = self._repl_edit.text().strip()
        if not find or not repl:
            return
        self._terms[find] = repl
        self._save_glossary()
        self._find_edit.clear()
        self._repl_edit.clear()
        self._refresh_table(self._search.text())

    def _remove_selected(self):
        row = self._table.currentRow()
        if row < 0:
            return
        find_item = self._table.item(row, 0)
        if find_item and find_item.text() in self._terms:
            del self._terms[find_item.text()]
            self._save_glossary()
            self._refresh_table(self._search.text())
