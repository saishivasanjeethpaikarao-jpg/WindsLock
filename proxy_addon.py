"""mitmproxy addon for Windslock path-level website blocking.

Run with:
  mitmproxy -s proxy_addon.py

Browsers must be configured to use the proxy and trust mitmproxy's local CA
certificate before HTTPS paths can be inspected.
"""

from __future__ import annotations

from mitmproxy import http

import audit_log
import config as cfg
import focus_manager
import override_manager
import url_rule_engine


BLOCK_HTML = b"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Blocked by Windslock</title></head>
<body style="font-family:Segoe UI,Arial,sans-serif;margin:40px;line-height:1.45">
<h1>Blocked by Windslock</h1>
<p>This URL path is blocked by your local Windslock rules.</p>
</body>
</html>"""


class WindslockProxyAddon:
    def request(self, flow: http.HTTPFlow) -> None:
        try:
            config = cfg.load_config_for_background()
        except Exception:
            return

        changed = override_manager.process_overrides(config)
        if not focus_manager.should_enforce(config):
            if changed:
                try:
                    cfg.save_config_for_background(config)
                except Exception:
                    pass
            return

        match = url_rule_engine.match_url(flow.request.pretty_url, config)
        if match.blocked and match.rule:
            target = f"{match.rule['domain']}{match.rule['path_prefix']}"
            audit_log.add_event(config, "url_path", target, "blocked", flow.request.pretty_url)
            changed = True
            flow.response = http.Response.make(
                403,
                BLOCK_HTML,
                {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"},
            )

        if changed:
            try:
                cfg.save_config_for_background(config)
            except Exception:
                pass


addons = [WindslockProxyAddon()]
