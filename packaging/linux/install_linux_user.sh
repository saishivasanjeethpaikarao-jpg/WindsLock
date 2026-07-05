#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${HOME}/.local/share/windslock"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"

mkdir -p "${APP_DIR}" "${BIN_DIR}" "${DESKTOP_DIR}" "${ICON_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cp -R "${ROOT_DIR}/"* "${APP_DIR}/"
cp "${ROOT_DIR}/assets/windslock_icon.png" "${ICON_DIR}/windslock.png"
cp "${ROOT_DIR}/packaging/linux/windslock.desktop" "${DESKTOP_DIR}/windslock.desktop"
cp "${ROOT_DIR}/packaging/linux/windslock-tray.desktop" "${DESKTOP_DIR}/windslock-tray.desktop"
cp "${ROOT_DIR}/packaging/linux/windslock-proxy.desktop" "${DESKTOP_DIR}/windslock-proxy.desktop"

cat > "${BIN_DIR}/windslock" <<EOF
#!/usr/bin/env bash
"${APP_DIR}/Windslock/Windslock" "\$@"
EOF

cat > "${BIN_DIR}/windslock-tray" <<EOF
#!/usr/bin/env bash
"${APP_DIR}/WindslockTray/WindslockTray" "\$@"
EOF

cat > "${BIN_DIR}/windslock-enforcer" <<EOF
#!/usr/bin/env bash
"${APP_DIR}/WindslockEnforcer/WindslockEnforcer" "\$@"
EOF

cat > "${BIN_DIR}/windslock-proxy" <<EOF
#!/usr/bin/env bash
"${APP_DIR}/WindslockProxy/WindslockProxy" "\$@"
EOF

chmod +x "${BIN_DIR}/windslock" "${BIN_DIR}/windslock-tray" "${BIN_DIR}/windslock-enforcer" "${BIN_DIR}/windslock-proxy"
chmod +x "${APP_DIR}/Windslock/Windslock" "${APP_DIR}/WindslockTray/WindslockTray" "${APP_DIR}/WindslockEnforcer/WindslockEnforcer" "${APP_DIR}/WindslockProxy/WindslockProxy"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${DESKTOP_DIR}" || true
fi

echo "Windslock installed for ${USER}."
echo "Make sure ${BIN_DIR} is on PATH, then run: windslock"
echo "Path-level proxy command: windslock-proxy"
