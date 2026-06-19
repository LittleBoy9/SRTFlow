"""
SRTFlow — Main application window.
Built with PyQt6. Dark, modern, DaVinci-inspired aesthetic.

This is the full-featured window for file-based SRT translation.
For timeline-based quick translation, see quick_translate.py.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QFileDialog,
    QScrollArea, QMessageBox,
)

from . import theme as T
from .widgets import (
    Divider, SectionLabel, LogPanel, ProgressPanel, FileDropZone,
    ToastManager, ShortcutHelpOverlay, Spinner,
)
from .components.header import build_header
from .components.lang_selector import LangSelector
from .components.settings_panel import SettingsPanel
from .components.file_panel import FileOutputPanel
from .components.glossary_editor import GlossaryEditor
from .worker import TranslationWorker
from ..srt_parser import parse_srt, SubtitleEntry
from ..translator import create_client
from ..cache import TranslationCache
from ..config_manager import ConfigManager
from ..resolve_bridge import ResolveBridge
from ..progress_store import ProgressStore
from ..subtitle_validator import validate_entries
from ..export import export_by_extension, get_export_filter


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class SRTFlowWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.cache = TranslationCache(enabled=self.config.get("cache_enabled", True))
        self.resolve = ResolveBridge()
        self._worker: Optional[TranslationWorker] = None
        self._entries: List[SubtitleEntry] = []
        self._original_entries: List[SubtitleEntry] = []  # kept for export comparison
        self._translated_entries: List[SubtitleEntry] = []  # populated after translation
        self._input_path: Optional[str] = None
        self._batch_paths: List[str] = []
        self._batch_index: int = 0
        self._progress_store = ProgressStore()
        self._last_output_path: Optional[str] = None

        self._load_glossary()
        self._build_window()
        self._build_ui()
        self._connect_signals()

        # Toast notification manager
        self.toast = ToastManager(self)

        # Shortcut help overlay
        self._shortcut_help = ShortcutHelpOverlay(self)

        # Welcome state — don't add to log, let empty state show
        if self.resolve.is_available():
            tl = self.resolve.get_timeline_name()
            self.toast.show(f"DaVinci connected — {tl}", "success")
        else:
            self.toast.show("Running in standalone mode", "info")

    # ── Setup ──────────────────────────────────────────────────────────────

    def _build_window(self):
        self.setWindowTitle("SRTFlow")
        self.setFixedWidth(660)
        self.setMinimumHeight(720)
        self.setStyleSheet(T.STYLESHEET + f"QMainWindow {{ background-color: {T.BG}; }}")

        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(sg.center().x() - 330, sg.center().y() - 380)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        central.setStyleSheet(f"background-color: {T.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ──
        header = build_header(self.resolve.is_available(), self.resolve.get_timeline_name())
        root.addWidget(header)

        # ── Scrollable content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background: {T.BG}; border: none; }}")

        content = QWidget()
        content.setStyleSheet(f"background: {T.BG};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 28)
        content_layout.setSpacing(18)

        self._build_content(content_layout)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _build_content(self, layout: QVBoxLayout):
        # ── File drop zone ──
        self.drop_zone = FileDropZone()
        layout.addWidget(self.drop_zone)

        # ── Language selector ──
        self.lang_selector = LangSelector(
            source_code=self.config.get("source_lang", "auto"),
            target_code=self.config.get("target_lang", "es"),
        )
        layout.addWidget(self.lang_selector)

        # ── Output file panel ──
        self.file_output = FileOutputPanel()
        self.file_output.set_suffix(self.config.get("output_suffix", "_{lang}"))
        layout.addWidget(self.file_output)

        # ── Settings ──
        self.settings_panel = SettingsPanel(self.config)
        layout.addWidget(self.settings_panel)

        # ── Glossary editor ──
        self.glossary_editor = GlossaryEditor()
        self.glossary_editor.glossary_changed.connect(self._on_glossary_changed)
        layout.addWidget(self.glossary_editor)

        layout.addWidget(Divider())

        # ── Log panel ──
        layout.addWidget(SectionLabel("Translation Log"))
        self.log = LogPanel()
        layout.addWidget(self.log)

        # ── Progress ──
        self.progress = ProgressPanel()
        layout.addWidget(self.progress)

        layout.addSpacing(4)

        # ── Translate button with inline spinner ──
        translate_container = QWidget()
        translate_layout = QHBoxLayout(translate_container)
        translate_layout.setContentsMargins(0, 0, 0, 0)
        translate_layout.setSpacing(0)

        self._btn_spinner = Spinner(size=20, color="#ffffff", stroke=2)
        self._btn_spinner.setVisible(False)

        self.translate_btn = QPushButton("Translate")
        self.translate_btn.setProperty("role", "primary")
        self.translate_btn.setFixedHeight(52)
        self.translate_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ba4ff, stop:1 #3d86e8);
                color: #ffffff;
                border: none;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.4px;
                border-radius: 13px;
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
        self.translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.translate_btn.setToolTip("Start translation  (Ctrl+T)")

        translate_layout.addWidget(self.translate_btn)
        layout.addWidget(translate_container)

        # ── Cancel button (hidden initially) ──
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("role", "danger")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setToolTip("Cancel translation  (Escape)")
        layout.addWidget(self.cancel_btn)

        # ── Post-translation action row (Export + Validate) ──
        self._action_row = QWidget()
        action_layout = QHBoxLayout(self._action_row)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)

        self._export_btn = QPushButton("Export As...")
        self._export_btn.setFixedHeight(40)
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setToolTip("Export to VTT, ASS, TTML, or CSV  (Ctrl+E)")
        self._export_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {T.BORDER};
                border-radius: 10px;
                color: {T.TEXT_2};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {T.ACCENT};
                color: {T.ACCENT};
                background: {T.ACCENT_GLOW};
            }}
        """)
        self._export_btn.clicked.connect(self._export_translation)

        self._validate_btn = QPushButton("Check Limits")
        self._validate_btn.setFixedHeight(40)
        self._validate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._validate_btn.setToolTip("Check character/line length limits")
        self._validate_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {T.BORDER};
                border-radius: 10px;
                color: {T.TEXT_2};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {T.WARNING};
                color: {T.WARNING};
                background: {T.WARNING_BG};
            }}
        """)
        self._validate_btn.clicked.connect(self._validate_subtitles)

        action_layout.addWidget(self._export_btn, 1)
        action_layout.addWidget(self._validate_btn, 1)
        self._action_row.setVisible(False)
        layout.addWidget(self._action_row)

        # ── Quick Translate button (only when DaVinci available) ──
        if self.resolve.is_available():
            self._quick_btn = QPushButton("⚡ Quick Translate Timeline")
            self._quick_btn.setFixedHeight(44)
            self._quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._quick_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1.5px solid {T.ACCENT};
                    border-radius: 12px;
                    color: {T.ACCENT};
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {T.ACCENT_GLOW};
                }}
            """)
            self._quick_btn.setToolTip("Translate timeline subtitles  (Ctrl+Shift+T)")
            self._quick_btn.clicked.connect(self._open_quick_translate)
            layout.addWidget(self._quick_btn)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _load_glossary(self):
        gpath = Path(__file__).parent.parent.parent / "glossary.json"
        try:
            import json
            data = json.loads(gpath.read_text(encoding="utf-8"))
            self._glossary = data.get("terms", {})
        except Exception:
            self._glossary = {}

    # ── Signal wiring ─────────────────────────────────────────────────────

    def _connect_signals(self):
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        self.drop_zone.files_dropped.connect(self._on_batch_files_selected)
        self.drop_zone.clicked.connect(self._browse_input)

        self.lang_selector.lang_changed.connect(self._on_lang_changed)

        self.translate_btn.clicked.connect(self._start_translation)
        self.cancel_btn.clicked.connect(self._cancel_translation)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self._start_translation)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._browse_input)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self).activated.connect(self._shortcut_quick_translate)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._on_escape)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._shortcut_undo)
        QShortcut(QKeySequence("Ctrl+/"), self).activated.connect(lambda: self._shortcut_help.toggle())
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self._export_translation)

    def _on_file_selected(self, path: str):
        self._input_path = path
        try:
            self._entries = parse_srt(path)
            self._original_entries = list(self._entries)
            count = len(self._entries)
            self.log.add_success(f"Loaded {count} subtitle line{'s' if count != 1 else ''} from {os.path.basename(path)}")
            self.file_output.set_input_path(path)
            self.file_output.set_target_lang(self.lang_selector.target_code())

            # Run subtitle validation
            result = validate_entries(self._entries)
            if result.warnings:
                warn_count = len(result.warnings)
                self.log.add_warning(f"Subtitle check: {warn_count} issue{'s' if warn_count != 1 else ''} found (use 'Check Limits' for details)")

            # Check for resumable progress
            target = self.lang_selector.target_code()
            if self._progress_store.has_progress(path, target):
                state = self._progress_store.get_progress(path, target)
                if state and state.completed_index < state.total_entries:
                    pct = int(state.completed_index / state.total_entries * 100)
                    self.log.add_info(
                        f"Resumable progress found: {state.completed_index}/{state.total_entries} "
                        f"({pct}%) — click Translate to resume"
                    )
        except Exception as e:
            self.log.add_error(f"Failed to parse SRT: {e}")
            self._entries = []

    def _browse_input(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open SRT File(s)", "", "SubRip Subtitles (*.srt);;All Files (*)"
        )
        if len(paths) == 1:
            self.drop_zone.set_file(paths[0])
            self._on_file_selected(paths[0])
        elif len(paths) > 1:
            self.drop_zone.set_files(paths)
            self._on_batch_files_selected(paths)

    def _on_batch_files_selected(self, paths: list):
        """Multiple SRT files selected for batch processing."""
        self._batch_paths = paths
        self._batch_index = 0
        # Load the first file as the active one
        self._on_file_selected(paths[0])
        self.log.add_info(f"Batch mode: {len(paths)} files queued for translation")

    def _on_lang_changed(self, source: str, target: str):
        self.config.set("source_lang", source)
        self.config.set("target_lang", target)
        self.file_output.set_target_lang(target)

    def _on_glossary_changed(self, terms: dict):
        self._glossary = terms

    # ── Translation ───────────────────────────────────────────────────────

    def _start_translation(self):
        if not self._entries:
            if not self._input_path:
                self.log.add_warning("Please select an SRT file first.")
            else:
                self.log.add_warning("No subtitle entries found in file.")
            return

        output_path = self.file_output.get_output_path()
        if not output_path:
            self.log.add_error("Cannot determine output path.")
            return

        source = self.lang_selector.source_code()
        target = self.lang_selector.target_code()
        engine = self.settings_panel.get_engine()

        if source == target:
            self.log.add_warning("Source and target languages are the same.")
            return

        self.cache.enabled = self.config.get("cache_enabled", True)

        # Check for resumable progress
        resume_from = 0
        resumed_texts = {}
        if self._input_path and self._progress_store.has_progress(self._input_path, target):
            state = self._progress_store.get_progress(self._input_path, target)
            if state:
                resumed_texts = state.translated_texts
                self.log.add_info(f"Resuming from previous progress ({len(resumed_texts)} cached translations)")

        client = create_client(
            engine=engine,
            endpoint=self.settings_panel.get_endpoint(),
            api_key=self.settings_panel.get_api_key(),
            timeout=self.config.get("timeout", 30),
            max_retries=self.config.get("max_retries", 3),
            retry_delay=self.config.get("retry_delay", 1.5),
        )

        self._worker = TranslationWorker(
            entries=self._entries,
            source_lang=source,
            target_lang=target,
            output_path=output_path,
            client=client,
            cache=self.cache,
            batch_size=self.config.get("batch_size", 10),
            glossary=self._glossary,
            input_path=self._input_path or "",
            engine=engine,
            resume_from=resume_from,
            resumed_texts=resumed_texts,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.line_done.connect(self._on_line_done)
        self._worker.line_skipped.connect(self._on_line_skipped)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.language_detected.connect(self._on_language_detected)
        self._worker.quality_report.connect(self._on_quality_report)

        self.log.clear_log()
        self.progress.reset()
        src_name = self.lang_selector.source_name()
        tgt_name = self.lang_selector.target_name()
        self.log.add_info(f"Translating {len(self._entries)} lines: {src_name} → {tgt_name}")
        if engine == "claude":
            self.log.add_info("Using Claude AI — context-aware translation")

        self._set_translating(True)
        self._worker.start()

    def _cancel_translation(self):
        if self._worker:
            self._worker.cancel()

    def _set_translating(self, active: bool):
        self.translate_btn.setEnabled(not active)
        if active:
            self.translate_btn.setText("  Translating…")
            self._btn_spinner.start()
        else:
            self.translate_btn.setText("Translate")
            self._btn_spinner.stop()
        self.cancel_btn.setVisible(active)
        self.drop_zone.setEnabled(not active)
        self.lang_selector.set_enabled(not active)

    def _on_progress(self, current: int, total: int):
        self.progress.set_progress(current, total)

    def _on_language_detected(self, lang_code: str):
        from ..translator import LANG_CODE_TO_NAME
        name = LANG_CODE_TO_NAME.get(lang_code, lang_code)
        self.log.add_info(f"Detected source language: {name}")

    def _on_line_done(self, index: int, original: str, translated: str):
        self.log.add_line_result(index, original, translated)

    def _on_line_skipped(self, index: int, text: str, error_msg: str):
        short = (text[:30] + "…") if len(text) > 30 else text
        self.log.add_warning(f"[{index:03d}] Skipped: {short} — {error_msg}")

    def _on_finished(self, output_path: str, success_count: int, skip_count: int):
        self._last_output_path = output_path

        # Load translated entries for export
        try:
            self._translated_entries = parse_srt(output_path)
        except Exception:
            self._translated_entries = []

        if skip_count > 0:
            self.log.add_warning(f"Saved to: {output_path} ({skip_count} line{'s' if skip_count != 1 else ''} skipped)")
        else:
            self.log.add_success(f"Saved to: {output_path}")

        # Batch mode: continue to next file
        if self._batch_paths and self._batch_index < len(self._batch_paths) - 1:
            self._batch_index += 1
            next_path = self._batch_paths[self._batch_index]
            self.log.add_info(f"Batch [{self._batch_index + 1}/{len(self._batch_paths)}] Starting: {os.path.basename(next_path)}")
            self._on_file_selected(next_path)
            QTimer.singleShot(300, self._start_translation)
            return

        # All done (single or batch complete)
        self._set_translating(False)
        self.progress.set_done(len(self._entries))

        # Show action row (Export + Validate)
        self._action_row.setVisible(True)

        if self._batch_paths and len(self._batch_paths) > 1:
            self.toast.show(f"Batch complete — {len(self._batch_paths)} files translated", "success")
            self.log.add_success(f"Batch complete: {len(self._batch_paths)} files translated")
            self._batch_paths = []
            self._batch_index = 0
        else:
            self.toast.show("Translation complete", "success")
        self.translate_btn.setText("Done")
        QTimer.singleShot(3000, lambda: self.translate_btn.setText("Translate"))

    def _on_error(self, msg: str):
        self._set_translating(False)
        self.log.add_error(msg)
        self.progress.set_error("Translation failed")
        self.toast.show("Translation failed", "error")

    def _on_cancelled(self):
        self._set_translating(False)
        self._batch_paths = []
        self._batch_index = 0
        self.log.add_warning("Translation cancelled. Progress saved — click Translate to resume.")
        self.progress.reset()

    # ── Shortcuts ───────────────────────────────────────────────────────

    def _on_escape(self):
        if self._shortcut_help.isVisible():
            self._shortcut_help.hide()
        else:
            self._cancel_translation()

    def _shortcut_quick_translate(self):
        if self.resolve.is_available():
            self._open_quick_translate()

    def _shortcut_undo(self):
        """Ctrl+Z — undo last timeline translation if available."""
        from ..undo import UndoManager
        mgr = UndoManager()
        if not mgr.can_undo:
            return
        entry = mgr.pop()
        if entry and self.resolve.is_available():
            items = self.resolve.get_subtitle_items(entry.track_index)
            restored = 0
            for item in items:
                if item.index in entry.items:
                    item.set_text(entry.items[item.index])
                    restored += 1
            self.log.add_success(f"Undo: restored {restored} subtitle(s) on track {entry.track_index}")

    # ── Quality Report ──────────────────────────────────────────────────

    def _on_quality_report(self, report):
        """Display quality scoring results in the log."""
        if not report or report.total_count == 0:
            return

        self.log.add_info(
            f"Quality score: {report.average_score:.0f}/100 "
            f"({report.flagged_count} flagged out of {report.total_count})"
        )

        # Show individual flags for low-scoring lines
        for ls in report.scores:
            if ls.score < 70:
                for flag in ls.flags:
                    if flag.severity == "error":
                        self.log.add_error(f"Quality: {flag.message}")
                    else:
                        self.log.add_warning(f"Quality: {flag.message}")

        if report.average_score >= 90:
            self.toast.show(f"Quality: {report.average_score:.0f}/100 — Excellent", "success")
        elif report.average_score >= 70:
            self.toast.show(f"Quality: {report.average_score:.0f}/100 — Good ({report.flagged_count} flagged)", "info")
        else:
            self.toast.show(f"Quality: {report.average_score:.0f}/100 — Review recommended", "warning")

    # ── Export ────────────────────────────────────────────────────────────

    def _export_translation(self):
        """Export the last translation to another format."""
        if not self._translated_entries:
            self.log.add_warning("No translation available to export. Translate first.")
            return

        filter_str = get_export_filter()
        default_dir = os.path.dirname(self._last_output_path) if self._last_output_path else ""
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Translation", default_dir, filter_str,
        )
        if not path:
            return

        try:
            export_by_extension(
                entries=self._translated_entries,
                path=path,
                original_entries=self._original_entries,
                source_lang=self.lang_selector.source_code(),
                target_lang=self.lang_selector.target_code(),
            )
            ext = Path(path).suffix.upper().lstrip(".")
            self.log.add_success(f"Exported as {ext}: {os.path.basename(path)}")
            self.toast.show(f"Exported to {ext}", "success")
        except Exception as e:
            self.log.add_error(f"Export failed: {e}")
            self.toast.show("Export failed", "error")

    # ── Subtitle Validation ──────────────────────────────────────────────

    def _validate_subtitles(self):
        """Run subtitle validation and show results."""
        entries = self._translated_entries if self._translated_entries else self._entries
        if not entries:
            self.log.add_warning("No subtitles to validate.")
            return

        result = validate_entries(entries)

        if not result.warnings:
            self.log.add_success(f"All {result.total_checked} subtitles pass length/speed checks")
            self.toast.show("All subtitles within limits", "success")
            return

        self.log.add_info(f"Validation: {len(result.warnings)} issue(s) in {result.total_checked} subtitles")
        for w in result.warnings[:20]:  # Cap display at 20
            if w.severity == "error":
                self.log.add_error(f"  {w.message}")
            else:
                self.log.add_warning(f"  {w.message}")

        if len(result.warnings) > 20:
            self.log.add_info(f"  ... and {len(result.warnings) - 20} more")

        self.toast.show(f"{len(result.warnings)} subtitle issues found", "warning")

    # ── Quick Translate ───────────────────────────────────────────────────

    def _open_quick_translate(self):
        from .quick_translate import QuickTranslateDialog
        dlg = QuickTranslateDialog(self.resolve, self.config, parent=self)
        dlg.exec()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_app():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SRTFlow")
    app.setApplicationVersion("2.0.0")

    window = SRTFlowWindow()
    window.show()
    window.raise_()
    window.activateWindow()

    if not QApplication.instance():
        sys.exit(app.exec())
    else:
        app.exec()
