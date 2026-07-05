#!/usr/bin/env bash
set -euo pipefail

rm -rf "${HOME}/.local/share/windslock"
rm -f "${HOME}/.local/bin/windslock" "${HOME}/.local/bin/windslock-tray" "${HOME}/.local/bin/windslock-proxy"
rm -f "${HOME}/.local/share/applications/windslock.desktop"
rm -f "${HOME}/.local/share/applications/windslock-tray.desktop"
rm -f "${HOME}/.local/share/applications/windslock-proxy.desktop"
rm -f "${HOME}/.local/share/icons/hicolor/256x256/apps/windslock.png"

echo "Windslock user install removed."
