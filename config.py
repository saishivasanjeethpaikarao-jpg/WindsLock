"""Encrypted configuration and master credential handling for Windslock.

The app config is encrypted with a random data key. The master password and
emergency recovery codes unlock encrypted copies of that data key; the password
itself is never stored. Optional background enforcement stores only the data
key protected by Windows DPAPI for the current user.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

import secure_store


APP_NAME = "Windslock"
ENV_APP_DIR = "WINDSLOCK_APP_DIR"
ITERATIONS = 390000
METADATA_VERSION = 2
RECOVERY_CODE_COUNT = 6
MAX_AUDIT_EVENTS = 500

DEFAULT_CONFIG: dict[str, Any] = {
    "locked_apps": [],
    "locked_folders": [],
    "blocked_sites": [],
    "blocked_url_paths": [],
    "override_requests": [],
    "focus_schedules": [],
    "settings": {
        "run_on_startup": False,
        "background_enabled": False,
        "website_hosts_applied": False,
        "tamper_hardened": False,
        "override_phrase": "I understand this is temporary and I will return to focus",
        "override_cooldown_minutes": 5,
        "override_window_minutes": 10,
        "schedule_only_mode": False,
        "focus_session_until": "",
    },
    "audit_log": [],
}


def get_app_dir() -> Path:
    override = os.environ.get(ENV_APP_DIR)
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def get_config_path() -> Path:
    return get_app_dir() / "config.enc"


def get_metadata_path() -> Path:
    return get_app_dir() / "security.json"


def get_legacy_salt_path() -> Path:
    return get_app_dir() / "salt.bin"


def get_service_key_path() -> Path:
    return get_app_dir() / "service_key.dpapi"


def ensure_app_dir() -> Path:
    app_dir = get_app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _atomic_write(path: Path, data: bytes) -> None:
    ensure_app_dir()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _load_metadata() -> dict[str, Any]:
    with get_metadata_path().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_metadata(metadata: dict[str, Any]) -> None:
    payload = json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8")
    _atomic_write(get_metadata_path(), payload)


def _derive_bytes(secret: str, salt: bytes, purpose: bytes, iterations: int | None = None) -> bytes:
    if iterations is None:
        iterations = ITERATIONS
    return hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt + b":" + purpose,
        iterations,
        dklen=32,
    )


def _derive_fernet_key(secret: str, salt: bytes, purpose: bytes, iterations: int | None = None) -> bytes:
    return base64.urlsafe_b64encode(_derive_bytes(secret, salt, purpose, iterations))


def _password_verifier(password: str, salt: bytes, iterations: int | None = None) -> bytes:
    return _derive_bytes(password, salt, b"verify", iterations)


def _encrypt_data_key(secret: str, salt: bytes, data_key: bytes, purpose: bytes) -> str:
    key = _derive_fernet_key(secret, salt, purpose)
    return Fernet(key).encrypt(data_key).decode("ascii")


def _decrypt_data_key(secret: str, salt: bytes, token: str, purpose: bytes) -> bytes:
    key = _derive_fernet_key(secret, salt, purpose)
    return Fernet(key).decrypt(token.encode("ascii"))


def _merge_defaults(config: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_CONFIG)
    for key, value in config.items():
        if key == "settings" and isinstance(value, dict):
            merged["settings"].update(value)
        else:
            merged[key] = value
    merged["locked_apps"] = _normalize_app_rules(merged.get("locked_apps", []))
    merged["blocked_sites"] = _normalize_site_rules(merged.get("blocked_sites", []))
    merged["blocked_url_paths"] = _normalize_url_path_rules(merged.get("blocked_url_paths", []))
    merged["override_requests"] = list(merged.get("override_requests", []))
    merged["focus_schedules"] = _normalize_focus_schedules(merged.get("focus_schedules", []))
    merged["audit_log"] = list(merged.get("audit_log", []))[-MAX_AUDIT_EVENTS:]
    return merged


def _normalize_app_rules(rules: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in rules:
        if isinstance(item, str):
            value = item.strip()
            mode = "path" if any(sep in value for sep in ("/", "\\")) else "name"
        elif isinstance(item, dict):
            value = str(item.get("value") or item.get("name") or item.get("path") or "").strip()
            mode = str(item.get("mode") or ("path" if any(sep in value for sep in ("/", "\\")) else "name"))
        else:
            continue
        if not value:
            continue
        mode = "path" if mode.lower() == "path" else "name"
        canonical = os.path.normcase(os.path.abspath(value)) if mode == "path" else value.lower()
        key = (mode, canonical)
        if key not in seen:
            normalized.append({"mode": mode, "value": canonical})
            seen.add(key)
    return normalized


def _normalize_site_rules(sites: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in sites:
        domain = str(item).strip().lower()
        domain = domain.removeprefix("http://").removeprefix("https://").split("/")[0]
        domain = domain.removeprefix("www.")
        if domain and domain not in seen:
            normalized.append(domain)
            seen.add(domain)
    return normalized


def _normalize_url_path_rules(rules: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in rules:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain", "")).strip().lower()
        domain = domain.removeprefix("http://").removeprefix("https://").split("/")[0]
        domain = domain.removeprefix("www.")
        path_prefix = str(item.get("path_prefix", "")).strip()
        if not domain or not path_prefix:
            continue
        if not path_prefix.startswith("/"):
            path_prefix = "/" + path_prefix
        key = (domain, path_prefix)
        if key not in seen:
            normalized.append({"domain": domain, "path_prefix": path_prefix})
            seen.add(key)
    return normalized


def _normalize_focus_schedules(schedules: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in schedules:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "Focus")).strip() or "Focus"
        days = [int(day) for day in item.get("days", []) if str(day).isdigit() and 0 <= int(day) <= 6]
        start = str(item.get("start", "")).strip()
        end = str(item.get("end", "")).strip()
        enabled = bool(item.get("enabled", True))
        if days and _looks_like_hhmm(start) and _looks_like_hhmm(end):
            normalized.append({"name": name, "days": days, "start": start, "end": end, "enabled": enabled})
    return normalized


def _looks_like_hhmm(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return False
    hour, minute = int(parts[0]), int(parts[1])
    return 0 <= hour <= 23 and 0 <= minute <= 59


def master_password_is_set() -> bool:
    return get_metadata_path().exists() and get_config_path().exists()


def set_master_password(password: str) -> list[str]:
    """First-time setup. Returns one-time recovery codes to show the user."""
    if len(password) < 8:
        raise ValueError("Use at least 8 characters for the master password.")
    if master_password_is_set() or get_legacy_salt_path().exists():
        raise RuntimeError("Master password already set. Use change_master_password() instead.")

    data_key = Fernet.generate_key()
    password_salt = os.urandom(16)
    recovery_codes = generate_recovery_codes()
    recovery_entries = []
    for code in recovery_codes:
        salt = os.urandom(16)
        recovery_entries.append(
            {
                "id": secrets.token_hex(4),
                "salt": _b64(salt),
                "verifier": _b64(_password_verifier(code, salt)),
                "envelope": _encrypt_data_key(code, salt, data_key, b"recovery-envelope"),
            }
        )

    metadata = {
        "version": METADATA_VERSION,
        "password": {
            "iterations": ITERATIONS,
            "salt": _b64(password_salt),
            "verifier": _b64(_password_verifier(password, password_salt)),
            "envelope": _encrypt_data_key(password, password_salt, data_key, b"password-envelope"),
        },
        "recovery": recovery_entries,
    }
    _save_metadata(metadata)
    _save_config_with_data_key(copy.deepcopy(DEFAULT_CONFIG), data_key)
    return recovery_codes


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    codes = []
    for _ in range(count):
        raw = secrets.token_hex(6).upper()
        codes.append("-".join(raw[i : i + 4] for i in range(0, len(raw), 4)))
    return codes


def _unlock_data_key_with_password(password: str) -> bytes:
    metadata = _load_metadata()
    password_meta = metadata["password"]
    iterations = int(password_meta.get("iterations", ITERATIONS))
    salt = _unb64(password_meta["salt"])
    expected = _unb64(password_meta["verifier"])
    actual = _password_verifier(password, salt, iterations)
    if not hmac.compare_digest(expected, actual):
        raise InvalidToken()
    return _decrypt_data_key(password, salt, password_meta["envelope"], b"password-envelope")


def _unlock_data_key_with_recovery_code(recovery_code: str) -> tuple[bytes, dict[str, Any]]:
    metadata = _load_metadata()
    for entry in metadata.get("recovery", []):
        salt = _unb64(entry["salt"])
        expected = _unb64(entry["verifier"])
        actual = _password_verifier(recovery_code, salt)
        if hmac.compare_digest(expected, actual):
            data_key = _decrypt_data_key(recovery_code, salt, entry["envelope"], b"recovery-envelope")
            return data_key, entry
    raise InvalidToken()


def verify_password(password: str) -> bool:
    try:
        if master_password_is_set():
            _unlock_data_key_with_password(password)
        else:
            _load_legacy_config(password)
        return True
    except Exception:
        return False


def load_config(password: str) -> dict[str, Any]:
    if master_password_is_set():
        data_key = _unlock_data_key_with_password(password)
        return _load_config_with_data_key(data_key)
    return _load_legacy_config(password)


def save_config(config: dict[str, Any], password: str, _salt_override: bytes | None = None) -> None:
    del _salt_override
    if master_password_is_set():
        data_key = _unlock_data_key_with_password(password)
        _save_config_with_data_key(_merge_defaults(config), data_key)
        return
    _save_legacy_config(config, password)


def change_master_password(old_password: str, new_password: str) -> list[str]:
    if len(new_password) < 8:
        raise ValueError("Use at least 8 characters for the new password.")
    data_key = _unlock_data_key_with_password(old_password)
    return _rotate_password_and_recovery(data_key, new_password)


def reset_password_with_recovery(recovery_code: str, new_password: str) -> list[str]:
    """Reset the master password using a recovery code and rotate all codes."""
    if len(new_password) < 8:
        raise ValueError("Use at least 8 characters for the new password.")
    data_key, _ = _unlock_data_key_with_recovery_code(recovery_code)
    return _rotate_password_and_recovery(data_key, new_password)


def _rotate_password_and_recovery(data_key: bytes, new_password: str) -> list[str]:
    password_salt = os.urandom(16)
    recovery_codes = generate_recovery_codes()
    recovery_entries = []
    for code in recovery_codes:
        salt = os.urandom(16)
        recovery_entries.append(
            {
                "id": secrets.token_hex(4),
                "salt": _b64(salt),
                "verifier": _b64(_password_verifier(code, salt)),
                "envelope": _encrypt_data_key(code, salt, data_key, b"recovery-envelope"),
            }
        )
    metadata = {
        "version": METADATA_VERSION,
        "password": {
            "iterations": ITERATIONS,
            "salt": _b64(password_salt),
            "verifier": _b64(_password_verifier(new_password, password_salt)),
            "envelope": _encrypt_data_key(new_password, password_salt, data_key, b"password-envelope"),
        },
        "recovery": recovery_entries,
    }
    _save_metadata(metadata)
    return recovery_codes


def _load_config_with_data_key(data_key: bytes) -> dict[str, Any]:
    encrypted = get_config_path().read_bytes()
    decrypted = Fernet(data_key).decrypt(encrypted)
    return _merge_defaults(json.loads(decrypted.decode("utf-8")))


def _save_config_with_data_key(config: dict[str, Any], data_key: bytes) -> None:
    payload = json.dumps(_merge_defaults(config), sort_keys=True).encode("utf-8")
    encrypted = Fernet(data_key).encrypt(payload)
    _atomic_write(get_config_path(), encrypted)


def enable_background_unlock(password: str) -> None:
    """Store the config data key protected by Windows DPAPI for enforcement."""
    data_key = _unlock_data_key_with_password(password)
    protected = secure_store.protect(data_key)
    _atomic_write(get_service_key_path(), protected)
    config = load_config(password)
    config["settings"]["background_enabled"] = True
    save_config(config, password)


def disable_background_unlock(password: str) -> None:
    _unlock_data_key_with_password(password)
    path = get_service_key_path()
    if path.exists():
        path.unlink()
    config = load_config(password)
    config["settings"]["background_enabled"] = False
    save_config(config, password)


def load_config_for_background() -> dict[str, Any]:
    protected = get_service_key_path().read_bytes()
    data_key = secure_store.unprotect(protected)
    return _load_config_with_data_key(data_key)


def save_config_for_background(config: dict[str, Any]) -> None:
    protected = get_service_key_path().read_bytes()
    data_key = secure_store.unprotect(protected)
    _save_config_with_data_key(config, data_key)


def _legacy_derive_key(password: str, salt: bytes) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32)
    return base64.urlsafe_b64encode(key)


def _load_legacy_config(password: str) -> dict[str, Any]:
    salt_path = get_legacy_salt_path()
    config_path = get_config_path()
    if not salt_path.exists() or not config_path.exists():
        raise FileNotFoundError("No Windslock config has been created yet.")
    salt = salt_path.read_bytes()
    key = _legacy_derive_key(password, salt)
    decrypted = Fernet(key).decrypt(config_path.read_bytes())
    return _merge_defaults(json.loads(decrypted.decode("utf-8")))


def _save_legacy_config(config: dict[str, Any], password: str) -> None:
    salt_path = get_legacy_salt_path()
    if not salt_path.exists():
        raise FileNotFoundError("Legacy salt is missing.")
    salt = salt_path.read_bytes()
    key = _legacy_derive_key(password, salt)
    encrypted = Fernet(key).encrypt(json.dumps(_merge_defaults(config)).encode("utf-8"))
    _atomic_write(get_config_path(), encrypted)


def migrate_legacy_store(password: str) -> list[str]:
    """Move an old salt.bin/config.enc store to the v2 recovery-code format."""
    if master_password_is_set():
        return []
    legacy_config = _load_legacy_config(password)
    data_key = Fernet.generate_key()
    password_salt = os.urandom(16)
    recovery_codes = generate_recovery_codes()
    recovery_entries = []
    for code in recovery_codes:
        salt = os.urandom(16)
        recovery_entries.append(
            {
                "id": secrets.token_hex(4),
                "salt": _b64(salt),
                "verifier": _b64(_password_verifier(code, salt)),
                "envelope": _encrypt_data_key(code, salt, data_key, b"recovery-envelope"),
            }
        )
    metadata = {
        "version": METADATA_VERSION,
        "password": {
            "iterations": ITERATIONS,
            "salt": _b64(password_salt),
            "verifier": _b64(_password_verifier(password, password_salt)),
            "envelope": _encrypt_data_key(password, password_salt, data_key, b"password-envelope"),
        },
        "recovery": recovery_entries,
    }
    _save_metadata(metadata)
    _save_config_with_data_key(legacy_config, data_key)
    legacy_salt = get_legacy_salt_path()
    if legacy_salt.exists():
        legacy_salt.replace(legacy_salt.with_suffix(".bin.legacy"))
    return recovery_codes
