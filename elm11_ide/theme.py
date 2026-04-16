"""Centralised colour themes (dark / light)."""
from PyQt6.QtCore import QSettings

DARK = {
    'name': 'dark',
    # Main chrome
    'window_bg': '#1e1e1e', 'window_fg': '#d4d4d4',
    'menubar_bg': '#2d2d2d', 'menubar_fg': '#cccccc',
    'toolbar_bg': '#2d2d2d',
    'selection':  '#094771',
    'tab_bg': '#2d2d2d', 'tab_fg': '#888',
    'tab_sel_bg': '#1e1e1e', 'tab_sel_fg': '#fff',
    'tab_accent': '#007acc',
    'splitter':   '#3c3c3c',
    'combo_bg': '#3c3c3c', 'combo_fg': '#d4d4d4',
    'btn_bg': '#3c3c3c', 'btn_fg': '#d4d4d4',
    'btn_hover': '#4c4c4c', 'btn_pressed': '#094771',
    'btn_disabled_fg': '#555',
    'border': '#555',
    'status_bg': '#3c3c3c', 'status_fg': '#d4d4d4',
    'status_on_bg': '#007acc', 'status_on_fg': '#fff',
    # Editor
    'ed_bg': '#1e1e1e', 'ed_fg': '#d4d4d4',
    'ed_linenum_bg': '#252526', 'ed_linenum_fg': '#858585', 'ed_linenum_cur': '#c6c6c6',
    'ed_curline': '#2a2d2e',
    # Terminal / build
    'term_bg': '#1a1a1a', 'term_fg': '#d4d4d4',
    'term_info': '#569cd6', 'term_error': '#f44747',
    'term_warning': '#e5c07b', 'term_success': '#6ab04c',
    # Tree
    'tree_bg': '#252526', 'tree_fg': '#cccccc',
    'tree_hover': '#2a2d2e', 'tree_sel': '#094771',
    # Dialogs
    'dlg_bg': '#2d2d2d', 'dlg_fg': '#cccccc',
    'dlg_input_bg': '#1e1e1e', 'dlg_input_fg': '#d4d4d4',
    # Syntax
    'syn_keyword': '#569cd6', 'syn_builtin': '#c586c0',
    'syn_elm11_func': '#dcdcaa', 'syn_elm11_const': '#4ec9b0',
    'syn_string': '#ce9178', 'syn_comment': '#6a9955',
    'syn_number': '#b5cea8', 'syn_preproc': '#c586c0',
}

LIGHT = {
    'name': 'light',
    # Main chrome
    'window_bg': '#ffffff', 'window_fg': '#1e1e1e',
    'menubar_bg': '#f0f0f0', 'menubar_fg': '#333333',
    'toolbar_bg': '#f0f0f0',
    'selection':  '#cce8ff',
    'tab_bg': '#ececec', 'tab_fg': '#666',
    'tab_sel_bg': '#ffffff', 'tab_sel_fg': '#1e1e1e',
    'tab_accent': '#007acc',
    'splitter':   '#d0d0d0',
    'combo_bg': '#ffffff', 'combo_fg': '#1e1e1e',
    'btn_bg': '#e0e0e0', 'btn_fg': '#1e1e1e',
    'btn_hover': '#d0d0d0', 'btn_pressed': '#cce8ff',
    'btn_disabled_fg': '#aaa',
    'border': '#ccc',
    'status_bg': '#e0e0e0', 'status_fg': '#333',
    'status_on_bg': '#007acc', 'status_on_fg': '#fff',
    # Editor
    'ed_bg': '#ffffff', 'ed_fg': '#1e1e1e',
    'ed_linenum_bg': '#f5f5f5', 'ed_linenum_fg': '#999999', 'ed_linenum_cur': '#333333',
    'ed_curline': '#f0f8ff',
    # Terminal / build
    'term_bg': '#ffffff', 'term_fg': '#1e1e1e',
    'term_info': '#0066cc', 'term_error': '#cc0000',
    'term_warning': '#996600', 'term_success': '#008000',
    # Tree
    'tree_bg': '#f5f5f5', 'tree_fg': '#333333',
    'tree_hover': '#e8e8e8', 'tree_sel': '#cce8ff',
    # Dialogs
    'dlg_bg': '#f5f5f5', 'dlg_fg': '#333333',
    'dlg_input_bg': '#ffffff', 'dlg_input_fg': '#1e1e1e',
    # Syntax
    'syn_keyword': '#0000ff', 'syn_builtin': '#af00db',
    'syn_elm11_func': '#795e26', 'syn_elm11_const': '#267f99',
    'syn_string': '#a31515', 'syn_comment': '#008000',
    'syn_number': '#098658', 'syn_preproc': '#af00db',
}

_current: dict | None = None


def current() -> dict:
    global _current
    if _current is None:
        name = QSettings().value('ui/theme', 'dark')
        _current = LIGHT if name == 'light' else DARK
    return _current


def set_theme(name: str):
    global _current
    _current = LIGHT if name == 'light' else DARK
    QSettings().setValue('ui/theme', name)


def is_dark() -> bool:
    return current()['name'] == 'dark'


# ── Stylesheet builders (called with current()) ──────────────────────────────

def main_stylesheet(t: dict) -> str:
    return f"""
QMainWindow, QWidget        {{ background:{t['window_bg']}; color:{t['window_fg']}; }}
QMenuBar                    {{ background:{t['menubar_bg']}; color:{t['menubar_fg']}; }}
QMenuBar::item:selected     {{ background:{t['selection']}; }}
QMenu                       {{ background:{t['menubar_bg']}; color:{t['menubar_fg']}; border:1px solid {t['border']}; }}
QMenu::item:selected        {{ background:{t['selection']}; }}
QToolBar                    {{ background:{t['toolbar_bg']}; border:none; spacing:4px; padding:3px; }}
QTabWidget::pane            {{ border:1px solid {t['border']}; background:{t['window_bg']}; }}
QTabBar::tab {{
    background:{t['tab_bg']}; color:{t['tab_fg']}; padding:6px 16px;
    border:none; border-right:1px solid {t['window_bg']};
}}
QTabBar::tab:selected       {{ background:{t['tab_sel_bg']}; color:{t['tab_sel_fg']}; border-top:2px solid {t['tab_accent']}; }}
QTabBar::tab:hover          {{ background:{t['tree_hover']}; color:{t['tab_sel_fg']}; }}
QSplitter::handle           {{ background:{t['splitter']}; }}
QComboBox {{
    background:{t['combo_bg']}; color:{t['combo_fg']};
    border:1px solid {t['border']}; padding:3px 8px; min-width:150px;
}}
QComboBox::drop-down        {{ border:none; }}
QComboBox:disabled          {{ color:{t['btn_disabled_fg']}; background:{t['window_bg']}; border-color:{t['window_bg']}; }}
QComboBox QAbstractItemView {{ background:{t['menubar_bg']}; color:{t['combo_fg']}; selection-background-color:{t['selection']}; }}
QPushButton {{
    background:{t['btn_bg']}; color:{t['btn_fg']};
    border:1px solid {t['border']}; padding:4px 12px;
}}
QPushButton:hover           {{ background:{t['btn_hover']}; }}
QPushButton:pressed         {{ background:{t['btn_pressed']}; }}
QPushButton:checked         {{ background:{t['btn_pressed']}; border-color:{t['tab_accent']}; }}
QPushButton:disabled        {{ color:{t['btn_disabled_fg']}; }}
QStatusBar                  {{ background:{t['status_bg']}; color:{t['status_fg']}; font-size:9pt; }}
QLabel                      {{ background:transparent; }}
"""


def tree_stylesheet(t: dict) -> str:
    return f"""
QTreeView {{
    background:{t['tree_bg']}; color:{t['tree_fg']};
    border:none; font-size:10pt;
}}
QTreeView::item:hover    {{ background:{t['tree_hover']}; }}
QTreeView::item:selected {{ background:{t['tree_sel']}; color:{t['tab_sel_fg']}; }}
QScrollBar:vertical      {{ background:{t['tree_bg']}; width:8px; }}
QScrollBar::handle:vertical {{ background:{t['border']}; border-radius:4px; }}
"""


def dialog_stylesheet(t: dict) -> str:
    return f"""
QDialog  {{ background:{t['dlg_bg']}; color:{t['dlg_fg']}; }}
QWidget  {{ background:{t['dlg_bg']}; color:{t['dlg_fg']}; }}
QTabWidget::pane {{ border:1px solid {t['border']}; }}
QTabBar::tab {{
    background:{t['btn_bg']}; color:{t['dlg_fg']};
    padding:6px 14px; border:none;
}}
QTabBar::tab:selected {{ background:{t['selection']}; }}
QLabel   {{ background:transparent; }}
QLineEdit, QSpinBox {{
    background:{t['dlg_input_bg']}; color:{t['dlg_input_fg']};
    border:1px solid {t['border']}; padding:4px;
}}
QPushButton {{
    background:{t['btn_bg']}; color:{t['dlg_fg']};
    border:1px solid {t['border']}; padding:4px 10px;
}}
QPushButton:hover {{ background:{t['btn_hover']}; }}
"""
