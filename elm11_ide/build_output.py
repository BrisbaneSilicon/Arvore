"""Build output panel — runs external processes and shows their output."""
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt6.QtCore import QProcess, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat

BG      = '#1a1a1a'
FG      = '#d4d4d4'
ERROR   = '#f44747'
WARNING = '#e5c07b'
SUCCESS = '#6ab04c'
INFO    = '#569cd6'


class BuildOutput(QWidget):
    build_finished = pyqtSignal(int)   # exit code

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        font = QFont('Monospace', 10)
        font.setStyleHint(QFont.StyleHint.TypeWriter)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(font)
        self._output.setMaximumBlockCount(2000)
        pal = self._output.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(BG))
        pal.setColor(QPalette.ColorRole.Text, QColor(FG))
        self._output.setPalette(pal)
        layout.addWidget(self._output)

    # ── Public API ────────────────────────────────────────────────────────

    def run_command(self, program: str, args: list[str], cwd: str | None = None):
        """Start an external command and stream its output here."""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._append('A build is already running.\n', WARNING)
            return

        self.clear()
        self._append(f'$ {program} {" ".join(args)}\n', INFO)

        self._process = QProcess(self)
        self._process.setProgram(program)
        self._process.setArguments(args)
        if cwd:
            self._process.setWorkingDirectory(cwd)
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
        color = SUCCESS if exit_code == 0 else ERROR
        self._append(f'\n--- {"Done" if exit_code == 0 else "Failed"} '
                     f'(exit {exit_code}) ---\n', color)
        self.build_finished.emit(exit_code)

    @staticmethod
    def _line_color(line: str, stderr: bool = False) -> str:
        ll = line.lower()
        if 'error:' in ll or ': error' in ll:
            return ERROR
        if 'warning:' in ll or ': warning' in ll:
            return WARNING
        if stderr:
            return WARNING
        return FG

    def _append(self, text: str, color: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
