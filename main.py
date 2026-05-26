#!/usr/bin/env python3
"""ELM11 IDE — entry point."""
import sys
import logging
import argparse
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon
from brs_ide.main_window import MainWindow


def _icon_path() -> Path:
    """Locate the application icon whether we're running from source, a
    PyInstaller bundle, or a system install."""
    # PyInstaller sets sys._MEIPASS to the bundle root at runtime.
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    for rel in ('brs_ide/elm11-ide.png', 'elm11-ide.png'):
        p = base / rel
        if p.is_file():
            return p
    return Path()


def main():
    parser = argparse.ArgumentParser(description='ELM11 IDE')
    parser.add_argument('--debug', action='store_true',
                        help='Enable verbose debug logging to stdout')
    args, remaining = parser.parse_known_args()

    log = logging.getLogger('brs_ide')
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
            datefmt='%H:%M:%S',
            stream=sys.stdout,
        )
        log.debug('Debug mode enabled')
    else:
        logging.basicConfig(level=logging.WARNING)

    # Only pass Qt-relevant args (not --debug) to QApplication
    app = QApplication([sys.argv[0]] + remaining)
    app.setApplicationName('ELM11 IDE')
    app.setDesktopFileName('elm11-ide')   # links the app to its .desktop file
    app.setOrganizationName('BrisbaneSilicon')
    # Store settings in a plain .ini file next to the app (easy to inspect)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)

    icon = _icon_path()
    if icon.exists():
        app_icon = QIcon(str(icon))
        app.setWindowIcon(app_icon)

    window = MainWindow()
    if icon.exists():
        window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
