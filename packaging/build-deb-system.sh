#!/usr/bin/env bash
# Build a light .deb for the ELM11 IDE — ships just the Python source and
# declares PyQt6 / pyserial as apt dependencies. Much smaller than the
# bundled build, but requires the target system to have python3-pyqt6
# and python3-serial available in the package index (Ubuntu 24.04+ or
# Debian 12+ in universe/main).
#
# Output:
#   dist/elm11-ide-system_<version>_all.deb

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DIST="$ROOT/dist"

VERSION="${VERSION:-0.1.0}"
PKG="elm11-ide-system_${VERSION}_all"
STAGE="$DIST/$PKG"

ICON_SRC="$ROOT/brs_ide/elm11-ide.png"
if [[ ! -f "$ICON_SRC" ]]; then
    echo "error: icon missing at $ICON_SRC — drop a 256x256 PNG there." >&2
    exit 1
fi

echo "[1/3] Staging $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/usr/lib/python3/dist-packages/brs_ide"
mkdir -p "$STAGE/usr/share/applications"
mkdir -p "$STAGE/usr/share/icons/hicolor/256x256/apps"

# Python package
cp -r "$ROOT/brs_ide/." "$STAGE/usr/lib/python3/dist-packages/brs_ide/"

# Launcher — short Python shim, relies on system PyQt6 + pyserial.
# Shebang pinned to /usr/bin/python3 so it uses the distro's interpreter
# (which has /usr/lib/python3/dist-packages on sys.path) rather than a
# pip/conda/pyenv python that might have shadowed `python3` on PATH.
cat > "$STAGE/usr/bin/elm11-ide" <<'SH'
#!/usr/bin/python3
import sys
# Defensive — normally /usr/bin/python3 already has this in its path.
if '/usr/lib/python3/dist-packages' not in sys.path:
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon
from brs_ide.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('ELM11 IDE')
    app.setDesktopFileName('elm11-ide')
    app.setOrganizationName('BrisbaneSilicon')
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)

    icon_path = Path('/usr/share/icons/hicolor/256x256/apps/elm11-ide.png')
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    if icon_path.is_file():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
SH
chmod +x "$STAGE/usr/bin/elm11-ide"

# Desktop entry + icon
cp "$HERE/elm11-ide.desktop" "$STAGE/usr/share/applications/elm11-ide.desktop"
cp "$ICON_SRC"               "$STAGE/usr/share/icons/hicolor/256x256/apps/elm11-ide.png"

# Control file — declare the Python deps so apt pulls them in.
INSTALLED_KB="$(du -sk "$STAGE" --exclude=DEBIAN | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: elm11-ide
Version: $VERSION
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyqt6, python3-serial
Conflicts: elm11-ide-bundled
Installed-Size: $INSTALLED_KB
Maintainer: BrisbaneSilicon <admin@brisbanesilicon.com.au>
Description: IDE for the ELM11 Embedded Lua Machine (system-python build)
 A graphical development environment for the ELM11 embedded Lua
 microcontroller: serial terminal with REPL, program upload, command-mode
 console, and integrated API documentation. Uses the distro's python3,
 python3-pyqt6 and python3-serial packages rather than bundling them.
EOF

# Refresh desktop + icon caches on install/remove.
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

echo "[2/3] Building package"
cd "$DIST"
dpkg-deb --build --root-owner-group "$PKG"

echo "[3/3] Done — $DIST/$PKG.deb"
