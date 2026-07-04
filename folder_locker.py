"""Folder locking by encrypting a folder into a reversible .locked file."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
import shutil
import zipfile

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import audit_log
import config as cfg


ITERATIONS = 390000


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _is_dangerous_folder(path: Path) -> bool:
    resolved = path.resolve()
    app_dir = cfg.get_app_dir().resolve()
    if resolved.parent == resolved:
        return True
    protected_names = {"windows", "program files", "program files (x86)", "users"}
    if resolved.name.lower() in protected_names:
        return True
    try:
        resolved.relative_to(app_dir)
        return True
    except ValueError:
        return False


def _zip_folder(folder_path: Path) -> bytes:
    buffer = io.BytesIO()
    parent = folder_path.parent
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                full_path = Path(root) / file_name
                arcname = full_path.relative_to(parent)
                zf.write(full_path, arcname.as_posix())
    return buffer.getvalue()


def _safe_extract(zf: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in zf.infolist():
        target = (destination / member.filename).resolve()
        try:
            target.relative_to(destination)
        except ValueError as exc:
            raise ValueError(f"Unsafe archive path: {member.filename}") from exc
    zf.extractall(destination)


def lock_folder(folder_path: str, password: str) -> str:
    folder = Path(folder_path).expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")
    if _is_dangerous_folder(folder):
        raise ValueError(f"Refusing to lock dangerous or app-internal folder: {folder}")

    locked_path = folder.with_name(folder.name + ".locked")
    if locked_path.exists():
        raise FileExistsError(f"Locked file already exists: {locked_path}")

    zipped = _zip_folder(folder)
    folder_salt = os.urandom(16)
    encrypted = Fernet(_derive_key(password, folder_salt)).encrypt(zipped)

    temp_path = locked_path.with_suffix(locked_path.suffix + ".tmp")
    with temp_path.open("wb") as handle:
        handle.write(folder_salt)
        handle.write(encrypted)
        handle.flush()
        os.fsync(handle.fileno())

    # Verify we can decrypt and read the archive before removing source files.
    with temp_path.open("rb") as handle:
        verify_salt = handle.read(16)
        verify_payload = handle.read()
    decrypted = Fernet(_derive_key(password, verify_salt)).decrypt(verify_payload)
    with zipfile.ZipFile(io.BytesIO(decrypted)) as zf:
        bad_file = zf.testzip()
        if bad_file:
            raise ValueError(f"Archive verification failed at {bad_file}")

    os.replace(temp_path, locked_path)
    shutil.rmtree(folder)

    config = cfg.load_config(password)
    config["locked_folders"].append({"original_path": str(folder), "locked_path": str(locked_path)})
    audit_log.add_event(config, "folder", str(folder), "locked", str(locked_path))
    cfg.save_config(config, password)
    return str(locked_path)


def unlock_folder(locked_path: str, password: str, restore_path: str | None = None) -> str:
    locked = Path(locked_path).expanduser().resolve()
    if not locked.exists():
        raise FileNotFoundError(str(locked))

    with locked.open("rb") as handle:
        folder_salt = handle.read(16)
        encrypted = handle.read()

    try:
        decrypted = Fernet(_derive_key(password, folder_salt)).decrypt(encrypted)
    except InvalidToken as exc:
        raise ValueError("Wrong password or corrupted locked folder.") from exc

    config = cfg.load_config(password)
    match = next((f for f in config["locked_folders"] if Path(f["locked_path"]).resolve() == locked), None)
    if restore_path is None:
        restore = Path(match["original_path"]).expanduser().resolve() if match else locked.with_suffix("")
    else:
        restore = Path(restore_path).expanduser().resolve()
    if _is_dangerous_folder(restore):
        raise ValueError(f"Refusing to restore into dangerous or app-internal folder: {restore}")
    if restore.exists():
        raise FileExistsError(f"Restore path already exists: {restore}")

    restore.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(decrypted)) as zf:
        _safe_extract(zf, restore.parent)

    if not restore.exists():
        raise ValueError("Unlock completed but restored folder was not found.")

    locked.unlink()
    config["locked_folders"] = [
        f for f in config["locked_folders"] if Path(f["locked_path"]).resolve() != locked
    ]
    audit_log.add_event(config, "folder", str(restore), "unlocked", str(locked))
    cfg.save_config(config, password)
    return str(restore)
