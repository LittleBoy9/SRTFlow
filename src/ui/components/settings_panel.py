"""
Collapsible API settings panel — engine selector, endpoint, API key, cache toggle.
Supports DatPMT, LibreTranslate, DeepL, and Google Translate engines.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLineEdit, QCheckBox, QLabel,
)

from .. import theme as T
from ..widgets import SectionLabel, Card
from ...translator import ENGINES, create_client
from ...config_manager import ConfigManager


# Which fields each engine needs
_ENGINE_FIELDS = {
    "datpmt":         {"endpoint": False, "api_key": False},
    "libretranslate": {"endpoint": True,  "api_key": True},
    "deepl":          {"endpoint": False, "api_key": True},
    "google":         {"endpoint": False, "api_key": True},
}

_ENGINE_PLACEHOLDERS = {
    "libretranslate": {"endpoint": "https://libretranslate.com", "api_key": "Leave blank for free tier"},
    "deepl":          {"endpoint": "", "api_key": "DeepL API key (free keys end with :fx)"},
    "google":         {"endpoint": "", "api_key": "Google Cloud Translation API key"},
}


class SettingsPanel(QWidget):
    """Collapsible panel for API settings."""

    changed = pyqtSignal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toggle header
        self._toggle_btn = QPushButton("⚙  API Settings", self)
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

        # Settings card
        ep_card = Card(self)
        ep_layout = QVBoxLayout(ep_card)
        ep_layout.setContentsMargins(14, 12, 14, 12)
        ep_layout.setSpacing(8)

        # Engine selector
        engine_label = SectionLabel("Translation Engine")
        self._engine_combo = QComboBox()
        for code, display in ENGINES.items():
            self._engine_combo.addItem(display, userData=code)
        saved_engine = self.config.get("translation_engine", "datpmt")
        for i in range(self._engine_combo.count()):
            if self._engine_combo.itemData(i) == saved_engine:
                self._engine_combo.setCurrentIndex(i)
                break
        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)

        # ── API key field (shared by LibreTranslate, DeepL, Google) ──
        self._key_container = QWidget()
        key_layout = QVBoxLayout(self._key_container)
        key_layout.setContentsMargins(0, 8, 0, 0)
        key_layout.setSpacing(6)

        self._key_label = SectionLabel("API Key")
        self._key_edit = QLineEdit(self.config.get("api_key", ""))
        self._key_edit.setPlaceholderText("API key")
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.textChanged.connect(lambda v: self.config.set("api_key", v))

        key_layout.addWidget(self._key_label)
        key_layout.addWidget(self._key_edit)

        # ── Endpoint field (LibreTranslate only) ──
        self._endpoint_container = QWidget()
        ep_field_layout = QVBoxLayout(self._endpoint_container)
        ep_field_layout.setContentsMargins(0, 8, 0, 0)
        ep_field_layout.setSpacing(6)

        ep_field_label = SectionLabel("API Endpoint")
        ep_row = QHBoxLayout()
        self._endpoint_edit = QLineEdit(self.config.get("api_endpoint", "https://libretranslate.com"))
        self._endpoint_edit.setPlaceholderText("https://libretranslate.com")
        self._endpoint_edit.textChanged.connect(self._on_endpoint_changed)

        self._test_btn = QPushButton("Test")
        self._test_btn.setFixedWidth(60)
        self._test_btn.setFixedHeight(36)
        self._test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.SURFACE_3};
                border: 1.5px solid {T.BORDER};
                border-radius: 8px;
                color: {T.TEXT_2};
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {T.ACCENT};
                color: {T.ACCENT};
                background: {T.ACCENT_GLOW};
            }}
        """)
        self._test_btn.clicked.connect(self._test_connection)
        ep_row.addWidget(self._endpoint_edit)
        ep_row.addWidget(self._test_btn)

        ep_field_layout.addWidget(ep_field_label)
        ep_field_layout.addLayout(ep_row)

        # ── Engine info label ──
        self._engine_info = QLabel("")
        self._engine_info.setStyleSheet(f"color: {T.TEXT_3}; font-size: 11px; background: transparent;")
        self._engine_info.setWordWrap(True)

        # Cache checkbox
        self._cache_check = QCheckBox("Enable translation cache")
        self._cache_check.setChecked(self.config.get("cache_enabled", True))
        self._cache_check.setStyleSheet(f"""
            QCheckBox {{
                color: {T.TEXT_2};
                font-size: 12px;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 15px; height: 15px;
                border: 1.5px solid {T.BORDER};
                border-radius: 4px;
                background: {T.SURFACE_2};
            }}
            QCheckBox::indicator:checked {{
                background: {T.ACCENT};
                border-color: {T.ACCENT};
            }}
        """)
        self._cache_check.toggled.connect(lambda v: self.config.set("cache_enabled", v))

        ep_layout.addWidget(engine_label)
        ep_layout.addWidget(self._engine_combo)
        ep_layout.addWidget(self._engine_info)
        ep_layout.addWidget(self._endpoint_container)
        ep_layout.addWidget(self._key_container)
        ep_layout.addWidget(self._cache_check)

        content_layout.addWidget(ep_card)

        root.addWidget(self._toggle_btn)
        root.addWidget(self._content)
        self._content.setVisible(False)

        # Set initial field visibility
        self._update_fields_for_engine(saved_engine)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        icon = "▾" if self._expanded else "⚙"
        self._toggle_btn.setText(f"{icon}  API Settings")

    def _on_engine_changed(self):
        engine = self._engine_combo.currentData()
        self.config.set("translation_engine", engine)
        self._update_fields_for_engine(engine)
        self.changed.emit()

    def _update_fields_for_engine(self, engine: str):
        """Show/hide fields and update placeholders based on selected engine."""
        fields = _ENGINE_FIELDS.get(engine, {"endpoint": False, "api_key": False})
        placeholders = _ENGINE_PLACEHOLDERS.get(engine, {})

        self._endpoint_container.setVisible(fields["endpoint"])
        self._key_container.setVisible(fields["api_key"])

        if fields["api_key"]:
            ph = placeholders.get("api_key", "API key")
            self._key_edit.setPlaceholderText(ph)
            # Update label based on engine
            if engine == "deepl":
                self._key_label.setText("DeepL API Key")
            elif engine == "google":
                self._key_label.setText("Google API Key")
            else:
                self._key_label.setText("API Key (optional)")

        if fields["endpoint"]:
            ph = placeholders.get("endpoint", "https://...")
            self._endpoint_edit.setPlaceholderText(ph)

        # Engine info
        info_map = {
            "datpmt": "Free engine, no API key needed. Good for basic translations.",
            "libretranslate": "Free tier or self-hosted. Set a custom endpoint for your own instance.",
            "deepl": "Industry-leading translation quality. Get a free API key at deepl.com/pro.",
            "google": "Widest language coverage. Requires a Google Cloud Translation API key.",
        }
        self._engine_info.setText(info_map.get(engine, ""))

    def _on_endpoint_changed(self, value: str):
        self.config.set("api_endpoint", value)
        self.changed.emit()

    def _test_connection(self):
        self._test_btn.setText("…")
        self._test_btn.setEnabled(False)

        engine = self._engine_combo.currentData()
        client = create_client(
            engine,
            endpoint=self._endpoint_edit.text().strip(),
            api_key=self._key_edit.text().strip(),
        )

        def do_test():
            return client.test_connection()

        class Tester(QThread):
            result = pyqtSignal(bool)
            def run(self_):
                self_.result.emit(do_test())

        self._tester = Tester(self)
        self._tester.result.connect(self._on_test_result)
        self._tester.start()

    def _on_test_result(self, ok: bool):
        self._test_btn.setEnabled(True)
        if ok:
            self._test_btn.setText("✓")
            self._test_btn.setStyleSheet(self._test_btn.styleSheet() +
                f"QPushButton {{ color: {T.SUCCESS}; border-color: {T.SUCCESS}; }}")
        else:
            self._test_btn.setText("✗")
            self._test_btn.setStyleSheet(self._test_btn.styleSheet() +
                f"QPushButton {{ color: {T.ERROR}; border-color: {T.ERROR}; }}")
        QTimer.singleShot(2000, lambda: self._test_btn.setText("Test"))

    def get_engine(self) -> str:
        return self._engine_combo.currentData()

    def get_endpoint(self) -> str:
        return self._endpoint_edit.text().strip()

    def get_api_key(self) -> str:
        return self._key_edit.text().strip()
