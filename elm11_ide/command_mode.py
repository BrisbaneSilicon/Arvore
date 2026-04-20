"""Command Mode side panel.

Gives the user a structured way to issue ELM11 command-mode commands. The panel
enters/exits command mode on the device via `cmd` / `exit`, and captures the
response stream for display.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QLabel, QTabWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from . import theme


_IO_TYPES = [
    'NONE', 'GPIO_OUT', 'GPIO_IN', 'PWM',
    'UART_OUT', 'UART_IN', 'SPI_OUT', 'SPI_IN', 'I2C',
]
_BAUD_RATES = [
    9600, 19200, 28800, 38400, 57600, 76800,
    115200, 230400, 460800, 576000, 921600,
]


class CommandModePanel(QWidget):
    """Sidebar panel for entering and driving ELM11 command mode."""

    active_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._terminal = None
        self._worker   = None
        self._active   = False
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
        list_tabs.setTabPosition(QTabWidget.TabPosition.South)
        list_tabs.setUsesScrollButtons(True)

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
            ('User Comms Config',     'list|user_comms_cfg'),
            ('Clock Frequency',       'list|clk_freq'),
            ('Program Count',         'list|program_count'),
            ('Programs',              'list|programs'),
            ('Boot Prompt Format',    'list|start_on_boot_prompt_format'),
            ('Boot Program',          'list|start_on_boot_program'),
            ('REPL History',          'list|repl_history'),
            ('CMD History',           'list|cmd_history'),
        ]
        for label, cmd in no_arg:
            list_tabs.addTab(self._make_list_page(cmd), label)

        # Program code / bytecode — parametrised, so no auto-send
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
        return list_tabs

    def _make_list_page(self, command: str) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.addStretch(1)
        lbl = QLabel(f'Opening this tab sends:\n\n{command}')
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        v.addWidget(lbl)
        v.addStretch(1)
        # Store the command on the widget so the tab-change handler can read it
        page.setProperty('list_command', command)
        return page

    def _on_list_tab_changed(self, index: int):
        if index < 0:
            return
        page = self._list_tabs.widget(index)
        cmd = page.property('list_command') if page else None
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
        # Stop any running program first. The ELM11 needs a brief moment to
        # process the user-interrupt before it's ready to accept `cmd`.
        self._worker.send(b'q\n')
        QTimer.singleShot(300, self._send_cmd_enter)
        self._active = True
        self._set_controls_enabled(True)
        self.active_changed.emit(True)

    def _send_cmd_enter(self):
        if self._active and self._worker:
            self._worker.send(b'cmd\n')

    def _deactivate(self, send_exit: bool):
        if self._worker and send_exit:
            self._worker.send(b'exit\n')
        was_active = self._active
        self._active = False
        self._set_controls_enabled(False)
        if was_active:
            self.active_changed.emit(False)

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
