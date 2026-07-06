"""Background enforcement loop for app and website rules."""

from __future__ import annotations

import os
from pathlib import Path
import time
import traceback

import app_blocker
import audit_log
import config as cfg
from database import EncryptedDatabase
import focus_manager
import override_manager
import runtime_control
import site_blocker


POLL_INTERVAL_SECONDS = 1.5
HOSTS_REFRESH_SECONDS = 60


def _lock_path() -> Path:
    return cfg.ensure_app_dir() / "enforcer.lock"


def _acquire_single_instance() -> bool:
    path = _lock_path()
    if path.exists():
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
            if pid and _pid_is_running_enforcer(pid):
                return False
        except Exception:
            pass
    path.write_text(str(os.getpid()), encoding="utf-8")
    return True


def _pid_exists(pid: int) -> bool:
    if app_blocker.psutil is None:
        return False
    return app_blocker.psutil.pid_exists(pid)


def _pid_is_running_enforcer(pid: int) -> bool:
    if app_blocker.psutil is None:
        return False
    try:
        proc = app_blocker.psutil.Process(pid)
        name = (proc.name() or "").lower()
        cmdline = " ".join(proc.cmdline()).lower()
    except app_blocker.psutil.Error:
        return False
    return (
        proc.is_running()
        and (
            "windslockenforcer" in name
            or "windslockenforcer" in cmdline
            or "enforcer.py" in cmdline
        )
    )


def _write_crash_log(exc: BaseException) -> None:
    try:
        path = cfg.ensure_app_dir() / "enforcer_error.log"
        path.write_text("Windslock enforcer crashed:\n" + "".join(traceback.format_exception(exc)), encoding="utf-8")
    except Exception:
        pass


def run_forever(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    if not _acquire_single_instance():
        return
    last_hosts_refresh = 0.0
    try:
        while True:
            config = cfg.load_config_for_background()
            changed = override_manager.process_overrides(config)
            enforce_now = focus_manager.should_enforce(config)

            locked_apps = list(config.get("locked_apps", []))
            if locked_apps and enforce_now:
                for event in app_blocker.watch_once(locked_apps, config):
                    audit_log.add_event(
                        config,
                        "app",
                        event["target"],
                        event["action"],
                        f"pid={event['pid']}",
                    )
                    changed = True
                    if event["action"] == "killed":
                        try:
                            if not runtime_control.is_lock_screen_running(event["target"]):
                                runtime_control.open_lock_screen(event["target"])
                        except Exception as exc:
                            audit_log.add_event(
                                config,
                                "app",
                                event["target"],
                                "lock_screen_failed",
                                str(exc),
                            )

            now = time.monotonic()
            hosts_due = now - last_hosts_refresh > HOSTS_REFRESH_SECONDS
            if config.get("settings", {}).get("website_hosts_applied") and (hosts_due or changed):
                try:
                    site_blocker.apply_hosts_block_with_config(config if enforce_now else {**config, "blocked_sites": []})
                    last_hosts_refresh = now
                except Exception as exc:
                    audit_log.add_event(config, "site", "hosts", "apply_failed", str(exc))
                    changed = True

            if changed:
                EncryptedDatabase(is_background=True).save_dict(config)
            time.sleep(poll_interval)
    finally:
        try:
            _lock_path().unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        run_forever()
    except Exception as exc:
        _write_crash_log(exc)
        raise
