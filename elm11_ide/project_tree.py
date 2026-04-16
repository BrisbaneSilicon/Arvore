"""Project / file-system tree panel."""
from PyQt6.QtWidgets import (
    QTreeView, QMenu, QMessageBox,
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, pyqtSignal, QModelIndex, QSortFilterProxyModel
from pathlib import Path

TREE_STYLE = """
QTreeView {
    background: #252526;
    color: #cccccc;
    border: none;
    font-size: 10pt;
}
QTreeView::item:hover    { background: #2a2d2e; }
QTreeView::item:selected { background: #094771; color: white; }
QScrollBar:vertical {
    background: #252526; width: 8px;
}
QScrollBar::handle:vertical {
    background: #555; border-radius: 4px;
}
"""


class _WorkspaceProxy(QSortFilterProxyModel):
    """Show only the workspace folder and its contents; hide siblings at every level."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workspace: Path | None = None

    def set_workspace(self, path: Path):
        self._workspace = path
        self.invalidateFilter()

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

        self.setStyleSheet(TREE_STYLE)

        # Default to home directory
        self.set_root(Path.home())

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def selected_dir(self) -> Path | None:
        """Return the selected directory, or the parent dir if a file is selected."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        path = self._source_path(index)
        return path if path.is_dir() else path.parent

    def set_root(self, path: Path):
        self._proxy.set_workspace(path)
        # Root the view at the parent so the workspace folder is a visible node.
        # When path is already the filesystem root (parent == self), stay there.
        parent_path = path.parent if path.parent != path else path
        parent_source = self._model.index(str(parent_path))
        self.setRootIndex(self._proxy.mapFromSource(parent_source))
        # Auto-expand the workspace folder
        ws_proxy = self._proxy.mapFromSource(self._model.index(str(path)))
        self.expand(ws_proxy)

    # ── Internal ─────────────────────────────────────────────────────────

    def _source_path(self, proxy_index: QModelIndex) -> Path:
        return Path(self._model.filePath(self._proxy.mapToSource(proxy_index)))

    def _activated(self, index: QModelIndex):
        path = self._source_path(index)
        if path.is_file():
            self.file_activated.emit(path)

    def _context_menu(self, pos):
        index = self.indexAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(
            'QMenu { background:#2d2d2d; color:#cccccc; border:1px solid #555; }'
            'QMenu::item:selected { background:#094771; }'
        )

        if index.isValid():
            path = self._source_path(index)
            if path.is_file():
                menu.addAction('Open').triggered.connect(
                    lambda: self.file_activated.emit(path))
            if path.is_dir():
                menu.addAction('New Directory').triggered.connect(
                    lambda: self._create_subfolder(path))
                menu.addSeparator()
                menu.addAction('New Workspace').triggered.connect(
                    lambda: self._set_workspace(path))

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


class _NameDialog(QDialog):
    """A simple name-input dialog with a guaranteed minimum width."""

    STYLE = """
    QDialog  { background:#2d2d2d; color:#cccccc; }
    QWidget  { background:#2d2d2d; color:#cccccc; }
    QLabel   { background:transparent; }
    QLineEdit {
        background:#1e1e1e; color:#d4d4d4;
        border:1px solid #555; padding:4px;
    }
    QPushButton {
        background:#3c3c3c; color:#cccccc;
        border:1px solid #555; padding:4px 14px;
    }
    QPushButton:hover    { background:#4c4c4c; }
    QPushButton:default  { border-color:#007acc; }
    """

    def __init__(self, title: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(340)
        self.setStyleSheet(self.STYLE)

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
