"""Main application window."""
import logging
log = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QSplitter, QTabWidget, QToolBar,
    QFileDialog, QMessageBox, QComboBox, QPushButton, QLabel,
    QWidget, QSizePolicy,
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
    """Resolve a bundled data directory (`elm11_ide/<name>/`) for dev,
    PyInstaller, and system-install layouts."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'elm11_ide' / name
    return Path(__file__).resolve().parent / name


def _c_runtime_objects() -> list[str]:
    """Return every `*.o` file shipped in `elm11_ide/c_runtime/`."""
    base = _ide_data_dir('c_runtime')
    if not base.is_dir():
        return []
    return sorted(str(p) for p in base.glob('*.o'))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log.debug('MainWindow init')
        self.setWindowTitle('ELM11 IDE')
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(theme.main_stylesheet(theme.current()))

        self._workspace_root: Path | None = None
        self._workspace_mode: str = 'Lua'

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
        if QSettings().value('ui/cmd_mode_visible', False, type=bool):
            self._cmd_toggle.setChecked(True)

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

        # Centre: editor on top, bottom panel below
        centre = QSplitter(Qt.Orientation.Vertical)
        self._outer.addWidget(centre)

        self._editor_tabs = QTabWidget()
        self._editor_tabs.setTabsClosable(True)
        self._editor_tabs.tabCloseRequested.connect(self._close_tab)
        self._editor_tabs.currentChanged.connect(self._on_tab_changed)
        centre.addWidget(self._editor_tabs)

        self._bottom = QTabWidget()
        self._terminal = SerialTerminal()
        self._terminal.connected.connect(self._on_connection_changed)
        self._upload_out = BuildOutput()
        self._build_out = BuildOutput()
        self._build_out.build_finished.connect(self._on_build_finished)
        self._bottom.addTab(self._terminal, 'Serial Terminal')
        self._bottom.addTab(self._upload_out, 'Upload Status')
        self._bottom.addTab(self._build_out, 'Build Output')
        centre.addWidget(self._bottom)
        centre.setChildrenCollapsible(False)

        # Middle-right: toggleable command-mode panel (left of docs)
        self._cmd_mode = CommandModePanel()
        self._cmd_mode.set_terminal(self._terminal)
        self._cmd_mode.active_changed.connect(self._on_cmd_mode_active_changed)
        self._cmd_mode.setMinimumWidth(280)
        self._cmd_mode.setVisible(False)
        self._outer.addWidget(self._cmd_mode)

        # Right-most: toggleable documentation panel
        self._docs = DocsPanel()
        self._docs.open_example.connect(self._open_example)
        self._docs.setMinimumWidth(240)
        self._docs.setVisible(False)
        self._outer.addWidget(self._docs)

        self._outer.setSizes([200, 900, 0, 0])
        centre.setSizes([520, 200])

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
        self._build_btn.setEnabled(False)
        tb.addWidget(self._build_btn)

        self._flash_btn = QPushButton('Flash')
        self._flash_btn.setToolTip('Flash the built binary to the ELM11')
        self._flash_btn.clicked.connect(self._flash)
        self._flash_btn.setEnabled(False)
        tb.addWidget(self._flash_btn)

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

        self._cmd_status = QLabel('')
        self._cmd_status.setStyleSheet('padding-right:8px;')
        tb.addWidget(self._cmd_status)

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
        self._cmd_toggle = QAction('&Command Mode Panel', self)
        self._cmd_toggle.setCheckable(True)
        self._cmd_toggle.setShortcut(QKeySequence('F1'))
        self._cmd_toggle.toggled.connect(self._toggle_cmd_mode)
        vm.addAction(self._cmd_toggle)
        self._docs_toggle = QAction('&Documentation Panel', self)
        self._docs_toggle.setCheckable(True)
        self._docs_toggle.setShortcut(QKeySequence('F2'))
        self._docs_toggle.toggled.connect(self._toggle_docs)
        vm.addAction(self._docs_toggle)

        # Tools
        tm = mb.addMenu('&Tools')
        tm.addAction(self._act('&Settings…',      'Ctrl+,', self._open_settings))
        tm.addSeparator()
        tm.addAction(self._act('Clear &Terminal', None,      self._terminal.clear))
        tm.addAction(self._act('Clear &Upload Status', None, self._upload_out.clear))
        tm.addAction(self._act('Clear &Build Output', None,  self._build_out.clear))

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
        w = self._editor_tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _refresh_ports(self):
        current = self._port_combo.currentText()
        if not current:
            current = QSettings().value('serial/last_port', '')
        ports = [p.device for p in serial.tools.list_ports.comports()]
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
        self._update_device_buttons()

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
        if not connected or is_c_mode:
            self._cmd_status.setText('')
        elif cmd_active:
            self._cmd_status.setText('COMMAND MODE')
        else:
            self._cmd_status.setText('REPL')
        # C-workflow buttons — enabled whenever a C workspace is open.
        # The handlers themselves check for a loaded file and warn if needed.
        has_workspace = self._workspace_root is not None
        self._build_btn.setEnabled(is_c_mode and has_workspace and not cmd_active)
        self._flash_btn.setEnabled(is_c_mode and has_workspace and usable)

    def _on_cmd_btn_toggled(self, checked: bool):
        self._cmd_mode.set_active(checked)

    def _on_cmd_mode_active_changed(self, active: bool):
        # Keep the toolbar button in sync if activation changed via other paths
        # (e.g. auto-deactivate on serial disconnect).
        if self._cmd_btn.isChecked() != active:
            self._cmd_btn.blockSignals(True)
            self._cmd_btn.setChecked(active)
            self._cmd_btn.blockSignals(False)
        self._update_device_buttons()

    # ── File operations ───────────────────────────────────────────────────────

    def _new_file(self):
        log.debug('New untitled file')
        editor = CodeEditor()
        idx = self._editor_tabs.addTab(editor, 'untitled.lua')
        self._editor_tabs.setCurrentIndex(idx)
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
            self.setWindowTitle('ELM11 IDE')

    def _open_path(self, path: Path):
        log.debug('Open path: %s', path)
        # Avoid duplicate tabs
        for i in range(self._editor_tabs.count()):
            w = self._editor_tabs.widget(i)
            if isinstance(w, CodeEditor) and w.file_path == path:
                self._editor_tabs.setCurrentIndex(i)
                return
        editor = CodeEditor()
        editor.set_file(path)
        editor.document().modificationChanged.connect(
            lambda _: self._refresh_tab_title(editor))
        idx = self._editor_tabs.addTab(editor, path.name)
        self._editor_tabs.setCurrentIndex(idx)
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
        for i in range(self._editor_tabs.count()):
            if self._editor_tabs.widget(i) is editor:
                name = editor.file_path.name if editor.file_path else 'untitled'
                dot   = ' ●' if editor.document().isModified() else ''
                stale = '' if self._is_build_artifact(editor.file_path) \
                    else (' ↑' if editor.is_stale else '')
                self._editor_tabs.setTabText(i, name + dot + stale)
                break
        if editor.file_path:
            self._tree.refresh_decoration(editor.file_path)

    def _editor_for(self, path: Path) -> CodeEditor | None:
        for i in range(self._editor_tabs.count()):
            w = self._editor_tabs.widget(i)
            if isinstance(w, CodeEditor) and w.file_path == path:
                return w
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
        log.debug('Close tab index=%d  title=%s', index, self._editor_tabs.tabText(index))
        editor = self._editor_tabs.widget(index)
        closed_path = editor.file_path if isinstance(editor, CodeEditor) else None
        if isinstance(editor, CodeEditor) and editor.document().isModified():
            name = self._editor_tabs.tabText(index).rstrip(' ●↑')
            reply = QMessageBox.question(
                self, 'Unsaved Changes', f'Save changes to {name}?',
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self._editor_tabs.removeTab(index)
        self._tree.refresh_decoration(closed_path)

    def _on_tab_changed(self, _index: int):
        self._update_device_buttons()

    # ── Serial connection ─────────────────────────────────────────────────────

    def _toggle_connect(self, checked: bool):
        log.debug('Toggle connect: checked=%s', checked)

        port = self._port_combo.currentText()
        if not port:
            QMessageBox.warning(self, 'No Port', 'No serial port selected.')
            self._connect_btn.setChecked(False)
            return

        if checked:
            self._terminal.connect_to_port(port, SettingsDialog.baud())
            self._bottom.setCurrentWidget(self._terminal)
        else:
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
        self._toggle_outer_pane(3, checked, 320, 'ui/docs_visible')

    def _toggle_cmd_mode(self, checked: bool):
        self._toggle_outer_pane(2, checked, 340, 'ui/cmd_mode_visible')

    def _open_example(self, filename: str, code: str):
        """Open an embLua example program in a new editor tab."""
        editor = CodeEditor()
        editor.setPlainText(code)
        editor.document().setModified(True)
        idx = self._editor_tabs.addTab(editor, filename)
        self._editor_tabs.setCurrentIndex(idx)
        editor.document().modificationChanged.connect(
            lambda _: self._refresh_tab_title(editor))
        self._refresh_tab_title(editor)
        self._update_device_buttons()

    def _build(self):
        if self._workspace_mode != 'C' or self._workspace_root is None:
            QMessageBox.warning(self, 'No C Workspace',
                'Open a C workspace to build.')
            return
        make_dir = self._workspace_root / 'build' / 'make'
        makefile = make_dir / 'Makefile'
        if not makefile.is_file():
            QMessageBox.warning(self, 'Missing Makefile',
                f'No Makefile found at:\n{makefile}\n\n'
                "The C workspace templates don't appear to be deployed.")
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

        toolchain_root = str(Path(compiler).resolve())
        self._build_out.clear()
        self._bottom.setCurrentWidget(self._build_out)
        self._build_out.run_command(
            'make',
            ['-C', str(make_dir), f'RISCV_PATH={toolchain_root}'],
            cwd=str(self._workspace_root))

    def _flash(self):
        if self._workspace_mode != 'C' or self._workspace_root is None:
            QMessageBox.warning(self, 'No C Workspace',
                'Open a C workspace to flash.')
            return
        make_dir = self._workspace_root / 'build' / 'make'
        makefile = make_dir / 'Makefile'
        if not makefile.is_file():
            QMessageBox.warning(self, 'Missing Makefile',
                f'No Makefile found at:\n{makefile}')
            return
        compiler = SettingsDialog.compiler_path()
        if not compiler:
            QMessageBox.warning(self, 'No C Compiler',
                'Set the compiler path in Settings → C.')
            return
        toolchain_root = str(Path(compiler).resolve().parent.parent)
        port = self._port_combo.currentText()
        args = ['-C', str(make_dir), 'flash', f'RISCV_PATH={toolchain_root}']
        if port:
            args.append(f'PORT={port}')
        self._build_out.clear()
        self._bottom.setCurrentWidget(self._build_out)
        self._build_out.run_command(
            'make', args, cwd=str(self._workspace_root))

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
        for i in range(self._editor_tabs.count()):
            w = self._editor_tabs.widget(i)
            if isinstance(w, CodeEditor):
                w.apply_theme()
        self._on_connection_changed(self._terminal.is_connected)
        self._rebuild_theme_menu()

    # ── Workspaces ────────────────────────────────────────────────────────────

    def _load_workspace(self, path: Path):
        log.debug('Load workspace: %s', path)
        """Switch the tree root to path and persist it in the workspace history."""
        # Persist the outgoing workspace's open files before we swap roots.
        self._save_workspace_tabs()
        self._workspace_root = path
        self._tree.set_root(path, is_workspace=True)
        self.setWindowTitle(f'ELM11 IDE — {path.name}')

        s = QSettings()
        raw = s.value('workspaces/history', [])
        # QSettings may return a string instead of list when there's only one entry
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
        entry = str(path)
        if entry in history:
            history.remove(entry)
        history.insert(0, entry)
        history = history[:10]          # keep the 10 most recent
        s.setValue('workspaces/history', history)

        # Restore or choose mode for this workspace
        mode_key = f'workspaces/mode/{path}'
        saved_mode = s.value(mode_key, None)
        is_new_workspace = saved_mode is None
        if is_new_workspace:
            # New workspace — ask the user to pick a language mode
            items = ['Lua', 'C']
            from PyQt6.QtWidgets import QInputDialog
            mode, ok = QInputDialog.getItem(
                self, 'Workspace Language',
                f'Select language mode for  {path.name}:',
                items, 0, False)
            if not ok:
                mode = 'Lua'
            s.setValue(mode_key, mode)
            saved_mode = mode
        self._set_mode(saved_mode)

        # Deploy the C build-system templates into a brand-new C workspace.
        if is_new_workspace and saved_mode == 'C':
            self._deploy_c_build_templates(path)

        self._rebuild_workspaces_menu()
        self._restore_workspace_tabs(path)

    def _deploy_c_build_templates(self, workspace: Path):
        """Seed a freshly-created C workspace with the bundled templates,
        laid out as:

          * `<workspace>/main.c`            — starter user source
          * `<workspace>/build/runtime/`    — prebuilt runtime objects
          * `<workspace>/build/make/`       — Makefile + linker script
          * `<workspace>/build/utilities/`  — helper Python scripts

        Files that already exist are skipped so user edits aren't
        clobbered."""
        import shutil

        def _target_for(src: Path) -> Path:
            """Where does a c_build file go? Rooted on `workspace`."""
            if src.name == 'main.c':
                return workspace / src.name
            if src.suffix == '.py':
                return workspace / 'build' / 'utilities' / src.name
            return workspace / 'build' / 'make' / src.name

        plan: list[tuple[Path, Path]] = []   # (source, destination)
        c_build = _ide_data_dir('c_build')
        if c_build.is_dir():
            for src in c_build.iterdir():
                if src.is_file() and not src.name.startswith('.'):
                    plan.append((src, _target_for(src)))
        c_runtime = _ide_data_dir('c_runtime')
        if c_runtime.is_dir():
            for src in c_runtime.iterdir():
                if src.is_file() and not src.name.startswith('.'):
                    plan.append((src, workspace / 'build' / 'runtime' / src.name))

        import re
        for src, dst in plan:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                log.warning('Could not create %s: %s', dst.parent, exc)
                continue
            if dst.exists():
                log.debug('Skipping existing %s', dst)
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
        """Record the currently-open file paths + active index under the
        current workspace's QSettings keys. No-op when no workspace is open."""
        if self._workspace_root is None:
            return
        files: list[str] = []
        for i in range(self._editor_tabs.count()):
            w = self._editor_tabs.widget(i)
            if isinstance(w, CodeEditor) and w.file_path:
                files.append(str(w.file_path))
        s = QSettings()
        s.setValue(f'workspaces/open_files/{self._workspace_root}', files)
        s.setValue(f'workspaces/active_tab/{self._workspace_root}',
                   self._editor_tabs.currentIndex())

    def _restore_workspace_tabs(self, path: Path):
        """Close any currently-open tabs and re-open the files recorded for
        `path` on its last close."""
        s = QSettings()
        raw = s.value(f'workspaces/open_files/{path}', [])
        files = (list(raw) if isinstance(raw, (list, tuple))
                 else ([raw] if raw else []))
        # Clear existing tabs (directly — bypasses the unsaved-changes prompt
        # that tabCloseRequested triggers; users should save before switching).
        while self._editor_tabs.count():
            self._editor_tabs.removeTab(0)
        for f in files:
            p = Path(f)
            if p.is_file():
                self._open_path(p)
        try:
            idx = int(s.value(f'workspaces/active_tab/{path}', 0))
        except (TypeError, ValueError):
            idx = 0
        if 0 <= idx < self._editor_tabs.count():
            self._editor_tabs.setCurrentIndex(idx)

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
        self.setWindowTitle('ELM11 IDE')
        if self._sb_mode:
            self._sb_mode.setVisible(False)
        self._update_device_buttons()

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
        s.remove(f'workspaces/open_files/{entry}')
        s.remove(f'workspaces/active_tab/{entry}')
        # Close if it's the current workspace
        if self._workspace_root and str(self._workspace_root) == entry:
            self._close_workspace()
        self._rebuild_workspaces_menu()

    def _clear_workspace_history(self):
        s = QSettings()
        # Remove all per-workspace keys
        raw = s.value('workspaces/history', [])
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])
        for entry in history:
            s.remove(f'workspaces/mode/{entry}')
            s.remove(f'workspaces/open_files/{entry}')
            s.remove(f'workspaces/active_tab/{entry}')
        s.remove('workspaces/history')
        self._close_workspace()
        self._rebuild_workspaces_menu()

    # ── Settings / About ──────────────────────────────────────────────────────

    def _open_settings(self):
        if SettingsDialog(self).exec():
            self._update_device_buttons()
            # Re-apply font to all open editors
            for i in range(self._editor_tabs.count()):
                w = self._editor_tabs.widget(i)
                if isinstance(w, CodeEditor):
                    w.apply_theme()

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
                self._tree.set_root(p, is_workspace=True)
                self.setWindowTitle(f'ELM11 IDE — {p.name}')
                saved_mode = s.value(f'workspaces/mode/{p}', 'Lua')
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
        for i in range(self._editor_tabs.count()):
            w = self._editor_tabs.widget(i)
            if isinstance(w, CodeEditor) and w.document().isModified():
                reply = QMessageBox.question(
                    self, 'Unsaved Changes',
                    'There are unsaved changes. Exit anyway?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    event.ignore()
                    return
                break

        self._save_workspace_tabs()
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
