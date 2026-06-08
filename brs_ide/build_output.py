"""Build output panel — runs external processes and shows their output."""
import logging
log = logging.getLogger(__name__)

import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt6.QtCore import QProcess, QProcessEnvironment, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat

from . import theme
from .settings import SettingsDialog


class BuildOutput(QWidget):
    build_finished = pyqtSignal(int)   # exit code

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(2000)
        layout.addWidget(self._output)

        self.apply_font()
        self.apply_theme()

    def apply_font(self):
        """Apply the configured global panel font size (monospaced)."""
        font = QFont('Monospace', SettingsDialog.panel_font_size())
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._output.setFont(font)

    def apply_theme(self):
        t = theme.current()
        pal = self._output.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(t['term_bg']))
        pal.setColor(QPalette.ColorRole.Text, QColor(t['term_fg']))
        self._output.setPalette(pal)

    # ── Public API ────────────────────────────────────────────────────────

    def run_command(self, program: str, args: list[str],
                    cwd: str | None = None,
                    env: dict[str, str] | None = None,
                    clear: bool = True):
        log.debug('run_command: %s %s  cwd=%s  env=%s  clear=%s',
                  program, args, cwd, list((env or {}).keys()), clear)
        """Start an external command and stream its output here.

        `env`   — optional dict of environment-variable overrides applied
                   on top of the inherited process environment.
        `clear` — when False, keep existing output visible (useful for
                   retries so the previous attempt's log stays on screen).
        """
        t = theme.current()
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._append('A build is already running.\n', t['term_warning'])
            return

        if clear:
            self.clear()
        self._append(f'$ {program} {" ".join(args)}\n', t['term_info'])

        self._process = QProcess(self)
        self._process.setProgram(program)
        self._process.setArguments(args)
        if cwd:
            self._process.setWorkingDirectory(cwd)
        if env:
            penv = QProcessEnvironment.systemEnvironment()
            for k, v in env.items():
                penv.insert(k, v)
            self._process.setProcessEnvironment(penv)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.start()

    def run_upload(self, script: str, lua_file: str, port: str, baud: int = 115200):
        """Convenience wrapper: run program_uploader.py."""
        self.run_command(sys.executable, [script, lua_file, port, str(baud)])

    def run_build(self, compiler: str, flags: list[str],
                  sources: list[str], output: str, cwd: str | None = None):
        """Convenience wrapper: compile C sources."""
        args = flags + sources + ['-o', output]
        self.run_command(compiler, args, cwd)

    def clear(self):
        self._output.clear()

    def is_running(self) -> bool:
        return bool(self._process) and \
            self._process.state() != QProcess.ProcessState.NotRunning

    def stop(self):
        """Kill the running process, if any. The resulting `finished` signal
        still fires (with a non-zero exit), so listeners reset normally."""
        if self.is_running():
            self._append('\n--- Stopping… ---\n', theme.current()['term_warning'])
            self._process.kill()

    # ── Internal ─────────────────────────────────────────────────────────

    def _on_stdout(self):
        raw = self._process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        for line in raw.splitlines(keepends=True):
            self._append(line, self._line_color(line))

    def _on_stderr(self):
        raw = self._process.readAllStandardError().data().decode('utf-8', errors='replace')
        for line in raw.splitlines(keepends=True):
            self._append(line, self._line_color(line, stderr=True))

    def _on_finished(self, exit_code: int, _status):
        t = theme.current()
        color = t['term_success'] if exit_code == 0 else t['term_error']
        self._append(f'\n--- {"Done" if exit_code == 0 else "Failed"} '
                     f'(exit {exit_code}) ---\n', color)
        self.build_finished.emit(exit_code)

    @staticmethod
    def _line_color(line: str, stderr: bool = False) -> str:
        t = theme.current()
        ll = line.lower()
        if 'error:' in ll or ': error' in ll:
            return t['term_error']
        if 'warning:' in ll or ': warning' in ll:
            return t['term_warning']
        if stderr:
            return t['term_warning']
        return t['term_fg']

    def _append(self, text: str, color: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
