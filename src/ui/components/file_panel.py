"""
File panel component — output file row with browse button.
"""

from __future__ import annotations
import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFileDialog,
)

from .. import theme as T
from ..widgets import SectionLabel, Card
from ...srt_parser import suggest_output_path


class FileOutputPanel(QWidget):
    """Shows the output file path with a 'Change' button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._custom_output: Optional[str] = None
        self._input_path: Optional[str] = None
        self._target_lang: str = "es"
        self._suffix: str = "_{lang}"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(SectionLabel("Output File"))

        card = Card(self)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 10, 10)
        card_layout.setSpacing(10)

        self._output_label = QLabel("Will be set after choosing source file")
        self._output_label.setStyleSheet(f"""
            color: {T.TEXT_3};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        self._output_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._output_label.setWordWrap(False)

        self._browse_btn = QPushButton("Change")
        self._browse_btn.setFixedHeight(32)
        self._browse_btn.setFixedWidth(72)
        self._browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.SURFACE_3};
                border: 1.5px solid {T.BORDER};
                border-radius: 8px;
                color: {T.TEXT_2};
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {T.ACCENT};
                color: {T.ACCENT};
            }}
        """)
        self._browse_btn.clicked.connect(self._browse_output)

        card_layout.addWidget(self._output_label, 1)
        card_layout.addWidget(self._browse_btn)
        layout.addWidget(card)

    def set_input_path(self, path: str):
        self._input_path = path
        self._custom_output = None
        self._update_label()

    def set_target_lang(self, lang_code: str):
        self._target_lang = lang_code
        self._update_label()

    def set_suffix(self, suffix: str):
        self._suffix = suffix
        self._update_label()

    def get_output_path(self) -> Optional[str]:
        if self._custom_output:
            return self._custom_output
        if not self._input_path:
            return None
        return str(suggest_output_path(self._input_path, self._target_lang, self._suffix))

    def _update_label(self):
        path = self.get_output_path()
        if path:
            self._output_label.setText(os.path.basename(path))
            self._output_label.setStyleSheet(f"""
                color: {T.TEXT_2};
                font-size: 12px;
                background: transparent;
                border: none;
            """)
        else:
            self._output_label.setText("Will be set after choosing source file")
            self._output_label.setStyleSheet(f"""
                color: {T.TEXT_3};
                font-size: 12px;
                background: transparent;
                border: none;
            """)

    def _browse_output(self):
        if not self._input_path:
            return
        default = self.get_output_path() or ""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Translated SRT", default, "SubRip Subtitles (*.srt)"
        )
        if path:
            self._custom_output = path
            self._output_label.setText(os.path.basename(path))
            self._output_label.setStyleSheet(f"""
                color: {T.TEXT_2};
                font-size: 12px;
                background: transparent;
                border: none;
            """)
