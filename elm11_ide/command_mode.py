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
    QAbstractItemView,
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


class _IoTypeCfgView(_ListOutputView):
    """Parse `list|io_type_cfg` output into a pin → type table."""

    _LINE_RE = re.compile(r'^\s*PIN(\d+)\s*:\s*(\S+)\s*$', re.MULTILINE)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(['PIN', 'Type'])
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

            type_name = m.group(2)
            type_item = QTableWidgetItem(type_name)
            colour = _IO_TYPE_COLORS.get(type_name)
            if colour:
                type_item.setForeground(QColor(colour))
            self._table.setItem(row, 1, type_item)


_LIST_VIEW_CLASSES: dict[str, type[_ListOutputView]] = {
    'list|programs':    _ProgramsView,
    'list|io_type_cfg': _IoTypeCfgView,
}


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

        # One tab per command family. The List tab already presents its own
        # (bottom-positioned) sub-tab bar, so it isn't wrapped in a scroll area.
        self._tabs.addTab(self._group_list(),                 'List')
        self._tabs.addTab(self._as_tab(self._group_set()),    'Set')
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
            ('Boot Prompt Format',    'list|start_on_boot_prompt_format'),
            ('I/O Capabilities',      'list|io_capabilities'),
            ('I/O Type Config',       'list|io_type_cfg'),
            ('I/O Baud Config',       'list|io_baud_cfg'),
            ('I/O PWM Config',        'list|io_pwm_cfg'),
            ('I/O SPI Config',        'list|io_spi_cfg'),
            ('Timer Config',          'list|timer_cfg'),
            ('Watchdog Config',       'list|watchdog_cfg'),
            ('Bus Config',            'list|bus_cfg'),
            ('XBar Config',           'list|xbar_cfg'),
            ('User Comms Config',     'list|user_comms_cfg'),
            ('Clock Frequency',       'list|clk_freq'),
            ('Programs',              'list|programs'),
            ('Boot Program',          'list|start_on_boot_program'),
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

        # Parametrised: program code / bytecode — no auto-send; user supplies a
        # program name and clicks a button.
        self._list_prog_name = QLineEdit()
        self._list_prog_name.setPlaceholderText('program name')
        code_btn = QPushButton('Send list|program_code')
        code_btn.clicked.connect(
            lambda: self._send(f'list|program_code("{self._list_prog_name.text().strip()}")'))
        bytecode_btn = QPushButton('Send list|program_bytecode')
        bytecode_btn.clicked.connect(
            lambda: self._send(f'list|program_bytecode("{self._list_prog_name.text().strip()}")'))
        self._track_buttons.extend([code_btn, bytecode_btn])

        param_page = QWidget()
        form = QFormLayout(param_page)
        form.addRow('Program:', self._list_prog_name)
        form.addRow(code_btn)
        form.addRow(bytecode_btn)
        list_tabs.addTab(param_page, 'Program Code')

        list_tabs.currentChanged.connect(self._on_list_tab_changed)
        self._list_tabs = list_tabs
        # Width of the inner vertical tab bar — used by the parent to offset
        # the outer tab bar so their edges line up visually.
        self._list_tab_bar_width = max(
            list_tabs.tabBar().tabSizeHint(i).width()
            for i in range(list_tabs.count())
        )
        return list_tabs

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
        w = QWidget()
        form = QFormLayout(w)

        # IO Type Config
        self._set_io_pin = QSpinBox(); self._set_io_pin.setRange(1, 64)
        self._set_io_type = QComboBox(); self._set_io_type.addItems(_IO_TYPES)
        btn = QPushButton('Set I/O Type')
        btn.clicked.connect(lambda: self._send(
            f'set|io_type_cfg(PIN{self._set_io_pin.value()}, {self._set_io_type.currentText()})'))
        row = QHBoxLayout()
        row.addWidget(QLabel('PIN'))
        row.addWidget(self._set_io_pin)
        row.addWidget(self._set_io_type)
        row.addWidget(btn)
        form.addRow('I/O Type:', self._wrap(row))
        self._track_buttons.append(btn)

        # IO Baud Config
        self._set_baud_pin = QSpinBox(); self._set_baud_pin.setRange(1, 64)
        self._set_baud = QComboBox()
        self._set_baud.addItems(str(b) for b in _BAUD_RATES)
        self._set_baud.setCurrentText('115200')
        btn = QPushButton('Set UART Baud')
        btn.clicked.connect(lambda: self._send(
            f'set|io_baud_cfg(PIN{self._set_baud_pin.value()}, {self._set_baud.currentText()})'))
        row = QHBoxLayout()
        row.addWidget(QLabel('PIN'))
        row.addWidget(self._set_baud_pin)
        row.addWidget(self._set_baud)
        row.addWidget(btn)
        form.addRow('UART Baud:', self._wrap(row))
        self._track_buttons.append(btn)

        # PWM Freq
        self._set_pwm_pin = QSpinBox(); self._set_pwm_pin.setRange(1, 64)
        self._set_pwm_khz = QSpinBox()
        self._set_pwm_khz.setRange(1, 200); self._set_pwm_khz.setValue(10)
        btn = QPushButton('Set PWM kHz')
        btn.clicked.connect(lambda: self._send(
            f'set|io_pwm_cfg(PIN{self._set_pwm_pin.value()}, {self._set_pwm_khz.value()})'))
        row = QHBoxLayout()
        row.addWidget(QLabel('PIN'))
        row.addWidget(self._set_pwm_pin)
        row.addWidget(self._set_pwm_khz)
        row.addWidget(QLabel('kHz'))
        row.addWidget(btn)
        form.addRow('PWM Freq:', self._wrap(row))
        self._track_buttons.append(btn)

        # SPI Freq
        self._set_spi_pin = QSpinBox(); self._set_spi_pin.setRange(1, 64)
        self._set_spi_khz = QSpinBox()
        self._set_spi_khz.setRange(1, 250); self._set_spi_khz.setValue(10)
        btn = QPushButton('Set SPI kHz')
        btn.clicked.connect(lambda: self._send(
            f'set|io_spi_cfg(PIN{self._set_spi_pin.value()}, {self._set_spi_khz.value()})'))
        row = QHBoxLayout()
        row.addWidget(QLabel('PIN'))
        row.addWidget(self._set_spi_pin)
        row.addWidget(self._set_spi_khz)
        row.addWidget(QLabel('kHz'))
        row.addWidget(btn)
        form.addRow('SPI Freq:', self._wrap(row))
        self._track_buttons.append(btn)

        # Boot defaults
        boot_row = QHBoxLayout()
        b1 = QPushButton('Current I/O → Boot Default')
        b1.clicked.connect(lambda: self._send('set|start_on_boot_io_type_cfg'))
        b2 = QPushButton('Current Prompt → Boot Default')
        b2.clicked.connect(lambda: self._send('set|start_on_boot_prompt_format'))
        boot_row.addWidget(b1); boot_row.addWidget(b2)
        form.addRow('Boot Defaults:', self._wrap(boot_row))
        self._track_buttons.extend([b1, b2])

        # Set start-on-boot program
        self._set_boot_prog = QLineEdit()
        self._set_boot_prog.setPlaceholderText('program name')
        b = QPushButton('Set Boot Program')
        b.clicked.connect(lambda: self._send(
            f'set|start_on_boot_program("{self._set_boot_prog.text().strip()}")'))
        row = QHBoxLayout()
        row.addWidget(self._set_boot_prog)
        row.addWidget(b)
        form.addRow('Boot Program:', self._wrap(row))
        self._track_buttons.append(b)

        return w

    def _group_reset(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._reset_pin = QSpinBox(); self._reset_pin.setRange(1, 64)
        b = QPushButton('Reset I/O Type')
        b.clicked.connect(lambda: self._send(
            f'reset|io_type_cfg(PIN{self._reset_pin.value()})'))
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
        if clean:
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
        else:
            t = theme.current()
            self._tabs.setStyleSheet(
                f'QTabBar::tab {{ color:{t["btn_disabled_fg"]}; }}'
                f'QTabBar::tab:selected {{ background:{t["tab_bg"]}; '
                f'color:{t["btn_disabled_fg"]}; '
                f'border-top:2px solid {t["border"]}; }}'
            )

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
