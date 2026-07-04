"""Website blocking by domain using reversible hosts-file entries."""

from __future__ import annotations

import os
from pathlib import Path
import re

import config as cfg
import override_manager


HOSTS_BEGIN = "# BEGIN WINDSLOCK BLOCKS"
HOSTS_END = "# END WINDSLOCK BLOCKS"
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
    config = cfg.load_config(password)
    sites = list(config.get("blocked_sites", []))
    if normalized not in sites:
        sites.append(normalized)
        config["blocked_sites"] = sorted(sites)
        cfg.save_config(config, password)


def remove_blocked_site(domain: str, password: str) -> None:
    normalized = normalize_domain(domain)
    config = cfg.load_config(password)
    config["blocked_sites"] = [site for site in config.get("blocked_sites", []) if site != normalized]
    cfg.save_config(config, password)


def list_blocked_sites(password: str) -> list[str]:
    return list(cfg.load_config(password).get("blocked_sites", []))


def get_default_hosts_path() -> Path:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return Path(system_root) / "System32" / "drivers" / "etc" / "hosts"


def build_hosts_block(domains: list[str]) -> str:
    lines = [HOSTS_BEGIN]
    for domain in sorted({normalize_domain(d) for d in domains}):
        lines.append(f"0.0.0.0 {domain}")
        lines.append(f"0.0.0.0 www.{domain}")
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
    config = cfg.load_config(password)
    path = apply_hosts_block_with_config(config, hosts_path)
    config["settings"]["website_hosts_applied"] = bool(config.get("blocked_sites", []))
    cfg.save_config(config, password)
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


def rollback_hosts_block(hosts_path: str | Path | None = None) -> Path:
    """Remove only Windslock-managed hosts entries."""
    path = Path(hosts_path) if hosts_path else get_default_hosts_path()
    original = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    path.write_text(_strip_existing_block(original), encoding="utf-8")
    return path
