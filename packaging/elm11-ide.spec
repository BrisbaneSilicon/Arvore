# PyInstaller spec for the ELM11 IDE.
# Build with:  pyinstaller packaging/elm11-ide.spec
# Output:      dist/elm11-ide/  (folder-style bundle)

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
IS_WIN = sys.platform.startswith('win')
# Windows wants a .ico file for the .exe icon; Linux/macOS use the PNG
# elsewhere at runtime via setWindowIcon.
WIN_ICON = ROOT / 'packaging' / 'elm11-ide.ico'
EXE_ICON = str(WIN_ICON) if IS_WIN and WIN_ICON.is_file() else None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Pre-extracted documentation data is loaded at runtime.
        (str(ROOT / 'ide' / 'docs_data.json'),   'ide'),
        (str(ROOT / 'ide' / 'docs_c_data.json'), 'ide'),
        # Window / taskbar icon used by QApplication.setWindowIcon.
        (str(ROOT / 'ide' / 'elm11-ide.png'), 'ide'),
        # Bundled flash helper invoked by the toolbar Flash button.
        (str(ROOT / 'ide' / 'firmware_uploader.py'), 'ide'),
        # Pre-built ELM11 C runtime objects — every user C program links
        # against these.
        (str(ROOT / 'ide' / 'elm11' / 'c' / 'runtime'), 'ide/elm11/c/runtime'),
        # Makefile + linker script + helper tools deployed into each new
        # C workspace.
        (str(ROOT / 'ide' / 'elm11' / 'c' / 'build'), 'ide/elm11/c/build'),
    ],
    hiddenimports=['serial.tools.list_ports_linux'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Trim heavyweight Qt bits we don't use.
        'PyQt6.QtBluetooth', 'PyQt6.QtQml', 'PyQt6.QtQuick',
        'PyQt6.QtQuickWidgets', 'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets', 'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebChannel',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='elm11-ide',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=EXE_ICON,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='elm11-ide',
)
