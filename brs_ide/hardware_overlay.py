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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

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

# Headers wrapped onto two lines (the space is replaced with a newline) to keep
# these columns from stretching the table too wide.
_TWO_LINE_HEADERS = {
    'General Timer',
    'Performance Timer',
    'Hardware Watchdog',
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

        self._refresh_btn = QPushButton('Refresh')
        self._refresh_btn.setToolTip('Download the latest hardware overlay summary')
        self._refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        # One row per overlay entry. The per-I/O bitmask columns are decoded
        # into a comma-separated I/O list (see _cap_text).
        self._table = QTableWidget(0, 0)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table, 1)

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
        # Use the CSV's own header row as the column labels, wrapping the
        # selected headers onto two lines (replace the first space with \n).
        labels = [h.replace(' ', '\n', 1) if h in _TWO_LINE_HEADERS else h
                  for h in headers]
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
        self._table.setUpdatesEnabled(True)

    @classmethod
    def _cap_text(cls, mask: int, n_io: int) -> str:
        """Comma-separated list of I/Os a capability bitmask covers."""
        if not n_io:
            n_io = mask.bit_length()
        # PINs are presented 1-based, while the mask bits are 0-based.
        ios = [i + 1 for i in range(n_io) if (mask >> i) & 1]
        return ', '.join(str(i) for i in ios) if ios else '—'

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
            f'padding:3px 6px; }}'
            f'QTableWidget::item:selected {{ background:{t["selection"]}; }}'
        )
