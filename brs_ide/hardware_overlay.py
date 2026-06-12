"""Hardware Overlay panel.

A full-centre page (toggled like Command Mode) showing the ELM11 hardware
overlay summary in a large table. The data is downloaded as CSV from the
Brisbane Silicon website and refreshed on demand.
"""
from __future__ import annotations

import csv
import io
import shutil
import sys
import urllib.request
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMenu, QMessageBox,
    QStylePainter, QStyleOptionComboBox, QStyle, QStyledItemDelegate,
    QSplitter, QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import QColor, QPixmap, QPainter, QPen, QFont

from . import theme


# Web root for the published per-board overlay data. Each board's summary CSV
# and per-row `.vg` images live in `<board>_hardware_overlay/`, where <board>
# mirrors the bundled board dir name ('elm11', 'elm11-feather').
_WEB_ROOT = 'https://brisbanesilicon.com.au/software/'


def _overlay_web_base(board: str) -> str:
    """Web directory holding `board`'s summary CSV and `.vg` images."""
    return f'{_WEB_ROOT}{board}_hardware_overlay/'


# Per-row firmware images live beside the summary CSV (locally and on the web),
# named `emblua_<stub>.vg`, where <stub> is the row's raw CSV fields joined by
# '_' with the clock given in Hz (the CSV shows MHz). Installing one copies it
# into the workspace as the stable `emblua.vg` the synth flow expects.
_VG_PREFIX = 'emblua_'


def _ide_base() -> Path:
    """Root of the bundled `brs_ide` data (dev, PyInstaller, install)."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'brs_ide'
    return Path(__file__).resolve().parent


def _bundled_overlay_dir(board: str) -> Path:
    """Bundled overlay dir for `board` (holds summary.csv + cached `.vg`s)."""
    return _ide_base() / board / 'hardware_overlay'


def _bundled_csv(board: str) -> Path:
    """Path to `board`'s CSV shipped with the IDE (dev, PyInstaller, install)."""
    return _bundled_overlay_dir(board) / 'summary.csv'


def _bundled_fw_dir(board: str) -> Path:
    """Bundled firmware dir holding `board`'s per-frequency timing constraints
    (`timing_<n>mhz.sdc`) alongside the HDL sources."""
    return _ide_base() / board / 'lua' / 'build' / 'fw'


# These summary columns aren't scalars — each is an integer bitmask where bit
# `i` indicates whether I/O `i` supports that capability. They're decoded into
# the per-I/O capability matrix rather than shown as a raw number. Headers are
# matched after stripping the common prefix below.
_CAP_PREFIX = 'I/O Module Support '
_CAP_HEADERS = [
    'GPIO Out',
    'GPIO In',
    'PWM',
    'Uart Out',
    'Uart In',
    'SPI Out',
    'SPI In',
    'I/O Buffer',
]

# Columns rendered as a boolean 'true'/'false' (non-zero ⇒ true) rather than
# their raw integer value.
_BOOL_HEADERS = {
    'General Timer',
    'Perf Timer',
    'Watchdog',
    'Software Interrupts',
    'Hardware Bus',
    'I/O',
    'LVM Accel',
}

# Display-only header relabelling, applied before wrapping (see _wrap_header).
# Used to abbreviate names that would otherwise wrap awkwardly.
_HEADER_RENAMES = {
    'General Timer': 'Gen. Timer',
    'Perf Timer': 'Perf. Timer',
    'Hardware Bus': 'HW Bus',
    'Software Interrupts': 'SW Int.',
    'Watchdog': 'Wdog',
    'Watchdog Timeout': 'Wdog T.O',
    'LVM Accel': 'LVM Accel.',
}

# Hover-tooltip text per column, keyed by the original CSV header. Edit any
# value here to change the popup shown when hovering that header. Every column
# is listed (in CSV order); a header not found here falls back to its full
# original name.
_HEADER_TOOLTIPS = {
    'ID':                  'Hardware Overlay ID',
    'Baud':                'User Comms Baud Rate',
    'Clk Mhz':             'Clock (MHz)',
    'General Timer':       'General Timer Enabled',
    'Perf Timer':          'Performance Timer Enabled',
    'Cores':               'CPU Cores',
    'Watchdog':            'Watchdog Enabled',
    'Watchdog Timeout':    'Watchdog Timeout (Milliseconds)',
    'I/O':                 'I/O Enable',
    'I/O Count':           'Number of I/O',
    'SPI Out':             'SPI Out Capable Pins',
    'SPI In':              'SPI In Capable Pins',
    'Uart Out':            'UART Out Capable Pins',
    'Uart In':             'UART In Capable Pins',
    'PWM':                 'PWM Capable Pins',
    'GPIO Out':            'GPIO Out Capable Pins',
    'GPIO In':             'GPIO In Capable Pins',
    'I/O Buffer':          'I/O Buffer Enabled on Pins',
    'Software Interrupts': 'Software Interrupts Enabled',
    'Hardware Bus':        'Hardware Bus Enabled',
    'LVM Accel':           'LVM Acceleration Enabled',
}

# Maximum width (in characters) for any one line of a column heading. Headers
# are wrapped to this so long names don't stretch the table: each word goes on
# its own line, and a word longer than this is split across lines, each split
# ending with a hyphen (which counts toward the width).
_HEADER_WRAP = 6


def _wrap_header(label: str) -> str:
    """Wrap a column heading so no line exceeds `_HEADER_WRAP` characters,
    placing each word on its own line and hyphenating any word too long to fit
    on a single line."""
    lines = []
    for word in label.split():
        while len(word) > _HEADER_WRAP:
            lines.append(word[:_HEADER_WRAP - 1] + '-')
            word = word[_HEADER_WRAP - 1:]
        lines.append(word)
    return '\n'.join(lines)


class _CsvDownloader(QThread):
    """Fetch and parse the summary CSV off the UI thread."""

    rows_ready = pyqtSignal(list)   # list[list[str]]
    failed     = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            req = urllib.request.Request(
                self._url, headers={'User-Agent': 'BRS-IDE'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode('utf-8-sig', errors='replace')
            rows = [r for r in csv.reader(io.StringIO(raw))]
            self.rows_ready.emit(rows)
        except Exception as exc:                       # noqa: BLE001
            self.failed.emit(str(exc))


class _VgDownloader(QThread):
    """Fetch a per-row `.vg` firmware image off the UI thread, write it to the
    workspace destination, and best-effort cache it beside the summary CSV."""

    done   = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, url: str, dest: Path, cache: Path, parent=None):
        super().__init__(parent)
        self._url = url
        self._dest = dest
        self._cache = cache

    def run(self):
        try:
            req = urllib.request.Request(
                self._url, headers={'User-Agent': 'BRS-IDE'})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            self._dest.parent.mkdir(parents=True, exist_ok=True)
            self._dest.write_bytes(data)
            try:                                   # cache for next time
                self._cache.write_bytes(data)
            except OSError:
                pass                               # read-only install — ignore
            self.done.emit()
        except Exception as exc:                   # noqa: BLE001
            self.failed.emit(str(exc))


class _CenterDelegate(QStyledItemDelegate):
    """Centres a combo popup's item text (honoured even under a stylesheet,
    where the plain TextAlignmentRole can be ignored)."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter


class _CenteredComboBox(QComboBox):
    """A combo whose closed-state text is centred (a plain combo left-aligns
    it). Stays non-editable, so a click toggles the popup natively and it
    persists until dismissed — unlike an editable read-only line edit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(_CenterDelegate(self))
        # Returns the width to centre the closed-state text within. Set by the
        # owner to the matching table column's width so the text lines up with
        # the (centred) cell text below it, rather than the combo's own width.
        self._cell_width = None

    def showPopup(self):
        # Clamp the open popup to the cell (column) width. The style sizes the
        # popup to its widest item (often wider than the combo), so we pin both
        # the view and its container frame after it's shown, then re-anchor it
        # under the combo since changing the width can otherwise shift it.
        w = int(self._cell_width() if self._cell_width else self.width())
        view = self.view()
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        super().showPopup()
        container = view.parentWidget()
        if container is not None:
            container.setFixedWidth(w)
        view.setFixedWidth(w)
        if container is not None:
            container.move(self.mapToGlobal(self.rect().bottomLeft()))

    def paintEvent(self, _event):
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        text = opt.currentText
        # Draw the frame + arrow without the label (blank it so the style
        # doesn't paint its own left-aligned text)…
        opt.currentText = ''
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        # …then draw the label so its horizontal midpoint sits half the *cell*
        # width from the left edge — the cell text below is centred on that same
        # point, so the two line up. We place the text ourselves rather than
        # relying on AlignCenter across a rect whose edges (and any arrow inset)
        # the stylesheet may shift — that's what kept reading as off-centre.
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text)
        cell_w = self._cell_width() if self._cell_width else self.width()
        cx = cell_w / 2.0
        text_rect = self.rect()
        text_rect.setLeft(int(cx - tw / 2.0))
        painter.setPen(QColor(theme.current()['dlg_input_fg']))
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            text)


# Minimum width (in pixels) of the diagram side-panel on the Hardware Overlay
# page. Tweak this to change how much room the diagram is guaranteed when shown.
_DIAGRAM_MIN_WIDTH = 320

# ── Diagram (lower pane) configuration ──────────────────────────────────────
# Board image shown behind the pin labels, looked up inside each board's
# `hardware_overlay/` dir. Use a PNG with a transparent background so the
# surround follows the theme background.
_BOARD_IMAGE = 'board.png'

# Per-pin anchor points on the board photo, keyed by board dir name then by
# 1-based pin number: (x_fraction, y_fraction, side). The fractions are of the
# *displayed image* (0..1 across width/height), so the labels track the photo
# as the pane resizes. `side` ('left'/'right') is the direction that pin's
# capability labels stretch out from the board.
#
# These are PLACEHOLDERS — nudge each (x, y) until its label row lines up with
# the matching pin. Set _OverlayDiagram._DEBUG_CLICK = True to print the
# fraction under the cursor on click, which makes tuning quick.
_PIN_MAPS = {
    'elm11-feather': {
        # Left edge, top → bottom (labels stretch left).
        1:  (0.000, 0.133, 'left'),
        2:  (0.000, 0.205, 'left'),
        3:  (0.000, 0.280, 'left'),
        4:  (0.000, 0.316, 'left'),
        5:  (0.000, 0.353, 'left'),
        6:  (0.000, 0.389, 'left'),
        7:  (0.000, 0.427, 'left'),
        8:  (0.000, 0.465, 'left'),
        9:  (0.000, 0.502, 'left'),
        10: (0.000, 0.539, 'left'),
        11: (0.000, 0.574, 'left'),
        12: (0.000, 0.614, 'left'),
        13: (0.000, 0.652, 'left'),
        14: (0.000, 0.687, 'left'),

        # Right edge, top → bottom (labels stretch right).
        15: (1.000, 0.392, 'right'),
        16: (1.000, 0.428, 'right'),
        17: (1.000, 0.466, 'right'),
        18: (1.000, 0.504, 'right'),
        19: (1.000, 0.541, 'right'),
        20: (1.000, 0.578, 'right'),
        21: (1.000, 0.615, 'right'),
        22: (1.000, 0.652, 'right'),
        23: (1.000, 0.689, 'right'),
    },
}



# Per-pin capability columns to surface as labels, in the left→right order they
# appear next to a pin. Each maps to its on-pill display text and colour. Edit
# the text/colours freely; drop an entry to stop showing that capability.
_CAP_LABELS = {
    'GPIO Out':   'GPIO O',
    'GPIO In':    'GPIO I',
    'PWM':        'PWM',
    'Uart Out':   'UART O',
    'Uart In':    'UART I',
    'SPI Out':    'SPI O',
    'SPI In':     'SPI I',
    'I/O Buffer': 'Buffer',
}
_CAP_COLORS = {
    'GPIO Out':   '#3b82f6',
    'GPIO In':    '#2563eb',
    'PWM':        '#a855f7',
    'Uart Out':   '#10b981',
    'Uart In':    '#059669',
    'SPI Out':    '#f59e0b',
    'SPI In':     '#d97706',
    'I/O Buffer': '#6b7280',
}

# Fixed width (in pixels) of every capability label, so they line up in even
# columns regardless of their text length.
_CAP_PILL_WIDTH = 60

# When 'Hardware Bus' is enabled, the pins past 'I/O Count' (up to the last pin
# in _PIN_MAPS) are consumed by the hardware bus rather than being configurable
# I/O — they're labelled with this instead of capability pills.
# Points to shave off the base font for the diagram's pin/feature/flag pills
# (their heights follow the font, so this also tightens them up).
_PILL_FONT_REDUCE = 1.5

_HW_BUS_LABEL = 'Hardware Bus'
_HW_BUS_COLOR = '#0d9488'
# Bracket/connector line colour joining the bus pins to their shared label.
_HW_BUS_LINE_COLOR = '#64748b'
# Gap (px) from the pin tags out to the hardware-bus bracket spine.
_HW_BUS_BRACKET_GAP = 18

# Innermost label identifying each I/O pin, drawn closest to the board for every
# pin (even ones with no capabilities) so it's obvious which pin is which. The
# capability pills extend outward beyond it. _PIN_LABELS optionally overrides
# the text per board/pin; anything unlisted just shows the pin number.
_PIN_LABEL_COLOR = '#334155'
# Fixed width (in pixels) of the pin-number label — independent of the
# capability pill width, since it only holds a short number.
_PIN_LABEL_WIDTH = 32
_PIN_LABELS = {
    # 'elm11-feather': {1: 'D0', 2: 'D1', ...},
}

# Fixed-function pins that aren't part of the configurable I/O (power, reset,
# etc.). These are constant for the board, so they're drawn for every overlay
# regardless of the selected row. Keyed by board dir name; each entry is
# (x_fraction, y_fraction, side, label) — same coordinate scheme as _PIN_MAPS.
# Placeholders — nudge the positions/labels to match the board.
_FIXED_PINS = {
    'elm11-feather': [
        (0.00, 0.168, 'left',  '3V3'),
        (0.00, 0.242, 'left',  'GND'),
        (1.00, 0.280, 'right', 'VBAT'),
        (1.00, 0.315, 'right', 'NC'),
        (1.00, 0.353, 'right', '5V'),
    ],
}
# Default pill colour for fixed-function pins (so they read distinctly from the
# capability pills). Per-label overrides below take precedence.
_FIXED_PILL_COLOR = '#475569'

# Per-label pill colour for fixed-function pins, keyed by the pin label. Labels
# not listed here use _FIXED_PILL_COLOR.
_FIXED_PILL_COLORS = {
    '3V3':  '#dc2626',   # red   — supply rails
    '5V':   '#dc2626',   # red
    'VBAT': '#f87171',   # light red — battery
    'GND':  '#000000',   # black — ground
}

# Feature callouts: a board-feature label drawn with a leader line pointing to a
# spot on the photo (e.g. the UART baud at the USB-C connector). Unlike the pin
# labels, these aren't per-pin — each shows a single overlay property. Keyed by
# board dir name; each entry is a dict:
#   field  — CSV header whose value fills the label (omit for a static label)
#   text   — label template; '{}' is replaced with the field value
#   point  — (x, y) fraction on the photo the leader line points to
#   offset — (dx, dy) pixels from `point` to the label centre
#   color  — pill colour
# Placeholders — nudge `point`/`offset` to sit the label by the right feature.
_FEATURE_CALLOUTS = {
    'elm11-feather': [
        {
            'field': 'Baud',
            'text': '{}',
            'point': (0.50, 0.00),     # USB-C connector, top-centre of board
            'offset': (0, -26),        # label sits just above it
            'color': '#d1d5db',
        },
        {
            'field': 'Clk Mhz',
            'text': '{} MHz',
            'point': (0.30, 0.795),     # FPGA IC, towards the bottom-left
            'offset': (-130, 0),       # label sits well out to the left of it
            'color': '#d1d5db',
        },
    ],
}

def _to_int(value) -> int:
    """Best-effort int from a raw CSV cell (0 if blank/unparseable)."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _fmt_hms_ms(ms: int) -> str:
    """Break a millisecond duration into 'H: h  M: m  S: s  MS: ms'."""
    h, rem = divmod(int(ms), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f'H: {h}  M: {m}  S: {s}  MS: {ms}'


# Board-level capability flags (not tied to a pin or physical spot) listed on
# the diagram when enabled (their field is non-zero). Each is (CSV header,
# display label), with an optional 3rd element: a callable taking the fields
# dict and returning extra detail appended in parentheses. Drawn top→bottom.
_FLAG_CAPS = [
    ('General Timer',       'General Timer'),
    ('Perf Timer',          'Performance Timer'),
    ('Watchdog',            'Watchdog',
        lambda f: _fmt_hms_ms(_to_int(f.get('Watchdog Timeout')))),
    ('Software Interrupts', 'Software Interrupts'),
    ('LVM Accel',           'LVM Acceleration'),
]
# The enabled-flags list hangs off a single vertical spine connected by a leader
# line to a point on the board (the FPGA IC). Per board:
#   point  — (x, y) fraction on the photo the leader connects to (the FPGA)
#   offset — (dx, dy) pixels from `point` to the top of the spine
#   color  — pill colour
# Each enabled flag's pill hangs off the spine; the stack grows downward.
_FLAG_LIST = {
    'elm11-feather': {
        'point': (0.66, 0.795),     # FPGA IC, same as the freq callout
        'offset': (100, 0),      # spine sits out to the right, slightly up
        'color': '#d1d5db',
    },
}


class _OverlayDiagram(QWidget):
    """Lower section of the Hardware Overlay page: a board photo annotated with
    the I/O capabilities of the overlay row selected in the table above.

    `show_overlay()` is the single hook the panel calls on every selection
    change, with the row's ID and its header→value map. The per-pin label
    positions live in `_PIN_MAPS` (placeholders, meant to be nudged)."""

    _PROMPT = 'Select a Hardware Overlay to view its Diagram.'

    # Flip to True while lining up _PIN_MAPS: overlays a numbered red marker at
    # every pin anchor and prints the fractional (x, y) under the cursor on each
    # click. Set back to False once the anchors line up with the photo's pins.
    _DEBUG_CLICK = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._board = ''
        self._pixmap: QPixmap | None = None
        self._pins: dict = {}
        self._fixed: list = []
        self._features: list = []
        self._flags_cfg: dict | None = None
        self._overlay_id = ''
        self._fields: dict = {}
        self._caption = ''
        # Horizontal content bounds tracked while painting, so the widget can
        # size itself (and its scroll area) to however far the labels extend.
        self._xmin = self._xmax = 0.0

    def set_board(self, board: str):
        """Load `board`'s photo and pin map (called when the panel's board
        changes). Unknown boards just show the 'no diagram' message."""
        self._board = board
        self._pins = _PIN_MAPS.get(board, {})
        self._fixed = _FIXED_PINS.get(board, [])
        self._features = _FEATURE_CALLOUTS.get(board, [])
        self._flags_cfg = _FLAG_LIST.get(board)
        pm = QPixmap(str(_bundled_overlay_dir(board) / _BOARD_IMAGE))
        self._pixmap = pm if not pm.isNull() else None
        self.update()

    def show_overlay(self, overlay_id: str, fields: dict, caption: str = ''):
        """Annotate the board for an overlay. `overlay_id` is the overlay's ID
        (empty ⇒ show the prompt instead); `fields` maps each CSV header to its
        raw value; `caption` is optional header text (e.g. to mark the row as
        the currently-installed overlay)."""
        self._overlay_id = overlay_id
        self._fields = dict(fields)
        self._caption = caption
        self.update()

    # ── Painting ────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        t = theme.current()
        painter.fillRect(self.rect(), QColor(t['window_bg']))
        # Nothing selected: just the prompt, centred — no board image.
        if not self._overlay_id:
            self._draw_message(painter, self._PROMPT)
            self._fit_width(None)
            return
        if self._pixmap is None:
            self._draw_message(painter, 'No board diagram available.')
            self._fit_width(None)
            return
        img = self._image_rect()
        self._xmin, self._xmax = img.left(), img.right()
        painter.drawPixmap(
            img, self._pixmap, QRectF(self._pixmap.rect()))
        if self._DEBUG_CLICK:
            self._draw_pin_markers(painter, img)
        # Slightly smaller font for the labels (and so their pills); the caption
        # keeps the base size.
        base = painter.font()
        small = QFont(base)
        if base.pointSizeF() > 0:
            small.setPointSizeF(max(6.0, base.pointSizeF() - _PILL_FONT_REDUCE))
        painter.setFont(small)
        # Fixed-function pins are constant for the board — always shown.
        self._draw_fixed_pins(painter, img)
        self._draw_pins(painter, img)
        self._draw_features(painter, img)
        self._draw_flags(painter, img)
        if self._caption:
            painter.setFont(base)
            self._draw_caption(painter)
        self._fit_width(img)

    def _grow(self, *xs):
        """Extend the tracked horizontal content bounds to include `xs`."""
        self._xmin = min(self._xmin, *xs)
        self._xmax = max(self._xmax, *xs)

    def _fit_width(self, img):
        """Size the widget to its content so the scroll area can scroll to any
        labels that overflow the board. Width is symmetric about the centred
        board (so neither side clips); a deferred set avoids re-entrant paints."""
        if img is None:
            needed = 0
        else:
            margin = 16
            ext = max(img.left() - self._xmin, self._xmax - img.right(), 0)
            needed = int(self._pixmap.width() + 2 * ext + 2 * margin)
        if needed != self.minimumWidth():
            QTimer.singleShot(0, lambda n=needed: self.setMinimumWidth(n))

    def _draw_caption(self, painter: QPainter):
        """Header text at the top-centre of the pane (e.g. the installed-overlay
        marker)."""
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(theme.current()['window_fg']))
        painter.drawText(
            self.rect().adjusted(8, 6, -8, 0),
            int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
            self._caption)

    def _image_rect(self) -> QRectF:
        """Photo rect: drawn at the image's native pixel size (no scaling) and
        centred, so the side gutters hold the outward-stretching labels."""
        w, h = self._pixmap.width(), self._pixmap.height()
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def _draw_pins(self, painter: QPainter, img: QRectF):
        """Per-pin labels for the selected overlay row: an innermost pin-number
        tag (every pin), then a pill per supported capability. Pins past
        'I/O Count' are the hardware bus when it's enabled, else skipped — and
        those bus pins share one joined label per side (see _draw_hardware_bus)."""
        n_io = self._int(self._fields.get('I/O Count'))
        hw_bus = self._int(self._fields.get('Hardware Bus')) != 0
        bus_pins = []                       # (pin, anchor, side) past I/O Count
        for pin, (xf, yf, side) in self._pins.items():
            anchor = QPointF(img.left() + xf * img.width(),
                             img.top() + yf * img.height())
            if n_io and pin > n_io:
                if hw_bus:
                    bus_pins.append((pin, anchor, side))
                continue                    # else: unused pin — nothing to show
            # Reserve one fixed-width slot per capability (in _CAP_LABELS order)
            # so each category always lands in the same column — an absent one
            # leaves an empty (None-colour) spacer rather than shifting the rest.
            pills = [(self._pin_label(pin), _PIN_LABEL_COLOR, _PIN_LABEL_WIDTH)]
            for c in _CAP_LABELS:
                if (self._int(self._fields.get(c)) >> (pin - 1)) & 1:
                    pills.append((_CAP_LABELS[c], _CAP_COLORS.get(c, '#888888'),
                                  _CAP_PILL_WIDTH))
                else:
                    pills.append(('', None, _CAP_PILL_WIDTH))   # empty column
            while len(pills) > 1 and pills[-1][1] is None:      # trim trailing
                pills.pop()
            self._draw_pill_row(painter, anchor, side, pills)
        if bus_pins:
            self._draw_hardware_bus(painter, bus_pins)

    def _draw_hardware_bus(self, painter: QPainter, bus_pins: list):
        """Draw the hardware-bus pins' number tags, then a single 'Hardware Bus'
        label per side joined to them by a bracket (a vertical spine off the
        tags), rather than repeating the label on every pin."""
        fm = painter.fontMetrics()
        pad_x, gap, stub, h = 6, 4, 10, fm.height() + 4
        bus_w = fm.horizontalAdvance(_HW_BUS_LABEL) + 2 * pad_x
        by_side: dict[str, list] = {}
        for pin, anchor, side in bus_pins:
            by_side.setdefault(side, []).append((pin, anchor))
        for side, items in by_side.items():
            items.sort(key=lambda pa: pa[1].y())
            sign = 1 if side == 'right' else -1
            # 1) each bus pin's number tag (dot + stub + tag pill).
            for pin, anchor in items:
                self._draw_pill_row(
                    painter, anchor, side,
                    [(self._pin_label(pin), _PIN_LABEL_COLOR, _PIN_LABEL_WIDTH)])
            # 2) bracket spine just outside the tag column, with a short
            #    connector from each tag to it.
            anchor_x = items[0][1].x()
            tag_outer = anchor_x + sign * (stub + _PIN_LABEL_WIDTH)
            bracket_x = tag_outer + sign * _HW_BUS_BRACKET_GAP
            ys = [a.y() for _, a in items]
            y_top, y_bot, mid = min(ys), max(ys), (min(ys) + max(ys)) / 2
            painter.setPen(QPen(QColor(_HW_BUS_LINE_COLOR), 1))
            painter.drawLine(QPointF(bracket_x, y_top), QPointF(bracket_x, y_bot))
            for _, a in items:
                painter.drawLine(QPointF(tag_outer, a.y()),
                                 QPointF(bracket_x, a.y()))
            # 3) one 'Hardware Bus' label, centred on the span, off the bracket.
            lx = bracket_x + sign * stub
            painter.drawLine(QPointF(bracket_x, mid), QPointF(lx, mid))
            bus_h = 2 * h           # double height to emphasise it's a bus
            rect = QRectF(lx if sign > 0 else lx - bus_w,
                          mid - bus_h / 2, bus_w, bus_h)
            self._grow(rect.left(), rect.right())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(_HW_BUS_COLOR))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor('#ffffff'))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter),
                             _HW_BUS_LABEL)

    def _pin_label(self, pin: int) -> str:
        """Display label for an I/O pin — a per-board/pin override if set in
        _PIN_LABELS, else the pin number."""
        return _PIN_LABELS.get(self._board, {}).get(pin, str(pin))

    def _draw_fixed_pins(self, painter: QPainter, img: QRectF):
        """Constant labels for the board's fixed-function pins (power, reset,
        etc.) — independent of the selected overlay."""
        for xf, yf, side, label in self._fixed:
            anchor = QPointF(img.left() + xf * img.width(),
                             img.top() + yf * img.height())
            color = _FIXED_PILL_COLORS.get(label, _FIXED_PILL_COLOR)
            # Lead with a dummy (numberless) pin tag so the function label lines
            # up with the I/O pins' first capability column.
            self._draw_pill_row(
                painter, anchor, side,
                [('', _PIN_LABEL_COLOR, _PIN_LABEL_WIDTH), (label, color)])

    def _draw_features(self, painter: QPainter, img: QRectF):
        """Feature callouts: a single-value label with a leader line pointing to
        a spot on the photo (e.g. UART baud at the USB-C connector)."""
        fm = painter.fontMetrics()
        pad_x, h = 6, fm.height() + 4
        t = theme.current()
        for feat in self._features:
            field = feat.get('field')
            value = self._fields.get(field, '') if field else ''
            if field and not value:
                continue
            text = feat.get('text', '{}').format(value)
            px = img.left() + feat['point'][0] * img.width()
            py = img.top() + feat['point'][1] * img.height()
            dx, dy = feat.get('offset', (0, -26))
            cx, cy = px + dx, py + dy            # label centre
            # Leader line from the label to the feature point (+ a small dot).
            painter.setPen(QPen(QColor(t['border']), 1))
            painter.setBrush(QColor(t['window_fg']))
            painter.drawLine(QPointF(cx, cy), QPointF(px, py))
            painter.drawEllipse(QPointF(px, py), 2.5, 2.5)
            # Pill centred on (cx, cy).
            w = fm.horizontalAdvance(text) + 2 * pad_x
            rect = QRectF(cx - w / 2, cy - h / 2, w, h)
            self._grow(rect.left(), rect.right())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(feat.get('color', '#0ea5e9')))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor(feat.get('text_color', '#1f2937')))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)

    def _draw_flags(self, painter: QPainter, img: QRectF):
        """Board-level capability flags (General Timer, Watchdog, …) this overlay
        has enabled, hung off a single vertical spine that connects by a leader
        line to the FPGA IC."""
        cfg = self._flags_cfg
        if not cfg:
            return
        labels = []
        for entry in _FLAG_CAPS:
            header, label = entry[0], entry[1]
            if self._int(self._fields.get(header)) == 0:
                continue
            detail = entry[2] if len(entry) > 2 else None
            if detail:
                label = f'{label}  ({detail(self._fields)})'
            labels.append(label)
        if not labels:
            return
        fm = painter.fontMetrics()
        pad_x, gap, stub, h = 6, 6, 12, fm.height() + 4
        t = theme.current()
        px = img.left() + cfg['point'][0] * img.width()
        py = img.top() + cfg['point'][1] * img.height()
        ox, oy = cfg.get('offset', (130, -60))
        sx, y0 = px + ox, py + oy            # spine x, first pill centre y
        last = y0 + (len(labels) - 1) * (h + gap)
        color = cfg.get('color', '#d1d5db')
        text_color = cfg.get('text_color', '#1f2937')
        # Leader from the FPGA to the top of the spine, then the spine itself.
        painter.setPen(QPen(QColor(t['border']), 1))
        painter.setBrush(QColor(t['window_fg']))
        painter.drawEllipse(QPointF(px, py), 2.5, 2.5)
        painter.drawLine(QPointF(px, py), QPointF(sx, y0))
        painter.drawLine(QPointF(sx, y0), QPointF(sx, last))
        self._grow(px, sx)
        for i, label in enumerate(labels):
            cy = y0 + i * (h + gap)
            painter.setPen(QPen(QColor(t['border']), 1))
            painter.drawLine(QPointF(sx, cy), QPointF(sx + stub, cy))
            w = fm.horizontalAdvance(label) + 2 * pad_x
            rect = QRectF(sx + stub, cy - h / 2, w, h)
            self._grow(rect.left(), rect.right())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor(text_color))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), label)

    def _draw_pill_row(self, painter: QPainter, anchor: QPointF,
                       side: str, pills: list):
        """Draw a pin anchor dot, a single connector running under the whole row
        out to the outermost pill, then the labelled pills on top. Each pill is a
        (label, colour) tuple, or (label, colour, width) to override the default
        _CAP_PILL_WIDTH."""
        fm = painter.fontMetrics()
        gap, stub = 4, 10
        h = fm.height() + 4
        t = theme.current()
        sign = 1 if side == 'right' else -1
        widths = [p[2] if len(p) > 2 else _CAP_PILL_WIDTH for p in pills]
        span = sum(widths) + gap * (len(pills) - 1)
        end_x = anchor.x() + sign * (stub + span)   # far edge of the last pill
        self._grow(anchor.x(), end_x)
        # Anchor dot + one line running under all pills to the outermost edge.
        painter.setPen(QPen(QColor(t['border']), 1))
        painter.setBrush(QColor(t['window_fg']))
        painter.drawEllipse(anchor, 2.5, 2.5)
        painter.drawLine(anchor, QPointF(end_x, anchor.y()))
        # Pills drawn on top of the line.
        x = anchor.x() + sign * stub
        for (pill, w) in zip(pills, widths):
            label, color = pill[0], pill[1]
            if side == 'right':
                rect = QRectF(x, anchor.y() - h / 2, w, h)
                x = rect.right() + gap
            else:
                rect = QRectF(x - w, anchor.y() - h / 2, w, h)
                x = rect.left() - gap
            if color is None:           # dummy spacer: reserve the column only
                continue
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(QColor('#ffffff'))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), label)

    def _draw_pin_markers(self, painter: QPainter, img: QRectF):
        """Debug aid: mark every anchor so the maps can be nudged to line up
        with the photo. Configurable I/O pins are red (numbered); fixed-function
        pins are orange (labelled). Independent of the selected overlay."""
        def mark(xf, yf, side, text, color):
            p = QPointF(img.left() + xf * img.width(),
                        img.top() + yf * img.height())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(p, 3, 3)
            painter.setPen(color)
            painter.drawText(
                QPointF(p.x() + (6 if side == 'right' else -20), p.y() - 5),
                text)

        red, orange = QColor('#ff0000'), QColor('#ff8c00')
        for pin, (xf, yf, side) in self._pins.items():
            mark(xf, yf, side, str(pin), red)
        for xf, yf, side, label in self._fixed:
            mark(xf, yf, side, label, orange)

    def _draw_message(self, painter: QPainter, text: str, bottom: bool = False):
        painter.setPen(QColor(theme.current()['window_fg']))
        rect = self.rect().adjusted(8, 8, -8, -8)
        align = (Qt.AlignmentFlag.AlignHCenter | (
            Qt.AlignmentFlag.AlignBottom if bottom
            else Qt.AlignmentFlag.AlignVCenter))
        painter.drawText(rect, int(align), text)

    def mousePressEvent(self, event):
        if self._DEBUG_CLICK and self._pixmap is not None:
            img = self._image_rect()
            if img.width() and img.height():
                xf = (event.position().x() - img.left()) / img.width()
                yf = (event.position().y() - img.top()) / img.height()
                print(f'[overlay-diagram] pin fraction: ({xf:.3f}, {yf:.3f})')
        super().mousePressEvent(event)

    @staticmethod
    def _int(value) -> int:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return 0


class HardwareOverlayPanel(QWidget):
    """Centre-stack page presenting the downloaded hardware overlay summary."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloader: _CsvDownloader | None = None
        self._vg_installer: _VgDownloader | None = None
        self._loaded = False
        # Target board dir name ('elm11', 'elm11-feather'); selects which board's
        # overlay data is shown. Updated by the owner via set_board().
        self._board = 'elm11'
        # Raw CSV headers/rows kept alongside the (display-transformed) table so
        # a row can be mapped back to its `.vg` image name on install.
        self._headers: list[str] = []
        self._rows_raw: list[list[str]] = []
        # Set by the owner: callable returning the destination Path for an
        # installed overlay (the workspace's emblua.vg), or None if no suitable
        # workspace is open.
        self.deploy_target_provider = None
        # Set by the owner: read/persist the installed overlay ID for the open
        # workspace (tracked alongside target/mode). Both None if unavailable.
        self.installed_overlay_getter = None   # callable() -> str | None
        self.installed_overlay_setter = None   # callable(overlay_id: str)
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel('Hardware Overlay Config')
        font = title.font()
        font.setPointSize(max(font.pointSize() + 3, 14))
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch(1)

        self._status = QLabel('')
        self._status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._status)

        # Filter rows by whether their `.vg` image is present locally.
        # _CenteredComboBox (no _cell_width set) centres on its own width.
        self._dl_filter = _CenteredComboBox()
        self._dl_filter.addItems(
            ['-', 'Downloaded', 'Not Downloaded'])
        self._dl_filter.setToolTip(
            'Filter rows based on downloaded state')
        self._dl_filter.currentIndexChanged.connect(self._apply_filters)
        header.addWidget(self._dl_filter)

        # Toggle the I/O diagram side-panel (off by default, like a dock).
        self._diagram_btn = QPushButton('Diagram')
        self._diagram_btn.setCheckable(True)
        self._diagram_btn.setToolTip(
            'Show the I/O diagram for the selected overlay alongside the table')
        self._diagram_btn.toggled.connect(self._toggle_diagram)
        header.addWidget(self._diagram_btn)

        self._reset_btn = QPushButton('Clear Filters')
        self._reset_btn.setToolTip('Reset every column filter to (All)')
        self._reset_btn.clicked.connect(self._clear_filters)
        header.addWidget(self._reset_btn)

        self._refresh_btn = QPushButton('Refresh')
        self._refresh_btn.setToolTip('Download the latest hardware overlay summary')
        self._refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        # Per-column filter row: one dropdown per column, positioned to line up
        # under its header (see _sync_filter_geometry). It scrolls with the
        # table's horizontal scrollbar.
        self._filter_bar = QWidget()
        self._filter_bar.setFixedHeight(0)
        self._filters: list[QComboBox] = []
        root.addWidget(self._filter_bar)

        # One row per overlay entry. The per-I/O bitmask columns are decoded
        # into a comma-separated I/O list (see _cap_text).
        self._table = QTableWidget(0, 0)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        # Right-click a row to install its overlay image.
        self._table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_menu)
        # Selecting a row updates the diagram side-panel.
        self._table.itemSelectionChanged.connect(self._on_row_selected)

        # Side-panel layout: the table fills the page, and an I/O diagram for
        # the selected row can be toggled in on the right (see _diagram_btn).
        # The diagram sits in a scroll area so its outward labels can be reached
        # with a horizontal scrollbar when they overflow the pane.
        self._diagram = _OverlayDiagram(self)
        self._diagram.set_board(self._board)
        self._diagram_scroll = QScrollArea()
        self._diagram_scroll.setWidgetResizable(True)
        self._diagram_scroll.setWidget(self._diagram)
        self._diagram_scroll.setMinimumWidth(_DIAGRAM_MIN_WIDTH)
        self._diagram_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._diagram_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Keep the (centred) board in view as the content width / pane resizes.
        self._diagram_scroll.horizontalScrollBar().rangeChanged.connect(
            self._center_diagram)
        self._split = QSplitter(Qt.Orientation.Horizontal)
        self._split.addWidget(self._table)
        self._split.addWidget(self._diagram_scroll)
        self._split.setStretchFactor(0, 3)      # table gets the lion's share
        self._split.setStretchFactor(1, 1)
        self._split.setCollapsible(0, False)
        self._split.setCollapsible(1, False)
        self._diagram_scroll.setVisible(self._diagram_btn.isChecked())  # off init
        root.addWidget(self._split, 1)

        # Keep the filter dropdowns aligned to their columns as the table is
        # resized, columns are resized, or it's scrolled horizontally.
        hh = self._table.horizontalHeader()
        hh.sectionResized.connect(lambda *_: self._sync_filter_geometry())
        hh.geometriesChanged.connect(self._sync_filter_geometry)
        self._table.horizontalScrollBar().valueChanged.connect(
            lambda *_: self._sync_filter_geometry())

        # Apply our own stylesheet up front — the main window only calls
        # apply_theme() on a theme *switch*, so without this the panel would
        # render unstyled (no header padding etc.) until the user changes theme.
        self.apply_theme()

    @staticmethod
    def _int(value) -> int:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return 0

    # ── External wiring ────────────────────────────────────────────────────

    def set_board(self, target: str):
        """Select which board's overlay data is shown. `target` is the board
        name ('ELM11', 'ELM11-Feather'); it maps directly to the bundle dir
        when lowercased. Reloads the table if it's already populated."""
        board = (target or 'ELM11').lower()
        if board == self._board:
            return
        self._board = board
        self._diagram.set_board(board)  # swap the photo + pin map
        if self._loaded:                # re-populate from the new board's bundle
            self._loaded = False
            self.ensure_loaded()

    def _csv_url(self) -> str:
        return _overlay_web_base(self._board) + 'summary.csv'

    def _vg_base_url(self) -> str:
        return _overlay_web_base(self._board)

    def ensure_loaded(self):
        """On first reveal, load the CSV bundled with the IDE. Pressing
        Refresh fetches the latest copy from the website instead."""
        if not self._loaded:
            self._load_bundled()

    def _load_bundled(self):
        """Read the shipped summary CSV synchronously (it's tiny and local)."""
        path = _bundled_csv(self._board)
        try:
            raw = path.read_text(encoding='utf-8-sig', errors='replace')
            rows = list(csv.reader(io.StringIO(raw)))
        except Exception as exc:                       # noqa: BLE001
            self._on_failed(f'{path}: {exc}')
            return
        if self._on_rows(rows):
            self._status.setText('Bundled')

    def refresh(self):
        """Download the latest summary CSV from the website and repopulate."""
        if self._downloader is not None and self._downloader.isRunning():
            return
        self._status.setText('Downloading…')
        self._refresh_btn.setEnabled(False)
        self._downloader = _CsvDownloader(self._csv_url(), self)
        self._downloader.rows_ready.connect(self._on_downloaded)
        self._downloader.failed.connect(self._on_failed)
        self._downloader.start()

    # ── Results ─────────────────────────────────────────────────────────────

    def _on_downloaded(self, rows: list):
        if self._on_rows(rows):
            self._status.setText('Downloaded')

    def _on_rows(self, rows: list) -> bool:
        """Populate the table from parsed CSV rows. Returns True on success."""
        self._refresh_btn.setEnabled(True)
        self._loaded = True
        headers = [str(c).strip() for c in rows[0]] if rows else []
        data = [
            cells for cells in
            ([str(v).strip() for v in r] for r in rows[1:])
            if any(cells)                              # skip blank/empty lines
        ] if rows else []
        if not headers or not data:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            self._status.setText('No data')
            return False
        self._populate(headers, data)
        self._status.setText(f'{len(data)} entries')
        return True

    def _populate(self, headers: list, data: list):
        # Keep the raw headers/rows so a table row maps back to its `.vg` image.
        self._headers = list(headers)
        self._rows_raw = [list(r) for r in data]
        # Column labels: apply display renames, then wrap each so no line is
        # wider than _HEADER_WRAP characters (long words are hyphenated).
        labels = [_wrap_header(_HEADER_RENAMES.get(h, h)) for h in headers]
        cap_cols = {i for i, h in enumerate(headers) if h in _CAP_HEADERS}
        bool_cols = {i for i, h in enumerate(headers) if h in _BOOL_HEADERS}
        try:
            pins_col = headers.index('I/O Pins')
        except ValueError:
            pins_col = -1

        self._table.setUpdatesEnabled(False)
        self._table.clearContents()
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(labels)
        # Hovering a (abbreviated/wrapped) header shows its tooltip — an entry
        # from _HEADER_TOOLTIPS, or the full original name as a fallback.
        for c, h in enumerate(headers):
            item = self._table.horizontalHeaderItem(c)
            if item is not None:
                item.setToolTip(_HEADER_TOOLTIPS.get(h, h))
        self._table.setRowCount(len(data))
        for r, row in enumerate(data):
            n_io = (self._int(row[pins_col])
                    if 0 <= pins_col < len(row) else 0)
            # Grey out rows whose `.vg` firmware image isn't present on disk.
            present = self._vg_path(row).is_file()
            for c in range(len(headers)):
                val = row[c] if c < len(row) else ''
                if c in cap_cols:
                    item = QTableWidgetItem(self._cap_text(self._int(val), n_io))
                elif c in bool_cols:
                    item = QTableWidgetItem(
                        'true' if self._int(val) != 0 else 'false')
                else:
                    item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if not present:
                    item.setForeground(QColor(Qt.GlobalColor.gray))
                self._table.setItem(r, c, item)
        self._table.resizeColumnsToContents()
        # Make every column the width of the widest one, so the (now uniform)
        # filter dropdowns and their popups line up — a combo's popup can't be
        # narrower than the widest item across the columns anyway.
        cols = self._table.columnCount()
        if cols:
            maxw = max(self._table.columnWidth(c) for c in range(cols))
            for c in range(cols):
                self._table.setColumnWidth(c, maxw)
        self._table.setUpdatesEnabled(True)
        # Rebuild the per-column filter dropdowns from the freshly shown values.
        self._build_filters()
        self._apply_filters()
        self._highlight_installed_row()
        # No row is selected yet — seed the diagram with the installed overlay.
        self._on_row_selected()

    # ── Per-column filtering ────────────────────────────────────────────────

    def _build_filters(self):
        """Make one dropdown per column, populated with that column's distinct
        values (plus '(All)'). Selecting a value filters rows on that column;
        choices across columns combine with AND."""
        for combo in self._filters:
            combo.deleteLater()
        self._filters = []
        rows = self._table.rowCount()
        for c in range(self._table.columnCount()):
            seen, uniq = [], set()
            for r in range(rows):
                item = self._table.item(r, c)
                txt = item.text() if item else ''
                if txt not in uniq:
                    uniq.add(txt)
                    seen.append(txt)
            combo = _CenteredComboBox(self._filter_bar)
            combo.setMinimumWidth(0)
            # Centre the closed text on the matching column's width, so the '-'
            # lines up with the centred cell text below it.
            combo._cell_width = lambda c=c: self._table.columnWidth(c)
            combo.addItem('-')                      # index 0 ⇒ no filter
            combo.addItems(self._sorted_values(seen))
            combo.currentIndexChanged.connect(self._apply_filters)
            combo.show()
            self._filters.append(combo)
        self._filter_bar.setFixedHeight(
            self._filters[0].sizeHint().height() if self._filters else 0)
        self._sync_filter_geometry()

    @staticmethod
    def _sorted_values(values: list) -> list:
        """Sort filter values numerically where possible, else alphabetically."""
        def key(v):
            try:
                return (0, float(v.strip()), '')
            except ValueError:
                return (1, 0.0, v.lower())
        return sorted(values, key=key)

    def _sync_filter_geometry(self):
        """Position each filter dropdown over its column (honouring the current
        horizontal scroll), so they stay aligned as things resize/scroll."""
        if not self._filters:
            return
        off = self._table.frameWidth()
        header = self._table.horizontalHeader()
        h = self._filter_bar.height()
        for c, combo in enumerate(self._filters):
            x = off + self._table.columnViewportPosition(c)
            combo.setGeometry(int(x), 0, int(header.sectionSize(c)), int(h))

    def _apply_filters(self, *_):
        """Hide rows that don't match every active (non-'(All)') column filter
        and the Downloaded filter."""
        selected = [(c, combo.currentText())
                    for c, combo in enumerate(self._filters)
                    if combo.currentIndex() > 0]
        dl_mode = self._dl_filter.currentIndex()   # 0 all, 1 yes, 2 no
        rows = self._table.rowCount()
        shown = 0
        for r in range(rows):
            ok = all((self._table.item(r, c).text() if self._table.item(r, c)
                      else '') == val for c, val in selected)
            if ok and dl_mode and r < len(self._rows_raw):
                present = self._vg_path(self._rows_raw[r]).is_file()
                ok = present if dl_mode == 1 else not present
            self._table.setRowHidden(r, not ok)
            shown += ok
        if selected or dl_mode:
            self._status.setText(f'{shown} / {rows} entries')
        elif rows:
            self._status.setText(f'{rows} entries')

    def _clear_filters(self):
        for combo in self._filters:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._dl_filter.blockSignals(True)
        self._dl_filter.setCurrentIndex(0)
        self._dl_filter.blockSignals(False)
        self._apply_filters()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_filter_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_filter_geometry()

    # ── Install overlay image ───────────────────────────────────────────────

    def _on_table_menu(self, pos):
        """Right-click context menu: install a row whose image is present, or
        download one that's missing (greyed out)."""
        row = self._table.rowAt(pos.y())
        if not 0 <= row < len(self._rows_raw):
            return
        self._table.selectRow(row)
        present = self._vg_path(self._rows_raw[row]).is_file()
        menu = QMenu(self)
        action = menu.addAction('Install' if present else 'Download')
        if menu.exec(self._table.viewport().mapToGlobal(pos)) is action:
            (self._install_row if present else self._download_row)(row)

    def _vg_path(self, raw_row: list) -> Path:
        """Local (bundled/cache) path of a raw row's `.vg` firmware image."""
        return _bundled_overlay_dir(self._board) / self._vg_name(raw_row)

    def _vg_name(self, raw_row: list) -> str:
        """`emblua_<stub>.vg` for a raw CSV row (clock converted MHz→Hz)."""
        headers = list(self._headers)
        fields = list(raw_row)
        # The generated 'ID' column isn't part of the image filename — drop it.
        if 'ID' in headers:
            idx = headers.index('ID')
            del headers[idx]
            if idx < len(fields):
                del fields[idx]
        try:
            ci = headers.index('Clk Mhz')
            fields[ci] = str(int(float(fields[ci]) * 1_000_000))
        except (ValueError, IndexError):
            pass                                   # leave as-is if unparseable
        return f'{_VG_PREFIX}{"_".join(fields)}.vg'

    def _row_id(self, row: int) -> str:
        """The row's overlay ID (the generated first column), e.g. '00007'."""
        try:
            return self._rows_raw[row][self._headers.index('ID')]
        except (ValueError, IndexError):
            return '?'

    def _row_clk(self, row: int) -> str:
        """The row's clock in whole MHz (e.g. '66'), for the timing filename."""
        try:
            val = self._rows_raw[row][self._headers.index('Clk Mhz')]
            return str(int(float(val)))
        except (ValueError, IndexError):
            return ''

    def _row_fields(self, row: int) -> dict:
        """Map the row's CSV headers to their raw values, for the diagram."""
        if not 0 <= row < len(self._rows_raw):
            return {}
        return dict(zip(self._headers, self._rows_raw[row]))

    def _toggle_diagram(self, checked: bool):
        """Show or hide the I/O diagram side-panel."""
        self._diagram_scroll.setVisible(checked)

    def _center_diagram(self, *_):
        """Centre the diagram's horizontal scroll on the (centred) board."""
        bar = self._diagram_scroll.horizontalScrollBar()
        bar.setValue((bar.minimum() + bar.maximum()) // 2)

    def _on_row_selected(self):
        """Push the selected row to the diagram (always captioned). With nothing
        selected, fall back to the overlay the workspace records as installed."""
        sel = self._table.selectionModel().selectedRows()
        if sel:
            row = sel[0].row()
            overlay_id = self._row_id(row)
            self._diagram.show_overlay(
                overlay_id, self._row_fields(row),
                caption=self._overlay_caption(overlay_id))
            return
        self._show_installed_overlay()

    def _show_installed_overlay(self):
        """Show the overlay the workspace records as installed (tracked like
        target/mode), or the prompt if none is recorded / not in the table."""
        overlay_id = (self.installed_overlay_getter()
                      if self.installed_overlay_getter else None)
        row = self._row_by_id(overlay_id) if overlay_id else None
        if row is None:
            self._diagram.show_overlay('', {})
            return
        self._diagram.show_overlay(
            self._row_id(row), self._row_fields(row),
            caption=self._overlay_caption(overlay_id))

    def _overlay_caption(self, overlay_id: str) -> str:
        """Diagram header for an overlay — 'Overlay <id>', suffixed '(Installed)'
        when it's the one recorded as installed in the workspace."""
        installed = (self.installed_overlay_getter()
                     if self.installed_overlay_getter else None)
        suffix = ' (Installed)' if overlay_id and overlay_id == installed else ''
        return f'Overlay {overlay_id}{suffix}'

    def _row_by_id(self, overlay_id: str) -> int | None:
        """Index of the row with the given overlay ID, or None if not present."""
        try:
            idx = self._headers.index('ID')
        except ValueError:
            return None
        for r, raw in enumerate(self._rows_raw):
            if idx < len(raw) and raw[idx] == overlay_id:
                return r
        return None

    def _highlight_installed_row(self):
        """Lightly tint the table row of the overlay recorded as installed
        (cleared from every other row)."""
        overlay_id = (self.installed_overlay_getter()
                      if self.installed_overlay_getter else None)
        target = self._row_by_id(overlay_id) if overlay_id else None
        bg = self._installed_bg()
        for r in range(self._table.rowCount()):
            for c in range(self._table.columnCount()):
                item = self._table.item(r, c)
                if item is None:
                    continue
                if r == target:
                    item.setBackground(bg)
                else:
                    item.setData(Qt.ItemDataRole.BackgroundRole, None)

    @staticmethod
    def _installed_bg() -> QColor:
        """A light tint for the installed row — the theme's selection colour
        blended toward the table background so it reads as a gentle highlight."""
        t = theme.current()
        sel, base = QColor(t['selection']), QColor(t['tree_bg'])
        f = 0.30
        return QColor(
            int(base.red() * (1 - f) + sel.red() * f),
            int(base.green() * (1 - f) + sel.green() * f),
            int(base.blue() * (1 - f) + sel.blue() * f))

    def deploy_default_overlay(self, overlay_id: str):
        """Install `overlay_id` into the open workspace non-interactively — used
        to seed a brand-new workspace with a default overlay. Quietly does
        nothing if the workspace, row, or local `.vg` image isn't available."""
        self.ensure_loaded()
        row = self._row_by_id(overlay_id)
        if row is None:
            return
        src = self._vg_path(self._rows_raw[row])
        dest = (self.deploy_target_provider()
                if self.deploy_target_provider else None)
        if dest is None or not src.is_file():
            return
        # Copies the image to emblua.vg, deploys timing.sdc, and records it as
        # the installed overlay (see _copy_overlay → _mark_installed).
        self._copy_overlay(src, dest, overlay_id, self._row_clk(row))

    def _install_row(self, row: int):
        """Copy (or offer to download) the row's `.vg` image into the workspace
        as the stable `emblua.vg`, plus its clock-matched timing constraints."""
        name = self._vg_name(self._rows_raw[row])
        overlay_id = self._row_id(row)
        clk = self._row_clk(row)
        dest = (self.deploy_target_provider()
                if self.deploy_target_provider else None)
        if dest is None:
            QMessageBox.warning(
                self, 'Install Overlay',
                'Open a Lua workspace before installing a hardware overlay.')
            return
        src = self._vg_path(self._rows_raw[row])
        if src.is_file():
            self._copy_overlay(src, dest, overlay_id, clk)
        elif QMessageBox.question(
                self, 'Install Overlay',
                f'{name} is not available locally.\n\n'
                f'Download it from {self._vg_base_url()}?'
                ) == QMessageBox.StandardButton.Yes:
            self._download_overlay(name, src, dest, overlay_id, clk, row)

    def _copy_overlay(self, src: Path, dest: Path, overlay_id: str, clk: str):
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        except OSError as exc:
            QMessageBox.critical(
                self, 'Install Overlay', f'Could not install overlay:\n{exc}')
            return
        self._deploy_timing(clk, dest.parent)
        self._mark_installed(overlay_id)
        self._status.setText(
            f'Installed Hardware Overlay {overlay_id}. '
            f'Please proceed with Synth-Program.')

    def _mark_installed(self, overlay_id: str):
        """Persist the just-installed overlay ID for the workspace (owner-set),
        and refresh the diagram if it's showing the installed view (no row
        selected) so the new overlay appears immediately."""
        if self.installed_overlay_setter:
            self.installed_overlay_setter(overlay_id)
        self._highlight_installed_row()
        if not self._table.selectionModel().selectedRows():
            self._show_installed_overlay()

    def _download_overlay(self, name: str, cache: Path, dest: Path,
                          overlay_id: str, clk: str, row: int):
        if self._vg_installer is not None and self._vg_installer.isRunning():
            return
        self._status.setText(f'Downloading Hardware Overlay {overlay_id}')
        self._vg_installer = _VgDownloader(
            self._vg_base_url() + name, dest, cache, self)
        self._vg_installer.done.connect(
            lambda: self._on_vg_done(overlay_id, dest.parent, clk, row))
        self._vg_installer.failed.connect(self._on_vg_failed)
        self._vg_installer.start()

    def _on_vg_done(self, overlay_id: str, dest_dir: Path, clk: str, row: int):
        self._deploy_timing(clk, dest_dir)
        self._refresh_row_grey(row)                 # un-grey now it's cached
        self._mark_installed(overlay_id)
        self._status.setText(
            f'Installed Hardware Overlay {overlay_id}. '
            f'Please proceed with Synth-Program.')

    def _download_row(self, row: int):
        """Fetch a missing row's `.vg` image into the local cache (no deploy),
        so the row un-greys and can be installed later."""
        if self._vg_installer is not None and self._vg_installer.isRunning():
            return
        name = self._vg_name(self._rows_raw[row])
        overlay_id = self._row_id(row)
        cache = self._vg_path(self._rows_raw[row])
        self._status.setText(f'Downloading Hardware Overlay {overlay_id}')
        # dest == cache: download straight into the local cache directory.
        self._vg_installer = _VgDownloader(
            self._vg_base_url() + name, cache, cache, self)
        self._vg_installer.done.connect(
            lambda: self._on_vg_cached(overlay_id, row))
        self._vg_installer.failed.connect(self._on_vg_failed)
        self._vg_installer.start()

    def _on_vg_cached(self, overlay_id: str, row: int):
        self._refresh_row_grey(row)
        self._status.setText(f'Downloaded Hardware Overlay {overlay_id}')

    def _refresh_row_grey(self, row: int):
        """Re-evaluate one row's `.vg` presence and (un)grey its cells."""
        if not 0 <= row < len(self._rows_raw):
            return
        present = self._vg_path(self._rows_raw[row]).is_file()
        for c in range(self._table.columnCount()):
            item = self._table.item(row, c)
            if item is None:
                continue
            if present:                             # clear the grey override
                item.setData(Qt.ItemDataRole.ForegroundRole, None)
            else:
                item.setForeground(QColor(Qt.GlobalColor.gray))
        # A newly-(un)downloaded row may now fall in/out of a Downloaded filter.
        self._apply_filters()

    def _deploy_timing(self, clk: str, dest_dir: Path):
        """Copy the clock-matched timing constraints into the workspace as the
        stable `timing.sdc` the synth flow references. Warns (without failing
        the install) if no constraints ship for that frequency."""
        src = _bundled_fw_dir(self._board) / f'timing_{clk}mhz.sdc'
        if not src.is_file():
            QMessageBox.warning(
                self, 'Install Overlay',
                f'No timing constraints bundled for {clk} MHz '
                f'({src.name}); timing.sdc was left unchanged.')
            return
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / 'timing.sdc')
        except OSError as exc:
            QMessageBox.critical(
                self, 'Install Overlay',
                f'Could not deploy timing constraints:\n{exc}')

    def _on_vg_failed(self, message: str):
        self._status.setText('Download failed')
        QMessageBox.critical(
            self, 'Install Overlay', f'Could not download overlay:\n{message}')

    @classmethod
    def _cap_text(cls, mask: int, n_io: int) -> str:
        """List of I/Os a capability bitmask covers, with consecutive runs
        collapsed into ranges (e.g. '1-3, 5, 8-9')."""
        if not n_io:
            n_io = mask.bit_length()
        # PINs are presented 1-based, while the mask bits are 0-based.
        ios = [i + 1 for i in range(n_io) if (mask >> i) & 1]
        if not ios:
            return '—'
        parts = []
        start = prev = ios[0]
        for x in ios[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            parts.append(str(start) if start == prev else f'{start}-{prev}')
            start = prev = x
        return ', '.join(parts)

    def _on_failed(self, message: str):
        # Keep whatever is already displayed (e.g. the bundled data) and just
        # flag the failure in the status, with the detail as a tooltip.
        self._refresh_btn.setEnabled(True)
        self._status.setText('Download failed')
        self._status.setToolTip(message)

    def shutdown(self):
        """Stop the download threads cleanly — call on application close."""
        if self._downloader is not None and self._downloader.isRunning():
            self._downloader.wait(3000)
        if self._vg_installer is not None and self._vg_installer.isRunning():
            self._vg_installer.wait(3000)

    # ── Theme ──────────────────────────────────────────────────────────────

    def apply_theme(self):
        t = theme.current()
        self.setStyleSheet(
            f'QWidget {{ background:{t["window_bg"]}; color:{t["window_fg"]}; }}'
            f'QTableWidget {{ background:{t["tree_bg"]}; color:{t["tree_fg"]}; '
            f'gridline-color:{t["border"]}; '
            f'alternate-background-color:{t["menubar_bg"]}; }}'
            f'QHeaderView::section {{ background:{t["menubar_bg"]}; '
            f'color:{t["menubar_fg"]}; border:1px solid {t["border"]}; '
            f'padding:2px 7px; }}'
            f'QTableWidget::item:selected {{ background:{t["selection"]}; }}'
            f'QComboBox {{ background:{t["dlg_input_bg"]}; '
            f'color:{t["dlg_input_fg"]}; border:1px solid {t["border"]}; '
            f'padding:1px 4px; }}'
            f'QComboBox QAbstractItemView {{ background:{t["menubar_bg"]}; '
            f'color:{t["dlg_input_fg"]}; '
            f'selection-background-color:{t["selection"]}; }}'
        )
        # Re-tint the installed row for the new theme (no-op before populate).
        self._highlight_installed_row()
