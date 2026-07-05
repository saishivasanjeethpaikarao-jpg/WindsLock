"""Website blocking by domain using reversible hosts-file entries."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess

import audit_log
import config as cfg
from database import EncryptedDatabase
import override_manager


HOSTS_BEGIN = "# BEGIN WINDSLOCK BLOCKS"
HOSTS_END = "# END WINDSLOCK BLOCKS"
HOSTS_IPV4 = "0.0.0.0"
HOSTS_IPV6 = "::1"
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def normalize_domain(domain: str) -> str:
    cleaned = domain.strip().lower()
    cleaned = cleaned.removeprefix("http://").removeprefix("https://").split("/")[0]
    cleaned = cleaned.removeprefix("www.")
    if not DOMAIN_RE.match(cleaned):
        raise ValueError(f"Invalid domain: {domain}")
    return cleaned


def add_blocked_site(domain: str, password: str) -> None:
    normalized = normalize_domain(domain)
    config = EncryptedDatabase(password)._data
    sites = list(config.get("blocked_sites", []))
    if normalized not in sites:
        sites.append(normalized)
        config["blocked_sites"] = sorted(sites)
        EncryptedDatabase(password).save_dict(config)


def remove_blocked_site(domain: str, password: str) -> None:
    normalized = normalize_domain(domain)
    config = EncryptedDatabase(password)._data
    config["blocked_sites"] = [site for site in config.get("blocked_sites", []) if site != normalized]
    EncryptedDatabase(password).save_dict(config)


def list_blocked_sites(password: str) -> list[str]:
    return list(EncryptedDatabase(password)._data.get("blocked_sites", []))


def get_default_hosts_path() -> Path:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return Path(system_root) / "System32" / "drivers" / "etc" / "hosts"


def domain_variants(domain: str) -> list[str]:
    """Hosts has no wildcard support, so add useful browser-facing variants."""
    normalized = normalize_domain(domain)
    variants = {normalized}
    for prefix in ("www.", "m."):
        if not normalized.startswith(prefix):
            variants.add(prefix + normalized)
    return sorted(variants)


def build_hosts_block(domains: list[str]) -> str:
    lines = [HOSTS_BEGIN]
    names: set[str] = set()
    for domain in domains:
        names.update(domain_variants(domain))
    for domain in sorted(names):
        lines.append(f"{HOSTS_IPV4} {domain}")
        lines.append(f"{HOSTS_IPV6} {domain}")
    lines.append(HOSTS_END)
    return "\n".join(lines) + "\n"


def _strip_existing_block(text: str) -> str:
    begin = text.find(HOSTS_BEGIN)
    end = text.find(HOSTS_END)
    if begin == -1 or end == -1 or end < begin:
        return text.rstrip() + ("\n" if text.strip() else "")
    end += len(HOSTS_END)
    stripped = (text[:begin] + text[end:]).strip()
    return stripped + ("\n" if stripped else "")


def apply_hosts_block(password: str, hosts_path: str | Path | None = None) -> Path:
    """Apply current blocked sites to hosts file. Requires admin on Windows."""
    config = EncryptedDatabase(password)._data
    path = apply_hosts_block_with_config(config, hosts_path)
    config["settings"]["website_hosts_applied"] = bool(config.get("blocked_sites", []))
    audit_log.add_event(
        config,
        "site",
        "hosts",
        "applied",
        f"domains={len(config.get('blocked_sites', []))} path={path}",
    )
    EncryptedDatabase(password).save_dict(config)
    if hosts_path is None:
        flush_dns_cache()
    return path


def apply_hosts_block_with_config(config: dict, hosts_path: str | Path | None = None) -> Path:
    """Apply site rules from a decrypted config object."""
    path = Path(hosts_path) if hosts_path else get_default_hosts_path()
    original = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    updated = _strip_existing_block(original)
    override_manager.process_overrides(config)
    domains = [
        domain
        for domain in config.get("blocked_sites", [])
        if not override_manager.is_overridden(config, "site", domain)
    ]
    if domains:
        updated += "\n" + build_hosts_block(domains)
    path.write_text(updated, encoding="utf-8")
    return path


def flush_dns_cache() -> bool:
    """Flush Windows DNS cache after hosts changes. Safe no-op elsewhere."""
    if os.name != "nt":
        return False
    try:
        subprocess.run(["ipconfig", "/flushdns"], check=False, capture_output=True, text=True)
        return True
    except OSError:
        return False


def hosts_contains_rules(domains: list[str], hosts_path: str | Path | None = None) -> bool:
    path = Path(hosts_path) if hosts_path else get_default_hosts_path()
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if HOSTS_BEGIN.lower() not in text or HOSTS_END.lower() not in text:
        return False
    expected = build_hosts_block(domains).lower().splitlines()
    return all(line in text for line in expected if line and not line.startswith("#"))


def website_block_status(password: str, hosts_path: str | Path | None = None) -> dict[str, object]:
    config = EncryptedDatabase(password)._data
    path = Path(hosts_path) if hosts_path else get_default_hosts_path()
    domains = list(config.get("blocked_sites", []))
    marker_present = False
    rules_present = False
    writable = False
    error = ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        marker_present = HOSTS_BEGIN in text and HOSTS_END in text
        rules_present = hosts_contains_rules(domains, path) if domains else not marker_present
        with path.open("a", encoding="utf-8"):
            writable = True
    except PermissionError:
        error = "admin_required"
    except OSError as exc:
        error = str(exc)
    return {
        "hosts_path": str(path),
        "domain_count": len(domains),
        "marker_present": marker_present,
        "rules_present": rules_present,
        "writable": writable,
        "error": error,
    }


def rollback_hosts_block(hosts_path: str | Path | None = None) -> Path:
    """Remove only Windslock-managed hosts entries."""
    path = Path(hosts_path) if hosts_path else get_default_hosts_path()
    original = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    path.write_text(_strip_existing_block(original), encoding="utf-8")
    if hosts_path is None:
        flush_dns_cache()
    return path
