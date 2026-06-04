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
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from . import theme


# Published summary of the ELM11 hardware overlay register/pin map.
_CSV_URL = ('https://brisbanesilicon.com.au/software/'
            'elm11_hardware_overlay/summary.csv')

# Per-row firmware images live beside the summary CSV (locally and on the web),
# named `emblua_<stub>.vg`, where <stub> is the row's raw CSV fields joined by
# '_' with the clock given in Hz (the CSV shows MHz). Installing one copies it
# into the workspace as the stable `emblua.vg` the synth flow expects.
_VG_PREFIX = 'emblua_'
_VG_BASE_URL = _CSV_URL.rsplit('/', 1)[0] + '/'   # same web dir as the CSV


def _ide_base() -> Path:
    """Root of the bundled `brs_ide` data (dev, PyInstaller, install)."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'brs_ide'
    return Path(__file__).resolve().parent


def _bundled_csv() -> Path:
    """Path to the CSV shipped with the IDE (dev, PyInstaller, install)."""
    return _ide_base() / 'elm11' / 'hardware_overlay' / 'summary.csv'


def _bundled_fw_dir() -> Path:
    """Bundled firmware dir holding the per-frequency timing constraints
    (`timing_<n>mhz.sdc`) alongside the HDL sources."""
    return _ide_base() / 'elm11' / 'lua' / 'build' / 'fw'


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
}

# Display-only header relabelling. The CSV already ships short names ('Perf
# Timer', 'Watchdog Timeout'), so nothing needs renaming today; this is kept as
# the hook for any future long→short mapping.
_HEADER_RENAMES = {}

# Headers (after renaming) wrapped onto two lines (the space is replaced with a
# newline) to keep these columns from stretching the table too wide.
_TWO_LINE_HEADERS = {
    'General Timer',
    'Perf Timer',
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


class HardwareOverlayPanel(QWidget):
    """Centre-stack page presenting the downloaded hardware overlay summary."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloader: _CsvDownloader | None = None
        self._vg_installer: _VgDownloader | None = None
        self._loaded = False
        # Raw CSV headers/rows kept alongside the (display-transformed) table so
        # a row can be mapped back to its `.vg` image name on install.
        self._headers: list[str] = []
        self._rows_raw: list[list[str]] = []
        # Set by the owner: callable returning the destination Path for an
        # installed overlay (the workspace's emblua.vg), or None if no suitable
        # workspace is open.
        self.deploy_target_provider = None
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
        # Right-click a row to install its overlay image.
        self._table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_menu)
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
        # Keep the raw headers/rows so a table row maps back to its `.vg` image.
        self._headers = list(headers)
        self._rows_raw = [list(r) for r in data]
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

    # ── Install overlay image ───────────────────────────────────────────────

    def _on_table_menu(self, pos):
        """Right-click context menu: install the clicked row's overlay image."""
        row = self._table.rowAt(pos.y())
        if not 0 <= row < len(self._rows_raw):
            return
        self._table.selectRow(row)
        menu = QMenu(self)
        install = menu.addAction('Install')
        if menu.exec(self._table.viewport().mapToGlobal(pos)) is install:
            self._install_row(row)

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
        src = _bundled_csv().parent / name
        if src.is_file():
            self._copy_overlay(src, dest, overlay_id, clk)
        elif QMessageBox.question(
                self, 'Install Overlay',
                f'{name} is not available locally.\n\n'
                f'Download it from {_VG_BASE_URL}?'
                ) == QMessageBox.StandardButton.Yes:
            self._download_overlay(name, src, dest, overlay_id, clk)

    def _copy_overlay(self, src: Path, dest: Path, overlay_id: str, clk: str):
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        except OSError as exc:
            QMessageBox.critical(
                self, 'Install Overlay', f'Could not install overlay:\n{exc}')
            return
        self._deploy_timing(clk, dest.parent)
        self._status.setText(f'Installed Hardware Overlay {overlay_id}')

    def _download_overlay(self, name: str, cache: Path, dest: Path,
                          overlay_id: str, clk: str):
        if self._vg_installer is not None and self._vg_installer.isRunning():
            return
        self._status.setText(f'Downloading {name}…')
        self._vg_installer = _VgDownloader(
            _VG_BASE_URL + name, dest, cache, self)
        self._vg_installer.done.connect(
            lambda: self._on_vg_done(overlay_id, dest.parent, clk))
        self._vg_installer.failed.connect(self._on_vg_failed)
        self._vg_installer.start()

    def _on_vg_done(self, overlay_id: str, dest_dir: Path, clk: str):
        self._deploy_timing(clk, dest_dir)
        self._status.setText(f'Installed Hardware Overlay {overlay_id}')

    def _deploy_timing(self, clk: str, dest_dir: Path):
        """Copy the clock-matched timing constraints into the workspace as the
        stable `timing.sdc` the synth flow references. Warns (without failing
        the install) if no constraints ship for that frequency."""
        src = _bundled_fw_dir() / f'timing_{clk}mhz.sdc'
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
