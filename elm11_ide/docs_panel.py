"""Documentation browser panel.

Displays pre-extracted embLua API reference and example programs.
Data source: `docs_data.json` (built by `scripts/build_docs.py`).
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QTextBrowser, QSplitter, QPushButton, QLabel,
    QPlainTextEdit, QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

from . import theme
from .settings import SettingsDialog
from .highlighter import LuaHighlighter


_LUA_DATA_FILE = Path(__file__).resolve().parent / 'docs_data.json'
_C_DATA_FILE   = Path(__file__).resolve().parent / 'docs_c_data.json'


def _load_lua_data() -> dict:
    if not _LUA_DATA_FILE.is_file():
        return {'api': [], 'examples': [], 'usage': []}
    try:
        return json.loads(_LUA_DATA_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'api': [], 'examples': [], 'usage': []}


def _load_c_data() -> dict:
    if not _C_DATA_FILE.is_file():
        return {'headers': []}
    try:
        return json.loads(_C_DATA_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'headers': []}


# ── HTML rendering ──────────────────────────────────────────────────────────

_CODE_LINE_RE = re.compile(r'^\s*\$\s?(.*)$')


def _render_description(desc: str) -> str:
    """Split embedded `$`-prefixed shell examples into <pre> blocks, escape prose."""
    lines = desc.splitlines()
    out: list[str] = []
    code_buf: list[str] = []
    for line in lines:
        m = _CODE_LINE_RE.match(line)
        if m:
            code_buf.append(m.group(1))
        else:
            if code_buf:
                out.append('<pre>' + html.escape('\n'.join(code_buf)) + '</pre>')
                code_buf = []
            if line.strip():
                out.append('<p>' + html.escape(line) + '</p>')
    if code_buf:
        out.append('<pre>' + html.escape('\n'.join(code_buf)) + '</pre>')
    return '\n'.join(out)


def _render_api_entry(entry: dict, t: dict) -> str:
    kind = entry.get('kind', '').capitalize() or 'Entry'
    return (
        f'<h2>{html.escape(entry["name"])}</h2>'
        f'<p style="color:{t["syn_comment"]};font-size:9pt;">'
        f'{html.escape(kind)}  ·  {html.escape(entry["category"])}</p>'
        + _render_description(entry.get('description', ''))
    )


def _render_example(ex: dict) -> str:
    return (
        f'<h2>{html.escape(ex["title"])}</h2>'
        f'<pre>{html.escape(ex["code"])}</pre>'
    )


def _render_usage(u: dict) -> str:
    return (
        f'<h2>{html.escape(u["title"])}</h2>'
        + _render_description(u.get('body', ''))
    )


def _render_c_function(entry: dict, t: dict) -> str:
    desc = entry.get('description', '')
    body = (
        f'<h2>{html.escape(entry["name"])}</h2>'
        f'<p style="color:{t["syn_comment"]};font-size:9pt;">'
        f'Function · {html.escape(entry.get("header", ""))}</p>'
        f'<pre>{html.escape(entry.get("signature", ""))}</pre>'
    )
    if desc:
        body += _render_description(desc)
    return body


def _render_c_macro(entry: dict, t: dict) -> str:
    desc = entry.get('description', '')
    args = entry.get('args', '')
    value = entry.get('value', '')
    rendered = f'#define {entry["name"]}{args}'
    if value:
        rendered = f'{rendered}  {value}'
    body = (
        f'<h2>{html.escape(entry["name"])}</h2>'
        f'<p style="color:{t["syn_comment"]};font-size:9pt;">'
        f'Macro · {html.escape(entry.get("header", ""))}</p>'
        f'<pre>{html.escape(rendered)}</pre>'
    )
    if desc:
        body += _render_description(desc)
    return body


def _page_css(t: dict) -> str:
    font = SettingsDialog.editor_font_family()
    return f"""
        body {{ background:{t['ed_bg']}; color:{t['ed_fg']};
                font-family:'{font}', monospace; font-size:10pt;
                padding:8px; }}
        h2 {{ color:{t['tab_accent']}; margin:0 0 6px 0; font-size:14pt; }}
        p  {{ margin:6px 0; }}
        pre {{ background:{t['term_bg']}; color:{t['ed_fg']};
               padding:8px; border:1px solid {t['border']};
               font-family:'{font}', monospace; white-space:pre-wrap; }}
    """


# ── Widget ──────────────────────────────────────────────────────────────────

class DocsPanel(QWidget):
    """Embedded documentation browser (tree + rendered content)."""

    open_example = pyqtSignal(str, str)   # (filename, code)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lua_data = _load_lua_data()
        self._c_data   = _load_c_data()
        self._mode     = 'Lua'   # flips to 'C' via set_mode()
        self._current_example: dict | None = None
        self._build_ui()
        self._populate()
        self.apply_theme()

    def set_mode(self, mode: str):
        """Switch between Lua and C documentation. Called by MainWindow
        whenever the workspace mode changes."""
        if mode == self._mode:
            return
        self._mode = 'C' if mode == 'C' else 'Lua'
        self._populate()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        top = QHBoxLayout()
        top.addWidget(QLabel('Search: '))
        self._search = QLineEdit()
        self._search.setPlaceholderText('filter by name or description…')
        self._search.textChanged.connect(self._on_search)
        top.addWidget(self._search)
        self._open_btn = QPushButton('Open example in editor')
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._emit_open_example)
        top.addWidget(self._open_btn)
        root.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setMinimumWidth(220)
        self._tree.currentItemChanged.connect(self._on_select)
        split.addWidget(self._tree)

        self._stack = QStackedWidget()
        self._view_html = QTextBrowser()
        self._view_html.setOpenExternalLinks(False)
        self._view_code = QPlainTextEdit()
        self._view_code.setReadOnly(True)
        self._view_code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._code_highlighter = LuaHighlighter(self._view_code.document())
        self._stack.addWidget(self._view_html)
        self._stack.addWidget(self._view_code)
        split.addWidget(self._stack)
        split.setSizes([260, 700])

    # ── Population ─────────────────────────────────────────────────────────

    def _populate(self):
        self._tree.clear()
        self._current_example = None
        self._open_btn.setEnabled(False)
        if self._mode == 'C':
            self._populate_c()
        else:
            self._populate_lua()

    def _populate_lua(self):
        # API, nested by category path (`Functions › Base Library › GPIO` →
        # API Reference / Functions / Base Library / GPIO)
        api_root = QTreeWidgetItem(self._tree, ['API Reference'])
        api_root.setExpanded(True)
        path_items: dict[tuple[str, ...], QTreeWidgetItem] = {(): api_root}
        for entry in self._lua_data.get('api', []):
            segments = tuple(s.strip() for s in entry['category'].split('›') if s.strip())
            parent = api_root
            for i in range(1, len(segments) + 1):
                key = segments[:i]
                node = path_items.get(key)
                if node is None:
                    node = QTreeWidgetItem(parent, [segments[i - 1]])
                    path_items[key] = node
                parent = node
            item = QTreeWidgetItem(parent, [entry['name']])
            item.setData(0, Qt.ItemDataRole.UserRole, ('api', entry))

        usage = self._lua_data.get('usage', [])
        if usage:
            usage_root = QTreeWidgetItem(self._tree, ['Example Usage'])
            for u in usage:
                item = QTreeWidgetItem(usage_root, [u['title']])
                item.setData(0, Qt.ItemDataRole.UserRole, ('usage', u))

        ex_root = QTreeWidgetItem(self._tree, ['Example Programs'])
        for ex in self._lua_data.get('examples', []):
            item = QTreeWidgetItem(ex_root, [ex['title']])
            item.setData(0, Qt.ItemDataRole.UserRole, ('example', ex))

    def _populate_c(self):
        # C API, grouped by header file. Each header contains Functions
        # and Macros sub-nodes.
        api_root = QTreeWidgetItem(self._tree, ['C API'])
        api_root.setExpanded(True)
        for header in self._c_data.get('headers', []):
            hname = header.get('name', '?')
            functions = header.get('functions', [])
            macros    = header.get('macros',    [])
            if not functions and not macros:
                continue
            h_node = QTreeWidgetItem(api_root, [hname])
            if functions:
                fn_node = QTreeWidgetItem(h_node, [f'Functions ({len(functions)})'])
                for fn in functions:
                    item = QTreeWidgetItem(fn_node, [fn['name']])
                    item.setData(0, Qt.ItemDataRole.UserRole, ('c_fn', fn))
            if macros:
                mc_node = QTreeWidgetItem(h_node, [f'Macros ({len(macros)})'])
                for mc in macros:
                    item = QTreeWidgetItem(mc_node, [mc['name']])
                    item.setData(0, Qt.ItemDataRole.UserRole, ('c_macro', mc))

    def _data(self) -> dict:
        """Active data dict — lets the search filter cover whichever
        documentation source is currently loaded."""
        return self._c_data if self._mode == 'C' else self._lua_data

    # ── Behaviour ──────────────────────────────────────────────────────────

    def _on_select(self, current, _prev):
        if not current:
            return
        payload = current.data(0, Qt.ItemDataRole.UserRole)
        t = theme.current()
        self._current_example = None
        self._open_btn.setEnabled(False)
        if not payload:
            self._view_html.setHtml(self._wrap('', t))
            self._stack.setCurrentWidget(self._view_html)
            return
        kind, obj = payload
        if kind == 'example':
            self._current_example = obj
            self._open_btn.setEnabled(True)
            self._view_code.setPlainText(obj.get('code', ''))
            self._stack.setCurrentWidget(self._view_code)
            return
        if kind == 'api':
            body = _render_api_entry(obj, t)
        elif kind == 'usage':
            body = _render_usage(obj)
        elif kind == 'c_fn':
            body = _render_c_function(obj, t)
        elif kind == 'c_macro':
            body = _render_c_macro(obj, t)
        else:
            body = ''
        self._view_html.setHtml(self._wrap(body, t))
        self._stack.setCurrentWidget(self._view_html)

    def _wrap(self, body: str, t: dict) -> str:
        return f'<html><head><style>{_page_css(t)}</style></head><body>{body}</body></html>'

    def _on_search(self, text: str):
        needle = text.strip().lower()

        def match(item: QTreeWidgetItem) -> bool:
            payload = item.data(0, Qt.ItemDataRole.UserRole)
            if payload is None:
                # Category item — visible if any descendant matches
                return False
            kind, obj = payload
            blob = ' '.join([
                obj.get('name', ''),
                obj.get('title', ''),
                obj.get('description', ''),
                obj.get('body', ''),
                obj.get('category', ''),
                obj.get('signature', ''),
                obj.get('header', ''),
                obj.get('value', ''),
            ])
            return needle in blob.lower()

        def filter_tree(item: QTreeWidgetItem) -> bool:
            any_visible = False
            for i in range(item.childCount()):
                child = item.child(i)
                if child.childCount():
                    shown = filter_tree(child)
                elif not needle:
                    shown = True
                else:
                    shown = match(child)
                child.setHidden(not shown)
                any_visible = any_visible or shown
            return any_visible

        root_count = self._tree.topLevelItemCount()
        for i in range(root_count):
            top = self._tree.topLevelItem(i)
            if not needle:
                top.setHidden(False)
                filter_tree(top)
            else:
                top.setHidden(not filter_tree(top))
                top.setExpanded(True)

    def _emit_open_example(self):
        if self._current_example:
            self.open_example.emit(
                self._current_example['title'],
                self._current_example['code'])

    # ── Theme ──────────────────────────────────────────────────────────────

    def apply_theme(self):
        t = theme.current()
        self.setStyleSheet(
            f'QWidget {{ background:{t["window_bg"]}; color:{t["window_fg"]}; }}'
            f'QTreeWidget, QTextBrowser, QPlainTextEdit {{ '
            f'background:{t["tree_bg"]}; color:{t["tree_fg"]}; '
            f'border:1px solid {t["border"]}; }}'
            f'QTreeWidget::item:hover    {{ background:{t["tree_hover"]}; }}'
            f'QTreeWidget::item:selected {{ background:{t["tree_sel"]}; }}'
            f'QLineEdit {{ background:{t["dlg_input_bg"]}; '
            f'color:{t["dlg_input_fg"]}; border:1px solid {t["border"]}; '
            f'padding:3px 6px; }}'
        )
        font = QFont(SettingsDialog.editor_font_family(),
                     SettingsDialog.editor_font_size())
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._view_code.setFont(font)
        pal = self._view_code.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(t['ed_bg']))
        pal.setColor(QPalette.ColorRole.Text, QColor(t['ed_fg']))
        self._view_code.setPalette(pal)
        # Rebuild highlighter so it picks up new syntax colours
        self._code_highlighter = LuaHighlighter(self._view_code.document())
        # Re-render current item so the HTML picks up new colours
        cur = self._tree.currentItem()
        if cur:
            self._on_select(cur, None)
