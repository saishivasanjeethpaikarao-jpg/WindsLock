"""Brand constants and asset paths for Windslock."""

from __future__ import annotations

from pathlib import Path
import sys


APP_NAME = "Windslock"
APP_TAGLINE = "Focus Security for Windows"
APP_DESCRIPTION = "Professional app, website, and folder locking for Windows focus."

BRAND_NAVY = "#111827"
BRAND_GREEN = "#22C55E"
BRAND_BLUE = "#2563EB"
BRAND_SLATE = "#334155"


def project_root() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


def assets_dir() -> Path:
    return project_root() / "assets"


def asset_path(name: str) -> Path:
    return assets_dir() / name


def logo_png() -> Path:
    return asset_path("windslock_logo.png")


def icon_ico() -> Path:
    return asset_path("windslock.ico")
