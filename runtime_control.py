"""Runtime helpers shared by the CLI and desktop UI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

import app_blocker
import config as cfg

def _popen_hidden(args: list[str]) -> subprocess.Popen:
    kwargs = {"close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, **kwargs)


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


def enforcer_error_path() -> Path:
    return cfg.ensure_app_dir() / "enforcer_error.log"


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
        if not proc.is_running():
            _clear_stale_lock()
            return False
    except app_blocker.psutil.Error:
        _clear_stale_lock()
        return False

    try:
        name = (proc.name() or "").lower()
        cmdline = " ".join(proc.cmdline()).lower()
    except app_blocker.psutil.AccessDenied:
        # The lock file was written by Windslock and the PID is alive. Some
        # packaged/elevated Windows processes do not expose cmdline reliably.
        return True
    except app_blocker.psutil.Error:
        return True

    looks_like_enforcer = (
        "windslockenforcer" in name
        or "windslockenforcer" in cmdline
        or "enforcer.py" in cmdline
    )
    if not looks_like_enforcer:
        _clear_stale_lock()
        return False
    return True


def start_enforcer() -> None:
    if is_enforcer_running():
        return
    _clear_old_error_log()
    packaged_enforcer = _packaged_executable("WindslockEnforcer")
    if packaged_enforcer:
        _popen_hidden([str(packaged_enforcer)])
        return
    if getattr(sys, "frozen", False):
        raise RuntimeError("WindslockEnforcer.exe was not found next to the installed app.")
    _popen_hidden([str(pythonw_executable()), str(enforcer_script())])


def start_enforcer_and_wait(timeout: float = 15.0) -> bool:
    start_enforcer()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_enforcer_running():
            return True
        time.sleep(0.3)
    return is_enforcer_running()


def last_enforcer_error(max_chars: int = 1200) -> str:
    path = enforcer_error_path()
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    return text[-max_chars:]


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
        candidates.append(exe.parent / app_name / name)
        candidates.append(exe.parent.parent / app_name / name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _clear_stale_lock() -> None:
    try:
        enforcer_lock_path().unlink(missing_ok=True)
    except OSError:
        pass


def _clear_old_error_log() -> None:
    try:
        enforcer_error_path().unlink(missing_ok=True)
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


def is_lock_screen_running(target: str) -> bool:
    if app_blocker.psutil is None:
        return False
    target_normalized = target.replace("\\", "/").lower()
    for proc in app_blocker.psutil.process_iter(["name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            cmdline_str = " ".join(cmdline).replace("\\", "/").lower()
            if ("gui.py" in cmdline_str or "windslock" in cmdline_str) and "--lock-screen" in cmdline_str:
                if target_normalized in cmdline_str:
                    return True
        except Exception:
            continue
    return False


def open_lock_screen(target: str) -> None:
    packaged_gui = _packaged_executable("Windslock")
    if packaged_gui and packaged_gui != Path(sys.executable):
        subprocess.Popen([str(packaged_gui), "--lock-screen", target], close_fds=True)
        return
    subprocess.Popen([str(pythonw_executable()), str(gui_script()), "--lock-screen", target], close_fds=True)
