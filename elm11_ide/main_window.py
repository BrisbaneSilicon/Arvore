"""Main application window."""
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QToolBar,
    QFileDialog, QMessageBox, QComboBox, QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence
import serial.tools.list_ports
from pathlib import Path
import sys

from .code_editor import CodeEditor
from .project_tree import ProjectTree
from .serial_terminal import SerialTerminal
from .build_output import BuildOutput
from .settings import SettingsDialog

DARK = """
QMainWindow, QWidget        { background:#1e1e1e; color:#d4d4d4; }
QMenuBar                    { background:#2d2d2d; color:#cccccc; }
QMenuBar::item:selected     { background:#094771; }
QMenu                       { background:#2d2d2d; color:#cccccc; border:1px solid #555; }
QMenu::item:selected        { background:#094771; }
QToolBar                    { background:#2d2d2d; border:none; spacing:4px; padding:3px; }
QTabWidget::pane            { border:1px solid #3c3c3c; background:#1e1e1e; }
QTabBar::tab {
    background:#2d2d2d; color:#888; padding:6px 16px;
    border:none; border-right:1px solid #1e1e1e;
}
QTabBar::tab:selected       { background:#1e1e1e; color:#fff; border-top:2px solid #007acc; }
QTabBar::tab:hover          { background:#2a2d2e; color:#ccc; }
QSplitter::handle           { background:#3c3c3c; }
QComboBox {
    background:#3c3c3c; color:#d4d4d4;
    border:1px solid #555; padding:3px 8px; min-width:150px;
}
QComboBox::drop-down        { border:none; }
QComboBox QAbstractItemView { background:#2d2d2d; color:#d4d4d4; selection-background-color:#094771; }
QPushButton {
    background:#3c3c3c; color:#d4d4d4;
    border:1px solid #555; padding:4px 12px;
}
QPushButton:hover           { background:#4c4c4c; }
QPushButton:pressed         { background:#094771; }
QPushButton:checked         { background:#094771; border-color:#007acc; }
QPushButton:disabled        { color:#555; border-color:#444; }
QStatusBar                  { background:#007acc; color:#fff; font-size:9pt; }
QLabel                      { background:transparent; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ELM11 IDE')
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(DARK)

        # Build central UI first so _terminal etc. exist before menu is wired
        self._setup_central()
        self._setup_toolbar()
        self._setup_menu()
        self._setup_statusbar()
        self._restore_geometry()

        # Auto-refresh serial port list
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._refresh_ports)
        self._port_timer.start(3000)
        self._refresh_ports()

    # ── Central widget ────────────────────────────────────────────────────────

    def _setup_central(self):
        outer = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(outer)

        # Left: project tree
        self._tree = ProjectTree()
        self._tree.file_activated.connect(self._open_path)
        self._tree.workspace_loaded.connect(self._load_workspace)
        self._tree.setMinimumWidth(120)
        outer.addWidget(self._tree)
        outer.setChildrenCollapsible(False)

        # Right: editor on top, bottom panel below
        right = QSplitter(Qt.Orientation.Vertical)
        outer.addWidget(right)

        self._editor_tabs = QTabWidget()
        self._editor_tabs.setTabsClosable(True)
        self._editor_tabs.tabCloseRequested.connect(self._close_tab)
        self._editor_tabs.currentChanged.connect(self._on_tab_changed)
        right.addWidget(self._editor_tabs)

        self._bottom = QTabWidget()
        self._terminal = SerialTerminal()
        self._terminal.connected.connect(self._on_connection_changed)
        self._build_out = BuildOutput()
        self._build_out.build_finished.connect(self._on_build_finished)
        self._bottom.addTab(self._terminal, 'Serial Terminal')
        self._bottom.addTab(self._build_out, 'Build Output')
        right.addWidget(self._bottom)
        right.setChildrenCollapsible(False)

        outer.setSizes([200, 900])
        right.setSizes([520, 200])

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _setup_toolbar(self):
        tb = QToolBar('Main', self)
        tb.setIconSize(QSize(16, 16))
        tb.setMovable(False)
        self.addToolBar(tb)

        tb.addAction(self._act('New',  'Ctrl+N', self._new_file))
        tb.addAction(self._act('Open', 'Ctrl+O', self._open_file))
        tb.addAction(self._act('Save', 'Ctrl+S', self._save_file))
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
        self._build_btn.setToolTip('Build C project (coming soon)')
        self._build_btn.clicked.connect(self._build)
        self._build_btn.setEnabled(False)
        tb.addWidget(self._build_btn)

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

        # Tools
        tm = mb.addMenu('&Tools')
        tm.addAction(self._act('&Settings…',      'Ctrl+,', self._open_settings))
        tm.addSeparator()
        tm.addAction(self._act('Clear &Terminal', None,      self._terminal.clear))
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
        self._sb_lang = QLabel('')
        self._sb_file = QLabel('')
        sb.addWidget(self._sb_conn)
        sb.addPermanentWidget(self._sb_lang)
        sb.addPermanentWidget(self._sb_file)

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
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self._port_combo.blockSignals(True)
        self._port_combo.clear()
        self._port_combo.addItems(ports)
        if current in ports:
            self._port_combo.setCurrentText(current)
        self._port_combo.blockSignals(False)

    def _update_device_buttons(self):
        connected = self._terminal.is_connected
        editor    = self._cur()
        is_lua    = editor is not None and editor.is_lua
        uploader  = SettingsDialog.uploader_path()
        self._upload_btn.setEnabled(connected and is_lua and bool(uploader))
        self._run_btn.setEnabled(connected and is_lua)
        # Build stays disabled until C toolchain support arrives
        self._build_btn.setEnabled(False)

    # ── File operations ───────────────────────────────────────────────────────

    def _new_file(self):
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
            self._load_workspace(Path(path))

    def _open_path(self, path: Path):
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
        self._update_device_buttons()

    def _save_file(self):
        editor = self._cur()
        if not editor:
            return
        if editor.file_path:
            editor.save()
            self._refresh_tab_title(editor)
        else:
            self._save_file_as()

    def _save_file_as(self):
        editor = self._cur()
        if not editor:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save As', '',
            'Lua (*.lua);;C source (*.c);;C header (*.h);;All (*)')
        if path:
            editor.save_as(Path(path))
            self._refresh_tab_title(editor)

    def _refresh_tab_title(self, editor: CodeEditor):
        for i in range(self._editor_tabs.count()):
            if self._editor_tabs.widget(i) is editor:
                name = editor.file_path.name if editor.file_path else 'untitled'
                dot  = '● ' if editor.document().isModified() else ''
                self._editor_tabs.setTabText(i, dot + name)
                break

    def _close_tab(self, index: int):
        editor = self._editor_tabs.widget(index)
        if isinstance(editor, CodeEditor) and editor.document().isModified():
            name = self._editor_tabs.tabText(index).lstrip('● ')
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

    def _on_tab_changed(self, _index: int):
        self._update_device_buttons()
        editor = self._cur()
        if editor and editor.file_path:
            lang = 'Lua' if editor.is_lua else 'C' if editor.is_c else ''
            self._sb_lang.setText(f'  {lang}  ')
            self._sb_file.setText(f'  {editor.file_path}  ')
        else:
            self._sb_lang.setText('')
            self._sb_file.setText('')

    # ── Serial connection ─────────────────────────────────────────────────────

    def _toggle_connect(self, checked: bool):
        if checked:
            port = self._port_combo.currentText()
            if not port:
                QMessageBox.warning(self, 'No Port', 'No serial port selected.')
                self._connect_btn.setChecked(False)
                return
            self._terminal.connect_to_port(port, SettingsDialog.baud())
            self._bottom.setCurrentWidget(self._terminal)
        else:
            self._terminal.disconnect_port()

    def _on_connection_changed(self, connected: bool):
        self._connect_btn.setChecked(connected)
        self._connect_btn.setText('Disconnect' if connected else 'Connect')
        if connected:
            port = self._port_combo.currentText()
            self._sb_conn.setText(f'  Connected: {port} @ {SettingsDialog.baud()}')
            self.statusBar().setStyleSheet('background:#007acc; color:#fff;')
        else:
            self._sb_conn.setText('  Not connected')
            self.statusBar().setStyleSheet('background:#3c3c3c; color:#d4d4d4;')
        self._update_device_buttons()

    # ── Device actions ────────────────────────────────────────────────────────

    def _upload(self):
        editor = self._cur()
        if not editor or not editor.file_path:
            return
        if editor.document().isModified():
            editor.save()

        uploader = SettingsDialog.uploader_path()
        if not uploader:
            QMessageBox.warning(self, 'No Uploader',
                'Set the path to program_uploader.py in Settings → Lua.')
            return

        port      = self._port_combo.currentText()
        lua_file  = str(editor.file_path)
        prog_name = editor.file_path.name

        self._terminal.append_info(f'\n--- Uploading {prog_name} ---\n')

        worker = self._terminal.get_worker()
        if worker:
            # Enter Command Mode, trigger upload, then hand the port to the script
            worker.send(b'command\n')
            QTimer.singleShot(150, lambda: self._do_upload_step2(
                worker, prog_name, uploader, lua_file, port))

    def _do_upload_step2(self, worker, prog_name, uploader, lua_file, port):
        worker.send(f'upload|program("{prog_name}")\n'.encode())
        QTimer.singleShot(200, lambda: self._do_upload_step3(
            worker, uploader, lua_file, port))

    def _do_upload_step3(self, worker, uploader, lua_file, port):
        worker.release_port()
        self._bottom.setCurrentWidget(self._build_out)
        self._build_out.run_upload(uploader, lua_file, port, SettingsDialog.baud())

    def _on_build_finished(self, exit_code: int):
        worker = self._terminal.get_worker()
        if worker:
            worker.reopen_port()
        self._bottom.setCurrentWidget(self._terminal)
        if exit_code == 0:
            self._terminal.append_info('--- Upload complete ---\n')
        else:
            self._terminal.append_info('--- Upload failed — check Build Output ---\n')

    def _run_program(self):
        editor = self._cur()
        if not editor or not editor.file_path:
            return
        prog_name = editor.file_path.name
        worker = self._terminal.get_worker()
        if worker:
            worker.send(b'command\n')
            QTimer.singleShot(150, lambda: worker.send(
                f'run|program("{prog_name}")\n'.encode()))
        self._bottom.setCurrentWidget(self._terminal)

    def _build(self):
        QMessageBox.information(self, 'Coming Soon',
            'C build support is coming soon.\n\n'
            'Configure your compiler in Settings → C when it arrives.')

    # ── Workspaces ────────────────────────────────────────────────────────────

    def _load_workspace(self, path: Path):
        """Switch the tree root to path and persist it in the workspace history."""
        self._tree.set_root(path)
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

        self._rebuild_workspaces_menu()

    def _rebuild_workspaces_menu(self):
        self._ws_menu.clear()
        self._ws_menu.addAction(self._act('Open Workspace…', 'Ctrl+Shift+O', self._open_folder))
        self._ws_menu.addSeparator()

        s = QSettings()
        raw = s.value('workspaces/history', [])
        history: list[str] = list(raw) if isinstance(raw, (list, tuple)) else ([raw] if raw else [])

        if history:
            for entry in history:
                p = Path(entry)
                action = self._ws_menu.addAction(str(p))
                action.setToolTip(entry)
                action.triggered.connect(lambda checked, _p=p: self._load_workspace(_p))
            self._ws_menu.addSeparator()
            self._ws_menu.addAction(self._act('Clear History', None, self._clear_workspace_history))
        else:
            no_ws = self._ws_menu.addAction('(no recent workspaces)')
            no_ws.setEnabled(False)

    def _clear_workspace_history(self):
        QSettings().remove('workspaces/history')
        self._rebuild_workspaces_menu()

    # ── Settings / About ──────────────────────────────────────────────────────

    def _open_settings(self):
        if SettingsDialog(self).exec():
            self._update_device_buttons()

    def _about(self):
        QMessageBox.about(self, 'ELM11 IDE',
            '<b>ELM11 IDE</b><br>'
            'An IDE for the ELM11 Embedded Lua Machine<br><br>'
            '© BrisbaneSilicon<br>'
            'brisbanesilicon.com.au')

    # ── Window state ──────────────────────────────────────────────────────────

    def _restore_geometry(self):
        s = QSettings()
        if s.contains('window/geometry'):
            self.restoreGeometry(s.value('window/geometry'))
        if s.contains('window/state'):
            self.restoreState(s.value('window/state'))

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
        self._terminal.disconnect_port()
        s = QSettings()
        s.setValue('window/geometry', self.saveGeometry())
        s.setValue('window/state',    self.saveState())
        event.accept()
