#!/usr/bin/env python3
"""ELM11 IDE — entry point."""
import sys
import logging
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from elm11_ide.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description='ELM11 IDE')
    parser.add_argument('--debug', action='store_true',
                        help='Enable verbose debug logging to stdout')
    args, remaining = parser.parse_known_args()

    log = logging.getLogger('elm11_ide')
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
    app.setOrganizationName('BrisbaneSilicon')
    # Store settings in a plain .ini file next to the app (easy to inspect)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
