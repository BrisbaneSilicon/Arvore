"""Command Mode side panel.

Gives the user a structured way to issue ELM11 command-mode commands. The panel
enters/exits command mode on the device via `cmd` / `exit`, and captures the
response stream for display.
"""
from __future__ import annotations

import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QLabel, QTabWidget,
    QScrollArea, QStyle, QStyleOptionTab, QStylePainter, QTabBar,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStackedWidget, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPen


from . import theme
from .serial_terminal import _AnsiStripper


class _VerticalTabBar(QTabBar):
    """QTabBar placed on the side but drawn with horizontal label text."""

    # Extra horizontal margin beyond the measured text, covers tab chrome
    # padding that the style adds on top when drawing the label.
    _TEXT_PADDING = 40

    def tabSizeHint(self, index):
        s = super().tabSizeHint(index)
        if self.shape() in (QTabBar.Shape.RoundedWest,
                            QTabBar.Shape.RoundedEast):
            s.transpose()
        needed = self.fontMetrics().horizontalAdvance(
            self.tabText(index)) + self._TEXT_PADDING
        if s.width() < needed:
            s.setWidth(needed)
        return s

    def minimumTabSizeHint(self, index):
        s = super().minimumTabSizeHint(index)
        if self.shape() in (QTabBar.Shape.RoundedWest,
                            QTabBar.Shape.RoundedEast):
            s.transpose()
        needed = self.fontMetrics().horizontalAdvance(
            self.tabText(index)) + self._TEXT_PADDING
        if s.width() < needed:
            s.setWidth(needed)
        return s

    def paintEvent(self, _event):
        painter = QStylePainter(self)
        opt = QStyleOptionTab()
        for i in range(self.count()):
            self.initStyleOption(opt, i)
            painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, opt)
            # Swap the shape to a north-style one for the label only, so the
            # text is drawn horizontally instead of being rotated.
            opt.shape = QTabBar.Shape.RoundedNorth
            painter.drawControl(QStyle.ControlElement.CE_TabBarTabLabel, opt)
        # Thin separator lines between adjacent tabs
        painter.setPen(QPen(QColor('white'), 1))
        for i in range(self.count() - 1):
            r = self.tabRect(i)
            y = r.bottom()
            painter.drawLine(r.left(), y, r.right(), y)


_IO_TYPES = [
    'NONE', 'GPIO_OUT', 'GPIO_IN', 'PWM',
    'UART_OUT', 'UART_IN', 'SPI_OUT', 'SPI_IN', 'I2C',
]
_BAUD_RATES = [
    9600, 19200, 28800, 38400, 57600, 76800,
    115200, 230400, 460800, 576000, 921600,
]


class _ListOutputView(QWidget):
    """Base widget that accepts captured text chunks for a list command."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer: str = ''

    def clear_output(self):
        self._buffer = ''

    def append_output(self, text: str):
        self._buffer += text


class _RawOutputView(_ListOutputView):
    """Fallback: just show the raw text response."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text)

    def clear_output(self):
        super().clear_output()
        self._text.clear()

    def append_output(self, text: str):
        super().append_output(text)
        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self._text.setTextCursor(cursor)


class _ProgramSourceView(_ListOutputView):
    """Show the response to `list|program_code` / `list|program_bytecode`.

    Switches to a prominent error label if the device reports that the
    program couldn't be printed (e.g. because it doesn't exist).
    """

    _ERROR_RE = re.compile(
        r'Error[^\n]*?(?:failed\s+to\s+print\s+program'
        r'|unable\s+to\s+load\s+program)[^\n]*',
        re.IGNORECASE)
    # Lines where the device echoes the command we just sent.
    _ECHO_RE = re.compile(
        r'^[ \t]*list\|program_(?:code|bytecode)\([^\n]*\n?',
        re.MULTILINE | re.IGNORECASE)

    def __init__(self, parent=None, *, highlight_lua: bool = False):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        if highlight_lua:
            from .highlighter import LuaHighlighter
            self._highlighter = LuaHighlighter(self._text.document())
        self._stack.addWidget(self._text)

        self._error = QLabel()
        self._error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error.setWordWrap(True)
        self._error.setStyleSheet('color: #c45330; font-weight: bold;')
        self._stack.addWidget(self._error)

        layout.addWidget(self._stack)

    def clear_output(self):
        super().clear_output()
        self._text.clear()
        self._error.clear()
        self._stack.setCurrentWidget(self._text)

    def append_output(self, text: str):
        super().append_output(text)
        m = self._ERROR_RE.search(self._buffer)
        if m:
            self._error.setText(m.group(0).strip())
            self._stack.setCurrentWidget(self._error)
            return
        # Normal case — replace the editor content with the accumulated
        # buffer (minus echoed command lines and any leading whitespace)
        # so incremental arrivals stay in order.
        display = self._ECHO_RE.sub('', self._buffer).lstrip()
        self._text.setPlainText(display)
        self._text.moveCursor(self._text.textCursor().MoveOperation.End)
        self._stack.setCurrentWidget(self._text)


class _ProgramsView(_ListOutputView):
    """Parse `list|programs` output into a numbered table."""

    _LINE_RE = re.compile(r'^\s*Program\s+(\d+)\.\s*:\s*(\S.*?)\s*$', re.MULTILINE)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(['#', 'Program'])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def clear_output(self):
        super().clear_output()
        self._table.setRowCount(0)

    def append_output(self, text: str):
        super().append_output(text)
        self._refresh()

    def _refresh(self):
        matches = list(self._LINE_RE.finditer(self._buffer))
        self._table.setRowCount(len(matches))
        for row, m in enumerate(matches):
            num_item  = QTableWidgetItem(m.group(1))
            num_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 0, num_item)
            self._table.setItem(row, 1, QTableWidgetItem(m.group(2)))


_IO_TYPE_COLORS = {
    'NONE':     '#808080',
    'GPIO_OUT': '#cc7833',
    'GPIO_IN':  '#cc7833',
    'PWM':      '#ffc66d',
    'UART_OUT': '#6d9cbe',
    'UART_IN':  '#6d9cbe',
    'SPI_OUT':  '#a1617a',
    'SPI_IN':   '#a1617a',
    'I2C':      '#b4c973',
}


class _PinValueView(_ListOutputView):
    """Generic `PIN<n> : <value>` table renderer; subclasses tweak labels/colours."""

    _LINE_RE = re.compile(r'^\s*PIN(\d+)\s*:\s*(\S.*?)\s*$', re.MULTILINE)

    # Subclasses override.
    _VALUE_HEADER:  str                = 'Value'
    _VALUE_COLOURS: dict[str, str]     = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(['PIN', self._VALUE_HEADER])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def clear_output(self):
        super().clear_output()
        self._table.setRowCount(0)

    def append_output(self, text: str):
        super().append_output(text)
        self._refresh()

    def _refresh(self):
        matches = list(self._LINE_RE.finditer(self._buffer))
        self._table.setRowCount(len(matches))
        for row, m in enumerate(matches):
            pin_item = QTableWidgetItem(f'PIN{m.group(1)}')
            pin_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 0, pin_item)

            val = m.group(2).strip()
            val_item = QTableWidgetItem(val)
            colour = self._VALUE_COLOURS.get(val)
            if colour:
                val_item.setForeground(QColor(colour))
            self._table.setItem(row, 1, val_item)


class _IoTypeCfgView(_PinValueView):
    _VALUE_HEADER  = 'Type'
    _VALUE_COLOURS = _IO_TYPE_COLORS


class _IoBaudCfgView(_PinValueView):
    _VALUE_HEADER = 'Baud'


class _IoPwmCfgView(_PinValueView):
    _VALUE_HEADER = 'PWM Freq'


class _IoSpiCfgView(_PinValueView):
    _VALUE_HEADER = 'SPI Freq'


class _IoCapsView(_ListOutputView):
    """Parse `list|io_capabilities` output into a pin capability matrix."""

    _ROW_RE = re.compile(r'^\s*PIN(\d+)\s*\|(.*)$', re.MULTILINE)
    _CAP_COLS = ['GPIO_OUT', 'GPIO_IN', 'PWM', 'UART_OUT', 'UART_IN',
                 'SPI_OUT', 'SPI_IN', 'I2C']
    _EXTRA_COLS = ['SW_INTRPTS', 'HW_BUFFER']
    _HEADERS = ['PIN'] + _CAP_COLS + _EXTRA_COLS

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, len(self._HEADERS))
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def clear_output(self):
        super().clear_output()
        self._table.setRowCount(0)

    def append_output(self, text: str):
        super().append_output(text)
        self._refresh()

    def _refresh(self):
        matches = list(self._ROW_RE.finditer(self._buffer))
        self._table.setRowCount(len(matches))
        for row, m in enumerate(matches):
            parts = [p.strip() for p in m.group(2).split('|')]
            pin_item = QTableWidgetItem(f'PIN{m.group(1)}')
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, pin_item)

            # 8 capability columns (indices 0-7 in parts)
            for i in range(len(self._CAP_COLS)):
                val = parts[i] if i < len(parts) else ''
                item = QTableWidgetItem('✓' if 'X' in val else '')
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, i + 1, item)

            # After the capability block there's a blank cell from the `||`
            # separator, then SW_INTRPTS and HW_BUFFER.
            sw_idx, hw_idx = 9, 10
            if len(parts) > sw_idx:
                item = QTableWidgetItem('✓' if 'X' in parts[sw_idx] else '')
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, 1 + len(self._CAP_COLS), item)
            if len(parts) > hw_idx:
                item = QTableWidgetItem(parts[hw_idx])
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, 2 + len(self._CAP_COLS), item)


class _KeyValueView(_ListOutputView):
    """Parse `<key>: <value>` lines into a name/value table.

    Used for `list|timer_cfg`, `list|watchdog_cfg`, etc. Values matching a
    known status token (enabled / disabled / yes / no) are colour-coded.
    """

    _LINE_RE = re.compile(r'^\s*(\S.*?)\s*:\s*(\S.*?)\s*$', re.MULTILINE)

    _KEY_HEADER:   str = 'Name'
    _VALUE_HEADER: str = 'Value'
    _VALUE_COLOURS: dict[str, str] = {
        'enabled':      '#b4c973',
        'disabled':     '#808080',
        'yes':          '#b4c973',
        'no':           '#808080',
        'unconfigured': '#808080',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels([self._KEY_HEADER, self._VALUE_HEADER])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def clear_output(self):
        super().clear_output()
        self._table.setRowCount(0)

    def append_output(self, text: str):
        super().append_output(text)
        self._refresh()

    def _refresh(self):
        matches = list(self._LINE_RE.finditer(self._buffer))
        self._table.setRowCount(len(matches))
        for row, m in enumerate(matches):
            self._table.setItem(row, 0, QTableWidgetItem(m.group(1).strip()))
            val = m.group(2).strip()
            item = QTableWidgetItem(val)
            colour = self._VALUE_COLOURS.get(val.lower())
            if colour:
                item.setForeground(QColor(colour))
            self._table.setItem(row, 1, item)


class _XbarCfgView(_ListOutputView):
    """Parse `list|xbar_cfg` output — two sub-tables (XBAR LOCK, XBAR DATA),
    each with core columns and named rows."""

    _SECTION_RE = re.compile(r'^\s*(XBAR\s+LOCK|XBAR\s+DATA)\s*$', re.MULTILINE)
    _HEADER_RE  = re.compile(r'^\s+\|(.*)\|\s*$')
    _ROW_RE     = re.compile(r'^\s*(\S.*?)\s*\|(.*)\|\s*$')

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self._lock_label = QLabel('XBAR LOCK')
        self._lock_table = self._make_table()
        self._data_label = QLabel('XBAR DATA')
        self._data_table = self._make_table()

        layout.addWidget(self._lock_label)
        layout.addWidget(self._lock_table, 1)
        layout.addWidget(self._data_label)
        layout.addWidget(self._data_table, 1)

    @staticmethod
    def _make_table() -> QTableWidget:
        t = QTableWidget(0, 0)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setVisible(True)
        return t

    def clear_output(self):
        super().clear_output()
        for t in (self._lock_table, self._data_table):
            t.clear()
            t.setRowCount(0)
            t.setColumnCount(0)

    def append_output(self, text: str):
        super().append_output(text)
        self._refresh()

    def _refresh(self):
        sections = self._split_sections(self._buffer.splitlines())
        if 'XBAR LOCK' in sections:
            self._populate(self._lock_table, sections['XBAR LOCK'])
        if 'XBAR DATA' in sections:
            self._populate(self._data_table, sections['XBAR DATA'])

    @classmethod
    def _split_sections(cls, lines: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        current: str | None = None
        buf: list[str] = []
        for line in lines:
            m = cls._SECTION_RE.match(line)
            if m:
                if current is not None:
                    result[current] = buf
                current = m.group(1).strip()
                buf = []
            elif current is not None:
                buf.append(line)
        if current is not None:
            result[current] = buf
        return result

    @classmethod
    def _populate(cls, table: QTableWidget, lines: list[str]):
        headers: list[str] = []
        rows: list[tuple[str, list[str]]] = []
        for line in lines:
            if not line.strip():
                continue
            if not headers:
                m = cls._HEADER_RE.match(line)
                if m:
                    headers = [c.strip() for c in m.group(1).split('|')]
                continue
            m = cls._ROW_RE.match(line)
            if m:
                label = m.group(1).strip()
                values = [c.strip() for c in m.group(2).split('|')]
                rows.append((label, values))

        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        table.setVerticalHeaderLabels([label for label, _ in rows])
        for r, (_, values) in enumerate(rows):
            for c in range(len(headers)):
                val = values[c] if c < len(values) else ''
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(r, c, item)


class _ClockFreqView(_ListOutputView):
    """Display `list|clk_freq` as a single prominent value."""

    _RE = re.compile(r'(\d+)\s*[Mm][Hh][Zz]')

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        self._value = QLabel('—')
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._value.font()
        font.setPointSize(max(font.pointSize() * 2, 28))
        font.setBold(True)
        self._value.setFont(font)
        layout.addWidget(self._value)
        caption = QLabel('Clock Frequency')
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(caption)
        layout.addStretch(1)

    def clear_output(self):
        super().clear_output()
        self._value.setText('—')

    def append_output(self, text: str):
        super().append_output(text)
        m = self._RE.search(self._buffer)
        if m:
            self._value.setText(f'{m.group(1)} MHz')


class _BootProgramView(_ListOutputView):
    """Display `list|start_on_boot_program` — either the program name
    or "(not configured)" when no start-on-boot program is set."""

    _NONE_RE = re.compile(r'No\s+start-on-boot\s+program\s+configured',
                          re.IGNORECASE)
    _PROG_RE = re.compile(r'\b([\w\-.]+\.lua)\b')

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        self._value = QLabel('—')
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._value.font()
        font.setPointSize(max(font.pointSize() * 2, 20))
        font.setBold(True)
        self._value.setFont(font)
        layout.addWidget(self._value)
        caption = QLabel('Start-on-boot Program')
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(caption)
        layout.addStretch(1)

    def clear_output(self):
        super().clear_output()
        self._value.setText('—')
        self._value.setStyleSheet('')

    def append_output(self, text: str):
        super().append_output(text)
        if self._NONE_RE.search(self._buffer):
            self._value.setText('(not configured)')
            self._value.setStyleSheet('color: #808080;')
            return
        m = self._PROG_RE.search(self._buffer)
        if m:
            self._value.setText(m.group(1))
            self._value.setStyleSheet('')


_LIST_VIEW_CLASSES: dict[str, type[_ListOutputView]] = {
    'list|programs':              _ProgramsView,
    'list|io_type_cfg':           _IoTypeCfgView,
    'list|io_baud_cfg':           _IoBaudCfgView,
    'list|io_pwm_cfg':            _IoPwmCfgView,
    'list|io_spi_cfg':            _IoSpiCfgView,
    'list|io_capabilities':       _IoCapsView,
    'list|timer_cfg':             _KeyValueView,
    'list|watchdog_cfg':          _KeyValueView,
    'list|bus_cfg':               _KeyValueView,
    'list|xbar_cfg':              _XbarCfgView,
    'list|clk_freq':              _ClockFreqView,
    'list|start_on_boot_program':        _BootProgramView,
    'list|start_on_boot_prompt_format':  _KeyValueView,
}


class _HistoryView(_ListOutputView):
    """Parse `list|repl_history` / `list|cmd_history` — numbered entries."""

    _LINE_RE = re.compile(r'^\s*(\d+)\s*:\s*(.+?)\s*$', re.MULTILINE)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(['#', 'Command'])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def clear_output(self):
        super().clear_output()
        self._table.setRowCount(0)

    def append_output(self, text: str):
        super().append_output(text)
        self._refresh()

    def _refresh(self):
        matches = list(self._LINE_RE.finditer(self._buffer))
        self._table.setRowCount(len(matches))
        for row, m in enumerate(matches):
            num_item = QTableWidgetItem(m.group(1))
            num_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 0, num_item)
            self._table.setItem(row, 1, QTableWidgetItem(m.group(2)))


_LIST_VIEW_CLASSES['list|repl_history'] = _HistoryView
_LIST_VIEW_CLASSES['list|cmd_history']  = _HistoryView


class CommandModePanel(QWidget):
    """Sidebar panel for entering and driving ELM11 command mode."""

    active_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._terminal = None
        self._worker   = None
        self._active   = False
        self._current_output_view: _ListOutputView | None = None
        # Buffered ANSI stripper — handles partial escape sequences split
        # across serial chunks so they don't leak into parser views.
        self._stripper = _AnsiStripper(reply_cb=None)
        self._build_ui()
        self._set_controls_enabled(False)

    @property
    def is_active(self) -> bool:
        return self._active

    # ── External wiring ────────────────────────────────────────────────────

    def set_terminal(self, terminal):
        """Attach the SerialTerminal whose worker we should drive."""
        if self._terminal is terminal:
            return
        if self._terminal is not None:
            try:
                self._terminal.connected.disconnect(self._on_connection_changed)
            except TypeError:
                pass
        self._terminal = terminal
        terminal.connected.connect(self._on_connection_changed)
        self._on_connection_changed(terminal.is_connected)

    def shutdown(self):
        """Cleanly exit command mode on the device (if active) — call on close."""
        if self._active:
            self._deactivate(send_exit=True)

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        root.addWidget(self._tabs, 1)

        # One tab per command family. List and Set present their own
        # vertical sub-tab bars, so they aren't wrapped in a scroll area.
        self._list_tab_idx = self._tabs.addTab(self._group_list(), 'List')
        self._tabs.addTab(self._group_set(),                  'Set')
        self._tabs.addTab(self._as_tab(self._group_reset()),  'Reset')
        self._tabs.addTab(self._as_tab(self._group_delete()), 'Delete')
        self._tabs.addTab(self._as_tab(self._group_load()),   'Load')
        self._tabs.addTab(self._as_tab(self._group_run()),    'Run')
        self._tabs.addTab(self._as_tab(self._group_cycle()),  'Cycle')

        # Raw tab (free-form input)
        raw = QWidget()
        raw_layout = QVBoxLayout(raw)
        raw_row = QHBoxLayout()
        self._raw_input = QLineEdit()
        self._raw_input.setPlaceholderText('e.g. list|programs')
        self._raw_input.returnPressed.connect(self._send_raw)
        raw_row.addWidget(self._raw_input)
        self._raw_send = QPushButton('Send')
        self._raw_send.clicked.connect(self._send_raw)
        raw_row.addWidget(self._raw_send)
        raw_layout.addLayout(raw_row)
        raw_layout.addStretch(1)
        self._tabs.addTab(raw, 'Raw')

        # Re-fire the currently-selected list command whenever the user
        # returns to the List outer tab from any other family.
        self._tabs.currentChanged.connect(self._on_outer_tab_changed)

        # Offset the outer tab bar so its left edge lines up with the right
        # edge of the inner vertical list tab bar. Use a QLabel with the
        # longest inner tab's text rendered transparently — this forces the
        # corner widget to claim the right width from its sizeHint, whereas a
        # plain QWidget sometimes collapses to zero width.
        offset = self._list_tab_bar_width
        if offset:
            spacer = QLabel('Boot Prompt Format')
            spacer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spacer.setStyleSheet(
                'color: transparent; background: transparent;'
                'padding: 0px; margin: 0px;'
            )
            # Use fixedWidth so the corner claims exactly the inner bar width
            # (plus a tiny nudge for the QTabWidget's own corner padding).
            spacer.setFixedWidth(offset + 4)
            self._tabs.setCornerWidget(spacer, Qt.Corner.TopLeftCorner)

    @staticmethod
    def _as_tab(content: QWidget) -> QWidget:
        """Wrap a group body in a scroll area so long tabs remain usable."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        return scroll

    # ── Command groups ─────────────────────────────────────────────────────

    def _group_list(self) -> QWidget:
        self._track_buttons = getattr(self, '_track_buttons', [])

        list_tabs = QTabWidget()
        list_tabs.setDocumentMode(True)
        list_tabs.setTabBar(_VerticalTabBar(list_tabs))
        # Must come *after* setTabBar — otherwise the new tab bar is created
        # with the default (North) shape.
        list_tabs.setTabPosition(QTabWidget.TabPosition.West)
        list_tabs.tabBar().setExpanding(False)
        list_tabs.tabBar().setUsesScrollButtons(False)
        list_tabs.setUsesScrollButtons(False)

        no_arg = [
            ('I/O Capabilities',      'list|io_capabilities'),
            ('I/O Type Config',       'list|io_type_cfg'),
            ('I/O Baud Config',       'list|io_baud_cfg'),
            ('I/O PWM Config',        'list|io_pwm_cfg'),
            ('I/O SPI Config',        'list|io_spi_cfg'),
            ('Timer Config',          'list|timer_cfg'),
            ('Watchdog Config',       'list|watchdog_cfg'),
            ('Bus Config',            'list|bus_cfg'),
            ('XBar Config',           'list|xbar_cfg'),
            ('Clock Frequency',       'list|clk_freq'),
            ('Programs',              'list|programs'),
            ('Boot Program',          'list|start_on_boot_program'),
            ('Boot Prompt Format',    'list|start_on_boot_prompt_format'),
            ('REPL History',          'list|repl_history'),
            ('CMD History',           'list|cmd_history'),
        ]
        for label, cmd in no_arg:
            view_cls = _LIST_VIEW_CLASSES.get(cmd, _RawOutputView)
            view = view_cls()
            page = QWidget()
            v = QVBoxLayout(page)
            v.setContentsMargins(4, 4, 4, 4)
            v.addWidget(view, 1)
            page.setProperty('list_command', cmd)
            page._output_view = view
            list_tabs.addTab(page, label)

        # Parametrised tabs — user supplies a program name and clicks a button.
        # (No auto-send on tab change for these, since an empty name produces
        # nothing useful.)
        list_tabs.addTab(
            self._build_program_source_tab('list|program_code'),
            'Program Code')
        list_tabs.addTab(
            self._build_program_source_tab('list|program_bytecode'),
            'Program Bytecode')

        list_tabs.currentChanged.connect(self._on_list_tab_changed)
        self._list_tabs = list_tabs
        # Reuse the programs view for these two — output is raw program
        # source / bytecode text, so we register them under `_RawOutputView`
        # implicitly (no explicit entry needed).
        # Width of the inner vertical tab bar — used by the parent to offset
        # the outer tab bar so their edges line up visually.
        self._list_tab_bar_width = max(
            list_tabs.tabBar().tabSizeHint(i).width()
            for i in range(list_tabs.count())
        )
        return list_tabs

    def _build_program_source_tab(self, command: str) -> QWidget:
        """Return a tab page with a program-name input + send button, above a
        source/error output view that shows the device's response."""
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(4, 4, 4, 4)

        row = QHBoxLayout()
        name_input = QLineEdit()
        name_input.setPlaceholderText('program name')
        btn_label = ('Print Program Code' if command == 'list|program_code'
                     else 'Print Program Bytecode')
        send_btn = QPushButton(btn_label)
        send_btn.clicked.connect(lambda: self._send_program_query(
            command, name_input.text().strip(), page))
        name_input.returnPressed.connect(send_btn.click)
        row.addWidget(QLabel('Program:'))
        row.addWidget(name_input, 1)
        row.addWidget(send_btn)
        v.addLayout(row)

        view = _ProgramSourceView(highlight_lua=(command == 'list|program_code'))
        v.addWidget(view, 1)

        page._output_view = view
        # These tabs don't have a fixed command (the name varies), so leave
        # `list_command` unset — the tab-change handler will skip auto-sending.
        self._track_buttons.append(send_btn)
        return page

    def _send_program_query(self, command: str, name: str, page: QWidget):
        if not name:
            return
        view = getattr(page, '_output_view', None)
        if view is not None:
            view.clear_output()
        self._current_output_view = view
        self._stripper._pending = ''
        self._send(f'{command}("{name}")')

    def _on_outer_tab_changed(self, index: int):
        """If we've landed back on the List tab, refresh its current view."""
        if index != getattr(self, '_list_tab_idx', -1):
            return
        if not self._active:
            return
        self._on_list_tab_changed(self._list_tabs.currentIndex())

    def _on_list_tab_changed(self, index: int):
        if index < 0:
            return
        page = self._list_tabs.widget(index)
        if not page:
            return
        view = getattr(page, '_output_view', None)
        if view is not None:
            view.clear_output()
        self._current_output_view = view
        # Drop any partial escape-sequence state carried over from the
        # previous tab's capture.
        self._stripper._pending = ''
        cmd = page.property('list_command')
        if cmd:
            self._send(cmd)

    def _group_set(self) -> QWidget:
        self._track_buttons = getattr(self, '_track_buttons', [])

        set_tabs = QTabWidget()
        set_tabs.setDocumentMode(True)
        set_tabs.setTabBar(_VerticalTabBar(set_tabs))
        set_tabs.setTabPosition(QTabWidget.TabPosition.West)
        set_tabs.tabBar().setExpanding(False)
        set_tabs.tabBar().setUsesScrollButtons(False)
        set_tabs.setUsesScrollButtons(False)

        set_tabs.addTab(self._set_io_type_tab(),     'I/O Type')
        set_tabs.addTab(self._set_uart_baud_tab(),   'UART Baud')
        set_tabs.addTab(self._set_pwm_freq_tab(),    'PWM Freq')
        set_tabs.addTab(self._set_spi_freq_tab(),    'SPI Freq')
        set_tabs.addTab(self._set_boot_io_tab(),     'Boot I/O Default')
        set_tabs.addTab(self._set_boot_prompt_tab(), 'Boot Prompt Default')
        set_tabs.addTab(self._set_boot_program_tab(),'Boot Program')

        return set_tabs

    # ── Per-tab builders (Set) ────────────────────────────────────────────

    @staticmethod
    def _make_pin_combo() -> QComboBox:
        """Dropdown with PIN1 through PIN32 — the max supported pin count."""
        combo = QComboBox()
        combo.addItems(f'PIN{i}' for i in range(1, 33))
        return combo

    def _set_io_type_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._set_io_pin = self._make_pin_combo()
        self._set_io_type = QComboBox(); self._set_io_type.addItems(_IO_TYPES)
        btn = QPushButton('Set I/O Type')
        btn.clicked.connect(lambda: self._send(
            f'set|io_type_cfg({self._set_io_pin.currentText()}, '
            f'{self._set_io_type.currentText()})'))
        form.addRow('PIN:',  self._set_io_pin)
        form.addRow('Type:', self._set_io_type)
        form.addRow(btn)
        self._track_buttons.append(btn)
        return page

    def _set_uart_baud_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._set_baud_pin = self._make_pin_combo()
        self._set_baud = QComboBox()
        self._set_baud.addItems(str(b) for b in _BAUD_RATES)
        self._set_baud.setCurrentText('115200')
        btn = QPushButton('Set UART Baud')
        btn.clicked.connect(lambda: self._send(
            f'set|io_baud_cfg({self._set_baud_pin.currentText()}, '
            f'{self._set_baud.currentText()})'))
        form.addRow('PIN:',  self._set_baud_pin)
        form.addRow('Baud:', self._set_baud)
        form.addRow(btn)
        self._track_buttons.append(btn)
        return page

    def _set_pwm_freq_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._set_pwm_pin = self._make_pin_combo()
        self._set_pwm_khz = QSpinBox()
        self._set_pwm_khz.setRange(1, 200); self._set_pwm_khz.setValue(10)
        self._set_pwm_khz.setSuffix(' kHz')
        btn = QPushButton('Set PWM Frequency')
        btn.clicked.connect(lambda: self._send(
            f'set|io_pwm_cfg({self._set_pwm_pin.currentText()}, '
            f'{self._set_pwm_khz.value()})'))
        form.addRow('PIN:',   self._set_pwm_pin)
        form.addRow('Freq:',  self._set_pwm_khz)
        form.addRow(btn)
        self._track_buttons.append(btn)
        return page

    def _set_spi_freq_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._set_spi_pin = self._make_pin_combo()
        self._set_spi_khz = QSpinBox()
        self._set_spi_khz.setRange(1, 250); self._set_spi_khz.setValue(10)
        self._set_spi_khz.setSuffix(' kHz')
        btn = QPushButton('Set SPI Frequency')
        btn.clicked.connect(lambda: self._send(
            f'set|io_spi_cfg({self._set_spi_pin.currentText()}, '
            f'{self._set_spi_khz.value()})'))
        form.addRow('PIN:',  self._set_spi_pin)
        form.addRow('Freq:', self._set_spi_khz)
        form.addRow(btn)
        self._track_buttons.append(btn)
        return page

    def _set_boot_io_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        info = QLabel('Store the current I/O type configuration as the\n'
                      'start-on-boot default.')
        info.setWordWrap(True)
        v.addWidget(info)
        btn = QPushButton('Save Current I/O as Boot Default')
        btn.clicked.connect(lambda: self._send('set|start_on_boot_io_type_cfg'))
        v.addWidget(btn)
        v.addStretch(1)
        self._track_buttons.append(btn)
        return page

    def _set_boot_prompt_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        info = QLabel('Store the current prompt format as the\n'
                      'start-on-boot default.')
        info.setWordWrap(True)
        v.addWidget(info)
        btn = QPushButton('Save Current Prompt as Boot Default')
        btn.clicked.connect(lambda: self._send('set|start_on_boot_prompt_format'))
        v.addWidget(btn)
        v.addStretch(1)
        self._track_buttons.append(btn)
        return page

    def _set_boot_program_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._set_boot_prog = QLineEdit()
        self._set_boot_prog.setPlaceholderText('program name')
        btn = QPushButton('Set Boot Program')
        btn.clicked.connect(lambda: self._send(
            f'set|start_on_boot_program("{self._set_boot_prog.text().strip()}")'))
        self._set_boot_prog.returnPressed.connect(btn.click)
        form.addRow('Program:', self._set_boot_prog)
        form.addRow(btn)
        self._track_buttons.append(btn)
        return page

    def _group_reset(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._reset_pin = self._make_pin_combo()
        b = QPushButton('Reset I/O Type')
        b.clicked.connect(lambda: self._send(
            f'reset|io_type_cfg({self._reset_pin.currentText()})'))
        row = QHBoxLayout()
        row.addWidget(QLabel('PIN'))
        row.addWidget(self._reset_pin)
        row.addWidget(b)
        form.addRow('I/O Type:', self._wrap(row))
        self._track_buttons.append(b)

        for label, cmd in [
            ('Reset All I/O Types',      'reset|all_io_type_cfg'),
            ('Reset Boot Prompt Format', 'reset|start_on_boot_prompt_format'),
            ('Reset Boot I/O Config',    'reset|start_on_boot_io_type_cfg'),
            ('Reset Boot Program',       'reset|start_on_boot_program'),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, c=cmd: self._send(c))
            form.addRow(btn)
            self._track_buttons.append(btn)
        return w

    def _group_delete(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._del_prog = QLineEdit()
        self._del_prog.setPlaceholderText('program name')
        b = QPushButton('Delete Program')
        b.clicked.connect(lambda: self._send(
            f'delete|program("{self._del_prog.text().strip()}")'))
        row = QHBoxLayout()
        row.addWidget(self._del_prog)
        row.addWidget(b)
        form.addRow('Program:', self._wrap(row))
        self._track_buttons.append(b)

        b2 = QPushButton('Delete ALL Programs')
        b2.clicked.connect(lambda: self._send('delete|all_programs'))
        form.addRow(b2)
        self._track_buttons.append(b2)
        return w

    def _group_load(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        b = QPushButton('Load Boot I/O Config')
        b.clicked.connect(lambda: self._send('load|start_on_boot_io_type_cfg'))
        v.addWidget(b)
        v.addStretch(1)
        self._track_buttons.append(b)
        return w

    def _group_run(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._run_prog = QLineEdit()
        self._run_prog.setPlaceholderText('program name')
        b = QPushButton('Run Program')
        b.clicked.connect(lambda: self._send(
            f'run|program("{self._run_prog.text().strip()}")'))
        row = QHBoxLayout()
        row.addWidget(self._run_prog)
        row.addWidget(b)
        form.addRow('Program:', self._wrap(row))
        self._track_buttons.append(b)

        reboot = QPushButton('Reboot Core')
        reboot.clicked.connect(lambda: self._send('run|reboot'))
        form.addRow(reboot)
        self._track_buttons.append(reboot)
        return w

    def _group_cycle(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        a = QPushButton('Cycle CPU Prompt')
        a.clicked.connect(lambda: self._send('cycle|cpuprompt'))
        b = QPushButton('Cycle Time Prompt')
        b.clicked.connect(lambda: self._send('cycle|timeprompt'))
        grid.addWidget(a, 0, 0)
        grid.addWidget(b, 0, 1)
        self._track_buttons.extend([a, b])
        return w

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    # ── Runtime behaviour ──────────────────────────────────────────────────

    def _on_connection_changed(self, connected: bool):
        if connected:
            self._worker = self._terminal.get_worker() if self._terminal else None
        else:
            if self._active:
                self._deactivate(send_exit=False)
            self._worker = None
            self._set_controls_enabled(False)

    def set_active(self, active: bool):
        """Public toggle used by an external button."""
        if active and not self._active:
            self._activate()
        elif not active and self._active:
            self._deactivate(send_exit=True)

    def _activate(self):
        if not self._worker:
            return
        # Tap the serial stream so we can route responses to per-tab views.
        self._worker.data_received.connect(self._on_response_data)
        # Stop any running program first. The ELM11 needs a brief moment to
        # process the user-interrupt before it's ready to accept `cmd`.
        self._worker.send(b'q\n')
        QTimer.singleShot(300, self._send_cmd_enter)
        self._active = True
        self._set_controls_enabled(True)
        self.active_changed.emit(True)
        # After command mode is ready, trigger the current list tab's command
        # so its view populates without requiring a click.
        QTimer.singleShot(600, lambda: self._on_list_tab_changed(
            self._list_tabs.currentIndex()))

    def _send_cmd_enter(self):
        if self._active and self._worker:
            self._worker.send(b'cmd\n')

    def _deactivate(self, send_exit: bool):
        if self._worker:
            try:
                self._worker.data_received.disconnect(self._on_response_data)
            except TypeError:
                pass
            if send_exit:
                self._worker.send(b'exit\n')
        was_active = self._active
        self._active = False
        self._current_output_view = None
        self._set_controls_enabled(False)
        if was_active:
            self.active_changed.emit(False)

    def _on_response_data(self, data: bytes):
        """Route serial bytes into the currently-selected list output view."""
        if not self._current_output_view:
            return
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            return
        clean = self._stripper.feed(text)
        if not clean:
            return
        # Normalise CRLF / stray CR so QPlainTextEdit doesn't render an
        # extra blank line per serial line.
        clean = clean.replace('\r\n', '\n').replace('\r', '\n')
        self._current_output_view.append_output(clean)

    def _send(self, cmd: str):
        if not self._active or not self._worker:
            return
        self._worker.send((cmd + '\n').encode())

    def _send_raw(self):
        cmd = self._raw_input.text().strip()
        if cmd:
            self._send(cmd)
            self._raw_input.clear()

    def _set_controls_enabled(self, enabled: bool):
        # Disable the whole tab area (tabs + all contents) when command mode
        # isn't active, so the panel clearly reads as inert.
        self._tabs.setEnabled(enabled)
        if enabled:
            self._tabs.setStyleSheet('')
            self._tabs.setGraphicsEffect(None)
        else:
            t = theme.current()
            self._tabs.setStyleSheet(
                f'QTabBar::tab {{ color:{t["btn_disabled_fg"]}; }}'
                f'QTabBar::tab:selected {{ background:{t["tab_bg"]}; '
                f'color:{t["btn_disabled_fg"]}; '
                f'border-top:2px solid {t["border"]}; }}'
            )
            # Dim the entire tab content so every widget (tables, inputs,
            # buttons, labels) reads as inactive, not just the tab bar.
            effect = QGraphicsOpacityEffect(self._tabs)
            effect.setOpacity(0.45)
            self._tabs.setGraphicsEffect(effect)

    # ── Theme ──────────────────────────────────────────────────────────────

    def apply_theme(self):
        t = theme.current()
        self.setStyleSheet(
            f'QWidget {{ background:{t["window_bg"]}; color:{t["window_fg"]}; }}'
            f'QLineEdit, QSpinBox, QComboBox {{ background:{t["dlg_input_bg"]}; '
            f'color:{t["dlg_input_fg"]}; border:1px solid {t["border"]}; padding:2px 4px; }}'
        )
        # Re-apply the disabled tab styling if currently inactive
        self._set_controls_enabled(self._active)
