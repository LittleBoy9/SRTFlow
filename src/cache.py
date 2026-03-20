"""
Translation cache — avoids re-translating identical lines.
Stored as JSON at ~/.srtflow/cache.json.
"""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Optional


def _cache_path() -> Path:
    base = Path.home() / ".srtflow"
    base.mkdir(exist_ok=True)
    return base / "cache.json"


def _key(source_lang: str, target_lang: str, text: str) -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return f"{source_lang}|{target_lang}|{digest}"


class TranslationCache:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._data: dict[str, str] = {}
        if enabled:
            self._load()

    def get(self, source_lang: str, target_lang: str, text: str) -> Optional[str]:
        if not self.enabled or not text.strip():
            return None
        return self._data.get(_key(source_lang, target_lang, text))

    def set(self, source_lang: str, target_lang: str, text: str, translation: str) -> None:
        if not self.enabled or not text.strip():
            return
        self._data[_key(source_lang, target_lang, text)] = translation
        self._save()

    def clear(self) -> None:
        self._data = {}
        self._save()

    @property
    def size(self) -> int:
        return len(self._data)

    def _load(self) -> None:
        p = _cache_path()
        if p.exists():
            try:
                self._data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        try:
            _cache_path().write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
