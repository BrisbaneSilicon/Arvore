#!/usr/bin/env bash
# Build an AppImage for the Arvore.
#
# Prerequisites:
#   pip install pyinstaller
#   and `appimagetool` on PATH (download from
#   https://github.com/AppImage/AppImageKit/releases — the x86_64 binary
#   that ends in `appimagetool-<arch>.AppImage`, chmod +x it and put it
#   somewhere in your PATH, renamed to `appimagetool`).
#
# Output:
#   dist/Arvore-<arch>.AppImage

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DIST="$ROOT/dist"
APPDIR="$DIST/Arvore.AppDir"

ICON_SRC="$ROOT/ide/arvore.png"
if [[ ! -f "$ICON_SRC" ]]; then
    echo "error: icon missing at $ICON_SRC — drop a 256x256 PNG there." >&2
    exit 1
fi

echo "[1/4] Running PyInstaller…"
cd "$ROOT"
pyinstaller --clean --noconfirm packaging/arvore.spec

echo "[2/4] Assembling AppDir…"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Move PyInstaller output into AppDir
cp -r "$DIST/arvore/." "$APPDIR/usr/bin/"

# Desktop entry + icon (must live at both AppDir root and the standard path)
cp "$HERE/arvore.desktop" "$APPDIR/arvore.desktop"
cp "$HERE/arvore.desktop" "$APPDIR/usr/share/applications/arvore.desktop"
cp "$ICON_SRC" "$APPDIR/arvore.png"
cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/256x256/apps/arvore.png"

# AppRun: the AppImage entry script. Also self-registers a user-level
# .desktop entry on launch so GNOME (Wayland) can match the window's
# app_id to an icon for the taskbar.
cat > "$APPDIR/AppRun" <<'SH'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"

# Integrate with the user session — runs every launch, cheap & idempotent.
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
mkdir -p "$APPS_DIR" "$ICON_DIR"
cp -f "$HERE/arvore.png" "$ICON_DIR/arvore.png" 2>/dev/null || true
# Point the installed .desktop at this AppImage (via $APPIMAGE, set by
# appimagetool) so launching from the menu runs the same binary.
TARGET="${APPIMAGE:-$HERE/AppRun}"
cat > "$APPS_DIR/arvore.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Arvore
Comment=IDE for the ELM11 Embedded Lua Machine
Exec="$TARGET" %U
Icon=arvore
Terminal=false
Categories=Development;IDE;
StartupWMClass=Arvore
DESK

exec "$HERE/usr/bin/arvore" "$@"
SH
chmod +x "$APPDIR/AppRun"

echo "[3/4] Running appimagetool…"
ARCH="${ARCH:-$(uname -m)}"
export ARCH
OUT="$DIST/Arvore-${ARCH}.AppImage"
rm -f "$OUT"
appimagetool "$APPDIR" "$OUT"

echo "[4/4] Done — $OUT"
