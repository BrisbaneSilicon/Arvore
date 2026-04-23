"""Settings dialog."""
import sys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QFileDialog, QFormLayout,
    QSpinBox, QDialogButtonBox, QComboBox,
)
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont, QFontDatabase, QFontInfo, QFontMetrics

from . import theme


def _default_mono_font() -> str:
    """Pick a sensible built-in monospaced font per platform."""
    if sys.platform.startswith('win'):
        return 'Consolas'
    if sys.platform == 'darwin':
        return 'Menlo'
    return 'Ubuntu Mono'


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setMinimumWidth(520)
        self.setStyleSheet(theme.dialog_stylesheet(theme.current()))
        self._s = QSettings()
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)

        # ── Editor ────────────────────────────────────────────────────
        editor_w = QWidget()
        f = QFormLayout(editor_w)
        self._font_combo = QComboBox()
        self._font_combo.addItems(self._monospaced_fonts())
        f.addRow('Font:', self._font_combo)
        self._font_size = QSpinBox()
        self._font_size.setRange(6, 48)
        f.addRow('Font size:', self._font_size)
        tabs.addTab(editor_w, 'Editor')

        # ── Serial ────────────────────────────────────────────────────
        serial_w = QWidget()
        f = QFormLayout(serial_w)
        self._baud = QSpinBox()
        self._baud.setRange(1200, 921600)
        self._baud.setSingleStep(1)
        f.addRow('Default baud rate:', self._baud)
        tabs.addTab(serial_w, 'Serial')

        # ── C ─────────────────────────────────────────────────────────
        c_w = QWidget()
        f = QFormLayout(c_w)

        self._compiler = QLineEdit()
        self._compiler.setPlaceholderText('e.g. arm-none-eabi-gcc')
        browse_cc = QPushButton('Browse…')
        browse_cc.clicked.connect(self._browse_compiler)
        row2 = QHBoxLayout()
        row2.addWidget(self._compiler)
        row2.addWidget(browse_cc)
        f.addRow('C compiler:', row2)

        self._cflags = QLineEdit()
        self._cflags.setPlaceholderText('-O2 -Wall')
        f.addRow('Compiler flags:', self._cflags)

        self._flash_tool = QLineEdit()
        self._flash_tool.setPlaceholderText('Path to flash tool')
        browse_flash = QPushButton('Browse…')
        browse_flash.clicked.connect(self._browse_flash_tool)
        row3 = QHBoxLayout()
        row3.addWidget(self._flash_tool)
        row3.addWidget(browse_flash)
        f.addRow('Flash tool:', row3)
        tabs.addTab(c_w, 'C')

        # ── Buttons ───────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    _mono_cache: list[str] | None = None

    @classmethod
    def _monospaced_fonts(cls) -> list[str]:
        """Return sorted list of monospaced font families available on the system."""
        if cls._mono_cache is None:
            cls._mono_cache = sorted(
                f for f in QFontDatabase.families()
                if QFontDatabase.isFixedPitch(f)
            )
        return cls._mono_cache

    def _browse_compiler(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select C compiler', '', 'All files (*)')
        if path:
            self._compiler.setText(path)

    def _browse_flash_tool(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select flash tool', '', 'All files (*)')
        if path:
            self._flash_tool.setText(path)

    def _load(self):
        saved_font = self._s.value('editor/font_family', _default_mono_font())
        idx = self._font_combo.findText(saved_font)
        if idx >= 0:
            self._font_combo.setCurrentIndex(idx)
        self._font_size.setValue(int(self._s.value('editor/font_size', 13)))
        self._baud.setValue(int(self._s.value('serial/baud', 115200)))
        self._compiler.setText(self._s.value('c/compiler_path', ''))
        self._cflags.setText(self._s.value('c/compiler_flags', ''))
        self._flash_tool.setText(self._s.value('c/flash_tool', ''))

    def _save(self):
        self._s.setValue('editor/font_family',    self._font_combo.currentText())
        self._s.setValue('editor/font_size',      self._font_size.value())
        self._s.setValue('serial/baud',           self._baud.value())
        self._s.setValue('c/compiler_path',       self._compiler.text())
        self._s.setValue('c/compiler_flags',      self._cflags.text())
        self._s.setValue('c/flash_tool',          self._flash_tool.text())

    # ── Static helpers used by MainWindow ─────────────────────────────
    @staticmethod
    def editor_font_family() -> str:
        return QSettings().value('editor/font_family', _default_mono_font())

    @staticmethod
    def editor_font_size() -> int:
        return int(QSettings().value('editor/font_size', 13))

    @staticmethod
    def baud() -> int:
        return int(QSettings().value('serial/baud', 115200))

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
