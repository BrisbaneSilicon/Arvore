"""Project / file-system tree panel."""
import logging
log = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QTreeView, QMenu, QMessageBox,
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, pyqtSignal, QModelIndex, QSortFilterProxyModel
from pathlib import Path
import shutil

from . import theme


class _WorkspaceProxy(QSortFilterProxyModel):
    """Show only the workspace folder and its contents; hide siblings at every level."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace: Path | None = None
        self._status_provider = None

    def set_workspace(self, path: Path):
        self._workspace = path
        self.invalidateFilter()

    def set_status_provider(self, fn):
        """fn(path: Path) -> tuple[bool, bool]  returns (dirty, stale)."""
        self._status_provider = fn

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        base = super().data(index, role)
        if role == Qt.ItemDataRole.DisplayRole and self._status_provider and base:
            src = self.mapToSource(index)
            path_str = self.sourceModel().filePath(src)
            if path_str:
                p = Path(path_str)
                if p.is_file():
                    dirty, stale = self._status_provider(p)
                    suffix = (' ●' if dirty else '') + (' ↑' if stale else '')
                    if suffix:
                        return f'{base}{suffix}'
        return base

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if self._workspace is None:
            return True

        idx = self.sourceModel().index(source_row, 0, source_parent)
        item_path = self.sourceModel().filePath(idx)
        if not item_path:
            return True          # path not yet loaded — don't hide prematurely

        item = Path(item_path)
        ws   = self._workspace

        # Accept: workspace itself, or anything inside it
        if item == ws or item.is_relative_to(ws):
            return True
        # Accept: ancestors of the workspace (needed so the root index is reachable)
        if ws.is_relative_to(item):
            return True
        # Reject everything else (siblings and their subtrees)
        return False


class ProjectTree(QTreeView):
    file_activated   = pyqtSignal(Path)
    workspace_loaded = pyqtSignal(Path)
    new_file_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = QFileSystemModel()
        self._model.setFilter(
            QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.Dirs
        )
        self._model.setRootPath('')

        self._proxy = _WorkspaceProxy(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setDynamicSortFilter(True)
        self.setModel(self._proxy)

        # Hide size / type / date columns — name only
        for col in range(1, 4):
            self.hideColumn(col)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setIndentation(16)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.activated.connect(self._activated)

        # Default to home directory
        self.set_root(Path.home())
        self.apply_theme()

    # ── Public API ────────────────────────────────────────────────────────

    def apply_theme(self):
        self.setStyleSheet(theme.tree_stylesheet(theme.current()))

    def set_status_provider(self, fn):
        """Install a callable used to decorate file names with dirty/stale markers."""
        self._proxy.set_status_provider(fn)

    def refresh_decoration(self, path: Path | None):
        """Notify the view that the decoration for `path` may have changed."""
        if not path:
            return
        src_idx = self._model.index(str(path))
        if not src_idx.isValid():
            return
        proxy_idx = self._proxy.mapFromSource(src_idx)
        if proxy_idx.isValid():
            self._proxy.dataChanged.emit(
                proxy_idx, proxy_idx, [Qt.ItemDataRole.DisplayRole])

    def _refresh_parent(self, parent: Path):
        """Force the model to rescan a directory after rename/delete."""
        idx = self._model.index(str(parent))
        if idx.isValid():
            # Toggling the root path forces QFileSystemModel to re-read
            old_root = self._model.rootPath()
            self._model.setRootPath('')
            self._model.setRootPath(old_root)

    @property
    def selected_dir(self) -> Path | None:
        """Return the selected directory, or the parent dir if a file is selected."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        path = self._source_path(index)
        return path if path.is_dir() else path.parent

    def set_root(self, path: Path):
        log.debug('set_root: path=%s  parent=%s', path, path.parent)
        self._proxy.set_workspace(path)
        parent_path = path.parent if path.parent != path else path
        parent_source = self._model.index(str(parent_path))
        proxy_root = self._proxy.mapFromSource(parent_source)
        log.debug('set_root: parent_source valid=%s  proxy_root valid=%s',
                  parent_source.isValid(), proxy_root.isValid())
        self.setRootIndex(proxy_root)
        # Auto-expand and select the workspace folder
        ws_proxy = self._proxy.mapFromSource(self._model.index(str(path)))
        log.debug('set_root: ws_proxy valid=%s', ws_proxy.isValid())
        self.expand(ws_proxy)
        self.setCurrentIndex(ws_proxy)

    # ── Internal ─────────────────────────────────────────────────────────

    def _source_path(self, proxy_index: QModelIndex) -> Path:
        return Path(self._model.filePath(self._proxy.mapToSource(proxy_index)))

    def _activated(self, index: QModelIndex):
        path = self._source_path(index)
        if path.is_file():
            self.file_activated.emit(path)

    def _context_menu(self, pos):
        index = self.indexAt(pos)
        t = theme.current()
        menu = QMenu(self)
        menu.setStyleSheet(
            f'QMenu {{ background:{t["menubar_bg"]}; color:{t["menubar_fg"]}; border:1px solid {t["border"]}; }}'
            f'QMenu::item:selected {{ background:{t["selection"]}; }}'
        )

        if index.isValid():
            path = self._source_path(index)
            if path.is_file():
                menu.addAction('Open').triggered.connect(
                    lambda: self.file_activated.emit(path))
            if path.is_dir():
                menu.addAction('New File').triggered.connect(
                    lambda: (self.setCurrentIndex(index), self.new_file_requested.emit()))
                menu.addAction('New Directory').triggered.connect(
                    lambda: self._create_subfolder(path))
                menu.addSeparator()
                menu.addAction('New Workspace').triggered.connect(
                    lambda: self._set_workspace(path))
            menu.addSeparator()
            menu.addAction('Rename…').triggered.connect(
                lambda: self._rename_item(path))
            menu.addAction('Delete').triggered.connect(
                lambda: self._delete_item(path))

        menu.exec(self.viewport().mapToGlobal(pos))

    def _set_workspace(self, path: Path):
        self.set_root(path)
        self.workspace_loaded.emit(path)

    def _create_subfolder(self, parent: Path):
        dlg = _NameDialog('New Directory', 'Directory name:', self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.value()
        if not name:
            return
        name = name.strip()
        new_dir = parent / name
        try:
            new_dir.mkdir(parents=False, exist_ok=False)
            # Expand the parent so the new folder is immediately visible
            self.expand(self._proxy.mapFromSource(self._model.index(str(parent))))
        except FileExistsError:
            QMessageBox.warning(self, 'Already Exists',
                f'"{name}" already exists in {parent.name}/')
        except OSError as exc:
            QMessageBox.critical(self, 'Error',
                f'Could not create folder:\n{exc}')

    def _rename_item(self, path: Path):
        kind = 'directory' if path.is_dir() else 'file'
        dlg = _NameDialog(f'Rename {kind}', f'New name for  {path.name}:', self)
        dlg._edit.setText(path.name)
        dlg._edit.selectAll()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = dlg.value()
        if not new_name or new_name == path.name:
            return
        new_path = path.parent / new_name
        try:
            path.rename(new_path)
            self._refresh_parent(path.parent)
        except FileExistsError:
            QMessageBox.warning(self, 'Already Exists',
                f'"{new_name}" already exists.')
        except OSError as exc:
            QMessageBox.critical(self, 'Error',
                f'Could not rename:\n{exc}')

    def _delete_item(self, path: Path):
        kind = 'directory' if path.is_dir() else 'file'
        msg = QMessageBox(self)
        msg.setWindowTitle(f'Delete {kind}')
        msg.setText(f'Permanently delete  {path.name}?')
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        msg.setStyleSheet(theme.dialog_stylesheet(theme.current()))
        msg.setMinimumWidth(450)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        try:
            parent = path.parent
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            self._refresh_parent(parent)
        except OSError as exc:
            QMessageBox.critical(self, 'Error',
                f'Could not delete:\n{exc}')


class _NameDialog(QDialog):
    """A simple name-input dialog with a guaranteed minimum width."""

    def __init__(self, title: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setStyleSheet(theme.dialog_stylesheet(theme.current()))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self._edit = QLineEdit()
        layout.addWidget(self._edit)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._edit.setFocus()
        self._edit.returnPressed.connect(self.accept)

    def value(self) -> str:
        return self._edit.text().strip()
