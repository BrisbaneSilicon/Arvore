"""Hardware Overlay panel.

A full-centre page (toggled like Command Mode) showing the ELM11 hardware
overlay summary in a large table. The data is downloaded as CSV from the
Brisbane Silicon website and refreshed on demand.
"""
from __future__ import annotations

import csv
import io
import urllib.request

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from . import theme


# Published summary of the ELM11 hardware overlay register/pin map.
_CSV_URL = ('https://brisbanesilicon.com.au/software/'
            'elm11_hardware_overlay/summary.csv')


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
        self._refresh_btn.setToolTip('Re-download the hardware overlay summary')
        self._refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self._refresh_btn)
        root.addLayout(header)

        self._table = QTableWidget(0, 0)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, 1)

    # ── External wiring ────────────────────────────────────────────────────

    def ensure_loaded(self):
        """Download once on first reveal; subsequent toggles reuse the data
        (use Refresh to force a re-fetch)."""
        if not self._loaded:
            self.refresh()

    def refresh(self):
        """(Re)download the summary CSV and repopulate the table."""
        if self._downloader is not None and self._downloader.isRunning():
            return
        self._status.setText('Downloading…')
        self._refresh_btn.setEnabled(False)
        self._downloader = _CsvDownloader(_CSV_URL, self)
        self._downloader.rows_ready.connect(self._on_rows)
        self._downloader.failed.connect(self._on_failed)
        self._downloader.start()

    # ── Download results ───────────────────────────────────────────────────

    def _on_rows(self, rows: list):
        self._refresh_btn.setEnabled(True)
        self._loaded = True
        if not rows:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            self._status.setText('No data')
            return
        headers = [str(c) for c in rows[0]]
        data = rows[1:]
        ncols = max([len(headers)] + [len(r) for r in data])
        self._table.setColumnCount(ncols)
        # Pad header labels out to the widest row.
        labels = headers + [''] * (ncols - len(headers))
        self._table.setHorizontalHeaderLabels(labels)
        self._table.setRowCount(len(data))
        for r, row in enumerate(data):
            for c in range(ncols):
                val = row[c] if c < len(row) else ''
                self._table.setItem(r, c, QTableWidgetItem(str(val)))
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setSectionResizeMode(
            ncols - 1, QHeaderView.ResizeMode.Stretch)
        self._status.setText(f'{len(data)} rows')

    def _on_failed(self, message: str):
        self._refresh_btn.setEnabled(True)
        self._status.setText('Download failed')
        self._table.setRowCount(1)
        self._table.setColumnCount(1)
        self._table.setHorizontalHeaderLabels([''])
        item = QTableWidgetItem(f'Could not download summary:\n{message}')
        item.setForeground(Qt.GlobalColor.red)
        self._table.setItem(0, 0, item)
        self._table.resizeColumnsToContents()

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
