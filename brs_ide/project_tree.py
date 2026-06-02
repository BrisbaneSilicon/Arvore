"""Project / file-system tree panel."""
import logging
log = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QTreeView, QMenu, QMessageBox, QAbstractItemView,
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, QTimer, pyqtSignal, QModelIndex, QSortFilterProxyModel
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


_MAX_AUTO_EXPAND_DEPTH = 4


class ProjectTree(QTreeView):
    file_activated   = pyqtSignal(Path)
    workspace_loaded = pyqtSignal(Path)
    new_file_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = QFileSystemModel()
        self._show_hidden = False
        self._apply_model_filter()
        # Read-write so QFileSystemModel.dropMimeData can perform real
        # filesystem moves; inline rename-by-editing is suppressed below
        # via setEditTriggers so the user still goes through our own dialog.
        self._model.setReadOnly(False)
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

        # Drag-and-drop file moves between directories.
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        # Suppress inline name-editing — user still uses the Rename dialog.
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.activated.connect(self._activated)

        # Cascade-expand subdirectories as QFileSystemModel lazy-loads them.
        self._model.directoryLoaded.connect(self._on_directory_loaded)

        # Default to home directory
        self.set_root(Path.home())
        self.apply_theme()

    # ── Public API ────────────────────────────────────────────────────────

    def _apply_model_filter(self):
        """(Re)build the QFileSystemModel filter from `self._show_hidden`.
        `.`/`..` are always excluded; hidden (dot-prefixed) entries are shown
        only when the user opts in."""
        flt = (QDir.Filter.NoDotAndDotDot | QDir.Filter.Files
               | QDir.Filter.Dirs)
        if self._show_hidden:
            flt |= QDir.Filter.Hidden
        self._model.setFilter(flt)

    def set_show_hidden(self, show: bool):
        """Show or hide dot-prefixed files/dirs (e.g. the `.build/` tree)."""
        show = bool(show)
        if show == self._show_hidden:
            return
        self._show_hidden = show
        self._apply_model_filter()

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

    def set_root(self, path: Path, is_workspace: bool = False,
                 auto_expand: bool = True):
        log.debug('set_root: path=%s  parent=%s  workspace=%s  auto_expand=%s',
                  path, path.parent, is_workspace, auto_expand)
        deep_expand = is_workspace and auto_expand
        self._auto_expand = deep_expand
        # An explicit re-root cancels any in-flight expansion-state restore.
        self._restore_paths = None
        self._proxy.set_workspace(path)
        parent_path = path.parent if path.parent != path else path
        parent_source = self._model.index(str(parent_path))
        proxy_root = self._proxy.mapFromSource(parent_source)
        log.debug('set_root: parent_source valid=%s  proxy_root valid=%s',
                  parent_source.isValid(), proxy_root.isValid())
        self.setRootIndex(proxy_root)
        # Always expand & select the workspace folder itself so its
        # top-level contents are visible.
        ws_proxy = self._proxy.mapFromSource(self._model.index(str(path)))
        log.debug('set_root: ws_proxy valid=%s', ws_proxy.isValid())
        self.expand(ws_proxy)
        self.setCurrentIndex(ws_proxy)
        # Deep-expand every subfolder only for real workspaces that opt in.
        # The home fallback would otherwise open the user's whole home tree,
        # and a freshly-created workspace opts out so it opens with the root
        # expanded but all nested folders collapsed.
        if deep_expand:
            self._expand_all_loaded(ws_proxy)
            # Disarm the lazy-cascade after the initial load window. Without
            # this, later filesystem rescans (e.g. _refresh_parent toggling
            # the model root after rename/delete, or build artefacts being
            # written) would re-fire `directoryLoaded` and re-expand every
            # directory the user might have just collapsed.
            QTimer.singleShot(5000, self._disarm_auto_expand)

    def _disarm_auto_expand(self):
        self._auto_expand = False

    # ── Expansion-state persistence ───────────────────────────────────────

    def expanded_dirs(self) -> list[str]:
        """Return the paths of every currently-expanded directory under the
        workspace root — used to persist the tree's open/closed state."""
        ws = self._proxy._workspace
        if ws is None:
            return []
        out: list[str] = []
        self._collect_expanded(
            self._proxy.mapFromSource(self._model.index(str(ws))), out)
        return out

    def _collect_expanded(self, idx: QModelIndex, out: list[str]):
        if not idx.isValid() or not self.isExpanded(idx):
            return
        out.append(str(self._source_path(idx)))
        for i in range(self._proxy.rowCount(idx)):
            child = self._proxy.index(i, 0, idx)
            if self._source_path(child).is_dir():
                self._collect_expanded(child, out)

    def restore_expanded(self, paths: list[str]):
        """Re-expand `paths` as QFileSystemModel lazily loads each directory.
        Call right after `set_root(..., auto_expand=False)`. Expanding a saved
        folder triggers its load, which fires `directoryLoaded` and expands its
        saved children in turn — so the whole saved tree unfolds."""
        self._restore_paths = set(paths)
        ws = self._proxy._workspace
        if ws is not None:
            # Apply to whatever is already loaded; the rest follow via the
            # directoryLoaded cascade as each folder populates.
            self._apply_restore_for(str(ws))
        # Stop reacting once the initial restore window passes, so later
        # filesystem rescans don't re-expand folders the user has collapsed.
        QTimer.singleShot(5000, self._disarm_restore)

    def _apply_restore_for(self, dir_path: str):
        proxy_idx = self._proxy.mapFromSource(self._model.index(dir_path))
        if not proxy_idx.isValid():
            return
        for i in range(self._proxy.rowCount(proxy_idx)):
            child = self._proxy.index(i, 0, proxy_idx)
            child_path = self._source_path(child)
            if child_path.is_dir() and str(child_path) in self._restore_paths:
                self.expand(child)

    def _disarm_restore(self):
        self._restore_paths = None

    def _is_under_build(self, path: Path) -> bool:
        """True if `path` is the workspace's `build/` directory or anything
        beneath it. Auto-expand skips these so the user isn't dumped into
        a tree of generated artefacts on workspace open."""
        ws = self._proxy._workspace
        if ws is None:
            return False
        try:
            rel = path.relative_to(ws)
        except (ValueError, OSError):
            return False
        return bool(rel.parts) and rel.parts[0] == 'build'

    def _expand_all_loaded(self, parent_idx: QModelIndex, depth: int = 0):
        """Recursively expand every already-populated child directory, up to
        `_MAX_AUTO_EXPAND_DEPTH` levels below the workspace root."""
        if depth >= _MAX_AUTO_EXPAND_DEPTH:
            return
        for i in range(self._proxy.rowCount(parent_idx)):
            child = self._proxy.index(i, 0, parent_idx)
            child_path = self._source_path(child)
            if child_path.is_dir() and not self._is_under_build(child_path):
                self.expand(child)
                self._expand_all_loaded(child, depth + 1)

    # ── Internal ─────────────────────────────────────────────────────────

    def _on_directory_loaded(self, dir_path: str):
        """Expand every subdirectory that lives under the current workspace
        as QFileSystemModel finishes loading it. The expansion triggers the
        model to load *that* directory's contents in turn, so the cascade
        continues until the whole tree under the workspace is expanded
        (capped at `_MAX_AUTO_EXPAND_DEPTH`)."""
        # Restoring a saved open/closed state takes priority over the
        # depth-based auto-expand cascade.
        if getattr(self, '_restore_paths', None) is not None:
            self._apply_restore_for(dir_path)
            return
        if not getattr(self, '_auto_expand', False):
            return
        ws = self._proxy._workspace
        if ws is None:
            return
        p = Path(dir_path)
        try:
            if p != ws and not p.is_relative_to(ws):
                return
            rel = p.relative_to(ws)
        except (ValueError, OSError):
            return
        # Don't drill into the build/ tree — those are generated artefacts.
        if rel.parts and rel.parts[0] == 'build':
            return
        depth = len(rel.parts)  # 0 for the workspace root itself
        if depth >= _MAX_AUTO_EXPAND_DEPTH:
            return
        proxy_idx = self._proxy.mapFromSource(self._model.index(dir_path))
        if not proxy_idx.isValid():
            return
        for i in range(self._proxy.rowCount(proxy_idx)):
            child = self._proxy.index(i, 0, proxy_idx)
            child_path = self._source_path(child)
            if child_path.is_dir() and not self._is_under_build(child_path):
                self.expand(child)

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
        # Don't switch the tree root yet — the handler prompts the user for
        # workspace config first and may cancel. It owns set_root() once the
        # workspace is actually committed.
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
