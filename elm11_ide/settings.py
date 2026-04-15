"""Settings dialog."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QFileDialog, QFormLayout,
    QSpinBox, QDialogButtonBox,
)
from PyQt6.QtCore import QSettings

STYLE = """
QDialog  { background:#2d2d2d; color:#cccccc; }
QWidget  { background:#2d2d2d; color:#cccccc; }
QTabWidget::pane { border:1px solid #3c3c3c; }
QTabBar::tab {
    background:#3c3c3c; color:#cccccc;
    padding:6px 14px; border:none;
}
QTabBar::tab:selected { background:#094771; }
QLineEdit, QSpinBox {
    background:#1e1e1e; color:#d4d4d4;
    border:1px solid #555; padding:4px;
}
QPushButton {
    background:#3c3c3c; color:#cccccc;
    border:1px solid #555; padding:4px 10px;
}
QPushButton:hover { background:#4c4c4c; }
QLabel { background:transparent; }
"""


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setMinimumWidth(520)
        self.setStyleSheet(STYLE)
        self._s = QSettings()
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)

        # ── Serial ────────────────────────────────────────────────────
        serial_w = QWidget()
        f = QFormLayout(serial_w)
        self._baud = QSpinBox()
        self._baud.setRange(1200, 921600)
        self._baud.setSingleStep(1)
        f.addRow('Default baud rate:', self._baud)
        tabs.addTab(serial_w, 'Serial')

        # ── Lua ───────────────────────────────────────────────────────
        lua_w = QWidget()
        f = QFormLayout(lua_w)
        self._uploader = QLineEdit()
        self._uploader.setPlaceholderText('Path to program_uploader.py')
        browse = QPushButton('Browse…')
        browse.clicked.connect(self._browse_uploader)
        row = QHBoxLayout()
        row.addWidget(self._uploader)
        row.addWidget(browse)
        f.addRow('Program uploader:', row)
        tabs.addTab(lua_w, 'Lua')

        # ── C (coming soon) ───────────────────────────────────────────
        c_w = QWidget()
        f = QFormLayout(c_w)

        self._compiler = QLineEdit()
        self._compiler.setPlaceholderText('e.g. arm-none-eabi-gcc   (coming soon)')
        self._compiler.setEnabled(False)
        browse_cc = QPushButton('Browse…')
        browse_cc.setEnabled(False)
        row2 = QHBoxLayout()
        row2.addWidget(self._compiler)
        row2.addWidget(browse_cc)
        f.addRow('C compiler:', row2)

        self._cflags = QLineEdit()
        self._cflags.setPlaceholderText('-O2 -Wall   (coming soon)')
        self._cflags.setEnabled(False)
        f.addRow('Compiler flags:', self._cflags)

        self._flash_tool = QLineEdit()
        self._flash_tool.setPlaceholderText('Flash tool path   (coming soon)')
        self._flash_tool.setEnabled(False)
        f.addRow('Flash tool:', self._flash_tool)

        note = QLabel('C toolchain support coming soon.')
        note.setStyleSheet('color:#888; font-style:italic;')
        f.addRow(note)
        tabs.addTab(c_w, 'C  (coming soon)')

        # ── Buttons ───────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _browse_uploader(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select program_uploader.py', '', 'Python files (*.py)')
        if path:
            self._uploader.setText(path)

    def _load(self):
        self._baud.setValue(int(self._s.value('serial/baud', 115200)))
        self._uploader.setText(self._s.value('lua/uploader_path', ''))

    def _save(self):
        self._s.setValue('serial/baud',          self._baud.value())
        self._s.setValue('lua/uploader_path',     self._uploader.text())
        self._s.setValue('c/compiler_path',       self._compiler.text())
        self._s.setValue('c/compiler_flags',      self._cflags.text())
        self._s.setValue('c/flash_tool',          self._flash_tool.text())

    # ── Static helpers used by MainWindow ─────────────────────────────
    @staticmethod
    def baud() -> int:
        return int(QSettings().value('serial/baud', 115200))

    @staticmethod
    def uploader_path() -> str:
        return QSettings().value('lua/uploader_path', '')

    @staticmethod
    def compiler_path() -> str:
        return QSettings().value('c/compiler_path', '')

    @staticmethod
    def compiler_flags() -> list[str]:
        raw = QSettings().value('c/compiler_flags', '')
        return raw.split() if raw else []

    @staticmethod
    def flash_tool() -> str:
        return QSettings().value('c/flash_tool', '')
