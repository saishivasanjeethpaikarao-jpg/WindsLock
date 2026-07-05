#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python -m PyInstaller \
  --noconfirm \
  --windowed \
  --add-data "assets:assets" \
  --name Windslock \
  gui.py

python -m PyInstaller \
  --noconfirm \
  --windowed \
  --add-data "assets:assets" \
  --name WindslockTray \
  tray_app.py

python -m PyInstaller \
  --noconfirm \
  --console \
  --add-data "assets:assets" \
  --add-data "proxy_addon.py:." \
  --name WindslockProxy \
  proxy_runner.py

PKG_DIR="dist/Windslock-Linux"
rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}"

cp -R dist/Windslock "${PKG_DIR}/Windslock"
cp -R dist/WindslockTray "${PKG_DIR}/WindslockTray"
cp -R dist/WindslockProxy "${PKG_DIR}/WindslockProxy"
cp -R assets "${PKG_DIR}/assets"
cp -R docs "${PKG_DIR}/docs"
cp README.md requirements.txt "${PKG_DIR}/"
mkdir -p "${PKG_DIR}/packaging"
cp -R packaging/linux "${PKG_DIR}/packaging/linux"
chmod +x "${PKG_DIR}/packaging/linux/install_linux_user.sh"
chmod +x "${PKG_DIR}/packaging/linux/uninstall_linux_user.sh"

cat > "${PKG_DIR}/run_windslock.sh" <<'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/Windslock/Windslock" "$@"
EOF

cat > "${PKG_DIR}/run_tray.sh" <<'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/WindslockTray/WindslockTray" "$@"
EOF

cat > "${PKG_DIR}/run_proxy.sh" <<'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/WindslockProxy/WindslockProxy" "$@"
EOF

chmod +x "${PKG_DIR}/run_windslock.sh" "${PKG_DIR}/run_tray.sh" "${PKG_DIR}/run_proxy.sh"

tar -C dist -czf dist/Windslock-Linux.tar.gz Windslock-Linux
echo "Built dist/Windslock-Linux.tar.gz"
