"""Encrypted audit history stored inside the Windslock config."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import config as cfg
from database import EncryptedDatabase


MAX_EVENTS = cfg.MAX_AUDIT_EVENTS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_event(config: dict[str, Any], event_type: str, target: str, action: str, detail: str = "") -> None:
    events = list(config.get("audit_log", []))
    events.append(
        {
            "timestamp": _now(),
            "type": event_type,
            "target": target,
            "action": action,
            "detail": detail,
        }
    )
    config["audit_log"] = events[-MAX_EVENTS:]


def record_with_password(password: str, event_type: str, target: str, action: str, detail: str = "") -> None:
    config = EncryptedDatabase(password)._data
    add_event(config, event_type, target, action, detail)
    EncryptedDatabase(password).save_dict(config)


def list_events(password: str, limit: int = 50) -> list[dict[str, str]]:
    config = EncryptedDatabase(password)._data
    return list(config.get("audit_log", []))[-limit:]
