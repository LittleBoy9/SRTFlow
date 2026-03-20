"""
Translation worker — runs translation in a background QThread.
Supports both file-based and timeline-based workflows.
Both workers use skip-and-continue: failed lines are logged and skipped.
"""

from __future__ import annotations
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ..srt_parser import SubtitleEntry, write_srt
from ..translator import TranslationError
from ..cache import TranslationCache
from ..resolve_bridge import TimelineSubtitleItem


class TranslationWorker(QThread):
    """Translates subtitle entries in batches on a background thread."""

    progress = pyqtSignal(int, int)           # current, total
    line_done = pyqtSignal(int, str, str)     # index, original, translated
    line_skipped = pyqtSignal(int, str, str)  # index, original_text, error_message
    finished = pyqtSignal(str, int, int)      # output_path, success_count, skip_count
    error = pyqtSignal(str)                   # fatal error message
    cancelled = pyqtSignal()
    language_detected = pyqtSignal(str)       # detected source language code

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
        total = len(self.entries)
        translated_entries: List[SubtitleEntry] = []
        skip_count = 0

        for batch_start in range(0, total, self.batch_size):
            if self._cancel:
                self.cancelled.emit()
                return

            batch = self.entries[batch_start: batch_start + self.batch_size]
            texts = [e.plain_text for e in batch]

            # Check cache first
            cached = [self.cache.get(self.source_lang, self.target_lang, t) for t in texts]
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
                    self.cancelled.emit()
                    return

                if translated is None:
                    # Skipped line — keep original
                    translated_entries.append(entry)
                    skip_count += 1
                else:
                    # Apply glossary
                    for src_term, repl in self.glossary.items():
                        translated = translated.replace(src_term, repl)
                    new_entry = entry.with_translated_text(translated)
                    translated_entries.append(new_entry)

                global_idx = batch_start + i + 1
                display_text = translated if translated else entry.plain_text
                self.line_done.emit(global_idx, entry.plain_text, display_text)
                self.progress.emit(global_idx, total)

        # Write output
        try:
            write_srt(translated_entries, self.output_path)
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
