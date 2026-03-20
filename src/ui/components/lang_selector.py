"""
Language selector component — source/target dropdowns with swap button.
"""

from __future__ import annotations
from typing import Dict, List, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
)

from .. import theme as T
from ..widgets import SectionLabel
from ...translator import LANGUAGES

# Languages for ComboBox — display name → code
_LANG_ITEMS: List[Tuple[str, str]] = list(LANGUAGES.items())
_TARGET_ITEMS: List[Tuple[str, str]] = [(n, c) for n, c in _LANG_ITEMS if c != "auto"]


class LangSelector(QWidget):
    """Source/target language dropdowns with a swap button."""

    lang_changed = pyqtSignal(str, str)  # source_code, target_code

    def __init__(self, source_code: str = "auto", target_code: str = "es", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build_ui(source_code, target_code)

    def _build_ui(self, source_code: str, target_code: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(SectionLabel("Languages"))

        row = QHBoxLayout()
        row.setSpacing(12)

        # Source language
        src_col = QVBoxLayout()
        src_lbl = QLabel("From")
        src_lbl.setStyleSheet(f"font-size: 11px; color: {T.TEXT_3}; background: transparent;")
        self.src_combo = QComboBox()
        _populate_combo(self.src_combo, _LANG_ITEMS, source_code)
        src_col.addWidget(src_lbl)
        src_col.addWidget(self.src_combo)

        # Swap button
        swap_col = QVBoxLayout()
        swap_col.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self._swap_btn = QPushButton("⇄")
        self._swap_btn.setFixedSize(38, 38)
        self._swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._swap_btn.setToolTip("Swap languages")
        self._swap_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.SURFACE_2};
                border: 1.5px solid {T.BORDER};
                border-radius: 10px;
                color: {T.TEXT_2};
                font-size: 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {T.ACCENT};
                color: {T.ACCENT};
                background: {T.ACCENT_GLOW};
            }}
        """)
        self._swap_btn.clicked.connect(self._swap_langs)
        swap_col.addWidget(self._swap_btn)

        # Target language
        tgt_col = QVBoxLayout()
        tgt_lbl = QLabel("To")
        tgt_lbl.setStyleSheet(f"font-size: 11px; color: {T.TEXT_3}; background: transparent;")
        self.tgt_combo = QComboBox()
        _populate_combo(self.tgt_combo, _TARGET_ITEMS, target_code)
        tgt_col.addWidget(tgt_lbl)
        tgt_col.addWidget(self.tgt_combo)

        row.addLayout(src_col, 1)
        row.addLayout(swap_col)
        row.addLayout(tgt_col, 1)
        layout.addLayout(row)

        # Signal forwarding
        self.src_combo.currentIndexChanged.connect(self._emit_changed)
        self.tgt_combo.currentIndexChanged.connect(self._emit_changed)

    def source_code(self) -> str:
        return self.src_combo.currentData()

    def target_code(self) -> str:
        return self.tgt_combo.currentData()

    def source_name(self) -> str:
        return self.src_combo.currentText()

    def target_name(self) -> str:
        return self.tgt_combo.currentText()

    def set_enabled(self, enabled: bool):
        self.src_combo.setEnabled(enabled)
        self.tgt_combo.setEnabled(enabled)
        self._swap_btn.setEnabled(enabled)

    def _swap_langs(self):
        src_code = self.src_combo.currentData()
        if src_code == "auto":
            return
        tgt_code = self.tgt_combo.currentData()

        for i in range(self.src_combo.count()):
            if self.src_combo.itemData(i) == tgt_code:
                self.src_combo.setCurrentIndex(i)
                break
        for i in range(self.tgt_combo.count()):
            if self.tgt_combo.itemData(i) == src_code:
                self.tgt_combo.setCurrentIndex(i)
                break

    def _emit_changed(self):
        self.lang_changed.emit(self.source_code(), self.target_code())


def _populate_combo(combo: QComboBox, items: list, selected_code: str):
    for name, code in items:
        combo.addItem(name, userData=code)
    for i in range(combo.count()):
        if combo.itemData(i) == selected_code:
            combo.setCurrentIndex(i)
            break
