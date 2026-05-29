"""Main application window."""
import logging
import os
import re
log = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QSplitter, QTabWidget, QToolBar,
    QFileDialog, QMessageBox, QComboBox, QPushButton, QLabel,
    QWidget, QSizePolicy, QMenu, QStackedWidget,
)
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QCursor
from PyQt6.QtWidgets import QToolTip
import serial.tools.list_ports
from pathlib import Path
import sys

from .code_editor import CodeEditor, _content_hash, _upload_hash_key
from .project_tree import ProjectTree
from .serial_terminal import SerialTerminal
from .build_output import BuildOutput
from .uploader import UploaderWorker
from .settings import SettingsDialog
from .docs_panel import DocsPanel
from .command_mode import CommandModePanel
from . import theme


def _ide_data_dir(name: str) -> Path:
    """Resolve a bundled data directory (`brs_ide/<name>/`) for dev,
    PyInstaller, and system-install layouts."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'brs_ide' / name
    return Path(__file__).resolve().parent / name


def _c_runtime_objects() -> list[str]:
    """Return every `*.o` file shipped in `brs_ide/elm11/c/runtime/`."""
    base = _ide_data_dir('elm11/c/runtime')
    if not base.is_dir():
        return []
    return sorted(str(p) for p in base.glob('*.o'))


def _port_is_acceptable(port: str) -> bool:
    """On Linux only `/dev/ttyUSB*` devices are usable for firmware /
    program uploads — built-in (`ttyS*`) and CDC-ACM (`ttyACM*`) ports
    aren't supported. Other platforms allow anything."""
    if not port:
        return False
    if not sys.platform.startswith('linux'):
        return True
    return Path(port).name.startswith('ttyUSB')


def _msys_path(p) -> str:
    """Convert a path to POSIX-style (forward slashes). Make on MSYS2
    treats backslashes as escape characters and several built-in
    functions (`wildcard`, `subst`) misbehave on backslash paths, so
    every absolute path we pass on the make command line goes through
    here. On Linux/macOS this is a no-op."""
    return str(p).replace('\\', '/')


def _make_invocation() -> tuple[str, dict[str, str] | None]:
    """Return `(program, env_overrides)` for invoking GNU make.

    On Linux/macOS this is just `('make', None)` — we trust `$PATH`. On
    Windows we look at the configured MSYS2 install root: the make binary
    lives at `<msys2>/usr/bin/make.exe`, and `<msys2>/usr/bin` is also
    prepended to the subprocess PATH so the recipes' Unix utilities
    (mkdir, rm, cp, date, …) resolve correctly. If MSYS2 isn't
    configured we fall back to plain `make` from PATH."""
    msys2 = SettingsDialog.msys2_path()
    if not (sys.platform.startswith('win') and msys2):
        return 'make', None
    bin_dir = str(Path(msys2) / 'usr' / 'bin')
    make    = str(Path(bin_dir) / 'make.exe')
    env = {'PATH': bin_dir + os.pathsep + os.environ.get('PATH', '')}
    return make, env


def _resolve_upload_port(intended: str) -> str:
    """Return `intended` if it's currently present, otherwise fall back to
    the highest-indexed acceptable port (so a replug-after-flash that
    bumps `/dev/ttyUSB0` to `/dev/ttyUSB1` is handled automatically).
    Returns `''` if nothing acceptable is connected."""
    available = [p.device for p in serial.tools.list_ports.comports()
                 if _port_is_acceptable(p.device)]
    if intended and intended in available:
        return intended
    if not available:
        return ''

    def _index(p: str) -> int:
        m = re.search(r'(\d+)$', Path(p).name)
        return int(m.group(1)) if m else -1

    return max(available, key=_index)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log.debug('MainWindow init')
        self.setWindowTitle('BrisbaneSilicon IDE')
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(theme.main_stylesheet(theme.current()))

        self._workspace_root: Path | None = None
        self._workspace_mode: str = 'Lua'
        self._workspace_target: str = 'ELM11'

        # Build central UI first so _terminal etc. exist before menu is wired
        log.debug('Setting up central UI')
        self._setup_central()
        log.debug('Setting up toolbar')
        self._setup_toolbar()
        log.debug('Setting up menu')
        self._setup_menu()
        log.debug('Setting up statusbar')
        self._setup_statusbar()
        log.debug('Restoring geometry')
        self._restore_geometry()
        log.debug('Restoring workspace')
        self._restore_workspace()

        if QSettings().value('ui/docs_visible', False, type=bool):
            self._docs_toggle.setChecked(True)

        # Auto-refresh serial port list
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._refresh_ports)
        self._port_timer.start(3000)
        self._refresh_ports()

    # ── Central widget ────────────────────────────────────────────────────────

    def _setup_central(self):
        self._outer = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self._outer)

        # Left: project tree
        self._tree = ProjectTree()
        self._tree.file_activated.connect(self._open_path)
        self._tree.workspace_loaded.connect(self._load_workspace)
        self._tree.new_file_requested.connect(self._new_file)
        self._tree.set_status_provider(self._file_status)
        self._tree.setMinimumWidth(120)
        self._outer.addWidget(self._tree)
        self._outer.setChildrenCollapsible(False)

        # Centre: editor + bottom panel, wrapped in a stack so Command Mode
        # can replace the whole centre region when active.
        self._centre = QSplitter(Qt.Orientation.Vertical)

        # Editor area: a horizontal splitter of one-or-more tab "panes".
        # A Lua workspace defaults to two panes; the active pane (tracked via
        # focus) receives New/Open/Save actions.
        self._editor_split = QSplitter(Qt.Orientation.Horizontal)
        self._editor_split.setChildrenCollapsible(False)
        self._editor_panes: list[QTabWidget] = []
        self._make_editor_pane()
        self._active_pane = self._editor_panes[0]
        QApplication.instance().focusChanged.connect(self._on_editor_focus_changed)
        self._centre.addWidget(self._editor_split)

        self._bottom = QTabWidget()
        self._terminal = SerialTerminal()
        self._terminal.connected.connect(self._on_connection_changed)
        self._upload_out = BuildOutput()
        self._build_out = BuildOutput()
        self._build_out.build_finished.connect(self._on_build_finished)
        self._flash_out = BuildOutput()
        self._bottom.addTab(self._terminal, 'Serial Terminal')
        self._bottom.addTab(self._upload_out, 'Upload Status')
        self._bottom.addTab(self._build_out, 'Build Output')
        self._bottom.addTab(self._flash_out, 'Flash Output')
        self._centre.addWidget(self._bottom)
        self._centre.setChildrenCollapsible(False)

        # Command-mode panel: page 1 of the centre stack. Activating Command
        # Mode swaps the centre from editors+bottom to this panel.
        self._cmd_mode = CommandModePanel()
        self._cmd_mode.set_terminal(self._terminal)
        self._cmd_mode.active_changed.connect(self._on_cmd_mode_active_changed)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self._centre)     # page 0: editors + bottom
        self._center_stack.addWidget(self._cmd_mode)   # page 1: command mode
        self._outer.addWidget(self._center_stack)

        # Right-most: toggleable documentation panel
        self._docs = DocsPanel()
        self._docs.open_example.connect(self._open_example)
        self._docs.setMinimumWidth(240)
        self._docs.setVisible(False)
        self._outer.addWidget(self._docs)

        self._outer.setSizes([200, 900, 0])
        self._centre.setSizes([520, 200])

    # ── Editor panes ────────────────────────────────────────────────────────────

    def _make_editor_pane(self) -> QTabWidget:
        """Create an editor tab-group, wire its signals, and add it to the
        editor splitter. Returns the new pane."""
        pane = QTabWidget()
        pane.setTabsClosable(True)
        pane.setMovable(True)
        pane.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        pane.tabCloseRequested.connect(self._close_tab)
        pane.currentChanged.connect(self._on_tab_changed)
        bar = pane.tabBar()
        bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        bar.customContextMenuRequested.connect(
            lambda pos, p=pane: self._tab_context_menu(p, pos))
        self._editor_panes.append(pane)
        self._editor_split.addWidget(pane)
        return pane

    def _set_pane_count(self, n: int):
        """Grow or shrink the editor to exactly `n` panes, then size them
        evenly. Tabs in a removed pane are moved into the first pane so
        nothing is lost."""
        n = max(1, n)
        while len(self._editor_panes) < n:
            self._make_editor_pane()
        while len(self._editor_panes) > n:
            pane = self._editor_panes.pop()
            while pane.count():
                w = pane.widget(0)
                text = pane.tabText(0)
                pane.removeTab(0)
                self._editor_panes[0].addTab(w, text)
            pane.setParent(None)
            pane.deleteLater()
        if self._active_pane not in self._editor_panes:
            self._active_pane = self._editor_panes[0]
        self._editor_split.setSizes([1] * len(self._editor_panes))
        # Keep the View-menu toggle in sync (the menu may not exist yet during
        # initial construction).
        if hasattr(self, '_split_toggle'):
            self._split_toggle.blockSignals(True)
            self._split_toggle.setChecked(len(self._editor_panes) > 1)
            self._split_toggle.blockSignals(False)

    def _pane_count_for_mode(self) -> int:
        """Lua workspaces default to two side-by-side editor panes; every
        other mode uses a single pane."""
        return 2 if self._workspace_mode == 'Lua' else 1

    def _default_pane_for(self, path: Path) -> QTabWidget:
        """Pick the pane a newly-opened file lands in. In a split layout, C
        sources/headers open in the right-hand pane and everything else in the
        left; with a single pane, everything opens in the active pane."""
        if len(self._editor_panes) < 2:
            return self._active_pane
        if path.suffix.lower() in ('.c', '.h'):
            return self._editor_panes[-1]
        return self._editor_panes[0]

    def _toggle_split_editor(self, checked: bool):
        """View-menu toggle: split the editor into two panes, or close the
        right-hand pane (its tabs move back into the left pane)."""
        self._set_pane_count(2 if checked else 1)

    def _all_editors(self):
        """Yield every CodeEditor across all panes."""
        for pane in self._editor_panes:
            for i in range(pane.count()):
                w = pane.widget(i)
                if isinstance(w, CodeEditor):
                    yield w

    def _pane_for_editor(self, editor) -> tuple[QTabWidget, int] | None:
        """Return the (pane, tab-index) holding `editor`, or None."""
        for pane in self._editor_panes:
            for i in range(pane.count()):
                if pane.widget(i) is editor:
                    return pane, i
        return None

    def _on_editor_focus_changed(self, _old, now):
        """Track which pane is 'active' so New/Open/Save target it. Focus
        landing anywhere inside a pane (editor body or tab bar) selects it;
        focus elsewhere (toolbar, tree) leaves the active pane unchanged."""
        w = now
        while w is not None:
            if w in self._editor_panes:
                self._active_pane = w
                return
            w = w.parentWidget()

    def _tab_context_menu(self, pane: QTabWidget, pos):
        """Right-click menu for an editor tab. Offers moving the tab to the
        adjacent pane — only meaningful when more than one pane exists."""
        if len(self._editor_panes) < 2:
            return
        bar = pane.tabBar()
        index = bar.tabAt(pos)
        if index < 0:
            return
        t = theme.current()
        menu = QMenu(self)
        menu.setStyleSheet(
            f'QMenu {{ background:{t["menubar_bg"]}; color:{t["menubar_fg"]}; '
            f'border:1px solid {t["border"]}; }}'
            f'QMenu::item:selected {{ background:{t["selection"]}; }}')
        act = menu.addAction('Move to Other Pane')
        act.triggered.connect(lambda: self._move_tab_to_other_pane(pane, index))
        menu.exec(bar.mapToGlobal(pos))

    def _move_tab_to_other_pane(self, pane: QTabWidget, index: int):
        """Relocate the tab at `index` into the next pane, preserving the
        editor widget and all its state (content, undo history, dirty/stale
        markers). The destination pane becomes active."""
        if len(self._editor_panes) < 2 or index < 0:
            return
        widget = pane.widget(index)
        if widget is None:
            return
        src_i = self._editor_panes.index(pane)
        dst = self._editor_panes[(src_i + 1) % len(self._editor_panes)]
        text = pane.tabText(index)
        pane.removeTab(index)
        new_idx = dst.addTab(widget, text)
        dst.setCurrentIndex(new_idx)
        self._active_pane = dst
        if isinstance(widget, CodeEditor):
            self._refresh_tab_title(widget)
        widget.setFocus()
        self._update_device_buttons()

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _setup_toolbar(self):
        tb = QToolBar('Main', self)
        tb.setIconSize(QSize(16, 16))
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction(self._act('New',  None, self._new_file))
        tb.addAction(self._act('Open', None, self._open_file))
        tb.addAction(self._act('Save', None, self._save_file))
        tb.addSeparator()

        tb.addWidget(QLabel(' Port: '))
        self._port_combo = QComboBox()
        tb.addWidget(self._port_combo)

        self._connect_btn = QPushButton('Connect')
        self._connect_btn.setCheckable(True)
        self._connect_btn.clicked.connect(self._toggle_connect)
        tb.addWidget(self._connect_btn)
        tb.addSeparator()

        self._build_btn = QPushButton('Build')
        self._build_btn.setToolTip('Build the current C project')
        self._build_btn.clicked.connect(self._build)
        tb.addWidget(self._build_btn)

        self._clean_btn = QPushButton('Clean')
        self._clean_btn.setToolTip('Delete build artefacts (make clean)')
        self._clean_btn.clicked.connect(self._clean)
        tb.addWidget(self._clean_btn)

        self._flash_btn = QPushButton('Flash')
        self._flash_btn.setToolTip('Flash the built binary to the ELM11')
        self._flash_btn.clicked.connect(self._flash)
        self._flash_btn.setEnabled(False)
        tb.addWidget(self._flash_btn)

        tb.addWidget(self._toolbar_spacer())

        self._upload_btn = QPushButton('Upload')
        self._upload_btn.setToolTip('Upload Lua program to ELM11')
        self._upload_btn.clicked.connect(self._upload)
        self._upload_btn.setEnabled(False)
        tb.addWidget(self._upload_btn)

        self._run_btn = QPushButton('Run')
        self._run_btn.setToolTip('Run uploaded program on ELM11')
        self._run_btn.clicked.connect(self._run_program)
        self._run_btn.setEnabled(False)
        tb.addWidget(self._run_btn)

        self._stop_btn = QPushButton('Stop')
        self._stop_btn.setToolTip('Stop the currently running program')
        self._stop_btn.clicked.connect(self._stop_program)
        self._stop_btn.setEnabled(False)
        tb.addWidget(self._stop_btn)

        tb.addWidget(self._toolbar_spacer())

        self._cmd_btn = QPushButton('Command Mode')
        self._cmd_btn.setCheckable(True)
        self._cmd_btn.setToolTip('Toggle ELM11 Command Mode')
        self._cmd_btn.setEnabled(False)
        self._cmd_btn.toggled.connect(self._on_cmd_btn_toggled)
        tb.addWidget(self._cmd_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet('background: transparent;')
        tb.addWidget(spacer)

        # Right-side toolbar label. Shows the workspace's target board
        # (always when a workspace is open) and, when relevant, prefixes
        # it with the device state ('REPL' / 'COMMAND MODE').
        # Fixed width sized to "COMMAND MODE — ELM11-Feather" plus
        # padding so toolbar layout doesn't shift as state changes.
        self._cmd_status = QLabel('')
        self._cmd_status.setStyleSheet('padding-right:8px;')
        self._cmd_status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._cmd_status.setFixedWidth(
            self._cmd_status.fontMetrics().horizontalAdvance(
                'COMMAND MODE — ELM11-Feather') + 24)
        tb.addWidget(self._cmd_status)

    @staticmethod
    def _toolbar_spacer(width: int = 12) -> QWidget:
        """A small fixed-width transparent gap for visually grouping toolbar
        buttons. Transparent so it blends with the toolbar background, which
        differs from the default widget background."""
        w = QWidget()
        w.setFixedWidth(width)
        w.setStyleSheet('background: transparent;')
        return w

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _setup_menu(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu('&File')
        fm.addAction(self._act('&New File',       'Ctrl+N',       self._new_file))
        fm.addAction(self._act('&Open File…',     'Ctrl+O',       self._open_file))
        fm.addAction(self._act('Open &Folder…',   None, self._open_folder))
        fm.addSeparator()
        fm.addAction(self._act('&Save',           'Ctrl+S',       self._save_file))
        fm.addAction(self._act('Save &As…',       'Ctrl+Shift+S', self._save_file_as))
        fm.addSeparator()
        fm.addAction(self._act('E&xit',           'Ctrl+Q',       self.close))

        # Edit
        em = mb.addMenu('&Edit')
        em.addAction(self._act('&Undo',  'Ctrl+Z', lambda: self._cur() and self._cur().undo()))
        em.addAction(self._act('&Redo',  'Ctrl+Y', lambda: self._cur() and self._cur().redo()))
        em.addSeparator()
        em.addAction(self._act('Cu&t',   'Ctrl+X', lambda: self._cur() and self._cur().cut()))
        em.addAction(self._act('&Copy',  'Ctrl+C', lambda: self._cur() and self._cur().copy()))
        em.addAction(self._act('&Paste', 'Ctrl+V', lambda: self._cur() and self._cur().paste()))
        em.addSeparator()
        em.addAction(self._act('Select &All', 'Ctrl+A',
                               lambda: self._cur() and self._cur().selectAll()))

        # View
        vm = mb.addMenu('&View')
        self._theme_menu = vm.addMenu('Theme')
        self._rebuild_theme_menu()
        vm.addSeparator()
        self._docs_toggle = QAction('&Documentation Panel', self)
        self._docs_toggle.setCheckable(True)
        self._docs_toggle.setShortcut(QKeySequence('F1'))
        self._docs_toggle.toggled.connect(self._toggle_docs)
        vm.addAction(self._docs_toggle)
        self._split_toggle = QAction('&Split Editor', self)
        self._split_toggle.setCheckable(True)
        self._split_toggle.setShortcut(QKeySequence('F2'))
        self._split_toggle.toggled.connect(self._toggle_split_editor)
        vm.addAction(self._split_toggle)

        # Tools
        tm = mb.addMenu('&Tools')
        tm.addAction(self._act('&Settings…',      'Ctrl+,', self._open_settings))
        tm.addSeparator()
        tm.addAction(self._act('Clear &Terminal', None,      self._terminal.clear))
        tm.addAction(self._act('Clear &Upload Status', None, self._upload_out.clear))
        tm.addAction(self._act('Clear &Build Output', None,  self._build_out.clear))
        tm.addAction(self._act('Clear &Flash Output', None,  self._flash_out.clear))

        # Workspaces
        self._ws_menu = mb.addMenu('&Workspaces')
        self._rebuild_workspaces_menu()

        # Help
        hm = mb.addMenu('&Help')
        hm.addAction(self._act('&About', None, self._about))

    # ── Status bar ────────────────────────────────────────────────────────────

    def _setup_statusbar(self):
        sb = self.statusBar()
        self._sb_conn = QLabel('  Not connected')
        sb.addWidget(self._sb_conn)
        self._sb_mode = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _act(self, name: str, shortcut: str | None, slot) -> QAction:
        a = QAction(name, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        return a

    def _cur(self) -> CodeEditor | None:
        w = self._active_pane.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _refresh_ports(self):
        current = self._port_combo.currentText()
        if not current:
            current = QSettings().value('serial/last_port', '')
        ports = [p.device for p in serial.tools.list_ports.comports()
                 if _port_is_acceptable(p.device)]
        self._port_combo.blockSignals(True)
        self._port_combo.clear()
        self._port_combo.addItems(ports)
        if current in ports:
            self._port_combo.setCurrentText(current)
        self._port_combo.blockSignals(False)

    @property
    def workspace_mode(self) -> str:
        """Current language mode: 'Lua' or 'C'."""
        return self._workspace_mode

    def _set_mode(self, mode: str):
        self._workspace_mode = mode
        if self._sb_mode is None:
            self._sb_mode = QLabel()
            self.statusBar().addPermanentWidget(self._sb_mode)
        self._sb_mode.setText(f'  {mode}  ')
        self._sb_mode.setVisible(True)
        self._docs.set_mode(mode)
        self._update_device_buttons()

    def _set_target(self, target: str):
        """Update the active workspace's target board. The toolbar
        status label is refreshed via `_update_device_buttons` to keep
        device-state / target-board composition in one place."""
        self._workspace_target = target
        self._refresh_status_label()

    def _refresh_status_label(self):
        """Compose the right-side toolbar label from (device state) and
        (target board). Either part may be empty."""
        connected = self._terminal.is_connected
        cmd_active = getattr(self, '_cmd_mode', None) and self._cmd_mode.is_active
        is_c_mode = self._workspace_mode == 'C'
        has_workspace = self._workspace_root is not None
        if connected and not is_c_mode:
            state = 'COMMAND MODE' if cmd_active else 'REPL'
        else:
            state = ''
        target = self._workspace_target if has_workspace else ''
        if state and target:
            self._cmd_status.setText(f'{state} — {target}')
        else:
            self._cmd_status.setText(state or target)

    def _update_device_buttons(self):
        connected = self._terminal.is_connected
        cmd_active = getattr(self, '_cmd_mode', None) and self._cmd_mode.is_active
        is_c_mode = self._workspace_mode == 'C'
        usable = connected and not cmd_active
        # Lua-workflow buttons — only relevant in Lua mode.
        lua_usable = usable and not is_c_mode
        self._upload_btn.setEnabled(lua_usable)
        self._run_btn.setEnabled(lua_usable)
        self._stop_btn.setEnabled(lua_usable)
        # Command Mode is a Lua-only concept — disabled entirely in C mode.
        self._cmd_btn.setEnabled(connected and not is_c_mode)
        self._refresh_status_label()
        # Build / Clean stay always enabled (their handlers validate the
        # workspace + Makefile). Flash is enabled whenever the ELM11 is
        # connected and not held by command mode — its handler validates the
        # workspace + built image.
        self._flash_btn.setEnabled(usable)

    def _on_cmd_btn_toggled(self, checked: bool):
        # Toolbar trigger. Drives device activation; the resulting
        # active_changed (or a snap-back if activation is refused) updates the
        # view via _sync_cmd_mode_ui.
        self._cmd_mode.set_active(checked)
        self._sync_cmd_mode_ui()

    def _on_cmd_mode_active_changed(self, _active: bool):
        # Activation changed (incl. auto-deactivate on disconnect) — refresh
        # everything from the authoritative state.
        self._sync_cmd_mode_ui()
        self._update_device_buttons()

    def _sync_cmd_mode_ui(self):
        """Reconcile the UI with `_cmd_mode.is_active`: keep the toolbar
        button checked-in-sync and swap the centre region to the command panel
        (when active) or back to the editors+bottom (when not)."""
        active = self._cmd_mode.is_active
        if self._cmd_btn.isChecked() != active:
            self._cmd_btn.blockSignals(True)
            self._cmd_btn.setChecked(active)
            self._cmd_btn.blockSignals(False)
        self._center_stack.setCurrentWidget(
            self._cmd_mode if active else self._centre)

    # ── File operations ───────────────────────────────────────────────────────

    def _new_file(self):
        log.debug('New untitled file')
        editor = CodeEditor()
        pane = self._active_pane
        idx = pane.addTab(editor, 'untitled.lua')
        pane.setCurrentIndex(idx)
        editor.document().modificationChanged.connect(
            lambda _: self._refresh_tab_title(editor))

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open File', '',
            'ELM11 files (*.lua *.c *.h);;Lua (*.lua);;C (*.c *.h);;All (*)')
        if path:
            self._open_path(Path(path))

    def _open_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Open Folder')
        if path:
            p = Path(path)
            self._workspace_root = None
            self._tree.set_root(p)
            self.setWindowTitle('BrisbaneSilicon IDE')

    def _open_path(self, path: Path, pane: QTabWidget | None = None):
        log.debug('Open path: %s', path)
        # Avoid duplicate tabs across all panes — focus the existing one.
        for p in self._editor_panes:
            for i in range(p.count()):
                w = p.widget(i)
                if isinstance(w, CodeEditor) and w.file_path == path:
                    p.setCurrentIndex(i)
                    self._active_pane = p
                    return
        editor = CodeEditor()
        editor.set_file(path)
        editor.document().modificationChanged.connect(
            lambda _: self._refresh_tab_title(editor))
        target = pane or self._default_pane_for(path)
        idx = target.addTab(editor, path.name)
        target.setCurrentIndex(idx)
        self._refresh_tab_title(editor)
        self._update_device_buttons()

    def _save_file(self):
        editor = self._cur()
        if not editor:
            return
        log.debug('Save file: %s', editor.file_path or 'untitled')
        if editor.file_path:
            editor.save()
            self._refresh_tab_title(editor)
        else:
            self._save_file_as()

    def _save_file_as(self):
        editor = self._cur()
        if not editor:
            return
        start_dir = str(
            self._tree.selected_dir
            or self._workspace_root
            or Path.home()
        )
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save As', start_dir,
            'Lua (*.lua);;C source (*.c);;C header (*.h);;All (*)')
        if path:
            editor.save_as(Path(path))
            self._refresh_tab_title(editor)

    def _refresh_tab_title(self, editor: CodeEditor):
        found = self._pane_for_editor(editor)
        if found:
            pane, i = found
            name = editor.file_path.name if editor.file_path else 'untitled'
            dot   = ' ●' if editor.document().isModified() else ''
            stale = '' if self._is_build_artifact(editor.file_path) \
                else (' ↑' if editor.is_stale else '')
            pane.setTabText(i, name + dot + stale)
        if editor.file_path:
            self._tree.refresh_decoration(editor.file_path)

    def _editor_for(self, path: Path) -> CodeEditor | None:
        for editor in self._all_editors():
            if editor.file_path == path:
                return editor
        return None

    def _is_build_artifact(self, path: Path | None) -> bool:
        """Suppress the upload/stale marker for anything the IDE deploys
        into `<workspace>/build/` — runtime objects, Makefiles, helpers."""
        if not path or not self._workspace_root:
            return False
        try:
            return path.is_relative_to(self._workspace_root / 'build')
        except (ValueError, OSError):
            return False

    def _file_status(self, path: Path) -> tuple[bool, bool]:
        """Return (dirty, stale) for the given path, used to decorate the tree."""
        editor = self._editor_for(path)
        if editor:
            stale = False if self._is_build_artifact(path) else editor.is_stale
            return (editor.document().isModified(), stale)
        if path.suffix.lower() != '.lua' or self._is_build_artifact(path):
            return (False, False)
        try:
            stored = QSettings().value(_upload_hash_key(path), '')
            text = path.read_text(encoding='utf-8', errors='replace')
            return (False, stored != _content_hash(text))
        except OSError:
            return (False, False)

    def _close_tab(self, index: int):
        pane = self.sender()
        if not isinstance(pane, QTabWidget) or pane not in self._editor_panes:
            pane = self._active_pane
        log.debug('Close tab index=%d  title=%s', index, pane.tabText(index))
        editor = pane.widget(index)
        closed_path = editor.file_path if isinstance(editor, CodeEditor) else None
        if isinstance(editor, CodeEditor) and editor.document().isModified():
            name = pane.tabText(index).rstrip(' ●↑')
            reply = QMessageBox.question(
                self, 'Unsaved Changes', f'Save changes to {name}?',
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                # Make this the active editor so _save_file targets it.
                pane.setCurrentIndex(index)
                self._active_pane = pane
                self._save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        pane.removeTab(index)
        self._tree.refresh_decoration(closed_path)

    def _on_tab_changed(self, _index: int):
        pane = self.sender()
        if isinstance(pane, QTabWidget) and pane in self._editor_panes:
            self._active_pane = pane
        self._update_device_buttons()

    def _close_all_editor_tabs(self):
        """Close every editor tab without prompting. Files that have
        unsaved modifications are saved silently first (untitled buffers
        with no `file_path` are still discarded — saving those would
        require a Save-As dialog we can't safely pop here)."""
        for editor in self._all_editors():
            if editor.document().isModified() and editor.file_path:
                editor.save()
        for pane in self._editor_panes:
            while pane.count():
                pane.removeTab(0)
        self._update_device_buttons()

    # ── Serial connection ─────────────────────────────────────────────────────

    def _toggle_connect(self, checked: bool):
        log.debug('Toggle connect: checked=%s', checked)

        if checked:
            # Connect path requires a port to be selected.
            port = self._port_combo.currentText()
            if not port:
                QMessageBox.warning(self, 'No Port', 'No serial port selected.')
                self._connect_btn.setChecked(False)
                return
            self._terminal.connect_to_port(port, SettingsDialog.baud())
            self._bottom.setCurrentWidget(self._terminal)
        else:
            # Disconnect path runs regardless of whether the original port
            # is still present (e.g. the user already physically unplugged
            # the ELM11 and it has dropped out of the combo). Use whatever
            # port the worker is holding open, or fall back to whatever is
            # selected — both are fine for the SerialTerminal's tear-down.
            worker = self._terminal.get_worker()
            port = worker.port if worker else self._port_combo.currentText()
            self._terminal.disconnect_port(port)

    def _on_connection_changed(self, connected: bool):
        log.debug('Connection changed: connected=%s', connected)
        self._connect_btn.setChecked(connected)
        self._connect_btn.setText('Disconnect' if connected else 'Connect')
        t = theme.current()
        if connected:
            port = self._port_combo.currentText()
            self._sb_conn.setText(f'  Connected: {port} @ {SettingsDialog.baud()}')
            self.statusBar().setStyleSheet(
                f"background:{t['status_on_bg']}; color:{t['status_on_fg']};")
        else:
            self._sb_conn.setText('  Not connected')
            self.statusBar().setStyleSheet(
                f"background:{t['status_bg']}; color:{t['status_fg']};")
        self._port_combo.setEnabled(not connected)
        self._update_device_buttons()

    # ── Device actions ────────────────────────────────────────────────────────

    def _upload(self):
        log.debug('Upload triggered')
        editor = self._cur()
        if not editor or not editor.file_path:
            QMessageBox.warning(self, 'No File',
                'Open a file to begin the Upload process.')
            return
        if editor.document().isModified():
            editor.save()

        lua_file  = str(editor.file_path)
        prog_name = editor.file_path.name
        self._upload_editor = editor

        worker = self._terminal.get_worker()
        if not worker or not worker.serial_port:
            return
        if not _port_is_acceptable(worker.port):
            QMessageBox.warning(self, 'Unsupported Port',
                f'The program uploader only supports /dev/ttyUSB* on Linux.\n'
                f'Currently connected to: {worker.port}')
            return
        # If the originally connected port has disappeared (e.g. board was
        # replugged), silently switch to whichever ttyUSB is available now.
        target = _resolve_upload_port(worker.port)
        if not target:
            QMessageBox.warning(self, 'No USB Port',
                'No /dev/ttyUSB* device is currently present.')
            return
        if target != worker.port:
            log.debug('Upload: %s no longer present, switching to %s',
                      worker.port, target)
            self._terminal.release_port()
            self._terminal.reacquire_port(target, SettingsDialog.baud())
            worker = self._terminal.get_worker()
            if not worker or not worker.serial_port:
                return

        # Switch to Upload Status tab immediately
        self._upload_out._append('\n--- Upload Begin ---\n\n', theme.current()['term_fg'])
        self._upload_out._append('Enter COMMAND mode...\n', theme.current()['term_fg'])
        self._bottom.setCurrentWidget(self._upload_out)

        # Enter Command Mode, then trigger the upload sequence
        worker.send(b'\ncmd\n')
        QTimer.singleShot(500, lambda: self._do_upload_step2(
            worker, prog_name, lua_file))

    def _do_upload_step2(self, worker, prog_name, lua_file):
        log.debug('Upload step 2: sending upload command for %s', prog_name)
        # Start capturing serial data to detect "Program already exists"
        self._upload_capture = b''
        worker.data_received.connect(self._capture_upload_response)
        worker.send(f'upload|program("{prog_name}")\n'.encode())
        QTimer.singleShot(500, lambda: self._do_upload_step3(
            worker, prog_name, lua_file))

    def _capture_upload_response(self, data: bytes):
        """Temporarily buffer serial data to check for overwrite prompt."""
        self._upload_capture += data

    def _do_upload_step3(self, worker, prog_name, lua_file):
        log.debug('Upload step 3: checking for overwrite prompt')
        # Stop capturing
        try:
            worker.data_received.disconnect(self._capture_upload_response)
        except TypeError:
            pass

        captured = self._upload_capture.decode('utf-8', errors='replace')
        self._upload_capture = b''
        log.debug('Upload capture: %r', captured)

        if 'already exists' in captured.lower():
            reply = QMessageBox.question(
                self, 'Program Already Exists',
                f'"{prog_name}" already exists on the ELM11.\n\n'
                'Overwrite it?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                worker.send(b'y')
                QTimer.singleShot(300, lambda: self._do_upload_start(
                    worker, lua_file))
            else:
                worker.send(b'n')
            return

        self._do_upload_start(worker, lua_file)

    def _do_upload_start(self, worker, lua_file):
        log.debug('Upload step 4: pausing serial worker, starting uploader')
        worker.pause()

        self._uploader = UploaderWorker(worker.serial_port, lua_file)
        self._uploader.progress.connect(self._on_upload_progress)
        self._uploader.finished_ok.connect(self._on_upload_ok)
        self._uploader.finished_err.connect(self._on_upload_err)
        self._uploader.finished.connect(self._on_uploader_thread_done)
        self._uploader.start()

    def _on_upload_progress(self, msg: str):
        self._upload_out._append(msg, theme.current()['term_fg'])

    def _on_upload_ok(self):
        log.debug('Upload OK')
        self._upload_out._append('\n--- Upload Complete ---\n',
                                 theme.current()['term_success'])
        if self._upload_editor:
            self._upload_editor.mark_uploaded()
            self._refresh_tab_title(self._upload_editor)
        self._upload_done()

    def _on_upload_err(self, reason: str):
        log.debug('Upload Error')
        self._upload_out._append(f'\n--- Upload Failed: {reason} ---\n',
                                  theme.current()['term_error'])
        self._upload_done()

    def _upload_done(self):
        log.debug('Upload Done')
        worker = self._terminal.get_worker()
        if worker:
            worker.resume()
            worker.send(b'exit\n')

    def _on_uploader_thread_done(self):
        """Called when the uploader thread has fully exited run()."""
        self._uploader = None

    def _on_build_finished(self, exit_code: int):
        """Handle C build completion (future use)."""
        log.debug('Build finished: exit_code=%d', exit_code)

    def _run_program(self):
        editor = self._cur()
        if not editor or not editor.file_path:
            QMessageBox.warning(self, 'No File',
                'Open a file to begin the Run process.')
            return
        prog_name = editor.file_path.name
        worker = self._terminal.get_worker()
        if worker:
            worker.send(f'run_program("{prog_name}")\n'.encode())
        self._bottom.setCurrentWidget(self._terminal)

    def _stop_program(self):
        worker = self._terminal.get_worker()
        if worker:
            worker.send(b'q\n')
        self._bottom.setCurrentWidget(self._terminal)

    def _toggle_outer_pane(self, idx: int, checked: bool,
                           min_w: int, setting_key: str):
        sizes = self._outer.sizes()
        widget = self._outer.widget(idx)
        if checked:
            widget.setVisible(True)
            if sizes[idx] == 0:
                pane_w = max(min_w, sum(sizes) // 3)
                centre = max(300, sizes[1] - pane_w)
                sizes[1] = centre
                sizes[idx] = pane_w
                self._outer.setSizes(sizes)
        else:
            pane_w = sizes[idx]
            widget.setVisible(False)
            if pane_w > 0:
                sizes[1] += pane_w
                sizes[idx] = 0
                self._outer.setSizes(sizes)
        QSettings().setValue(setting_key, checked)

    def _toggle_docs(self, checked: bool):
        self._toggle_outer_pane(2, checked, 320, 'ui/docs_visible')

    def _open_example(self, filename: str, code: str):
        """Open an embLua example program in a new editor tab."""
        editor = CodeEditor()
        editor.setPlainText(code)
        editor.document().setModified(True)
        pane = self._active_pane
        idx = pane.addTab(editor, filename)
        pane.setCurrentIndex(idx)
        editor.document().modificationChanged.connect(
            lambda _: self._refresh_tab_title(editor))
        self._refresh_tab_title(editor)
        self._update_device_buttons()

    def _build_make_dir(self) -> Path:
        """Directory holding the workspace's Makefile. C workspaces deploy it
        to `<ws>/build/make`; Lua workspaces nest the C build system under
        `<ws>/embLua/build/make`."""
        if self._workspace_mode == 'C':
            return self._workspace_root / 'build' / 'make'
        return self._workspace_root / 'embLua' / 'build' / 'make'

    def _build_out_dir(self) -> Path:
        """Directory holding the build's memory image (`<proj>.v`). C
        workspaces emit it to `<ws>/build/out`; Lua workspaces nest the C
        build system under `<ws>/embLua/build/out`."""
        if self._workspace_mode == 'C':
            return self._workspace_root / 'build' / 'out'
        return self._workspace_root / 'embLua' / 'build' / 'out'

    def _build(self):
        if self._workspace_root is None:
            QMessageBox.warning(self, 'No Workspace',
                'Open a workspace to build.')
            return
        make_dir = self._build_make_dir()
        makefile = make_dir / 'Makefile'
        if not makefile.is_file():
            QMessageBox.warning(self, 'Missing Makefile',
                f'No Makefile found at:\n{makefile}\n\n'
                "The C build templates don't appear to be deployed.")
            return
        # Save any in-flight edits before invoking make.
        editor = self._cur()
        if editor and editor.file_path and editor.document().isModified():
            editor.save()
        compiler = SettingsDialog.compiler_path()
        if not compiler:
            QMessageBox.warning(self, 'No C Compiler',
                'Set the compiler path in Settings → C.')
            return

        toolchain_root = _msys_path(Path(compiler).resolve())
        make_prog, make_env = _make_invocation()
        self._build_out.clear()
        self._bottom.setCurrentWidget(self._build_out)
        self._build_out.run_command(
            make_prog,
            ['-C', _msys_path(make_dir), f'RISCV_PATH={toolchain_root}'],
            cwd=str(self._workspace_root),
            env=make_env)

    def _clean(self):
        if self._workspace_root is None:
            QMessageBox.warning(self, 'No Workspace',
                'Open a workspace to clean.')
            return
        make_dir = self._build_make_dir()
        makefile = make_dir / 'Makefile'
        if not makefile.is_file():
            QMessageBox.warning(self, 'Missing Makefile',
                f'No Makefile found at:\n{makefile}')
            return
        make_prog, make_env = _make_invocation()
        self._build_out.clear()
        self._bottom.setCurrentWidget(self._build_out)
        self._build_out.run_command(
            make_prog,
            ['-C', _msys_path(make_dir), 'clean'],
            cwd=str(self._workspace_root),
            env=make_env)

    def _flash(self):
        if self._workspace_root is None:
            QMessageBox.warning(self, 'No Workspace',
                'Open a workspace to flash.')
            return
        if not self._terminal.is_connected:
            QMessageBox.warning(self, 'Not Connected',
                'Connect to the ELM11 before flashing.')
            return
        worker = self._terminal.get_worker()
        if worker and not _port_is_acceptable(worker.port):
            QMessageBox.warning(self, 'Unsupported Port',
                f'The firmware uploader only supports /dev/ttyUSB* on Linux.\n'
                f'Currently connected to: {worker.port}')
            return
        # Disconnect the USB / COM port immediately — as soon as Flash is
        # clicked, the IDE should let go so the user can begin the
        # unplug/replug cycle. Subsequent file-existence checks reacquire
        # the port silently if they bail out.
        held = self._terminal.release_port()
        if not held:
            QMessageBox.warning(self, 'Not Connected',
                'Connection dropped before flashing could start. '
                'Reconnect and try again.')
            return
        self._flash_held_port = held

        def _abort_and_reacquire():
            self._terminal.reacquire_port(held, SettingsDialog.baud())
            self._flash_held_port = ''

        # Locate the bundled firmware uploader and the Memory image.
        if hasattr(sys, '_MEIPASS'):
            uploader = Path(sys._MEIPASS) / 'brs_ide' / 'firmware_uploader.py'
        else:
            uploader = Path(__file__).resolve().parent / 'firmware_uploader.py'
        if not uploader.is_file():
            QMessageBox.warning(self, 'Missing Firmware Uploader',
                f'firmware_uploader.py not found at:\n{uploader}')
            _abort_and_reacquire()
            return
        v_file = self._build_out_dir() / f'{self._workspace_root.name}.v'
        if not v_file.is_file():
            QMessageBox.warning(self, 'No Build Output',
                f'Memory image not found:\n{v_file}\n\n'
                'Run Build first.')
            _abort_and_reacquire()
            return
        # Walk the user through putting the board in flash-mode.
        reply = QMessageBox.information(
            self, 'Prepare ELM11 for Flash',
            'Unplug-Plug the ELM11 while holding BTN2, ensuring LEDs 1-3 '
            'remain illuminated after releasing BTN2.',
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok)
        if reply != QMessageBox.StandardButton.Ok:
            # Cancel: silently restore the connection we just released.
            _abort_and_reacquire()
            return
        # Wait for the device to re-enumerate as a USB serial port. The
        # dialog blocks the next step (the firmware uploader subprocess)
        # while polling, but the user can cancel; a 5 s timeout protects
        # against forgotten replugs.
        self._wait_for_target_port(uploader, v_file)

    _FLASH_MAX_ATTEMPTS    = 2
    _FLASH_RETRY_DELAY_MS  = 1000
    _PORT_WAIT_TIMEOUT_MS  = 5000
    _PORT_WAIT_POLL_MS     = 250

    def _wait_for_target_port(self, uploader: Path, v_file: Path):
        """Poll for an acceptable USB port. Show a modal dialog with a
        Cancel button while waiting; on success, kick off the firmware
        uploader; on cancel/timeout, warn the user and reacquire the
        previously-held port."""
        held = getattr(self, '_flash_held_port', '')

        # Modal dialog with a Cancel button. We poll outside the dialog
        # via a QTimer so the dialog can be dismissed asynchronously.
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle('Waiting for ELM11')
        dlg.setStyleSheet(theme.dialog_stylesheet(theme.current()))
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel('Waiting for the ELM11 to enumerate as a serial port…'))
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(dlg.reject)
        v.addWidget(cancel_btn)

        timer = QTimer(self)
        elapsed = [0]
        outcome: dict = {'kind': None, 'port': ''}

        def _poll():
            target = _resolve_upload_port(held)
            if target:
                outcome['kind'], outcome['port'] = 'ok', target
                timer.stop()
                dlg.accept()
                return
            elapsed[0] += self._PORT_WAIT_POLL_MS
            if elapsed[0] >= self._PORT_WAIT_TIMEOUT_MS:
                outcome['kind'] = 'timeout'
                timer.stop()
                dlg.reject()

        timer.timeout.connect(_poll)
        timer.start(self._PORT_WAIT_POLL_MS)
        dlg.exec()
        timer.stop()

        if outcome['kind'] == 'ok':
            self._proceed_with_flash(uploader, v_file, outcome['port'])
            return

        # Cancel or timeout — silently restore the connection.
        if outcome['kind'] == 'timeout':
            QMessageBox.warning(self, 'No USB Port',
                f'No acceptable USB serial port appeared within '
                f'{self._PORT_WAIT_TIMEOUT_MS // 1000}s.')
        if held:
            self._terminal.reacquire_port(held, SettingsDialog.baud())
        self._flash_held_port = ''

    def _proceed_with_flash(self, uploader: Path, v_file: Path, target_port: str):
        self._flash_out.clear()
        self._bottom.setCurrentWidget(self._flash_out)
        try:
            self._flash_out.build_finished.disconnect(self._on_flash_finished)
        except TypeError:
            pass
        self._flash_out.build_finished.connect(self._on_flash_finished)
        # Cache the args so retries can re-issue the same call.
        self._flash_attempt = 0
        self._flash_run_args = (
            sys.executable,
            [str(uploader), str(v_file), target_port, '115200'],
            str(self._workspace_root),
        )
        # Give the OS a moment to actually release the port before the
        # firmware uploader tries to open it.
        QTimer.singleShot(500, self._invoke_firmware_uploader)

    def _invoke_firmware_uploader(self):
        if not getattr(self, '_flash_run_args', None):
            return
        self._flash_attempt += 1
        prog, args, cwd = self._flash_run_args
        # First attempt clears the panel; retries keep the previous
        # attempt's failure log visible.
        self._flash_out.run_command(
            prog, args, cwd=cwd, clear=(self._flash_attempt == 1))

    def _on_flash_finished(self, code: int):
        # Retry up to MAX_ATTEMPTS times on a non-zero exit.
        if code != 0 and self._flash_attempt < self._FLASH_MAX_ATTEMPTS:
            log.debug('Flash attempt %d failed (exit %d) — retrying',
                      self._flash_attempt, code)
            QTimer.singleShot(self._FLASH_RETRY_DELAY_MS,
                              self._invoke_firmware_uploader)
            return

        # Final outcome — disconnect the hook and reacquire the port.
        try:
            self._flash_out.build_finished.disconnect(self._on_flash_finished)
        except TypeError:
            pass
        self._flash_run_args = None
        held = getattr(self, '_flash_held_port', '')
        self._flash_held_port = ''
        if not held:
            return

        def _reconnect():
            # The device may re-enumerate after flashing, so re-resolve.
            target = _resolve_upload_port(held)
            if target:
                self._terminal.reacquire_port(target, SettingsDialog.baud())

        # Brief delay so the device is ready post-flash before we reopen.
        QTimer.singleShot(800, _reconnect)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _rebuild_theme_menu(self):
        self._theme_menu.clear()
        names = theme.theme_names()
        ids   = theme.theme_ids()
        cur   = theme.current()['name']
        for name, tid in zip(names, ids):
            act = self._theme_menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(tid == cur)
            act.triggered.connect(lambda checked, t=tid: self._switch_theme(t))

    def _switch_theme(self, name: str):
        theme.set_theme(name)
        self._apply_theme()

    def _apply_theme(self):
        t = theme.current()
        self.setStyleSheet(theme.main_stylesheet(t))
        self._tree.apply_theme()
        self._terminal.apply_theme()
        self._upload_out.apply_theme()
        self._build_out.apply_theme()
        self._docs.apply_theme()
        self._cmd_mode.apply_theme()
        for editor in self._all_editors():
            editor.apply_theme()
        self._on_connection_changed(self._terminal.is_connected)
        self._rebuild_theme_menu()

    # ── Workspaces ────────────────────────────────────────────────────────────

    def _load_workspace(self, path: Path):
        """Switch the tree root to path and persist it in the workspace history."""
        log.debug('Load workspace: %s', path)
        # Persist the outgoing workspace's open files before we swap roots.
        self._save_workspace_tabs()
        self._workspace_root = path

        s = QSettings()
        mode_key = f'workspaces/mode/{path}'
        target_key = f'workspaces/target/{path}'
        saved_mode = s.value(mode_key, None)
        is_new_workspace = saved_mode is None

        # Opening a workspace (new or existing) shows the root expanded with
        # all nested folders collapsed — no full auto-expand cascade.
        self._tree.set_root(path, is_workspace=True, auto_expand=False)
        self.setWindowTitle(f'BrisbaneSilicon IDE — {path.name}')

        raw = s.value('workspaces/history', [])
        # QSettings may return a string instead of list when there's only one entry
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
        entry = str(path)
        if entry in history:
            history.remove(entry)
        history.insert(0, entry)
        history = history[:10]          # keep the 10 most recent
        s.setValue('workspaces/history', history)

        # Restore or choose mode + target board for this workspace
        if is_new_workspace:
            target, mode = self._prompt_new_workspace_config(path.name)
            s.setValue(mode_key, mode)
            s.setValue(target_key, target)
            saved_mode = mode
        else:
            target = s.value(target_key, 'ELM11')
        self._set_target(target)
        self._set_mode(saved_mode)

        # Deploy the build-system templates into a brand-new workspace.
        # Both Lua and C workspaces get their language-specific build/ and
        # runtime/ trees seeded from the IDE's bundle.
        if is_new_workspace:
            self._deploy_build_templates(path, saved_mode.lower())

        self._rebuild_workspaces_menu()
        self._restore_workspace_tabs(path)

    def _prompt_new_workspace_config(self, name: str) -> tuple[str, str]:
        """Ask the user to pick a Target Board and Language Mode for a
        freshly-opened workspace. Returns `(target_board, mode)`.
        Cancelling the dialog falls back to the safe defaults
        (`ELM11`, `Lua`)."""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QComboBox,
            QDialogButtonBox, QLabel,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle('New Workspace')
        dlg.setStyleSheet(theme.dialog_stylesheet(theme.current()))
        dlg.setMinimumWidth(360)
        root = QVBoxLayout(dlg)
        root.addWidget(QLabel(f'Configure workspace  {name}:'))

        form = QFormLayout()
        target_combo = QComboBox()
        target_combo.addItems(['ELM11', 'ELM11-Feather'])
        form.addRow('Target Board:', target_combo)

        mode_combo = QComboBox()
        mode_combo.addItems(['Lua', 'C'])
        form.addRow('Language Mode:', mode_combo)
        root.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        root.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return ('ELM11', 'Lua')
        return (target_combo.currentText(), mode_combo.currentText())

    def _deploy_build_templates(self, workspace: Path, lang: str):
        """Seed a freshly-created workspace with the bundled templates for
        `lang` ('c' or 'lua'), sourced from `brs_ide/elm11/<lang>/`. Files
        are laid out as:

          * `<workspace>/*.c`               — starter user source
          * `<workspace>/build/runtime/`    — prebuilt runtime objects
          * `<workspace>/build/make/`       — Makefile / linker / startup
          * `<workspace>/build/header/`     — bundled C headers
          * `<workspace>/build/utilities/`  — helper Python scripts

        Existing files at the destinations are overwritten so the
        deployed templates always reflect the IDE's current bundle."""
        import shutil

        # Lua workspaces nest every deployed artefact under an `embLua/`
        # subdirectory; C workspaces deploy straight into the workspace root.
        dest_root = workspace / 'embLua' if lang == 'lua' else workspace

        def _target_for(src: Path) -> Path:
            """Where does a build-template file go? Rooted on `dest_root`."""
            if src.suffix == '.c':
                return dest_root / src.name
            if src.suffix == '.py':
                return dest_root / 'build' / 'utilities' / src.name
            if src.suffix == '.h':
                return dest_root / 'build' / 'header' / src.name
            # `.S` startup files, Makefile, linker script, etc. all sit in
            # the make/ directory.
            return dest_root / 'build' / 'make' / src.name

        plan: list[tuple[Path, Path]] = []   # (source, destination)
        build_src = _ide_data_dir(f'elm11/{lang}/build')
        if build_src.is_dir():
            for src in build_src.iterdir():
                if src.is_file() and not src.name.startswith('.'):
                    plan.append((src, _target_for(src)))
        runtime_src = _ide_data_dir(f'elm11/{lang}/runtime')
        if runtime_src.is_dir():
            for src in runtime_src.iterdir():
                if src.is_file() and not src.name.startswith('.'):
                    plan.append((src, dest_root / 'build' / 'runtime' / src.name))

        import re
        for src, dst in plan:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                log.warning('Could not create %s: %s', dst.parent, exc)
                continue
            try:
                if src.name == 'Makefile':
                    # Substitute the placeholder PROJ_NAME with the workspace
                    # directory name so the emitted artefacts are named after
                    # the project rather than a generic "NONE".
                    content = src.read_text(encoding='utf-8')
                    content = re.sub(
                        r'^(PROJ_NAME\s*:=\s*)\S+',
                        lambda m: f'{m.group(1)}{workspace.name}',
                        content,
                        count=1,
                        flags=re.MULTILINE,
                    )
                    dst.write_text(content, encoding='utf-8')
                    shutil.copymode(src, dst)
                else:
                    shutil.copy2(src, dst)
                log.debug('Deployed %s -> %s', src, dst)
            except OSError as exc:
                log.warning('Could not deploy %s: %s', src, exc)

    # ── Per-workspace tab persistence ─────────────────────────────────────

    def _save_workspace_tabs(self):
        """Record each pane's open files + active tab, plus which pane was
        active, under the current workspace's QSettings keys. No-op when no
        workspace is open."""
        if self._workspace_root is None:
            return
        s = QSettings()
        ws = self._workspace_root
        s.setValue(f'workspaces/pane_count/{ws}', len(self._editor_panes))
        try:
            active = self._editor_panes.index(self._active_pane)
        except ValueError:
            active = 0
        s.setValue(f'workspaces/active_pane/{ws}', active)
        for pi, pane in enumerate(self._editor_panes):
            files: list[str] = []
            for i in range(pane.count()):
                w = pane.widget(i)
                if isinstance(w, CodeEditor) and w.file_path:
                    files.append(str(w.file_path))
            s.setValue(f'workspaces/open_files/{ws}/{pi}', files)
            s.setValue(f'workspaces/active_tab/{ws}/{pi}', pane.currentIndex())

    def _save_tree_state(self):
        """Persist the current workspace tree's expanded-folder state so the
        next IDE launch can restore it. Captured only here (on IDE close) and
        only for the active workspace — switching workspaces does not save."""
        if self._workspace_root is None:
            return
        QSettings().setValue(
            f'tree/expanded/{self._workspace_root}',
            self._tree.expanded_dirs())

    def _restore_workspace_tabs(self, path: Path):
        """Clear all panes, set the pane count for the current mode, then
        re-open each pane's recorded files (with its active tab) and select
        the previously-active pane."""
        s = QSettings()
        ws = path
        # Clear every pane first (directly — bypasses the unsaved-changes
        # prompt; users should save before switching) so the pane-count
        # adjustment never shuffles stale tabs between panes.
        for pane in self._editor_panes:
            while pane.count():
                pane.removeTab(0)
        # Honour the layout saved for this workspace; fall back to the mode
        # default (Lua=2) for a workspace that has never been saved.
        raw_pc = s.value(f'workspaces/pane_count/{ws}', None)
        try:
            pane_count = (int(raw_pc) if raw_pc is not None
                          else self._pane_count_for_mode())
        except (TypeError, ValueError):
            pane_count = self._pane_count_for_mode()
        self._set_pane_count(pane_count)

        def _as_list(raw):
            return (list(raw) if isinstance(raw, (list, tuple))
                    else ([raw] if raw else []))

        for pi, pane in enumerate(self._editor_panes):
            raw = s.value(f'workspaces/open_files/{ws}/{pi}', None)
            # Back-compat with the pre-multipane single-list key (pane 0).
            if raw is None and pi == 0:
                raw = s.value(f'workspaces/open_files/{ws}', [])
            for f in _as_list(raw):
                p = Path(f)
                if p.is_file():
                    self._open_path(p, pane=pane)
            try:
                idx = int(s.value(f'workspaces/active_tab/{ws}/{pi}', 0))
            except (TypeError, ValueError):
                idx = 0
            if 0 <= idx < pane.count():
                pane.setCurrentIndex(idx)

        try:
            ap = int(s.value(f'workspaces/active_pane/{ws}', 0))
        except (TypeError, ValueError):
            ap = 0
        if 0 <= ap < len(self._editor_panes):
            self._active_pane = self._editor_panes[ap]

    def _rebuild_workspaces_menu(self):
        self._ws_menu.clear()
        self._ws_menu.addAction(self._act('Open Workspace…', 'Ctrl+Shift+O', self._open_folder))
        self._ws_menu.addAction(self._act('Close Workspace',  None,           self._close_workspace))
        self._ws_menu.addSeparator()

        s = QSettings()
        raw = s.value('workspaces/history', [])
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])

        if history:
            for entry in history:
                p = Path(entry)
                sub = self._ws_menu.addMenu(p.name)
                sub.setToolTipsVisible(True)
                sub.setTitle(p.name)

                open_act = sub.addAction('Open')
                open_act.setData(entry)
                open_act.triggered.connect(lambda checked, _p=p: self._load_workspace(_p))

                remove_act = sub.addAction('Delete')
                remove_act.triggered.connect(lambda checked, _e=entry: self._remove_workspace(_e))

                # Show full path as tooltip on the submenu title item
                sub.hovered.connect(self._show_workspace_tooltip)
                title_act = sub.menuAction()
                title_act.setData(entry)

            self._ws_menu.hovered.connect(self._show_workspace_tooltip)
            self._ws_menu.addSeparator()
            self._ws_menu.addAction(self._act('Delete All Workspaces', None, self._clear_workspace_history))
        else:
            no_ws = self._ws_menu.addAction('(no recent workspaces)')
            no_ws.setEnabled(False)

    def _close_workspace(self):
        self._save_workspace_tabs()
        self._workspace_root = None
        self._tree.set_root(Path.home())
        self.setWindowTitle('BrisbaneSilicon IDE')
        if self._sb_mode:
            self._sb_mode.setVisible(False)
        self._workspace_target = ''
        self._refresh_status_label()
        self._update_device_buttons()
        # Tear down any active serial connection and clear the editor.
        # Disconnect first — the resulting `_on_connection_changed(False)`
        # will close tabs via its own hook; the explicit call covers the
        # already-disconnected case.
        if self._terminal.is_connected:
            self._terminal.disconnect_port(self._port_combo.currentText())
        self._close_all_editor_tabs()

    def _show_workspace_tooltip(self, action: QAction):
        full_path = action.data()
        if full_path:
            QToolTip.showText(QCursor.pos(), full_path)
        else:
            QToolTip.hideText()

    def _remove_workspace(self, entry: str):
        s = QSettings()
        raw = s.value('workspaces/history', [])
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
        if entry in history:
            history.remove(entry)
        s.setValue('workspaces/history', history)
        s.remove(f'workspaces/mode/{entry}')
        s.remove(f'workspaces/target/{entry}')
        s.remove(f'workspaces/open_files/{entry}')
        s.remove(f'workspaces/active_tab/{entry}')
        s.remove(f'workspaces/pane_count/{entry}')
        s.remove(f'workspaces/active_pane/{entry}')
        s.remove(f'tree/expanded/{entry}')
        # Close if it's the current workspace, and clear out its open tabs.
        if self._workspace_root and str(self._workspace_root) == entry:
            self._close_workspace()
        if self._terminal.is_connected:
            self._terminal.disconnect_port(self._port_combo.currentText())
        self._close_all_editor_tabs()
        self._rebuild_workspaces_menu()

    def _clear_workspace_history(self):
        s = QSettings()
        # Remove all per-workspace keys
        raw = s.value('workspaces/history', [])
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
        for entry in history:
            s.remove(f'workspaces/mode/{entry}')
            s.remove(f'workspaces/target/{entry}')
            s.remove(f'workspaces/open_files/{entry}')
            s.remove(f'workspaces/active_tab/{entry}')
            s.remove(f'workspaces/pane_count/{entry}')
            s.remove(f'workspaces/active_pane/{entry}')
            s.remove(f'tree/expanded/{entry}')
        s.remove('workspaces/history')
        self._close_workspace()
        self._rebuild_workspaces_menu()

    # ── Settings / About ──────────────────────────────────────────────────────

    def _open_settings(self):
        if SettingsDialog(self).exec():
            self._update_device_buttons()
            # Re-apply font to all open editors
            for editor in self._all_editors():
                editor.apply_theme()

    def _about(self):
        QMessageBox.about(self, 'ELM11 IDE',
            '<b>ELM11 IDE</b><br>'
            'An IDE for the ELM11 Embedded Lua Machine<br><br>'
            '© BrisbaneSilicon<br>'
            'brisbanesilicon.com.au')

    # ── Window state ──────────────────────────────────────────────────────────

    def _restore_workspace(self):
        s = QSettings()
        raw = s.value('workspaces/history', [])
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
        log.debug('Workspace history: %s', history)
        if history:
            p = Path(history[0])
            if p.is_dir():
                log.debug('Restoring workspace: %s', p)
                self._workspace_root = p
                # Restore with the root expanded, then re-apply the folder
                # open/closed state saved when the IDE last closed (falling
                # back to "subfolders collapsed" when none was saved).
                self._tree.set_root(p, is_workspace=True, auto_expand=False)
                raw = s.value(f'tree/expanded/{p}', [])
                expanded = (list(raw) if isinstance(raw, (list, tuple))
                            else ([raw] if raw else []))
                if expanded:
                    self._tree.restore_expanded(expanded)
                self.setWindowTitle(f'BrisbaneSilicon IDE — {p.name}')
                saved_mode = s.value(f'workspaces/mode/{p}', 'Lua')
                self._set_target(s.value(f'workspaces/target/{p}', 'ELM11'))
                self._set_mode(saved_mode)
                self._restore_workspace_tabs(p)
            else:
                log.debug('Workspace dir no longer exists: %s', p)
        else:
            log.debug('No workspaces in history')

    def _restore_geometry(self):
        s = QSettings()
        if s.contains('window/width'):
            saved_w = int(s.value('window/width'))
            saved_h = int(s.value('window/height'))
            saved_screen = s.value('window/screen', '')
            log.debug('Saved window: %d x %d  screen: %s', saved_w, saved_h, saved_screen)

            # Find the saved screen and move the window there
            target = None
            if saved_screen:
                for scr in QApplication.screens():
                    if scr.name() == saved_screen:
                        target = scr
                        break

            if target:
                geom = target.availableGeometry()
                # Place at center of the target screen
                x = geom.x() + (geom.width() - saved_w) // 2
                y = geom.y() + (geom.height() - saved_h) // 2
                log.debug('Moving to screen %s at (%d, %d)', target.name(), x, y)
                self.move(x, y)

            def _apply():
                screen = self.screen().availableGeometry()
                max_w = int(screen.width() * 0.95)
                max_h = int(screen.height() * 0.95)
                w = min(saved_w, max_w)
                h = min(saved_h, max_h)
                log.debug('Applying window size: %d x %d  (max: %d x %d, screen: %s)',
                          w, h, max_w, max_h, self.screen().name())
                self.resize(w, h)

            QTimer.singleShot(200, _apply)
        else:
            log.debug('No saved window size found')

    def closeEvent(self, event):
        if any(e.document().isModified() for e in self._all_editors()):
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'There are unsaved changes. Exit anyway?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        self._save_workspace_tabs()
        self._save_tree_state()
        self._cmd_mode.shutdown()
        port = self._port_combo.currentText()
        if port:
            self._terminal.disconnect_port(port)

        s = QSettings()
        screen = self.screen().availableGeometry()
        max_w = int(screen.width() * 0.95)
        max_h = int(screen.height() * 0.95)
        w = min(self.width(), max_w)
        h = min(self.height(), max_h)
        log.debug('Saving window size: %d x %d  (max: %d x %d, screen: %s)',
                  w, h, max_w, max_h, self.screen().name())
        log.debug('Settings file: %s', s.fileName())
        s.setValue('window/width',  w)
        s.setValue('window/height', h)
        s.setValue('window/screen', self.screen().name())
        s.setValue('serial/last_port', self._port_combo.currentText())
        s.sync()
        log.debug('Settings synced to disk')
        event.accept()
