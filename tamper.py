"""Basic tamper-resistance helpers.

These controls raise the bar for casual editing. They are not a boundary
against the same Windows admin user.
"""

from __future__ import annotations

import os
import subprocess

import config as cfg
from database import EncryptedDatabase


def harden_config_acl(password: str) -> str:
    """Restrict the app data directory ACL to the current user and admins."""
    if os.name != "nt":
        raise RuntimeError("ACL hardening is only supported on Windows.")
    app_dir = cfg.ensure_app_dir()
    command = [
        "icacls",
        str(app_dir),
        "/inheritance:r",
        "/grant:r",
        f"{os.getlogin()}:(OI)(CI)F",
        "Administrators:(OI)(CI)F",
        "SYSTEM:(OI)(CI)F",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "icacls failed")
    config = EncryptedDatabase(password)._data
    config["settings"]["tamper_hardened"] = True
    EncryptedDatabase(password).save_dict(config)
    return result.stdout.strip()
