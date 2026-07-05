"""Start-with-Windows helpers using the current user's Run registry key."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import config as cfg
from database import EncryptedDatabase


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_VALUE = "WindslockEnforcer"
TASK_NAME = "WindslockEnforcer"


def _packaged_executable(app_name: str) -> Path | None:
    exe = Path(sys.executable)
    names = [f"{app_name}.exe", app_name]
    candidates: list[Path] = []
    for name in names:
        candidates.append(exe.with_name(name))
        candidates.append(exe.parent / app_name / name)
        candidates.append(exe.parent.parent / app_name / name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _pythonw_executable() -> Path:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else exe


def _script_command(script_name: str) -> str:
    exe = _pythonw_executable()
    script = Path(__file__).with_name(script_name)
    return f'"{exe}" "{script}"'


def _command() -> str:
    packaged = _packaged_executable("WindslockEnforcer")
    if packaged:
        return f'"{packaged}"'
    if getattr(sys, "frozen", False):
        raise RuntimeError("WindslockEnforcer.exe was not found next to the installed app.")
    return _script_command("enforcer.py")


def _tray_command() -> str:
    packaged = _packaged_executable("WindslockTray")
    if packaged:
        return f'"{packaged}"'
    if getattr(sys, "frozen", False):
        raise RuntimeError("WindslockTray.exe was not found next to the installed app.")
    return _script_command("tray_app.py")


def enable_startup(password: str) -> None:
    if os.name != "nt":
        raise RuntimeError("This startup option only works on Windows.")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_VALUE, 0, winreg.REG_SZ, _command())
    config = EncryptedDatabase(password)._data
    config["settings"]["run_on_startup"] = True
    config["settings"]["startup_task"] = "run_key"
    EncryptedDatabase(password).save_dict(config)


def disable_startup(password: str) -> None:
    if os.name != "nt":
        raise RuntimeError("This startup option only works on Windows.")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, APP_VALUE)
        except FileNotFoundError:
            pass
    config = EncryptedDatabase(password)._data
    config["settings"]["run_on_startup"] = False
    if config["settings"].get("startup_task") == "run_key":
        config["settings"]["startup_task"] = ""
    EncryptedDatabase(password).save_dict(config)


def install_scheduled_task(password: str, launch_tray: bool = True) -> str:
    """Create an at-logon scheduled task for the current user.

    If Windows denies highest-privilege task creation, fall back to the normal
    current-user Run key so startup still works without admin rights.
    """
    if os.name != "nt":
        raise RuntimeError("Stronger startup only works on Windows.")
    command = _tray_command() if launch_tray else _command()
    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            TASK_NAME,
            "/SC",
            "ONLOGON",
            "/TR",
            command,
            "/RL",
            "HIGHEST",
            "/F",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "schtasks create failed"
        if "access is denied" in detail.lower():
            enable_startup(password)
            config = EncryptedDatabase(password)._data
            config["settings"]["startup_task"] = "run_key_fallback"
            EncryptedDatabase(password).save_dict(config)
            return "Windows did not allow stronger startup, so normal startup was enabled instead. Run Windslock as administrator if you want stronger startup."
        raise RuntimeError(detail)
    config = EncryptedDatabase(password)._data
    config["settings"]["run_on_startup"] = True
    config["settings"]["startup_task"] = TASK_NAME
    EncryptedDatabase(password).save_dict(config)
    return "Stronger startup is installed."


def uninstall_scheduled_task(password: str | None = None) -> None:
    if os.name != "nt":
        raise RuntimeError("Stronger startup only works on Windows.")
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    detail = (result.stderr + result.stdout).lower()
    if result.returncode != 0 and "cannot find" not in detail and "does not exist" not in detail:
        if "access is denied" not in detail:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "schtasks delete failed")
    if password:
        try:
            disable_startup(password)
        except Exception:
            pass
        config = EncryptedDatabase(password)._data
        config["settings"]["run_on_startup"] = False
        config["settings"]["startup_task"] = ""
        EncryptedDatabase(password).save_dict(config)
