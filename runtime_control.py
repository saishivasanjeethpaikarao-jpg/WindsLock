"""Runtime helpers shared by the CLI and desktop UI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import app_blocker
import config as cfg


def enforcer_script() -> Path:
    return Path(__file__).with_name("enforcer.py")


def gui_script() -> Path:
    return Path(__file__).with_name("gui.py")


def tray_script() -> Path:
    return Path(__file__).with_name("tray_app.py")


def proxy_script() -> Path:
    return Path(__file__).with_name("proxy_addon.py")


def pythonw_executable() -> Path:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else exe


def enforcer_lock_path() -> Path:
    return cfg.ensure_app_dir() / "enforcer.lock"


def read_enforcer_pid() -> int | None:
    path = enforcer_lock_path()
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def is_enforcer_running() -> bool:
    pid = read_enforcer_pid()
    if not pid or app_blocker.psutil is None:
        return False
    return app_blocker.psutil.pid_exists(pid)


def start_enforcer() -> None:
    subprocess.Popen([str(pythonw_executable()), str(enforcer_script())], close_fds=True)


def open_gui() -> None:
    subprocess.Popen([str(pythonw_executable()), str(gui_script())], close_fds=True)


def start_proxy() -> None:
    mitmweb = Path(sys.executable).with_name("mitmweb.exe")
    if not mitmweb.exists():
        raise RuntimeError("mitmweb.exe was not found. Install requirements first.")
    subprocess.Popen(
        [str(mitmweb), "--listen-host", "127.0.0.1", "--listen-port", "8080", "-s", str(proxy_script())],
        close_fds=True,
    )


def stop_enforcer() -> bool:
    pid = read_enforcer_pid()
    if not pid or app_blocker.psutil is None:
        return False
    try:
        proc = app_blocker.psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except app_blocker.psutil.TimeoutExpired:
            proc.kill()
        return True
    except app_blocker.psutil.Error:
        return False
