"""Desktop app blocking by executable name or full path."""

from __future__ import annotations

import os
import time
from typing import Any

import config as cfg
from database import EncryptedDatabase
import override_manager

try:
    import psutil
except ImportError:  # pragma: no cover - exercised on machines without deps
    psutil = None


def require_psutil() -> Any:
    if psutil is None:
        raise RuntimeError("psutil is required for process enforcement. Install requirements.txt first.")
    return psutil


def normalize_app_rule(value: str) -> dict[str, str]:
    cleaned = value.strip().strip('"')
    if not cleaned:
        raise ValueError("App rule cannot be empty.")
    mode = "path" if any(sep in cleaned for sep in ("/", "\\")) else "name"
    normalized = os.path.normcase(os.path.abspath(cleaned)) if mode == "path" else cleaned.lower()
    return {"mode": mode, "value": normalized}


def _rule_key(rule: dict[str, str]) -> tuple[str, str]:
    return rule["mode"], rule["value"]


def add_locked_app(exe_name_or_path: str, password: str) -> None:
    config = EncryptedDatabase(password)._data
    rule = normalize_app_rule(exe_name_or_path)
    rules = config.get("locked_apps", [])
    if _rule_key(rule) not in {_rule_key(r) for r in rules}:
        rules.append(rule)
        config["locked_apps"] = rules
        EncryptedDatabase(password).save_dict(config)


def remove_locked_app(exe_name_or_path: str, password: str) -> None:
    config = EncryptedDatabase(password)._data
    rule = normalize_app_rule(exe_name_or_path)
    config["locked_apps"] = [r for r in config.get("locked_apps", []) if _rule_key(r) != _rule_key(rule)]
    EncryptedDatabase(password).save_dict(config)


def list_locked_apps(password: str) -> list[dict[str, str]]:
    config = EncryptedDatabase(password)._data
    return list(config.get("locked_apps", []))


def list_running_processes() -> list[str]:
    ps = require_psutil()
    names = set()
    for proc in ps.process_iter(["name"]):
        try:
            if proc.info["name"]:
                names.add(proc.info["name"])
        except (ps.NoSuchProcess, ps.AccessDenied):
            continue
    return sorted(names)


def list_running_process_details() -> list[dict[str, str]]:
    ps = require_psutil()
    processes: list[dict[str, str]] = []
    for proc in ps.process_iter(["pid", "name", "exe"]):
        try:
            name = proc.info.get("name") or proc.name() or ""
            if not name:
                continue
            exe = proc.info.get("exe") or ""
            processes.append({"pid": str(proc.info.get("pid") or proc.pid), "name": name, "exe": exe})
        except (ps.NoSuchProcess, ps.AccessDenied, ps.ZombieProcess):
            continue
    return sorted(processes, key=lambda item: (item["name"].lower(), item["pid"]))


def _name_matches(rule_value: str, process_name: str) -> bool:
    if process_name == rule_value:
        return True
    proc_base, _ = os.path.splitext(process_name)
    return "." not in rule_value and proc_base == rule_value


def _process_matches(proc: Any, rules: list[dict[str, str]], config: dict | None = None) -> tuple[bool, str]:
    ps = require_psutil()
    try:
        name = (proc.info.get("name") or proc.name() or "").lower()
        exe = proc.info.get("exe")
        if exe is None:
            try:
                exe = proc.exe()
            except (ps.NoSuchProcess, ps.AccessDenied, ps.ZombieProcess):
                exe = ""
        exe_norm = os.path.normcase(os.path.abspath(exe)) if exe else ""
    except (ps.NoSuchProcess, ps.AccessDenied, ps.ZombieProcess):
        return False, ""

    for rule in rules:
        if rule["mode"] == "name" and _name_matches(rule["value"], name):
            if config and override_manager.is_overridden(config, "app", rule["value"]):
                return False, ""
            return True, name
        if rule["mode"] == "path" and exe_norm == rule["value"]:
            if config and override_manager.is_overridden(config, "app", rule["value"]):
                return False, ""
            return True, exe_norm
    return False, ""


def find_matching_processes(rules: list[dict[str, str]], config: dict | None = None) -> list[dict[str, str]]:
    """Return running processes that match app rules without killing them."""
    ps = require_psutil()
    matches: list[dict[str, str]] = []
    for proc in ps.process_iter(["pid", "name", "exe"]):
        matched, target = _process_matches(proc, rules, config)
        if not matched:
            continue
        try:
            matches.append(
                {
                    "pid": str(proc.info.get("pid") or proc.pid),
                    "name": proc.info.get("name") or proc.name() or "",
                    "exe": proc.info.get("exe") or "",
                    "target": target,
                }
            )
        except (ps.NoSuchProcess, ps.AccessDenied, ps.ZombieProcess):
            continue
    return matches


def _kill(proc: Any) -> bool:
    ps = require_psutil()
    try:
        proc.kill()
        return True
    except (ps.NoSuchProcess, ps.AccessDenied, ps.ZombieProcess):
        return False


def watch_once(locked_apps: list[dict[str, str]], config: dict | None = None) -> list[dict[str, str]]:
    """Single process scan. Kills matches and returns blocked attempts."""
    ps = require_psutil()
    blocked = []
    strict = True if config is None else bool(config.get("settings", {}).get("strict_app_lock", True))
    for proc in ps.process_iter(["pid", "name", "exe"]):
        matched, target = _process_matches(proc, locked_apps, config)
        if matched:
            killed = _kill(proc) if strict else False
            blocked.append(
                {
                    "pid": str(getattr(proc, "pid", "")),
                    "target": target,
                    "action": "killed" if killed else ("detected" if not strict else "access_denied"),
                }
            )
    return blocked


def start_watching(password: str, poll_interval: float = 1.5, on_block=None) -> None:
    print(f"App watcher running every {poll_interval}s. Press Ctrl+C to stop.")
    try:
        while True:
            config = EncryptedDatabase(password)._data
            locked = list(config.get("locked_apps", []))
            changed = override_manager.process_overrides(config)
            if changed:
                EncryptedDatabase(password).save_dict(config)
            import focus_manager
            if locked and focus_manager.should_enforce(config):
                for event in watch_once(locked, config):
                    if on_block:
                        on_block(event)
                    else:
                        print(f"Blocked app: {event['target']} ({event['action']})")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("App watcher stopped.")
