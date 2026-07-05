"""Focus sessions, schedules, and one-click preset rule bundles."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import app_blocker
import audit_log
import config as cfg
from database import EncryptedDatabase
import site_blocker
import url_rule_engine


PRESETS: dict[str, dict[str, list[str] | list[tuple[str, str]]]] = {
    "Deep Work": {
        "apps": ["steam.exe", "EpicGamesLauncher.exe", "Discord.exe", "Telegram.exe"],
        "sites": ["reddit.com", "x.com", "twitter.com", "instagram.com", "netflix.com"],
        "paths": [("youtube.com", "/shorts"), ("instagram.com", "/reels"), ("reddit.com", "/r/all")],
    },
    "Study Mode": {
        "apps": ["steam.exe", "EpicGamesLauncher.exe", "RobloxPlayerBeta.exe", "Discord.exe"],
        "sites": ["tiktok.com", "instagram.com", "snapchat.com", "reddit.com"],
        "paths": [("youtube.com", "/shorts"), ("youtube.com", "/feed/trending"), ("instagram.com", "/reels")],
    },
    "Social Detox": {
        "apps": ["Discord.exe", "Telegram.exe", "WhatsApp.exe"],
        "sites": ["instagram.com", "facebook.com", "x.com", "twitter.com", "reddit.com", "tiktok.com"],
        "paths": [("youtube.com", "/shorts"), ("instagram.com", "/reels")],
    },
}


def _now() -> datetime:
    return datetime.now().astimezone()


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def apply_preset(password: str, preset_name: str) -> None:
    preset = PRESETS[preset_name]
    for app in preset["apps"]:
        app_blocker.add_locked_app(str(app), password)
    for site in preset["sites"]:
        site_blocker.add_blocked_site(str(site), password)
    for domain, path_prefix in preset["paths"]:
        url_rule_engine.add_path_rule(domain, path_prefix, password)
    config = EncryptedDatabase(password)._data
    audit_log.add_event(config, "preset", preset_name, "applied", "added preset rules")
    EncryptedDatabase(password).save_dict(config)


def start_focus_session(password: str, minutes: int) -> str:
    if minutes < 1:
        raise ValueError("Focus session must be at least 1 minute.")
    until = _now() + timedelta(minutes=minutes)
    config = EncryptedDatabase(password)._data
    config["settings"]["focus_session_until"] = until.isoformat(timespec="seconds")
    audit_log.add_event(config, "focus", "session", "started", f"until={config['settings']['focus_session_until']}")
    EncryptedDatabase(password).save_dict(config)
    return config["settings"]["focus_session_until"]


def stop_focus_session(password: str) -> None:
    config = EncryptedDatabase(password)._data
    config["settings"]["focus_session_until"] = ""
    audit_log.add_event(config, "focus", "session", "stopped", "")
    EncryptedDatabase(password).save_dict(config)


def set_schedule_only_mode(password: str, enabled: bool) -> None:
    config = EncryptedDatabase(password)._data
    config["settings"]["schedule_only_mode"] = bool(enabled)
    audit_log.add_event(config, "focus", "schedule_only_mode", "enabled" if enabled else "disabled", "")
    EncryptedDatabase(password).save_dict(config)


def add_schedule(password: str, name: str, days: list[int], start: str, end: str) -> None:
    _parse_hhmm(start)
    _parse_hhmm(end)
    if not days:
        raise ValueError("Choose at least one day.")
    config = EncryptedDatabase(password)._data
    config["focus_schedules"].append(
        {"name": name.strip() or "Focus", "days": sorted(set(days)), "start": start, "end": end, "enabled": True}
    )
    audit_log.add_event(config, "focus", name or "Focus", "schedule_added", f"{days} {start}-{end}")
    EncryptedDatabase(password).save_dict(config)


def remove_schedule(password: str, index: int) -> None:
    config = EncryptedDatabase(password)._data
    schedules = list(config.get("focus_schedules", []))
    removed = schedules.pop(index)
    config["focus_schedules"] = schedules
    audit_log.add_event(config, "focus", removed.get("name", "Focus"), "schedule_removed", "")
    EncryptedDatabase(password).save_dict(config)


def is_session_active(config: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or _now()
    until = _parse_iso(config.get("settings", {}).get("focus_session_until", ""))
    return bool(until and now < until)


def active_schedule(config: dict[str, Any], now: datetime | None = None) -> dict[str, Any] | None:
    now = now or _now()
    weekday = now.weekday()
    current = now.time()
    for schedule in config.get("focus_schedules", []):
        if not schedule.get("enabled", True) or weekday not in schedule.get("days", []):
            continue
        start = _parse_hhmm(schedule["start"])
        end = _parse_hhmm(schedule["end"])
        if start <= end:
            if start <= current <= end:
                return schedule
        elif current >= start or current <= end:
            return schedule
    return None


def should_enforce(config: dict[str, Any], now: datetime | None = None) -> bool:
    if not config.get("settings", {}).get("schedule_only_mode", False):
        return True
    return is_session_active(config, now) or active_schedule(config, now) is not None
