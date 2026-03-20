"""
Config manager — loads and persists user settings.
Project config.json provides defaults; user overrides go to ~/.srtflow/config.json.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_PLUGIN_DIR = Path(__file__).parent.parent
_DEFAULT_CONFIG = _PLUGIN_DIR / "config.json"
_USER_CONFIG = Path.home() / ".srtflow" / "config.json"


class ConfigManager:
    def __init__(self):
        self._data: dict[str, Any] = {}
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def update(self, values: dict[str, Any]) -> None:
        self._data.update(values)
        self._save()

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def _load(self) -> None:
        # Start with plugin defaults
        if _DEFAULT_CONFIG.exists():
            try:
                self._data = json.loads(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

        # Overlay with user overrides
        if _USER_CONFIG.exists():
            try:
                user = json.loads(_USER_CONFIG.read_text(encoding="utf-8"))
                self._data.update(user)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        try:
            _USER_CONFIG.parent.mkdir(exist_ok=True)
            _USER_CONFIG.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
