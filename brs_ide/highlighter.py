"""Syntax highlighters for Lua (+ ELM11 API) and C."""
import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextBlockUserData
from PyQt6.QtCore import QRegularExpression


class SkipHighlight(QTextBlockUserData):
    """Marker: blocks carrying this user data are not syntax-highlighted."""
    pass

from . import theme


def _colors() -> dict:
    """Map short names to current theme's syntax colours."""
    t = theme.current()
    return {
        'keyword':     t['syn_keyword'],
        'elm11_func':  t['syn_elm11_func'],
        'elm11_const': t['syn_elm11_const'],
        'string':      t['syn_string'],
        'comment':     t['syn_comment'],
        'number':      t['syn_number'],
        'builtin':     t['syn_builtin'],
        'preproc':     t['syn_preproc'],
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

# SystemVerilog (IEEE 1800) — control/structural keywords.
SV_KEYWORDS = [
    'module', 'endmodule', 'program', 'endprogram', 'package', 'endpackage',
    'interface', 'endinterface', 'modport', 'primitive', 'endprimitive',
    'function', 'endfunction', 'task', 'endtask', 'class', 'endclass',
    'extends', 'implements', 'virtual', 'pure', 'extern', 'forkjoin',
    'generate', 'endgenerate', 'genvar', 'parameter', 'localparam',
    'defparam', 'specparam', 'begin', 'end', 'fork', 'join', 'join_any',
    'join_none', 'if', 'else', 'case', 'casex', 'casez', 'endcase',
    'randcase', 'default', 'for', 'foreach', 'while', 'do', 'repeat',
    'forever', 'break', 'continue', 'return', 'assign', 'deassign', 'force',
    'release', 'always', 'always_comb', 'always_ff', 'always_latch',
    'initial', 'final', 'wait', 'wait_order', 'disable', 'posedge',
    'negedge', 'edge', 'iff', 'input', 'output', 'inout', 'ref', 'const',
    'static', 'automatic', 'typedef', 'struct', 'union', 'enum', 'packed',
    'tagged', 'import', 'export', 'context', 'unique', 'unique0', 'priority',
    'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'buf', 'signed',
    'unsigned', 'assert', 'assume', 'cover', 'expect', 'property',
    'endproperty', 'sequence', 'endsequence', 'clocking', 'endclocking',
    'covergroup', 'endgroup', 'constraint', 'rand', 'randc', 'solve',
    'before', 'with', 'inside', 'dist', 'throughout', 'within',
    'first_match', 'bind', 'new', 'null', 'this', 'super',
]

# SystemVerilog data types — highlighted distinctly from control keywords.
SV_TYPES = [
    'logic', 'reg', 'wire', 'bit', 'byte', 'shortint', 'int', 'longint',
    'integer', 'time', 'real', 'shortreal', 'realtime', 'string', 'chandle',
    'event', 'void', 'tri', 'triand', 'trior', 'tri0', 'tri1', 'trireg',
    'wand', 'wor', 'uwire', 'supply0', 'supply1', 'genvar',
    'semaphore', 'mailbox', 'process',
]

# VHDL (IEEE 1076) — keywords (the language is case-insensitive).
VHDL_KEYWORDS = [
    'abs', 'access', 'after', 'alias', 'all', 'and', 'architecture',
    'array', 'assert', 'attribute', 'begin', 'block', 'body', 'buffer',
    'bus', 'case', 'component', 'configuration', 'constant', 'disconnect',
    'downto', 'else', 'elsif', 'end', 'entity', 'exit', 'file', 'for',
    'function', 'generate', 'generic', 'group', 'guarded', 'if', 'impure',
    'in', 'inertial', 'inout', 'is', 'label', 'library', 'linkage',
    'literal', 'loop', 'map', 'mod', 'nand', 'new', 'next', 'nor', 'not',
    'null', 'of', 'on', 'open', 'or', 'others', 'out', 'package', 'port',
    'postponed', 'procedure', 'process', 'pure', 'range', 'record',
    'register', 'reject', 'rem', 'report', 'return', 'rol', 'ror', 'select',
    'severity', 'signal', 'shared', 'sla', 'sll', 'sra', 'srl', 'subtype',
    'then', 'to', 'transport', 'type', 'unaffected', 'units', 'until',
    'use', 'variable', 'wait', 'when', 'while', 'with', 'xnor', 'xor',
]

# VHDL standard types and common functions.
VHDL_TYPES = [
    'std_logic', 'std_logic_vector', 'std_ulogic', 'std_ulogic_vector',
    'signed', 'unsigned', 'integer', 'natural', 'positive', 'boolean',
    'bit', 'bit_vector', 'character', 'string', 'real', 'time', 'severity_level',
    'rising_edge', 'falling_edge', 'resize', 'to_integer', 'to_signed',
    'to_unsigned', 'to_stdlogicvector', 'conv_integer', 'conv_std_logic_vector',
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


def _word_rule(word: str, fmt: QTextCharFormat, ci: bool = False):
    rx = QRegularExpression(rf'\b{re.escape(word)}\b')
    if ci:
        rx.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
    return (rx, fmt)


# ── Lua highlighter ───────────────────────────────────────────────────────────
class LuaHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        kw_fmt     = _fmt(_colors()['keyword'],     bold=True)
        fn_fmt     = _fmt(_colors()['elm11_func'])
        const_fmt  = _fmt(_colors()['elm11_const'], bold=True)
        bi_fmt     = _fmt(_colors()['builtin'])
        num_fmt    = _fmt(_colors()['number'])
        str_fmt    = _fmt(_colors()['string'])
        cmt_fmt    = _fmt(_colors()['comment'],     italic=True)

        # Generic function-call highlight: any identifier immediately before
        # '(' is coloured like a builtin (e.g. print). Added first so the
        # keyword / ELM11 / builtin rules below override it for known tokens
        # (so `if(` stays a keyword, `set_gpio(` stays an ELM11 function),
        # while strings/comments (added last) still win over it.
        self._rules.append(
            (QRegularExpression(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()'), bi_fmt))

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
        if isinstance(self.currentBlock().userData(), SkipHighlight):
            return

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
    # NOTE: shares the multi-line-comment walk pattern with the SV/VHDL
    # highlighters (see _BlockCommentMixin below), kept inline here.
    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        kw_fmt  = _fmt(_colors()['keyword'],  bold=True)
        pp_fmt  = _fmt(_colors()['preproc'])
        num_fmt = _fmt(_colors()['number'])
        str_fmt = _fmt(_colors()['string'])
        cmt_fmt = _fmt(_colors()['comment'],  italic=True)

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


class _BlockCommentMixin:
    """Shared `highlightBlock` for C-style languages: applies `self._rules`
    then handles multi-line `self._ml_start` … `self._ml_end` comments."""

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

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


# ── SystemVerilog highlighter ───────────────────────────────────────────────────
class SystemVerilogHighlighter(_BlockCommentMixin, QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        c = _colors()
        kw_fmt   = _fmt(c['keyword'],     bold=True)
        type_fmt = _fmt(c['elm11_const'], bold=True)
        bi_fmt   = _fmt(c['builtin'])
        pp_fmt   = _fmt(c['preproc'])
        num_fmt  = _fmt(c['number'])
        str_fmt  = _fmt(c['string'])
        cmt_fmt  = _fmt(c['comment'],     italic=True)

        for kw in SV_KEYWORDS:
            self._rules.append(_word_rule(kw, kw_fmt))
        for ty in SV_TYPES:
            self._rules.append(_word_rule(ty, type_fmt))

        self._rules += [
            # Compiler directives: `define, `include, `timescale, `ifdef …
            (QRegularExpression(r'`[A-Za-z_]\w*'),                     pp_fmt),
            # System tasks / functions: $display, $clog2, $finish …
            (QRegularExpression(r'\$[A-Za-z_]\w*'),                    bi_fmt),
            # Sized literals: 8'hFF, 4'b1010, 32'sd10, 'hABC …
            (QRegularExpression(r"\b\d*'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_]+"), num_fmt),
            (QRegularExpression(r'\b0x[0-9a-fA-F]+\b'),                num_fmt),
            (QRegularExpression(r'\b\d[\d_]*\.?\d*([eE][+-]?\d+)?\b'), num_fmt),
            (QRegularExpression(r'"([^"\\]|\\.)*"'),                   str_fmt),
            (QRegularExpression(r'//[^\n]*'),                          cmt_fmt),
        ]

        self._ml_fmt   = cmt_fmt
        self._ml_start = QRegularExpression(r'/\*')
        self._ml_end   = QRegularExpression(r'\*/')


# ── VHDL highlighter ────────────────────────────────────────────────────────────
class VHDLHighlighter(_BlockCommentMixin, QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        c = _colors()
        kw_fmt   = _fmt(c['keyword'],     bold=True)
        type_fmt = _fmt(c['elm11_const'], bold=True)
        num_fmt  = _fmt(c['number'])
        str_fmt  = _fmt(c['string'])
        cmt_fmt  = _fmt(c['comment'],     italic=True)

        # VHDL is case-insensitive, so match keywords/types either case.
        for kw in VHDL_KEYWORDS:
            self._rules.append(_word_rule(kw, kw_fmt, ci=True))
        for ty in VHDL_TYPES:
            self._rules.append(_word_rule(ty, type_fmt, ci=True))

        self._rules += [
            # Based / sized literals: 16#FF#, 2#1010#, and plain numbers.
            (QRegularExpression(r'\b\d+#[0-9a-fA-F_]+#'),              num_fmt),
            (QRegularExpression(r'\b\d[\d_]*\.?\d*([eE][+-]?\d+)?\b'), num_fmt),
            # String / vector literals "1010", bit/char literals '0' 'Z' 'a'.
            (QRegularExpression(r'"[^"\n]*"'),                         str_fmt),
            (QRegularExpression(r"'[^'\n]'"),                          str_fmt),
            # Line comments: -- to EOL.
            (QRegularExpression(r'--[^\n]*'),                          cmt_fmt),
        ]

        # VHDL-2008 also allows /* … */ block comments.
        self._ml_fmt   = cmt_fmt
        self._ml_start = QRegularExpression(r'/\*')
        self._ml_end   = QRegularExpression(r'\*/')


MAKE_DIRECTIVES = [
    'include', '-include', 'sinclude',
    'ifeq', 'ifneq', 'ifdef', 'ifndef', 'else', 'endif',
    'define', 'endef', 'override', 'export', 'unexport',
    'vpath', 'undefine',
]
MAKE_BUILTINS = [
    'patsubst', 'subst', 'strip', 'findstring', 'filter', 'filter-out',
    'sort', 'word', 'wordlist', 'words', 'firstword', 'lastword',
    'dir', 'notdir', 'suffix', 'basename', 'addsuffix', 'addprefix',
    'join', 'wildcard', 'realpath', 'abspath',
    'if', 'or', 'and', 'foreach', 'call', 'value', 'eval', 'origin',
    'flavor', 'shell', 'error', 'warning', 'info',
]


class MakefileHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for GNU Makefiles."""

    def __init__(self, document):
        super().__init__(document)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        c = _colors()
        kw_fmt      = _fmt(c['keyword'],     bold=True)
        builtin_fmt = _fmt(c['builtin'])
        str_fmt     = _fmt(c['string'])
        num_fmt     = _fmt(c['number'])
        cmt_fmt     = _fmt(c['comment'],     italic=True)
        pp_fmt      = _fmt(c['preproc'])
        target_fmt  = _fmt(c['elm11_func'],  bold=True)
        var_fmt     = _fmt(c['elm11_const'])

        # Directives
        for d in MAKE_DIRECTIVES:
            self._rules.append((
                QRegularExpression(rf'^\s*{re.escape(d)}\b'), kw_fmt))

        # Built-in function calls: $(wildcard ...), $(patsubst ...)
        for fn in MAKE_BUILTINS:
            self._rules.append((
                QRegularExpression(rf'\$\(\s*{re.escape(fn)}\b'), builtin_fmt))

        # Target definitions: name[ name2]: deps
        self._rules.append((
            QRegularExpression(r'^[A-Za-z0-9_./%\-${}()]+\s*::?\s*'), target_fmt))

        # Assignments: VAR := value / VAR = value / VAR += / VAR ?=
        self._rules.append((
            QRegularExpression(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*(\?=|:=|\+=|=)'),
            pp_fmt))

        # $(VAR), ${VAR}, $@, $<, $^, $*, $?, $%, $+, $|
        self._rules.append((
            QRegularExpression(r'\$[@<^*?%+|]'), var_fmt))
        self._rules.append((
            QRegularExpression(r'\$[({][A-Za-z_][A-Za-z0-9_]*[)}]'), var_fmt))

        # Strings and numbers
        self._rules.append((QRegularExpression(r'"([^"\\]|\\.)*"'), str_fmt))
        self._rules.append((QRegularExpression(r"'([^'\\]|\\.)*'"), str_fmt))
        self._rules.append((QRegularExpression(r'\b\d+\b'),         num_fmt))

        # Line comments: # ... to EOL
        self._rules.append((QRegularExpression(r'(^|[^\\])#[^\n]*'), cmt_fmt))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
