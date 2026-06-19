"""
Progress persistence — save/resume interrupted translations.
Stores progress state in ~/.srtflow/progress.json.
"""

from __future__ import annotations
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


_PROGRESS_DIR = Path.home() / ".srtflow"
_PROGRESS_FILE = _PROGRESS_DIR / "progress.json"


@dataclass
class ProgressState:
    """Saved state of an interrupted translation."""
    input_path: str
    output_path: str
    source_lang: str
    target_lang: str
    engine: str
    total_entries: int
    completed_index: int       # last completed entry index (1-based)
    translated_texts: Dict[str, str]  # original_text_hash → translated_text
    file_hash: str             # hash of input file to detect changes
    timestamp: str             # ISO timestamp of last save


def _file_hash(path: str) -> str:
    """Quick MD5 hash of file contents for change detection."""
    try:
        content = Path(path).read_bytes()
        return hashlib.md5(content).hexdigest()
    except Exception:
        return ""


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


class ProgressStore:
    """Manages saving and loading translation progress."""

    def __init__(self):
        _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            if _PROGRESS_FILE.exists():
                self._data = json.loads(_PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}

    def _save(self):
        try:
            _PROGRESS_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    @staticmethod
    def _key(input_path: str, target_lang: str) -> str:
        """Unique key for a translation job."""
        return f"{input_path}|{target_lang}"

    def save_progress(
        self,
        input_path: str,
        output_path: str,
        source_lang: str,
        target_lang: str,
        engine: str,
        total_entries: int,
        completed_index: int,
        translated_texts: Dict[str, str],
    ) -> None:
        """Save current progress for a translation job."""
        key = self._key(input_path, target_lang)
        state = ProgressState(
            input_path=input_path,
            output_path=output_path,
            source_lang=source_lang,
            target_lang=target_lang,
            engine=engine,
            total_entries=total_entries,
            completed_index=completed_index,
            translated_texts=translated_texts,
            file_hash=_file_hash(input_path),
            timestamp=_now_iso(),
        )
        self._data[key] = asdict(state)
        self._save()

    def get_progress(self, input_path: str, target_lang: str) -> Optional[ProgressState]:
        """
        Retrieve saved progress for a job. Returns None if:
        - No saved progress exists
        - The input file has changed since last save
        """
        key = self._key(input_path, target_lang)
        data = self._data.get(key)
        if not data:
            return None

        # Verify file hasn't changed
        current_hash = _file_hash(input_path)
        if current_hash and data.get("file_hash") and current_hash != data["file_hash"]:
            # File changed — progress is stale
            self.clear_progress(input_path, target_lang)
            return None

        return ProgressState(**data)

    def clear_progress(self, input_path: str, target_lang: str) -> None:
        """Remove saved progress for a job."""
        key = self._key(input_path, target_lang)
        self._data.pop(key, None)
        self._save()

    def has_progress(self, input_path: str, target_lang: str) -> bool:
        """Check if there's saved progress for a job."""
        return self.get_progress(input_path, target_lang) is not None

    def clear_all(self) -> None:
        """Remove all saved progress."""
        self._data = {}
        self._save()

    def list_jobs(self) -> List[ProgressState]:
        """List all saved progress states."""
        results = []
        for data in self._data.values():
            try:
                results.append(ProgressState(**data))
            except Exception:
                continue
        return results
