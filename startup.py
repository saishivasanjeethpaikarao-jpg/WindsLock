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


def _command() -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    service = Path(__file__).with_name("enforcer.py")
    return f'"{exe}" "{service}"'


def _tray_command() -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    tray = Path(__file__).with_name("tray_app.py")
    return f'"{exe}" "{tray}"'


def enable_startup(password: str) -> None:
    if os.name != "nt":
        raise RuntimeError("Start with Windows is only supported on Windows.")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_VALUE, 0, winreg.REG_SZ, _command())
    config = EncryptedDatabase(password)._data
    config["settings"]["run_on_startup"] = True
    EncryptedDatabase(password).save_dict(config)


def disable_startup(password: str) -> None:
    if os.name != "nt":
        raise RuntimeError("Start with Windows is only supported on Windows.")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, APP_VALUE)
        except FileNotFoundError:
            pass
    config = EncryptedDatabase(password)._data
    config["settings"]["run_on_startup"] = False
    EncryptedDatabase(password).save_dict(config)


def install_scheduled_task(password: str, launch_tray: bool = True) -> None:
    """Create an at-logon scheduled task for the current user.

    This is stronger than the Run key and can be created with highest privileges
    when the caller is elevated.
    """
    if os.name != "nt":
        raise RuntimeError("Scheduled tasks are only supported on Windows.")
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
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "schtasks create failed")
    config = EncryptedDatabase(password)._data
    config["settings"]["run_on_startup"] = True
    config["settings"]["startup_task"] = TASK_NAME
    EncryptedDatabase(password).save_dict(config)


def uninstall_scheduled_task(password: str | None = None) -> None:
    if os.name != "nt":
        raise RuntimeError("Scheduled tasks are only supported on Windows.")
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and "cannot find" not in (result.stderr + result.stdout).lower():
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "schtasks delete failed")
    if password:
        config = EncryptedDatabase(password)._data
        config["settings"]["run_on_startup"] = False
        config["settings"]["startup_task"] = ""
        EncryptedDatabase(password).save_dict(config)
