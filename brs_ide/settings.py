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


# LD_PRELOAD libraries the Gowin CLI flow needs on Linux. These are the
# usual Debian/Ubuntu locations; the user can override them in Settings if
# their distro keeps the libraries elsewhere.
_DEFAULT_FREETYPE = '/lib/x86_64-linux-gnu/libfreetype.so'
_DEFAULT_LIBZ = '/lib/x86_64-linux-gnu/libz.so.1'


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
        f.addRow('Compiler Path:', row2)

        self._cflags = QLineEdit()
        self._cflags.setPlaceholderText('-O2 -Wall')
        f.addRow('Compiler flags:', self._cflags)

        # `MSYS2 Path` is Windows-only — Linux/macOS users always have GNU
        # make + the standard Unix utilities on $PATH, so the field would
        # be needless clutter. The widget is still created (for
        # _load/_save symmetry) but only shown on Windows. The IDE
        # appends `<msys2>/usr/bin` to the subprocess PATH when invoking
        # make so its recipes can find mkdir / rm / cp / date / etc.
        self._msys2 = QLineEdit()
        self._msys2.setPlaceholderText('e.g. C:\\msys64')
        if sys.platform.startswith('win'):
            browse_msys2 = QPushButton('Browse…')
            browse_msys2.clicked.connect(self._browse_msys2)
            row_msys2 = QHBoxLayout()
            row_msys2.addWidget(self._msys2)
            row_msys2.addWidget(browse_msys2)
            f.addRow('MSYS2 Path:', row_msys2)

        tabs.addTab(c_w, 'C')

        # ── Hardware ──────────────────────────────────────────────────
        hw_w = QWidget()
        f = QFormLayout(hw_w)
        self._gowin = QLineEdit()
        self._gowin.setPlaceholderText(
            'GoWIN EDA install path, i.e. /opt/Gowin/Gowin_V1.9.12_linux/')
        browse_gowin = QPushButton('Browse…')
        browse_gowin.clicked.connect(self._browse_gowin)
        row_gowin = QHBoxLayout()
        row_gowin.addWidget(self._gowin)
        row_gowin.addWidget(browse_gowin)
        f.addRow('Gowin IDE Path:', row_gowin)

        # LD_PRELOAD libraries the Gowin CLI flow needs (Linux). Defaults
        # cover Debian/Ubuntu; override if your distro stores them elsewhere.
        self._libfreetype = QLineEdit()
        self._libfreetype.setPlaceholderText(_DEFAULT_FREETYPE)
        browse_ft = QPushButton('Browse…')
        browse_ft.clicked.connect(self._browse_freetype)
        row_ft = QHBoxLayout()
        row_ft.addWidget(self._libfreetype)
        row_ft.addWidget(browse_ft)
        f.addRow('libfreetype.so:', row_ft)

        self._libz = QLineEdit()
        self._libz.setPlaceholderText(_DEFAULT_LIBZ)
        browse_z = QPushButton('Browse…')
        browse_z.clicked.connect(self._browse_libz)
        row_z = QHBoxLayout()
        row_z.addWidget(self._libz)
        row_z.addWidget(browse_z)
        f.addRow('libz.so.1:', row_z)

        tabs.addTab(hw_w, 'Hardware')

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

    def _browse_msys2(self):
        path = QFileDialog.getExistingDirectory(self, 'Select MSYS2 install root')
        if path:
            self._msys2.setText(path)

    def _browse_gowin(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Select Gowin EDA install folder')
        if path:
            self._gowin.setText(path)

    def _browse_freetype(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select libfreetype.so', '/lib', 'Shared libraries (*.so*)')
        if path:
            self._libfreetype.setText(path)

    def _browse_libz(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select libz.so.1', '/lib', 'Shared libraries (*.so*)')
        if path:
            self._libz.setText(path)

    def _load(self):
        saved_font = self._s.value('editor/font_family', _default_mono_font())
        idx = self._font_combo.findText(saved_font)
        if idx >= 0:
            self._font_combo.setCurrentIndex(idx)
        self._font_size.setValue(int(self._s.value('editor/font_size', 13)))
        self._baud.setValue(int(self._s.value('serial/baud', 115200)))
        self._compiler.setText(self._s.value('c/compiler_path', ''))
        self._cflags.setText(self._s.value('c/compiler_flags', ''))
        self._msys2.setText(self._s.value('c/msys2_path', ''))
        self._gowin.setText(self._s.value('hw/gowin_path', ''))
        self._libfreetype.setText(self._s.value('hw/libfreetype_path', _DEFAULT_FREETYPE))
        self._libz.setText(self._s.value('hw/libz_path', _DEFAULT_LIBZ))

    def _save(self):
        self._s.setValue('editor/font_family',    self._font_combo.currentText())
        self._s.setValue('editor/font_size',      self._font_size.value())
        self._s.setValue('serial/baud',           self._baud.value())
        self._s.setValue('c/compiler_path',       self._compiler.text())
        self._s.setValue('c/compiler_flags',      self._cflags.text())
        self._s.setValue('c/msys2_path',          self._msys2.text())
        self._s.setValue('hw/gowin_path',         self._gowin.text())
        self._s.setValue('hw/libfreetype_path',   self._libfreetype.text())
        self._s.setValue('hw/libz_path',          self._libz.text())

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
    def show_hidden_files() -> bool:
        """Whether the project tree should show dot-prefixed (hidden) files
        and directories, e.g. the generated `.build/` tree. Defaults off."""
        return QSettings().value('tree/show_hidden', False, type=bool)

    @staticmethod
    def compiler_path() -> str:
        return QSettings().value('c/compiler_path', '')

    @staticmethod
    def gowin_path() -> str:
        """Gowin EDA install root (contains IDE/bin/gw_sh), used to synthesise
        the FPGA firmware. Empty string means 'not configured'."""
        return QSettings().value('hw/gowin_path', '')

    @staticmethod
    def gowin_preload_libs() -> list[str]:
        """The libraries LD_PRELOAD'd for the Gowin CLI flow (libfreetype +
        libz), in order. User-overridable; falls back to the Debian/Ubuntu
        defaults."""
        s = QSettings()
        return [
            s.value('hw/libfreetype_path', _DEFAULT_FREETYPE),
            s.value('hw/libz_path', _DEFAULT_LIBZ),
        ]

    @staticmethod
    def compiler_flags() -> list[str]:
        raw = QSettings().value('c/compiler_flags', '')
        return raw.split() if raw else []

    @staticmethod
    def msys2_path() -> str:
        """Return the configured MSYS2 install root. Windows-only setting —
        on Linux/macOS we always defer to `$PATH`. Empty string means
        'use whatever `make` is on PATH'."""
        if not sys.platform.startswith('win'):
            return ''
        return QSettings().value('c/msys2_path', '')
