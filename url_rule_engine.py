"""Granular URL path blocking rules for proxy-based enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import config as cfg
from database import EncryptedDatabase
import override_manager
import site_blocker


@dataclass(frozen=True)
class UrlMatch:
    blocked: bool
    rule: dict[str, str] | None = None
    reason: str = ""


def normalize_path_prefix(path_prefix: str) -> str:
    value = path_prefix.strip()
    if not value:
        raise ValueError("Path prefix cannot be empty.")
    if not value.startswith("/"):
        value = "/" + value
    return value


def normalize_rule(domain: str, path_prefix: str) -> dict[str, str]:
    return {
        "domain": site_blocker.normalize_domain(domain),
        "path_prefix": normalize_path_prefix(path_prefix),
    }


def add_path_rule(domain: str, path_prefix: str, password: str) -> None:
    rule = normalize_rule(domain, path_prefix)
    config = EncryptedDatabase(password)._data
    rules = list(config.get("blocked_url_paths", []))
    if rule not in rules:
        rules.append(rule)
        config["blocked_url_paths"] = sorted(rules, key=lambda item: (item["domain"], item["path_prefix"]))
        EncryptedDatabase(password).save_dict(config)


def remove_path_rule(domain: str, path_prefix: str, password: str) -> None:
    rule = normalize_rule(domain, path_prefix)
    config = EncryptedDatabase(password)._data
    config["blocked_url_paths"] = [item for item in config.get("blocked_url_paths", []) if item != rule]
    EncryptedDatabase(password).save_dict(config)


def list_path_rules(password: str) -> list[dict[str, str]]:
    return list(EncryptedDatabase(password)._data.get("blocked_url_paths", []))


def match_url(url: str, config: dict) -> UrlMatch:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path or "/"
    for rule in config.get("blocked_url_paths", []):
        domain = rule["domain"]
        if host == domain or host.endswith("." + domain):
            target = f"{domain}{rule['path_prefix']}"
            if override_manager.is_overridden(config, "url_path", target):
                continue
            if path == rule["path_prefix"] or path.startswith(rule["path_prefix"].rstrip("/") + "/"):
                return UrlMatch(True, rule, "path_prefix")
    return UrlMatch(False)
