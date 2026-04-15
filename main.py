#!/usr/bin/env python3
"""ELM11 IDE — entry point."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from elm11_ide.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('ELM11 IDE')
    app.setOrganizationName('BrisbaneSilicon')
    # Store settings in a plain .ini file next to the app (easy to inspect)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
