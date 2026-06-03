"""Hardware Overlay panel.

A full-centre page (toggled like Command Mode) showing the ELM11 hardware
overlay summary in a large table. The data is downloaded as CSV from the
Brisbane Silicon website and refreshed on demand.
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QStylePainter, QStyleOptionComboBox, QStyle, QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from . import theme


# Published summary of the ELM11 hardware overlay register/pin map.
_CSV_URL = ('https://brisbanesilicon.com.au/software/'
            'elm11_hardware_overlay/summary.csv')


def _bundled_csv() -> Path:
    """Path to the CSV shipped with the IDE (dev, PyInstaller, install)."""
    if hasattr(sys, '_MEIPASS'):
        base = Path(sys._MEIPASS) / 'brs_ide'
    else:
        base = Path(__file__).resolve().parent
    return base / 'elm11' / 'hardware_overlay' / 'summary.csv'


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
    'Performance Timer',
    'Hardware Watchdog',
    'Software Interrupts',
    'Hardware Bus',
}

# Display-only header relabelling (the CSV keeps its own names; we just show
# something shorter/clearer).
_HEADER_RENAMES = {
    'Hardware Watchdog Timeout': 'Watchdog Timeout',
    'Performance Timer': 'Perf Timer',
}

# Headers (after renaming) wrapped onto two lines (the space is replaced with a
# newline) to keep these columns from stretching the table too wide.
_TWO_LINE_HEADERS = {
    'General Timer',
    'Perf Timer',
    'Hardware Watchdog',
    'Watchdog Timeout',
    'I/O Buffer',
    'Software Interrupts',
    'Hardware Bus',
}


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

    def showPopup(self):
        # Keep the popup at the combo (column) width. Constrain the view
        # *before* showPopup sizes the container (a post-show resize of the
        # popup window is unreliable across platforms), then clamp the shown
        # window too as a belt-and-suspenders.
        w = self.width()
        view = self.view()
        view.setMinimumWidth(w)
        view.setMaximumWidth(w)
        view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        super().showPopup()
        win = view.window()
        if win is not None and win is not self.window():
            win.setFixedWidth(w)
            win.move(self.mapToGlobal(self.rect().bottomLeft()))

    def paintEvent(self, _event):
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        text = opt.currentText
        # Draw the frame + arrow without the label (blank it so the style
        # doesn't paint its own left-aligned text)…
        opt.currentText = ''
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        # …then draw the label centred across the *whole* combo. Inset by the
        # arrow's width on both sides so the text's midpoint stays the widget
        # centre (rather than the smaller area left of the arrow, which reads
        # as left-of-centre). SC_ComboBoxEditField is unreliable under a
        # stylesheet, so derive the rect from the widget bounds.
        arrow = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, opt,
            QStyle.SubControl.SC_ComboBoxArrow, self)
        aw = arrow.width() if arrow.width() > 0 else 16
        text_rect = self.rect().adjusted(aw, 0, -aw, 0)
        painter.setPen(QColor(theme.current()['dlg_input_fg']))
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignCenter), text)


class HardwareOverlayPanel(QWidget):
    """Centre-stack page presenting the downloaded hardware overlay summary."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloader: _CsvDownloader | None = None
        self._loaded = False
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
        root.addWidget(self._table, 1)

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

    def ensure_loaded(self):
        """On first reveal, load the CSV bundled with the IDE. Pressing
        Refresh fetches the latest copy from the website instead."""
        if not self._loaded:
            self._load_bundled()

    def _load_bundled(self):
        """Read the shipped summary CSV synchronously (it's tiny and local)."""
        path = _bundled_csv()
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
        self._downloader = _CsvDownloader(_CSV_URL, self)
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
        data = [[str(v).strip() for v in r] for r in rows[1:]] if rows else []
        if not headers or not data:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            self._status.setText('No data')
            return False
        self._populate(headers, data)
        self._status.setText(f'{len(data)} entries')
        return True

    def _populate(self, headers: list, data: list):
        # Column labels: apply display renames, then wrap the selected ones
        # onto two lines (replace the first space with \n).
        labels = []
        for h in headers:
            name = _HEADER_RENAMES.get(h, h)
            labels.append(name.replace(' ', '\n', 1)
                          if name in _TWO_LINE_HEADERS else name)
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
        self._table.setRowCount(len(data))
        for r, row in enumerate(data):
            n_io = (self._int(row[pins_col])
                    if 0 <= pins_col < len(row) else 0)
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
        """Hide rows that don't match every active (non-'(All)') column filter."""
        selected = [(c, combo.currentText())
                    for c, combo in enumerate(self._filters)
                    if combo.currentIndex() > 0]
        rows = self._table.rowCount()
        shown = 0
        for r in range(rows):
            ok = all((self._table.item(r, c).text() if self._table.item(r, c)
                      else '') == val for c, val in selected)
            self._table.setRowHidden(r, not ok)
            shown += ok
        if selected:
            self._status.setText(f'{shown} / {rows} entries')
        elif rows:
            self._status.setText(f'{rows} entries')

    def _clear_filters(self):
        for combo in self._filters:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._apply_filters()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_filter_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_filter_geometry()

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
        """Stop the download thread cleanly — call on application close."""
        if self._downloader is not None and self._downloader.isRunning():
            self._downloader.wait(3000)

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
