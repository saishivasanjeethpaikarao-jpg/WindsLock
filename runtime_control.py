"""Runtime helpers shared by the CLI and desktop UI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

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
    try:
        proc = app_blocker.psutil.Process(pid)
        name = (proc.name() or "").lower()
        cmdline = " ".join(proc.cmdline()).lower()
    except app_blocker.psutil.Error:
        _clear_stale_lock()
        return False
    looks_like_enforcer = (
        "windslockenforcer" in name
        or "windslockenforcer" in cmdline
        or "enforcer.py" in cmdline
    )
    if not looks_like_enforcer:
        _clear_stale_lock()
        return False
    return proc.is_running()


def start_enforcer() -> None:
    if is_enforcer_running():
        return
    packaged_enforcer = _packaged_executable("WindslockEnforcer")
    if packaged_enforcer:
        subprocess.Popen([str(packaged_enforcer)], close_fds=True)
        return
    subprocess.Popen([str(pythonw_executable()), str(enforcer_script())], close_fds=True)


def start_enforcer_and_wait(timeout: float = 4.0) -> bool:
    start_enforcer()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_enforcer_running():
            return True
        time.sleep(0.2)
    return is_enforcer_running()


def open_gui() -> None:
    packaged_gui = _packaged_executable("Windslock")
    if packaged_gui and packaged_gui != Path(sys.executable):
        subprocess.Popen([str(packaged_gui)], close_fds=True)
        return
    subprocess.Popen([str(pythonw_executable()), str(gui_script())], close_fds=True)


def start_proxy() -> None:
    packaged_proxy = _packaged_executable("WindslockProxy")
    if packaged_proxy:
        subprocess.Popen([str(packaged_proxy)], close_fds=True)
        return
    mitmweb = Path(sys.executable).with_name("mitmweb.exe")
    if not mitmweb.exists():
        mitmweb = Path(sys.executable).with_name("mitmweb")
    if not mitmweb.exists():
        raise RuntimeError("mitmweb was not found. Install requirements first.")
    subprocess.Popen(
        [str(mitmweb), "--listen-host", "127.0.0.1", "--listen-port", "8080", "-s", str(proxy_script())],
        close_fds=True,
    )


def _packaged_executable(app_name: str) -> Path | None:
    exe = Path(sys.executable)
    names = [f"{app_name}.exe", app_name]
    candidates = []
    for name in names:
        candidates.append(exe.with_name(name))
        candidates.append(exe.parent.parent / app_name / name)
        candidates.append(exe.parent / app_name / name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _clear_stale_lock() -> None:
    try:
        enforcer_lock_path().unlink(missing_ok=True)
    except OSError:
        pass


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
