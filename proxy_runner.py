"""Packaged entry point for the Windslock path-level proxy."""

from __future__ import annotations

from pathlib import Path

from mitmproxy.tools.main import mitmweb


def main() -> int | None:
    addon = Path(__file__).with_name("proxy_addon.py")
    return mitmweb(
        [
            "--listen-host",
            "127.0.0.1",
            "--listen-port",
            "8080",
            "-s",
            str(addon),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
