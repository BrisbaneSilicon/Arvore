"""Serial terminal widget + background read thread."""
import logging
log = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker, QEvent
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat

import serial
import serial.tools.list_ports

from . import theme
from .highlighter import LuaHighlighter, SkipHighlight

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
        self._tx_queue = bytearray()
        self.tx_delay_ms = 1          # per-byte output delay
        self._paused = False

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
                # While paused (e.g. during upload), stay out of the way
                if self._paused:
                    self.msleep(50)
                    continue

                # ── Transmit one queued byte ──────────────────────
                tx = None
                with QMutexLocker(self._mutex):
                    if self._tx_queue and self._ser and self._ser.is_open:
                        tx = bytes([self._tx_queue.pop(0)])
                if tx is not None:
                    try:
                        self._ser.write(tx)
                    except serial.SerialException:
                        pass
                    self.msleep(self.tx_delay_ms)
                    continue  # drain tx queue before polling rx

                # ── Receive ───────────────────────────────────────
                try:
                    if not self._ser or not self._ser.is_open:
                        self.msleep(50)
                        continue
                    waiting = self._ser.in_waiting
                    if waiting:
                        self.data_received.emit(self._ser.read(waiting))
                    else:
                        self.msleep(10)
                except (serial.SerialException, OSError):
                    self.msleep(50)
        except serial.SerialException as exc:
            self.connection_lost.emit(str(exc))
        finally:
            self._close_serial()

    def send(self, data: bytes):
        """Queue data for byte-by-byte transmission (non-blocking)."""
        with QMutexLocker(self._mutex):
            self._tx_queue.extend(data)

    def stop(self):
        self._running = False
        self.wait(2000)

    def pause(self):
        """Pause the read/write loop so another thread can use the port."""
        self._paused = True

    def resume(self):
        """Resume the read/write loop."""
        self._paused = False

    @property
    def serial_port(self) -> serial.Serial | None:
        """Direct access to the underlying serial.Serial (use while paused)."""
        return self._ser

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
        self._highlighter = LuaHighlighter(self._output.document())
        layout.addWidget(self._output)

        # Input row
        row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setFont(font)
        self._input.setPlaceholderText('Type Lua here and press Enter…')
        self._input.returnPressed.connect(self._send_input)
        self._input.installEventFilter(self)

        self._send_btn = QPushButton('Send')
        self._send_btn.setFixedWidth(60)
        self._send_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._send_btn.clicked.connect(self._send_input)

        self._clear_btn = QPushButton('Clear')
        self._clear_btn.setFixedWidth(60)
        self._clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._clear_btn.clicked.connect(self.clear)

        row.addWidget(self._input)
        row.addWidget(self._send_btn)
        row.addWidget(self._clear_btn)
        layout.addLayout(row)

        self._input.setEnabled(False)
        self._send_btn.setEnabled(False)
        self.connected.connect(self._on_connected)

        self.apply_theme()

    def apply_theme(self):
        t = theme.current()
        pal = self._output.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(t['term_bg']))
        pal.setColor(QPalette.ColorRole.Text, QColor(t['term_fg']))
        self._output.setPalette(pal)
        self._input.setStyleSheet(
            f"background:{t['term_bg']}; color:{t['term_fg']};"
            f"border:1px solid {t['border']}; padding:2px;")
        self._highlighter = LuaHighlighter(self._output.document())

    def _on_connected(self, connected: bool):
        self._input.setEnabled(connected)
        self._send_btn.setEnabled(connected)
        if connected:
            self._input.setFocus()
        else:
            self._input.clear()

    # ── Public API ────────────────────────────────────────────────────────

    def connect_to_port(self, port: str, baud: int = 115200):
        log.debug('Connecting to %s @ %d', port, baud)

        if self._worker:
            self._worker.stop()
            self._worker = None

        # Flush any stale data sitting in the serial buffer
        try:
            tmp = serial.Serial(port, baud, timeout=0.05)
            tmp.read(1024)
            tmp.close()
        except serial.SerialException:
            pass

        self._worker = SerialWorker(port, baud)
        self._worker.data_received.connect(self._on_data)
        self._worker.connection_lost.connect(self._on_lost)
        self._worker.start()
        t = theme.current()
        self._append(f'\n\n - Connected to {port} @ {baud} -\n\n', t['term_fg'],
                     italic=True, skip_highlight=True)
        self.connected.emit(True)

    def disconnect_port(self, port: str):
        if self._worker:
            log.debug('Disconnecting serial')

            t = theme.current()
            self._append(f'\n\n - Disconnected from {port} -\n\n', t['term_fg'],
                        italic=True, skip_highlight=True)

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

        text = text.replace('\r\n', '\n')
        text = text.replace('\n\r', '\n')
        for chunk, color in self._ansi.feed(text):
            self._append(chunk, color or theme.current()['term_fg'])

    def _on_lost(self, error: str):
        log.warning('Connection lost: %s', error)
        self._worker = None
        self.connected.emit(False)

    def _append(self, text: str, color: str, italic: bool = False,
                skip_highlight: bool = False):
        doc = self._output.document()

        # Detach highlighter before inserting skip_highlight text so it
        # doesn't colour the block before we can mark it.
        if skip_highlight:
            self._highlighter.setDocument(None)

        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontItalic(italic)
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

        if skip_highlight:
            # Mark every block we just wrote so the highlighter skips them
            end_block = cursor.block()
            block = doc.findBlock(cursor.position() - len(text))
            while block.isValid() and block.blockNumber() <= end_block.blockNumber():
                block.setUserData(SkipHighlight())
                block = block.next()
            # Re-attach — highlighter will now see SkipHighlight markers
            self._highlighter.setDocument(doc)

        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
