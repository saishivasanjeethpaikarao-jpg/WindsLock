"""Database wrapper for the encrypted JSON store.

Provides a structured EncryptedDatabase class to encapsulate the JSON/Fernet logic.
"""

from __future__ import annotations

from typing import Any
import config as cfg

class EncryptedDatabase:
    """A structured class wrapping the secure JSON file store."""
    _cache = {}
    """A structured class wrapping the secure JSON file store."""

    def __init__(self, password: str | None = None, is_background: bool = False):
        self._password = password
        self._is_background = is_background
        self._data: dict[str, Any] = {}
        if password or is_background:
            self.load()

    def load(self) -> None:
        cache_key = "background" if self._is_background else self._password
        if cache_key in EncryptedDatabase._cache:
            self._data = EncryptedDatabase._cache[cache_key]
            return

        if self._is_background:
            self._data = cfg.load_config_for_background()
        elif self._password:
            self._data = cfg.load_config(self._password)
        else:
            raise ValueError("Must provide password or specify background mode to load DB.")

        EncryptedDatabase._cache[cache_key] = self._data
    def save(self) -> None:
        cache_key = "background" if self._is_background else self._password
        EncryptedDatabase._cache[cache_key] = self._data

        if self._is_background:
            cfg.save_config_for_background(self._data)
        elif self._password:
            cfg.save_config(self._data, self._password)
        else:
            raise ValueError("Must provide password or specify background mode to save DB.")
    def save_dict(self, data_dict: dict[str, Any]) -> None:
        """Helper to save an external dictionary to the database."""
        self._data = data_dict
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update_setting(self, setting_key: str, value: Any) -> None:
        settings = self.get("settings", {})
        settings[setting_key] = value
        self.set("settings", settings)

    def get_setting(self, setting_key: str, default: Any = None) -> Any:
        return self.get("settings", {}).get(setting_key, default)

    @classmethod
    def reset_cache(cls):
        cls._cache.clear()
