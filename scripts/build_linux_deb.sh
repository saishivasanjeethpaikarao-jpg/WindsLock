#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

VERSION="${WINDSLOCK_VERSION:-0.1.0}"
ARCH="${WINDSLOCK_ARCH:-amd64}"
SOURCE_DIR="dist/Windslock-Linux"
PKG_ROOT="dist/deb/windslock_${VERSION}_${ARCH}"
DEB_PATH="dist/Windslock-Linux-Debian.deb"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Missing ${SOURCE_DIR}. Run scripts/build_linux_app.sh first." >&2
  exit 1
fi

rm -rf "${PKG_ROOT}" "${DEB_PATH}"
mkdir -p \
  "${PKG_ROOT}/DEBIAN" \
  "${PKG_ROOT}/opt/windslock" \
  "${PKG_ROOT}/usr/local/bin" \
  "${PKG_ROOT}/usr/share/applications" \
  "${PKG_ROOT}/usr/share/icons/hicolor/256x256/apps" \
  "${PKG_ROOT}/usr/share/doc/windslock"

cp -R "${SOURCE_DIR}/." "${PKG_ROOT}/opt/windslock/"
install -m 0644 assets/windslock_icon.png "${PKG_ROOT}/usr/share/icons/hicolor/256x256/apps/windslock.png"
install -m 0644 packaging/linux/windslock.desktop "${PKG_ROOT}/usr/share/applications/windslock.desktop"
install -m 0644 packaging/linux/windslock-tray.desktop "${PKG_ROOT}/usr/share/applications/windslock-tray.desktop"
install -m 0644 packaging/linux/windslock-proxy.desktop "${PKG_ROOT}/usr/share/applications/windslock-proxy.desktop"
install -m 0644 README.md "${PKG_ROOT}/usr/share/doc/windslock/README.md"

cat > "${PKG_ROOT}/usr/local/bin/windslock" <<'EOF'
#!/usr/bin/env bash
exec /opt/windslock/Windslock/Windslock "$@"
EOF

cat > "${PKG_ROOT}/usr/local/bin/windslock-tray" <<'EOF'
#!/usr/bin/env bash
exec /opt/windslock/WindslockTray/WindslockTray "$@"
EOF

cat > "${PKG_ROOT}/usr/local/bin/windslock-enforcer" <<'EOF'
#!/usr/bin/env bash
exec /opt/windslock/WindslockEnforcer/WindslockEnforcer "$@"
EOF

cat > "${PKG_ROOT}/usr/local/bin/windslock-proxy" <<'EOF'
#!/usr/bin/env bash
exec /opt/windslock/WindslockProxy/WindslockProxy "$@"
EOF

chmod 0755 \
  "${PKG_ROOT}/usr/local/bin/windslock" \
  "${PKG_ROOT}/usr/local/bin/windslock-tray" \
  "${PKG_ROOT}/usr/local/bin/windslock-enforcer" \
  "${PKG_ROOT}/usr/local/bin/windslock-proxy"

cat > "${PKG_ROOT}/DEBIAN/control" <<EOF
Package: windslock
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: Windslock <support@windslock.local>
Depends: libayatana-appindicator3-1 | libappindicator3-1
Homepage: https://github.com/saishivasanjeethpaikarao-jpg/WindsLock
Description: Desktop app, website, URL path, and folder locking tool
 Windslock is a focus-security desktop app with app rules, domain blocks,
 path-level proxy rules, folder locking, audit history, and recovery flows.
EOF

chmod -R go-w "${PKG_ROOT}"
dpkg-deb --build "${PKG_ROOT}" "${DEB_PATH}"
echo "Built ${DEB_PATH}"
