"""
Translation worker — runs translation in a background QThread.
Supports both file-based and timeline-based workflows.
Both workers use skip-and-continue: failed lines are logged and skipped.
Integrates quality scoring and progress persistence.
"""

from __future__ import annotations
import hashlib
from typing import List, Optional, Dict

from PyQt6.QtCore import QThread, pyqtSignal

from ..srt_parser import SubtitleEntry, write_srt
from ..translator import TranslationError
from ..cache import TranslationCache
from ..resolve_bridge import TimelineSubtitleItem
from ..quality import score_translation, LineScore, QualityReport
from ..progress_store import ProgressStore


class TranslationWorker(QThread):
    """Translates subtitle entries in batches on a background thread."""

    progress = pyqtSignal(int, int)           # current, total
    line_done = pyqtSignal(int, str, str)     # index, original, translated
    line_skipped = pyqtSignal(int, str, str)  # index, original_text, error_message
    finished = pyqtSignal(str, int, int)      # output_path, success_count, skip_count
    error = pyqtSignal(str)                   # fatal error message
    cancelled = pyqtSignal()
    language_detected = pyqtSignal(str)       # detected source language code
    quality_report = pyqtSignal(object)       # QualityReport after translation completes

    def __init__(
        self,
        entries: List[SubtitleEntry],
        source_lang: str,
        target_lang: str,
        output_path: str,
        client,
        cache: TranslationCache,
        batch_size: int = 10,
        glossary: Optional[dict] = None,
        input_path: str = "",
        engine: str = "datpmt",
        resume_from: int = 0,
        resumed_texts: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self.entries = entries
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.output_path = output_path
        self.client = client
        self.cache = cache
        self.batch_size = batch_size
        self.glossary = glossary or {}
        self.input_path = input_path
        self.engine = engine
        self.resume_from = resume_from
        self.resumed_texts = resumed_texts or {}
        self._cancel = False
        self._lang_detected_emitted = False
        self._progress_store = ProgressStore()
        self._translated_map: Dict[str, str] = dict(self.resumed_texts)

    def cancel(self):
        self._cancel = True

    def _check_detected_language(self):
        if not self._lang_detected_emitted and hasattr(self.client, 'detected_language'):
            det = self.client.detected_language
            if det:
                self._lang_detected_emitted = True
                self.language_detected.emit(det)

    def _text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _save_progress(self, completed_index: int):
        """Periodically save progress for resume capability."""
        if self.input_path:
            try:
                self._progress_store.save_progress(
                    input_path=self.input_path,
                    output_path=self.output_path,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    engine=self.engine,
                    total_entries=len(self.entries),
                    completed_index=completed_index,
                    translated_texts=self._translated_map,
                )
            except Exception:
                pass

    def run(self):
        total = len(self.entries)
        translated_entries: List[SubtitleEntry] = []
        skip_count = 0
        originals_for_quality: List[str] = []
        translations_for_quality: List[str] = []

        for batch_start in range(0, total, self.batch_size):
            if self._cancel:
                # Save progress before cancelling
                self._save_progress(batch_start)
                self.cancelled.emit()
                return

            batch = self.entries[batch_start: batch_start + self.batch_size]
            texts = [e.plain_text for e in batch]

            # Check resumed texts first, then cache
            cached = []
            for t in texts:
                th = self._text_hash(t)
                if th in self.resumed_texts:
                    cached.append(self.resumed_texts[th])
                else:
                    cached.append(self.cache.get(self.source_lang, self.target_lang, t))

            to_translate_indices = [i for i, c in enumerate(cached) if c is None]
            to_translate_texts = [texts[i] for i in to_translate_indices]

            if to_translate_texts:
                try:
                    results = self.client.translate_batch(
                        to_translate_texts, self.source_lang, self.target_lang
                    )
                    self._check_detected_language()
                    for idx, result in zip(to_translate_indices, results):
                        self.cache.set(
                            self.source_lang, self.target_lang,
                            texts[idx], result
                        )
                        cached[idx] = result
                except TranslationError:
                    # Batch failed — try one-by-one for this batch
                    for idx in to_translate_indices:
                        try:
                            result = self.client.translate(
                                texts[idx], self.source_lang, self.target_lang
                            )
                            self._check_detected_language()
                            self.cache.set(
                                self.source_lang, self.target_lang,
                                texts[idx], result
                            )
                            cached[idx] = result
                        except TranslationError as e2:
                            # Skip this line — keep original text
                            cached[idx] = None
                            global_skip_idx = batch_start + idx + 1
                            self.line_skipped.emit(
                                global_skip_idx, texts[idx], str(e2)
                            )

            for i, (entry, translated) in enumerate(zip(batch, cached)):
                if self._cancel:
                    self._save_progress(batch_start + i)
                    self.cancelled.emit()
                    return

                if translated is None:
                    # Skipped line — keep original
                    translated_entries.append(entry)
                    skip_count += 1
                    originals_for_quality.append(entry.plain_text)
                    translations_for_quality.append(entry.plain_text)
                else:
                    # Apply glossary
                    for src_term, repl in self.glossary.items():
                        translated = translated.replace(src_term, repl)
                    new_entry = entry.with_translated_text(translated)
                    translated_entries.append(new_entry)
                    originals_for_quality.append(entry.plain_text)
                    translations_for_quality.append(translated)

                    # Track for progress persistence
                    self._translated_map[self._text_hash(entry.plain_text)] = translated

                global_idx = batch_start + i + 1
                display_text = translated if translated else entry.plain_text
                self.line_done.emit(global_idx, entry.plain_text, display_text)
                self.progress.emit(global_idx, total)

            # Save progress every batch
            self._save_progress(batch_start + len(batch))

        # Write output
        try:
            write_srt(translated_entries, self.output_path)

            # Clear saved progress on successful completion
            if self.input_path:
                self._progress_store.clear_progress(self.input_path, self.target_lang)

            # Run quality scoring
            from ..quality import score_batch
            report = score_batch(
                originals_for_quality, translations_for_quality,
                source_lang=self.source_lang, target_lang=self.target_lang,
            )
            self.quality_report.emit(report)

            self.finished.emit(self.output_path, total - skip_count, skip_count)
        except OSError as e:
            self.error.emit(f"Failed to write output file: {e}")


class TimelineTranslationWorker(QThread):
    """
    Translates subtitle items for the DaVinci timeline.
    Does NOT write back — returns results for preview.
    Write-back happens after user confirms in the preview dialog.
    """

    progress = pyqtSignal(int, int)           # current, total
    line_done = pyqtSignal(int, str, str)     # index, original, translated
    line_skipped = pyqtSignal(int, str, str)  # index, original_text, error_message
    finished = pyqtSignal(list)               # List[(TimelineSubtitleItem, original_text, translated_text)]
    error = pyqtSignal(str)
    cancelled = pyqtSignal()
    language_detected = pyqtSignal(str)       # detected source language code

    def __init__(
        self,
        items: List[TimelineSubtitleItem],
        source_lang: str,
        target_lang: str,
        client,
        cache: TranslationCache,
        batch_size: int = 10,
        glossary: Optional[dict] = None,
    ):
        super().__init__()
        self.items = items
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.client = client
        self.cache = cache
        self.batch_size = batch_size
        self.glossary = glossary or {}
        self._cancel = False
        self._lang_detected_emitted = False

    def cancel(self):
        self._cancel = True

    def _check_detected_language(self):
        if not self._lang_detected_emitted and hasattr(self.client, 'detected_language'):
            det = self.client.detected_language
            if det:
                self._lang_detected_emitted = True
                self.language_detected.emit(det)

    def run(self):
        total = len(self.items)
        # Results: list of (item, original_text, translated_text)
        results: list = []

        for batch_start in range(0, total, self.batch_size):
            if self._cancel:
                self.cancelled.emit()
                return

            batch = self.items[batch_start: batch_start + self.batch_size]
            texts = [item.text for item in batch]

            # Check cache
            cached = [self.cache.get(self.source_lang, self.target_lang, t) for t in texts]
            to_translate_indices = [i for i, c in enumerate(cached) if c is None]
            to_translate_texts = [texts[i] for i in to_translate_indices]

            if to_translate_texts:
                try:
                    api_results = self.client.translate_batch(
                        to_translate_texts, self.source_lang, self.target_lang
                    )
                    self._check_detected_language()
                    for idx, result in zip(to_translate_indices, api_results):
                        self.cache.set(
                            self.source_lang, self.target_lang,
                            texts[idx], result
                        )
                        cached[idx] = result
                except TranslationError:
                    # Batch failed — try one-by-one
                    for idx in to_translate_indices:
                        try:
                            result = self.client.translate(
                                texts[idx], self.source_lang, self.target_lang
                            )
                            self._check_detected_language()
                            self.cache.set(
                                self.source_lang, self.target_lang,
                                texts[idx], result
                            )
                            cached[idx] = result
                        except TranslationError as e2:
                            cached[idx] = None
                            global_skip_idx = batch_start + idx + 1
                            self.line_skipped.emit(
                                global_skip_idx, texts[idx], str(e2)
                            )

            for i, (item, translated) in enumerate(zip(batch, cached)):
                if self._cancel:
                    self.cancelled.emit()
                    return

                original = item.text

                if translated is None:
                    # Skipped — keep original
                    results.append((item, original, original))
                else:
                    # Apply glossary
                    for src_term, repl in self.glossary.items():
                        translated = translated.replace(src_term, repl)
                    results.append((item, original, translated))

                global_idx = batch_start + i + 1
                display = translated if translated else original
                self.line_done.emit(global_idx, original, display)
                self.progress.emit(global_idx, total)

        self.finished.emit(results)
