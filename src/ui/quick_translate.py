"""
Quick Translate dialog — minimal popup for translating subtitle items
directly on the DaVinci Resolve timeline.

User flow:
1. SRTFlow detects subtitle items on the active timeline
2. User picks subtitle track (multi-track support)
3. User selects which items to translate (all or a subset)
4. Picks source/target language
5. Hits Translate — translation runs in background thread
6. Preview dialog shows original vs translated side-by-side
7. User confirms → translations written to timeline + undo entry stored
"""

from __future__ import annotations
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QCheckBox,
    QApplication, QWidget, QComboBox,
)

from . import theme as T
from .widgets import SectionLabel, LogPanel, ProgressPanel, StatusBadge
from .components.lang_selector import LangSelector
from .worker import TimelineTranslationWorker
from .preview_dialog import PreviewDialog
from ..resolve_bridge import ResolveBridge, TimelineSubtitleItem
from ..translator import create_client
from ..cache import TranslationCache
from ..config_manager import ConfigManager
from ..undo import UndoManager, UndoEntry


class QuickTranslateDialog(QDialog):
    """
    Minimal dialog for translating timeline subtitles in-place.
    Launched from the Scripts menu when DaVinci is running.
    """

    def __init__(self, resolve: ResolveBridge, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.resolve = resolve
        self.config = config
        self.cache = TranslationCache(enabled=config.get("cache_enabled", True))
        self.undo = UndoManager()
        self._items: List[TimelineSubtitleItem] = []
        self._worker: Optional[TimelineTranslationWorker] = None
        self._skip_count = 0
        self._glossary = self._load_glossary()

        self._build_window()
        self._build_ui()
        self._load_timeline_items()

    def _build_window(self):
        self.setWindowTitle("SRTFlow — Quick Translate")
        self.setFixedWidth(560)
        self.setMinimumHeight(640)
        self.setStyleSheet(T.STYLESHEET + f"""
            QDialog {{
                background-color: {T.BG};
            }}
        """)

        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(sg.center().x() - 280, sg.center().y() - 320)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        # ── Header ──
        header_row = QHBoxLayout()
        title = QLabel("Quick Translate")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {T.TEXT_1};
            background: transparent;
        """)
        self._timeline_badge = StatusBadge("Loading…", "info")
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self._timeline_badge)
        root.addLayout(header_row)

        desc = QLabel("Select subtitle blocks from the timeline to translate. You'll preview before applying.")
        desc.setStyleSheet(f"color: {T.TEXT_2}; font-size: 12px; background: transparent;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        # ── Track selector ──
        track_row = QHBoxLayout()
        track_lbl = QLabel("Subtitle Track")
        track_lbl.setStyleSheet(f"color: {T.TEXT_2}; font-size: 12px; background: transparent;")
        self._track_combo = QComboBox()
        self._track_combo.setFixedHeight(34)
        self._track_combo.currentIndexChanged.connect(lambda _: self._load_timeline_items())
        track_row.addWidget(track_lbl)
        track_row.addWidget(self._track_combo, 1)
        root.addLayout(track_row)

        # ── Subtitle list ──
        root.addWidget(SectionLabel("Timeline Subtitles"))

        # Select all checkbox
        select_row = QHBoxLayout()
        self._select_all_cb = QCheckBox("Select All")
        self._select_all_cb.setChecked(True)
        self._select_all_cb.setStyleSheet(f"""
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
        self._select_all_cb.toggled.connect(self._toggle_select_all)
        self._item_count_label = QLabel("")
        self._item_count_label.setStyleSheet(f"color: {T.TEXT_3}; font-size: 11px; background: transparent;")
        select_row.addWidget(self._select_all_cb)
        select_row.addStretch()
        select_row.addWidget(self._item_count_label)
        root.addLayout(select_row)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._list.setMinimumHeight(160)
        self._list.setMaximumHeight(220)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {T.SURFACE};
                border: 1.5px solid {T.BORDER};
                border-radius: 10px;
                padding: 6px;
                color: {T.TEXT_1};
                font-family: {T.FONT_MONO};
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {T.ACCENT_GLOW};
                color: {T.TEXT_1};
            }}
            QListWidget::item:hover {{
                background-color: {T.SURFACE_2};
            }}
        """)
        root.addWidget(self._list)

        # ── Language selector ──
        self._lang = LangSelector(
            source_code=self.config.get("source_lang", "auto"),
            target_code=self.config.get("target_lang", "es"),
        )
        root.addWidget(self._lang)

        # ── Log panel ──
        root.addWidget(SectionLabel("Log"))
        self._log = LogPanel()
        self._log.setMaximumHeight(120)
        root.addWidget(self._log)

        # ── Progress ──
        self._progress = ProgressPanel()
        root.addWidget(self._progress)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedHeight(40)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.SURFACE_2};
                border: 1.5px solid {T.BORDER};
                border-radius: 10px;
                color: {T.TEXT_2};
                font-size: 13px;
                font-weight: 500;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                border-color: {T.ACCENT};
                color: {T.ACCENT};
                background: {T.ACCENT_GLOW};
            }}
        """)
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._load_timeline_items)

        # Undo button
        self._undo_btn = QPushButton("Undo Last")
        self._undo_btn.setFixedHeight(40)
        self._undo_btn.setVisible(self.undo.can_undo)
        self._undo_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.SURFACE_2};
                border: 1.5px solid {T.WARNING};
                border-radius: 10px;
                color: {T.WARNING};
                font-size: 13px;
                font-weight: 500;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {T.WARNING_BG};
            }}
        """)
        self._undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._undo_btn.clicked.connect(self._perform_undo)

        self._translate_btn = QPushButton("Translate Selected")
        self._translate_btn.setFixedHeight(48)
        self._translate_btn.setStyleSheet(f"""
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
            QPushButton:disabled {{
                background: {T.SURFACE_3};
                color: {T.TEXT_3};
            }}
        """)
        self._translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._translate_btn.clicked.connect(self._start_translation)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("role", "danger")
        self._cancel_btn.setFixedHeight(40)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_translation)

        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._undo_btn)
        btn_row.addWidget(self._translate_btn, 1)
        root.addLayout(btn_row)
        root.addWidget(self._cancel_btn)

    # ── Timeline loading ──────────────────────────────────────────────────

    def _get_selected_track(self) -> int:
        data = self._track_combo.currentData()
        return data if data else 1

    def _load_timeline_items(self):
        self._list.clear()
        self._items = []

        self.resolve.refresh_timeline()

        if not self.resolve.is_available():
            self._timeline_badge.setText("No Timeline")
            self._log.add_error("DaVinci Resolve timeline not found.")
            self._item_count_label.setText("0 items")
            return

        tl_name = self.resolve.get_timeline_name() or "Unknown"
        self._timeline_badge.setText(tl_name)

        # Populate track combo
        tracks = self.resolve.get_subtitle_track_names()
        if not tracks:
            self._track_combo.clear()
            self._log.add_warning("No subtitle tracks found on the timeline.")
            self._item_count_label.setText("0 items")
            return

        prev_track = self._get_selected_track()
        self._track_combo.blockSignals(True)
        self._track_combo.clear()
        for idx, name in tracks.items():
            self._track_combo.addItem(f"Track {idx}: {name}", userData=idx)
        for i in range(self._track_combo.count()):
            if self._track_combo.itemData(i) == prev_track:
                self._track_combo.setCurrentIndex(i)
                break
        self._track_combo.blockSignals(False)

        track_index = self._get_selected_track()
        self._items = self.resolve.get_subtitle_items(track_index=track_index)

        for item in self._items:
            preview = item.text[:60] + ("…" if len(item.text) > 60 else "")
            display = f"[{item.index:03d}]  {item.start}  {preview}"
            list_item = QListWidgetItem(display)
            list_item.setData(Qt.ItemDataRole.UserRole, item.index)
            self._list.addItem(list_item)

        if self._select_all_cb.isChecked():
            self._list.selectAll()

        count = len(self._items)
        self._item_count_label.setText(f"{count} item{'s' if count != 1 else ''}")
        self._log.add_success(f"Loaded {count} subtitle{'s' if count != 1 else ''} from \"{tl_name}\"")

        # Update undo button visibility
        self._undo_btn.setVisible(self.undo.can_undo)

    def _toggle_select_all(self, checked: bool):
        if checked:
            self._list.selectAll()
        else:
            self._list.clearSelection()

    def _get_selected_items(self) -> List[TimelineSubtitleItem]:
        selected_indices = set()
        for list_item in self._list.selectedItems():
            idx = list_item.data(Qt.ItemDataRole.UserRole)
            selected_indices.add(idx)
        return [item for item in self._items if item.index in selected_indices]

    # ── Translation ───────────────────────────────────────────────────────

    def _start_translation(self):
        selected = self._get_selected_items()
        if not selected:
            self._log.add_warning("No subtitle items selected.")
            return

        source = self._lang.source_code()
        target = self._lang.target_code()

        if source == target:
            self._log.add_warning("Source and target languages are the same.")
            return

        self.config.set("source_lang", source)
        self.config.set("target_lang", target)

        engine = self.config.get("translation_engine", "datpmt")
        client = create_client(
            engine=engine,
            endpoint=self.config.get("api_endpoint", "https://libretranslate.com"),
            api_key=self.config.get("api_key", ""),
            timeout=self.config.get("timeout", 30),
            max_retries=self.config.get("max_retries", 3),
            retry_delay=self.config.get("retry_delay", 1.5),
        )

        self.cache.enabled = self.config.get("cache_enabled", True)
        self._skip_count = 0

        self._worker = TimelineTranslationWorker(
            items=selected,
            source_lang=source,
            target_lang=target,
            client=client,
            cache=self.cache,
            batch_size=self.config.get("batch_size", 10),
            glossary=self._glossary,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.line_done.connect(self._on_line_done)
        self._worker.line_skipped.connect(self._on_line_skipped)
        self._worker.finished.connect(self._on_translation_ready)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)

        self._log.clear_log()
        self._progress.reset()
        src_name = self._lang.source_name()
        tgt_name = self._lang.target_name()
        self._log.add_info(f"Translating {len(selected)} items: {src_name} → {tgt_name}")

        self._set_translating(True)
        self._worker.start()

    def _cancel_translation(self):
        if self._worker:
            self._worker.cancel()

    def _set_translating(self, active: bool):
        self._translate_btn.setEnabled(not active)
        self._translate_btn.setText("Translating…" if active else "Translate Selected")
        self._cancel_btn.setVisible(active)
        self._refresh_btn.setEnabled(not active)
        self._undo_btn.setEnabled(not active)
        self._list.setEnabled(not active)
        self._lang.set_enabled(not active)
        self._track_combo.setEnabled(not active)

    def _on_progress(self, current: int, total: int):
        self._progress.set_progress(current, total)

    def _on_line_done(self, index: int, original: str, translated: str):
        self._log.add_line_result(index, original, translated)

    def _on_line_skipped(self, index: int, text: str, error_msg: str):
        short = (text[:30] + "…") if len(text) > 30 else text
        self._log.add_warning(f"[{index:03d}] Skipped: {short} — {error_msg}")
        self._skip_count += 1

    def _on_translation_ready(self, results: list):
        """Translation done — show preview dialog before writing to timeline."""
        self._set_translating(False)
        total = len(results)
        self._progress.set_done(total)

        if not results:
            self._log.add_warning("No translations to apply.")
            return

        self._log.add_info("Opening preview…")

        # Show preview dialog
        preview = PreviewDialog(
            results=results,
            source_lang=self._lang.source_code(),
            target_lang=self._lang.target_code(),
            skip_count=self._skip_count,
            parent=self,
        )

        if preview.exec() == QDialog.DialogCode.Accepted:
            self._apply_to_timeline(results)
        else:
            self._log.add_warning("Translation discarded — no changes applied.")
            self._translate_btn.setText("Translate Selected")

    def _apply_to_timeline(self, results: list):
        """Write translations to timeline and store undo entry."""
        tl_name = self.resolve.get_timeline_name() or "Unknown"
        track_index = self._get_selected_track()

        # Store undo entry (original texts)
        originals = {}
        for item, original, translated in results:
            if original != translated:
                originals[item.index] = original

        if originals:
            self.undo.push(UndoEntry(
                timeline_name=tl_name,
                track_index=track_index,
                items=originals,
            ))

        # Write translations to timeline
        success = 0
        fail = 0
        for item, original, translated in results:
            if original != translated:
                if item.set_text(translated):
                    success += 1
                else:
                    fail += 1

        if fail == 0:
            self._log.add_success(f"Applied {success} translation{'s' if success != 1 else ''} to timeline.")
            self._translate_btn.setText("✓ Done")
        else:
            self._log.add_warning(f"Applied {success}, failed {fail}.")
            self._translate_btn.setText("✓ Done (with errors)")

        QTimer.singleShot(3000, lambda: self._translate_btn.setText("Translate Selected"))
        self._undo_btn.setVisible(True)

        # Refresh list to show updated text
        QTimer.singleShot(500, self._load_timeline_items)

    # ── Undo ──────────────────────────────────────────────────────────────

    def _perform_undo(self):
        entry = self.undo.peek()
        if not entry:
            self._log.add_warning("Nothing to undo.")
            return

        tl_name = self.resolve.get_timeline_name() or ""
        if entry.timeline_name != tl_name:
            self._log.add_warning(
                f"Undo entry is for timeline \"{entry.timeline_name}\" "
                f"but current timeline is \"{tl_name}\". Proceeding anyway…"
            )

        # Get current items from the track
        items = self.resolve.get_subtitle_items(track_index=entry.track_index)
        items_by_index = {item.index: item for item in items}

        restored = 0
        failed = 0
        for idx, original_text in entry.items.items():
            item = items_by_index.get(idx)
            if item and item.set_text(original_text):
                restored += 1
            else:
                failed += 1

        self.undo.pop()  # Remove from history

        if failed == 0:
            self._log.add_success(f"Undo complete — restored {restored} subtitle{'s' if restored != 1 else ''}.")
        else:
            self._log.add_warning(f"Undo: restored {restored}, failed {failed}.")

        self._undo_btn.setVisible(self.undo.can_undo)
        QTimer.singleShot(300, self._load_timeline_items)

    # ── Error handlers ────────────────────────────────────────────────────

    def _on_error(self, msg: str):
        self._set_translating(False)
        self._log.add_error(msg)
        self._progress.set_error("Translation failed")

    def _on_cancelled(self):
        self._set_translating(False)
        self._log.add_warning("Translation cancelled.")
        self._progress.reset()

    def _load_glossary(self) -> dict:
        from pathlib import Path
        import json
        gpath = Path(__file__).parent.parent.parent / "glossary.json"
        try:
            data = json.loads(gpath.read_text(encoding="utf-8"))
            return data.get("terms", {})
        except Exception:
            return {}
