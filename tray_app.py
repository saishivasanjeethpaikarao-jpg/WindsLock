"""Windslock tray controller."""

from __future__ import annotations

import sys
import threading
import webbrowser

from PIL import Image, ImageDraw
import pystray

import brand
import config as cfg
import runtime_control


def _icon_image() -> Image.Image:
    if brand.asset_path("windslock_icon.png").exists():
        return Image.open(brand.asset_path("windslock_icon.png"))
    image = Image.new("RGBA", (64, 64), (28, 36, 54, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, 28, 48, 52), radius=6, fill=(74, 222, 128, 255))
    draw.arc((20, 10, 44, 38), 180, 360, fill=(74, 222, 128, 255), width=6)
    draw.rectangle((24, 28, 40, 34), fill=(74, 222, 128, 255))
    return image


def _status_text() -> str:
    state = "running" if runtime_control.is_enforcer_running() else "stopped"
    try:
        config = cfg.load_config_for_background()
        apps = len(config.get("locked_apps", []))
        sites = len(config.get("blocked_sites", []))
        paths = len(config.get("blocked_url_paths", []))
        return f"Enforcer {state} | Apps {apps} | Sites {sites} | Paths {paths}"
    except Exception:
        return f"Enforcer {state} | Unlock in Windslock to enable background mode"


def _notify(icon: pystray.Icon, title: str, message: str) -> None:
    try:
        icon.notify(message, title)
    except Exception:
        pass


def _run_async(icon: pystray.Icon, title: str, fn) -> None:
    def worker():
        try:
            fn()
            _notify(icon, title, "Done")
        except Exception as exc:
            _notify(icon, title, str(exc))
        icon.update_menu()

    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    icon = pystray.Icon(brand.APP_NAME, _icon_image(), brand.APP_NAME)

    def open_ui(_icon, _item):
        runtime_control.open_gui()

    def start_enforcer(_icon, _item):
        _run_async(icon, "Windslock", runtime_control.start_enforcer)

    def stop_enforcer(_icon, _item):
        _run_async(icon, "Windslock", runtime_control.stop_enforcer)

    def start_proxy(_icon, _item):
        _run_async(icon, "Windslock Proxy", runtime_control.start_proxy)

    def cert_help(_icon, _item):
        webbrowser.open("http://mitm.it")

    def quit_app(_icon, _item):
        icon.stop()

    def status_item(_item):
        return _status_text()

    icon.menu = pystray.Menu(
        pystray.MenuItem(status_item, None, enabled=False),
        pystray.MenuItem("Open Windslock", open_ui, default=True),
        pystray.MenuItem("Start enforcement", start_enforcer),
        pystray.MenuItem("Stop enforcement", stop_enforcer),
        pystray.MenuItem("Start path-level proxy", start_proxy),
        pystray.MenuItem("Proxy certificate help", cert_help),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit tray", quit_app),
    )
    icon.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
