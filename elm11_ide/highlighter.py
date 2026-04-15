"""Syntax highlighters for Lua (+ ELM11 API) and C."""
import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import QRegularExpression

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    'keyword':     '#569cd6',   # blue
    'elm11_func':  '#dcdcaa',   # yellow
    'elm11_const': '#4ec9b0',   # teal
    'string':      '#ce9178',   # orange
    'comment':     '#6a9955',   # green
    'number':      '#b5cea8',   # light green
    'builtin':     '#c586c0',   # purple
    'preproc':     '#c586c0',   # purple (C preprocessor)
}

# ── Token lists ───────────────────────────────────────────────────────────────
LUA_KEYWORDS = [
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
    'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or',
    'repeat', 'return', 'then', 'true', 'until', 'while',
]

LUA_BUILTINS = [
    'print', 'pairs', 'ipairs', 'type', 'tostring', 'tonumber',
    'error', 'assert', 'pcall', 'xpcall', 'select', 'unpack',
    'rawget', 'rawset', 'rawequal', 'rawlen', 'setmetatable',
    'getmetatable', 'next', 'load', 'loadfile', 'dofile', 'require',
    'collectgarbage', 'string', 'table', 'math', 'io',
]

ELM11_CONSTANTS = [
    *[f'PIN{i}'          for i in range(1, 17)],
    *[f'PIN{i}_BITMASK'  for i in range(1, 17)],
    *[f'CORE{i}'         for i in range(1, 9)],
    'LOW', 'HIGH', 'TOGGLE',
    'NONE', 'GPIO_OUT', 'GPIO_IN', 'PWM',
    'UART_OUT', 'UART_IN', 'SPI_OUT', 'SPI_IN', 'I2C',
    'GPIO_INTRPT_LOW', 'GPIO_INTRPT_HIGH',
    'GPIO_INTRPT_RISING_EDGE', 'GPIO_INTRPT_FALLING_EDGE',
    'UART_RX_INTRPT_DATA_AVAILABLE',
    'PWM_MAX', '_VERSION', '_sW', '_fW', '_hW', '_cl',
]

ELM11_FUNCTIONS = [
    'import',
    'set_io_type_cfg', 'reset_io_type_cfg', 'reset_all_io_type_cfg',
    'set_gpio', 'get_gpio',
    'set_pwm',
    'spi_tx', 'spi_tx_byte', 'spi_tx_char', 'spi_tx_int',
    'spi_rx_byte', 'spi_rx_char',
    'spi_rx_byte_nonblocking', 'spi_rx_char_nonblocking',
    'uart_tx', 'uart_tx_char', 'uart_tx_byte', 'uart_tx_int',
    'uart_rx_byte', 'uart_rx_char',
    'uart_rx_byte_nonblocking', 'uart_rx_char_nonblocking',
    'i2c_tx', 'i2c_tx_char', 'i2c_tx_byte', 'i2c_tx_int',
    'i2c_rx_byte', 'i2c_rx_char',
    'i2c_rx_byte_nonblocking', 'i2c_rx_char_nonblocking',
    'fpga_write', 'fpga_write_nonblocking',
    'fpga_read',  'fpga_read_nonblocking',
    'global_interrupt_enable', 'global_interrupt_disable',
    'repl_interrupt_mode_enable', 'repl_interrupt_mode_disable',
    'set_interrupt_types_for_pin', 'enable_interrupt_types_for_pin',
    'disable_interrupt_types_for_pin', 'get_interrupts_on_pin',
    'ack_interrupt_types_on_pin', 'ack_interrupt_types_on_pins',
    'interrupt_handler',
    'sleep', 'sleep_f', 'msleep', 'msleep_f', 'usleep',
    'sleep_noint', 'mssleep_noint', 'usleep_noint',
    'watchdog_reset', 'get_watchdog_timer',
    'pipe_tx_byte', 'pipe_tx_byte_nonblocking',
    'pipe_rx_byte', 'pipe_rx_byte_nonblocking',
    'lock', 'lock_nonblocking', 'unlock', 'unlock_nonblocking',
    'run_program',
    'reboot', 'exit',
]

C_KEYWORDS = [
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default',
    'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto',
    'if', 'inline', 'int', 'long', 'register', 'restrict', 'return',
    'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef',
    'union', 'unsigned', 'void', 'volatile', 'while',
    '_Alignas', '_Alignof', '_Atomic', '_Bool', '_Complex',
    '_Generic', '_Imaginary', '_Noreturn', '_Static_assert', '_Thread_local',
    'NULL', 'true', 'false',
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


def _word_rule(word: str, fmt: QTextCharFormat):
    return (QRegularExpression(rf'\b{re.escape(word)}\b'), fmt)


# ── Lua highlighter ───────────────────────────────────────────────────────────
class LuaHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        kw_fmt     = _fmt(C['keyword'],     bold=True)
        fn_fmt     = _fmt(C['elm11_func'])
        const_fmt  = _fmt(C['elm11_const'], bold=True)
        bi_fmt     = _fmt(C['builtin'])
        num_fmt    = _fmt(C['number'])
        str_fmt    = _fmt(C['string'])
        cmt_fmt    = _fmt(C['comment'],     italic=True)

        for kw in LUA_KEYWORDS:
            self._rules.append(_word_rule(kw, kw_fmt))
        for fn in ELM11_FUNCTIONS:
            self._rules.append(_word_rule(fn, fn_fmt))
        for ct in ELM11_CONSTANTS:
            self._rules.append(_word_rule(ct, const_fmt))
        for bi in LUA_BUILTINS:
            self._rules.append(_word_rule(bi, bi_fmt))

        self._rules += [
            (QRegularExpression(r'\b0x[0-9a-fA-F]+\b'),              num_fmt),
            (QRegularExpression(r'\b\d+\.?\d*([eE][+-]?\d+)?\b'),    num_fmt),
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),           str_fmt),
            (QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),           str_fmt),
            (QRegularExpression(r'--(?!\[\[)[^\n]*'),                 cmt_fmt),
        ]

        self._ml_fmt   = cmt_fmt
        self._ml_start = QRegularExpression(r'--\[\[')
        self._ml_end   = QRegularExpression(r'\]\]')

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multi-line --[[ ... ]] comments
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            m = self._ml_start.match(text)
            start = m.capturedStart() if m.hasMatch() else -1

        while start >= 0:
            m_end = self._ml_end.match(text, start)
            if m_end.hasMatch():
                length = m_end.capturedEnd() - start
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
                length = len(text) - start
            self.setFormat(start, length, self._ml_fmt)
            if self.currentBlockState() == 1:
                break
            m = self._ml_start.match(text, start + length)
            start = m.capturedStart() if m.hasMatch() else -1


# ── C highlighter ─────────────────────────────────────────────────────────────
class CHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        kw_fmt  = _fmt(C['keyword'],  bold=True)
        pp_fmt  = _fmt(C['preproc'])
        num_fmt = _fmt(C['number'])
        str_fmt = _fmt(C['string'])
        cmt_fmt = _fmt(C['comment'],  italic=True)

        # Preprocessor (#include, #define …)
        self._rules.append((QRegularExpression(r'^\s*#\s*\w+'), pp_fmt))

        for kw in C_KEYWORDS:
            self._rules.append(_word_rule(kw, kw_fmt))

        self._rules += [
            (QRegularExpression(r'\b0x[0-9a-fA-F]+[uUlL]*\b'),          num_fmt),
            (QRegularExpression(r'\b\d+\.?\d*([eE][+-]?\d+)?[fFlL]?\b'), num_fmt),
            (QRegularExpression(r'"([^"\\]|\\.)*"'),                      str_fmt),
            (QRegularExpression(r"'([^'\\]|\\.)*'"),                      str_fmt),
            (QRegularExpression(r'//[^\n]*'),                             cmt_fmt),
        ]

        self._ml_fmt   = cmt_fmt
        self._ml_start = QRegularExpression(r'/\*')
        self._ml_end   = QRegularExpression(r'\*/')

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multi-line /* ... */ comments
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            m = self._ml_start.match(text)
            start = m.capturedStart() if m.hasMatch() else -1

        while start >= 0:
            m_end = self._ml_end.match(text, start)
            if m_end.hasMatch():
                length = m_end.capturedEnd() - start
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
                length = len(text) - start
            self.setFormat(start, length, self._ml_fmt)
            if self.currentBlockState() == 1:
                break
            m = self._ml_start.match(text, start + length)
            start = m.capturedStart() if m.hasMatch() else -1
