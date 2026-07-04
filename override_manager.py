"""Friction-based temporary override workflow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

import audit_log
import config as cfg


STATUS_DENIED = "denied"
STATUS_COOLDOWN = "cooldown"
STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def from_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def target_key(target_type: str, target: str) -> str:
    return f"{target_type}:{target}".lower()


def process_overrides(config: dict[str, Any], now: datetime | None = None) -> bool:
    """Activate ready overrides and expire elapsed ones. Returns True if changed."""
    now = now or utc_now()
    changed = False
    window = int(config["settings"].get("override_window_minutes", 10))
    for request in config.get("override_requests", []):
        status = request.get("status")
        if status == STATUS_COOLDOWN and now >= from_iso(request["ready_at"]):
            request["status"] = STATUS_ACTIVE
            request["activated_at"] = to_iso(now)
            request["expires_at"] = to_iso(now + timedelta(minutes=window))
            audit_log.add_event(
                config,
                "override",
                request["target"],
                "activated",
                f"type={request['target_type']} expires_at={request['expires_at']}",
            )
            changed = True
        elif status == STATUS_ACTIVE and now >= from_iso(request["expires_at"]):
            request["status"] = STATUS_EXPIRED
            request["expired_at"] = to_iso(now)
            audit_log.add_event(
                config,
                "override",
                request["target"],
                "relocked",
                f"type={request['target_type']}",
            )
            changed = True
    return changed


def request_override(password: str, target_type: str, target: str, phrase: str) -> dict[str, Any]:
    config = cfg.load_config(password)
    changed = process_overrides(config)
    now = utc_now()
    expected = config["settings"].get("override_phrase", "")
    if phrase != expected:
        request = {
            "id": secrets.token_hex(8),
            "target_type": target_type,
            "target": target,
            "key": target_key(target_type, target),
            "status": STATUS_DENIED,
            "requested_at": to_iso(now),
            "reason": "phrase_mismatch",
        }
        config["override_requests"].append(request)
        audit_log.add_event(config, "override", target, "denied", f"type={target_type} reason=phrase_mismatch")
        cfg.save_config(config, password)
        return request

    cooldown = int(config["settings"].get("override_cooldown_minutes", 5))
    request = {
        "id": secrets.token_hex(8),
        "target_type": target_type,
        "target": target,
        "key": target_key(target_type, target),
        "status": STATUS_COOLDOWN,
        "requested_at": to_iso(now),
        "ready_at": to_iso(now + timedelta(minutes=cooldown)),
    }
    config["override_requests"].append(request)
    audit_log.add_event(config, "override", target, "cooldown_started", f"type={target_type} ready_at={request['ready_at']}")
    if changed:
        audit_log.add_event(config, "override", "system", "processed", "processed pending override state")
    cfg.save_config(config, password)
    return request


def is_overridden(config: dict[str, Any], target_type: str, target: str, now: datetime | None = None) -> bool:
    process_overrides(config, now)
    key = target_key(target_type, target)
    for request in config.get("override_requests", []):
        if request.get("key") == key and request.get("status") == STATUS_ACTIVE:
            return True
    return False


def list_overrides(password: str) -> list[dict[str, Any]]:
    config = cfg.load_config(password)
    changed = process_overrides(config)
    if changed:
        cfg.save_config(config, password)
    return list(config.get("override_requests", []))


def update_settings(password: str, phrase: str, cooldown_minutes: int, window_minutes: int) -> None:
    if not phrase:
        raise ValueError("Override phrase cannot be empty.")
    if cooldown_minutes < 0 or window_minutes < 1:
        raise ValueError("Cooldown must be 0+ minutes and window must be at least 1 minute.")
    config = cfg.load_config(password)
    config["settings"]["override_phrase"] = phrase
    config["settings"]["override_cooldown_minutes"] = cooldown_minutes
    config["settings"]["override_window_minutes"] = window_minutes
    audit_log.add_event(config, "override", "settings", "updated", "override phrase/timers changed")
    cfg.save_config(config, password)
