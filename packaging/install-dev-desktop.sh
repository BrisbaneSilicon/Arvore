#!/usr/bin/env bash
# Register a user-level .desktop entry that points at the in-repo
# `python3 main.py` launcher — this gives GNOME (Wayland) an app_id
# it can match to a real icon when you're running the IDE from source.
#
# Uninstall with:
#   rm ~/.local/share/applications/elm11-ide.desktop
#   rm ~/.local/share/icons/hicolor/256x256/apps/elm11-ide.png

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$APPS_DIR" "$ICON_DIR"

cp "$ROOT/elm11_ide/elm11-ide.png" "$ICON_DIR/elm11-ide.png"

cat > "$APPS_DIR/elm11-ide.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ELM11 IDE (dev)
Exec=python3 $ROOT/main.py
Icon=elm11-ide
Terminal=false
Categories=Development;IDE;
StartupWMClass=ELM11 IDE
EOF

# Make GNOME pick up the new entry without a session restart.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" || true
fi

echo "Installed $APPS_DIR/elm11-ide.desktop"
echo "Now just 'python3 main.py' — the taskbar icon will pick up."
