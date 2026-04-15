"""Serial terminal widget + background read thread."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker, QEvent
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat

import serial
import serial.tools.list_ports

# ── Terminal colours ──────────────────────────────────────────────────────────
TERM_BG        = '#1a1a1a'
TERM_FG        = '#d4d4d4'
TERM_INFO      = '#569cd6'   # blue  – connection messages
TERM_OUTPUT    = '#6ab04c'   # green – REPL return values
TERM_ERROR     = '#f44747'   # red
TERM_WARNING   = '#e5c07b'   # amber
TERM_TIMESTAMP = '#d4a04a'   # amber – boot log timestamps

# Basic ANSI 3x colour map (foreground)
_ANSI_FG = {
    30: '#1a1a1a', 31: '#f44747', 32: '#6ab04c', 33: '#e5c07b',
    34: '#569cd6', 35: '#c586c0', 36: '#4ec9b0', 37: '#d4d4d4',
    90: '#555555', 91: '#f97583', 92: '#85e89d', 93: '#ffea7f',
    94: '#79b8ff', 95: '#b392f0', 96: '#39d5d5', 97: '#ffffff',
}


# ── Serial worker (background QThread) ───────────────────────────────────────
class SerialWorker(QThread):
    data_received    = pyqtSignal(bytes)
    connection_lost  = pyqtSignal(str)

    def __init__(self, port: str, baud: int = 115200):
        super().__init__()
        self.port  = port
        self.baud  = baud
        self._ser: serial.Serial | None = None
        self._running = False
        self._mutex   = QMutex()

    def run(self):
        try:
            self._ser = serial.Serial(
                self.port, self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.05,
            )
            self._running = True
            while self._running:
                try:
                    waiting = self._ser.in_waiting
                    if waiting:
                        self.data_received.emit(self._ser.read(waiting))
                    else:
                        self.msleep(10)
                except serial.SerialException as exc:
                    self.connection_lost.emit(str(exc))
                    break
        except serial.SerialException as exc:
            self.connection_lost.emit(str(exc))
        finally:
            self._close_serial()

    def send(self, data: bytes):
        with QMutexLocker(self._mutex):
            if self._ser and self._ser.is_open:
                try:
                    self._ser.write(data)
                except serial.SerialException:
                    pass

    def stop(self):
        self._running = False
        self.wait(2000)

    def release_port(self):
        """Close the serial port without stopping the thread (needed for upload)."""
        with QMutexLocker(self._mutex):
            self._close_serial()

    def reopen_port(self):
        """Re-open the port after an upload completes."""
        with QMutexLocker(self._mutex):
            if self._ser and not self._ser.is_open:
                try:
                    self._ser.open()
                except serial.SerialException:
                    pass

    def _close_serial(self):
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass


# ── ANSI escape-code parser ───────────────────────────────────────────────────
class _AnsiParser:
    def __init__(self):
        self._color: str | None = None

    def feed(self, text: str) -> list[tuple[str, str | None]]:
        """Return list of (chunk, colour_hex | None)."""
        chunks: list[tuple[str, str | None]] = []
        i = 0
        while i < len(text):
            if text[i] == '\x1b' and i + 1 < len(text) and text[i + 1] == '[':
                end = text.find('m', i + 2)
                if end != -1:
                    try:
                        code = int(text[i + 2:end]) if text[i + 2:end] else 0
                        self._color = None if code == 0 else _ANSI_FG.get(code, self._color)
                    except ValueError:
                        pass
                    i = end + 1
                    continue
            chunks.append((text[i], self._color))
            i += 1

        # Merge consecutive same-colour runs
        merged: list[list] = []
        for ch, col in chunks:
            if merged and merged[-1][1] == col:
                merged[-1][0] += ch
            else:
                merged.append([ch, col])
        return [(t, c) for t, c in merged]


# ── Terminal widget ───────────────────────────────────────────────────────────
class SerialTerminal(QWidget):
    connected = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: SerialWorker | None = None
        self._ansi   = _AnsiParser()
        self._buf    = b''          # partial-UTF-8 accumulator
        self._history: list[str] = []
        self._hist_pos = -1
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        font = QFont('Monospace', 10)
        font.setStyleHint(QFont.StyleHint.TypeWriter)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(font)
        self._output.setMaximumBlockCount(5000)
        pal = self._output.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(TERM_BG))
        pal.setColor(QPalette.ColorRole.Text, QColor(TERM_FG))
        self._output.setPalette(pal)
        layout.addWidget(self._output)

        # Input row
        row = QHBoxLayout()
        self._prompt = QLabel('$')
        self._prompt.setStyleSheet(
            f'color:{TERM_FG}; font-family:Monospace; font-size:10pt; padding:0 4px;')
        self._input = QLineEdit()
        self._input.setFont(font)
        self._input.setStyleSheet(
            f'background:{TERM_BG}; color:{TERM_FG};'
            f'border:1px solid #3c3c3c; padding:2px;')
        self._input.setPlaceholderText('Type Lua here and press Enter…')
        self._input.returnPressed.connect(self._send_input)
        self._input.installEventFilter(self)

        send_btn = QPushButton('Send')
        send_btn.setFixedWidth(60)
        send_btn.clicked.connect(self._send_input)

        row.addWidget(self._prompt)
        row.addWidget(self._input)
        row.addWidget(send_btn)
        layout.addLayout(row)

    # ── Public API ────────────────────────────────────────────────────────

    def connect_to_port(self, port: str, baud: int = 115200):
        self.disconnect_port()
        self._worker = SerialWorker(port, baud)
        self._worker.data_received.connect(self._on_data)
        self._worker.connection_lost.connect(self._on_lost)
        self._worker.start()
        self._append(f'Connected to {port} @ {baud}\n', TERM_INFO)
        self.connected.emit(True)

    def disconnect_port(self):
        if self._worker:
            self._worker.stop()
            self._worker = None
        self.connected.emit(False)

    def send_raw(self, data: bytes):
        if self._worker:
            self._worker.send(data)

    def get_worker(self) -> SerialWorker | None:
        return self._worker

    @property
    def is_connected(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def append_info(self, text: str):
        self._append(text, TERM_INFO)

    def clear(self):
        self._output.clear()

    # ── History navigation ────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Up:
                if self._history and self._hist_pos < len(self._history) - 1:
                    self._hist_pos += 1
                    self._input.setText(self._history[-(self._hist_pos + 1)])
                return True
            if key == Qt.Key.Key_Down:
                if self._hist_pos > 0:
                    self._hist_pos -= 1
                    self._input.setText(self._history[-(self._hist_pos + 1)])
                elif self._hist_pos == 0:
                    self._hist_pos = -1
                    self._input.clear()
                return True
        return super().eventFilter(obj, event)

    # ── Internal ─────────────────────────────────────────────────────────

    def _send_input(self):
        if not self._worker:
            return
        text = self._input.text()
        if text and (not self._history or self._history[-1] != text):
            self._history.append(text)
        self._hist_pos = -1
        self._input.clear()
        self._worker.send((text + '\n').encode('utf-8'))
        self._append(text + '\n', TERM_FG)

    def _on_data(self, data: bytes):
        self._buf += data
        try:
            text = self._buf.decode('utf-8')
            self._buf = b''
        except UnicodeDecodeError:
            try:
                text = self._buf[:-1].decode('utf-8')
                self._buf = self._buf[-1:]
            except UnicodeDecodeError:
                text = self._buf.decode('utf-8', errors='replace')
                self._buf = b''

        for chunk, color in self._ansi.feed(text):
            self._append(chunk, color or TERM_FG)

    def _on_lost(self, error: str):
        self._append(f'\nConnection lost: {error}\n', TERM_ERROR)
        self._worker = None
        self.connected.emit(False)

    def _append(self, text: str, color: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
