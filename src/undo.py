"""
Undo manager — stores original subtitle text before timeline overwrites.
Allows reverting the last Quick Translate operation.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("srtflow.undo")

_UNDO_PATH = Path.home() / ".srtflow" / "undo_history.json"
_MAX_HISTORY = 10  # Keep last N undo operations


class UndoEntry:
    """A single undo record: maps item index → original text for one operation."""

    def __init__(self, timeline_name: str, track_index: int, items: Dict[int, str]):
        self.timeline_name = timeline_name
        self.track_index = track_index
        self.items = items  # {subtitle_index: original_text}

    def to_dict(self) -> dict:
        return {
            "timeline": self.timeline_name,
            "track": self.track_index,
            "items": {str(k): v for k, v in self.items.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UndoEntry":
        return cls(
            timeline_name=data["timeline"],
            track_index=data["track"],
            items={int(k): v for k, v in data["items"].items()},
        )


class UndoManager:
    """Manages undo history for timeline subtitle translations."""

    def __init__(self):
        self._history: List[UndoEntry] = []
        self._load()

    def push(self, entry: UndoEntry) -> None:
        """Record a new undo entry (call before writing translations)."""
        self._history.append(entry)
        if len(self._history) > _MAX_HISTORY:
            self._history = self._history[-_MAX_HISTORY:]
        self._save()

    def peek(self) -> Optional[UndoEntry]:
        """Return the most recent undo entry without removing it."""
        return self._history[-1] if self._history else None

    def pop(self) -> Optional[UndoEntry]:
        """Remove and return the most recent undo entry."""
        if not self._history:
            return None
        entry = self._history.pop()
        self._save()
        return entry

    @property
    def can_undo(self) -> bool:
        return len(self._history) > 0

    @property
    def size(self) -> int:
        return len(self._history)

    def _load(self) -> None:
        if not _UNDO_PATH.exists():
            return
        try:
            data = json.loads(_UNDO_PATH.read_text(encoding="utf-8"))
            self._history = [UndoEntry.from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning("Failed to load undo history: %s", e)
            self._history = []

    def _save(self) -> None:
        try:
            _UNDO_PATH.parent.mkdir(exist_ok=True)
            _UNDO_PATH.write_text(
                json.dumps([e.to_dict() for e in self._history], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("Failed to save undo history: %s", e)
