"""Project / file-system tree panel."""
from PyQt6.QtWidgets import QTreeView, QMenu
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, pyqtSignal, QModelIndex
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


class ProjectTree(QTreeView):
    file_activated = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = QFileSystemModel()
        self._model.setFilter(
            QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.Dirs
        )
        # Show all files — no name filtering
        self._model.setRootPath('')
        self.setModel(self._model)

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

    def set_root(self, path: Path):
        root_index = self._model.index(str(path))
        self.setRootIndex(root_index)

    # ── Internal ─────────────────────────────────────────────────────────

    def _activated(self, index: QModelIndex):
        path = Path(self._model.filePath(index))
        if path.is_file():
            self.file_activated.emit(path)

    def _context_menu(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        path = Path(self._model.filePath(index))
        menu = QMenu(self)
        menu.setStyleSheet(
            'QMenu { background:#2d2d2d; color:#cccccc; border:1px solid #555; }'
            'QMenu::item:selected { background:#094771; }'
        )
        if path.is_file():
            menu.addAction('Open').triggered.connect(
                lambda: self.file_activated.emit(path))
        menu.exec(self.viewport().mapToGlobal(pos))
