"""Small Windows DPAPI wrapper used for local machine/user secrets.

DPAPI is only available on Windows. The helpers intentionally fail closed on
other platforms so tests and non-Windows development do not accidentally store
secrets in a weaker fallback.
"""

import ctypes
from ctypes import wintypes
import os


class DPAPIUnavailable(RuntimeError):
    pass


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _require_windows() -> None:
    if os.name != "nt":
        raise DPAPIUnavailable("Windows DPAPI is only available on Windows.")


def _blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    return blob, buffer


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)


def protect(data: bytes, description: str = "Windslock local secret") -> bytes:
    """Protect bytes for the current Windows user using DPAPI."""
    _require_windows()
    in_blob, _buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        description,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    return _bytes_from_blob(out_blob)


def unprotect(data: bytes) -> bytes:
    """Unprotect bytes that were protected for the current Windows user."""
    _require_windows()
    in_blob, _buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    return _bytes_from_blob(out_blob)
