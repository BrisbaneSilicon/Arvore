#!/usr/bin/env bash
# Build a self-contained .deb for the Arvore — bundles the PyInstaller
# output into /opt/arvore/ so the package has no Python runtime deps.
#
# Prerequisites:
#   pip install pyinstaller
#   dpkg-deb (already present on Debian/Ubuntu).
#
# Output:
#   dist/arvore_<version>_<arch>.deb

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DIST="$ROOT/dist"

VERSION="${VERSION:-0.1.0}"
ARCH="${ARCH:-$(dpkg --print-architecture)}"
PKG="arvore_${VERSION}_${ARCH}"
STAGE="$DIST/$PKG"

ICON_SRC="$ROOT/ide/arvore.png"
if [[ ! -f "$ICON_SRC" ]]; then
    echo "error: icon missing at $ICON_SRC — drop a 256x256 PNG there." >&2
    exit 1
fi

echo "[1/4] Running PyInstaller…"
cd "$ROOT"
pyinstaller --clean --noconfirm packaging/arvore.spec

echo "[2/4] Staging $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/opt/arvore"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/icons/hicolor/256x256/apps"

# PyInstaller output — everything goes under /opt/arvore/
cp -r "$DIST/arvore/." "$STAGE/opt/arvore/"

# Launcher in /usr/bin so users can type `arvore` from the terminal.
cat > "$STAGE/usr/bin/arvore" <<'SH'
#!/usr/bin/env bash
exec /opt/arvore/arvore "$@"
SH
chmod +x "$STAGE/usr/bin/arvore"

# Desktop entry + icon
cp "$HERE/arvore.desktop" "$STAGE/usr/share/applications/arvore.desktop"
cp "$ICON_SRC"               "$STAGE/usr/share/icons/hicolor/256x256/apps/arvore.png"

# Control file — no Python deps since everything's bundled in /opt
INSTALLED_KB="$(du -sk "$STAGE" --exclude=DEBIAN | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: arvore
Version: $VERSION
Section: devel
Priority: optional
Architecture: $ARCH
Depends: libc6, libxcb-cursor0 | libxcb-cursor-dev
Installed-Size: $INSTALLED_KB
Maintainer: BrisbaneSilicon <admin@brisbanesilicon.com.au>
Description: IDE for the ELM11 Embedded Lua Machine
 A graphical development environment for the ELM11 embedded Lua
 microcontroller: serial terminal with REPL, program upload, command-mode
 console, and integrated API documentation. Self-contained — Python
 and Qt libraries are bundled under /opt/arvore.
EOF

# postinst / postrm so GNOME picks up the new .desktop and icon caches.
cat > "$STAGE/DEBIAN/postinst" <<'SH'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
fi
SH
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/postrm" <<'SH'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
fi
SH
chmod 755 "$STAGE/DEBIAN/postrm"

echo "[3/4] Building package"
cd "$DIST"
dpkg-deb --build --root-owner-group "$PKG"

echo "[4/4] Done — $DIST/$PKG.deb"
