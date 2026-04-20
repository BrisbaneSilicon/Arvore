"""Centralised colour themes (dark / light)."""
from PyQt6.QtCore import QSettings

DARK = {
    'name': 'dark',
    # Main chrome — Afterglow palette
    'window_bg': '#2e2e2e', 'window_fg': '#d6d6d6',
    'menubar_bg': '#262626', 'menubar_fg': '#d6d6d6',
    'toolbar_bg': '#262626',
    'selection':  '#5a647e',
    'tab_bg': '#262626', 'tab_fg': '#797979',
    'tab_sel_bg': '#2e2e2e', 'tab_sel_fg': '#d6d6d6',
    'tab_accent': '#cc7833',
    'splitter':   '#404040',
    'combo_bg': '#393939', 'combo_fg': '#d6d6d6',
    'btn_bg': '#393939', 'btn_fg': '#d6d6d6',
    'btn_hover': '#484848', 'btn_pressed': '#5a647e',
    'btn_disabled_fg': '#555',
    'border': '#404040',
    'status_bg': '#262626', 'status_fg': '#d6d6d6',
    'status_on_bg': '#cc7833', 'status_on_fg': '#fff',
    # Scrollbars
    'scroll_bg': '#1f1f1f', 'scroll_handle': '#5a5a5a', 'scroll_handle_hover': '#7a7a7a',
    # Editor
    'ed_bg': '#2e2e2e', 'ed_fg': '#d6d6d6',
    'ed_linenum_bg': '#262626', 'ed_linenum_fg': '#797979', 'ed_linenum_cur': '#d6d6d6',
    'ed_curline': '#333435',
    # Terminal / build
    'term_bg': '#262626', 'term_fg': '#d6d6d6',
    'term_info': '#6d9cbe', 'term_error': '#c45330',
    'term_warning': '#e5b567', 'term_success': '#b4c973',
    # Tree
    'tree_bg': '#262626', 'tree_fg': '#d6d6d6',
    'tree_hover': '#333435', 'tree_sel': '#5a647e',
    # Dialogs
    'dlg_bg': '#2e2e2e', 'dlg_fg': '#d6d6d6',
    'dlg_input_bg': '#262626', 'dlg_input_fg': '#d6d6d6',
    # Syntax — Afterglow / idlefingers derived
    'syn_keyword': '#cc7833', 'syn_builtin': '#c45837',
    'syn_elm11_func': '#ffc66d', 'syn_elm11_const': '#6d9cbe',
    'syn_string': '#b4c973', 'syn_comment': '#797979',
    'syn_number': '#b4c973', 'syn_preproc': '#a1617a',
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
    # Scrollbars
    'scroll_bg': '#e8e8e8', 'scroll_handle': '#a0a0a0', 'scroll_handle_hover': '#707070',
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

SOLARIZED_DARK = {
    'name': 'solarized_dark',
    # Main chrome — Solarized base03/base02
    'window_bg': '#002b36', 'window_fg': '#839496',
    'menubar_bg': '#073642', 'menubar_fg': '#93a1a1',
    'toolbar_bg': '#073642',
    'selection':  '#073642',
    'tab_bg': '#073642', 'tab_fg': '#586e75',
    'tab_sel_bg': '#002b36', 'tab_sel_fg': '#93a1a1',
    'tab_accent': '#268bd2',
    'splitter':   '#073642',
    'combo_bg': '#073642', 'combo_fg': '#839496',
    'btn_bg': '#073642', 'btn_fg': '#839496',
    'btn_hover': '#0a4050', 'btn_pressed': '#073642',
    'btn_disabled_fg': '#586e75',
    'border': '#073642',
    'status_bg': '#073642', 'status_fg': '#839496',
    'status_on_bg': '#268bd2', 'status_on_fg': '#fdf6e3',
    # Scrollbars
    'scroll_bg': '#002b36', 'scroll_handle': '#586e75', 'scroll_handle_hover': '#839496',
    # Editor
    'ed_bg': '#002b36', 'ed_fg': '#839496',
    'ed_linenum_bg': '#073642', 'ed_linenum_fg': '#586e75', 'ed_linenum_cur': '#93a1a1',
    'ed_curline': '#073642',
    # Terminal / build
    'term_bg': '#002b36', 'term_fg': '#839496',
    'term_info': '#268bd2', 'term_error': '#dc322f',
    'term_warning': '#b58900', 'term_success': '#859900',
    # Tree
    'tree_bg': '#073642', 'tree_fg': '#839496',
    'tree_hover': '#0a4050', 'tree_sel': '#073642',
    # Dialogs
    'dlg_bg': '#073642', 'dlg_fg': '#839496',
    'dlg_input_bg': '#002b36', 'dlg_input_fg': '#839496',
    # Syntax — Solarized accents
    'syn_keyword': '#859900', 'syn_builtin': '#6c71c4',
    'syn_elm11_func': '#268bd2', 'syn_elm11_const': '#2aa198',
    'syn_string': '#2aa198', 'syn_comment': '#586e75',
    'syn_number': '#d33682', 'syn_preproc': '#cb4b16',
}

SOLARIZED_LIGHT = {
    'name': 'solarized_light',
    # Main chrome — Solarized base3/base2
    'window_bg': '#fdf6e3', 'window_fg': '#657b83',
    'menubar_bg': '#eee8d5', 'menubar_fg': '#586e75',
    'toolbar_bg': '#eee8d5',
    'selection':  '#eee8d5',
    'tab_bg': '#eee8d5', 'tab_fg': '#93a1a1',
    'tab_sel_bg': '#fdf6e3', 'tab_sel_fg': '#586e75',
    'tab_accent': '#268bd2',
    'splitter':   '#eee8d5',
    'combo_bg': '#eee8d5', 'combo_fg': '#657b83',
    'btn_bg': '#eee8d5', 'btn_fg': '#657b83',
    'btn_hover': '#e6dfca', 'btn_pressed': '#eee8d5',
    'btn_disabled_fg': '#93a1a1',
    'border': '#eee8d5',
    'status_bg': '#eee8d5', 'status_fg': '#657b83',
    'status_on_bg': '#268bd2', 'status_on_fg': '#fdf6e3',
    # Scrollbars
    'scroll_bg': '#eee8d5', 'scroll_handle': '#93a1a1', 'scroll_handle_hover': '#586e75',
    # Editor
    'ed_bg': '#fdf6e3', 'ed_fg': '#657b83',
    'ed_linenum_bg': '#eee8d5', 'ed_linenum_fg': '#93a1a1', 'ed_linenum_cur': '#586e75',
    'ed_curline': '#eee8d5',
    # Terminal / build
    'term_bg': '#fdf6e3', 'term_fg': '#657b83',
    'term_info': '#268bd2', 'term_error': '#dc322f',
    'term_warning': '#b58900', 'term_success': '#859900',
    # Tree
    'tree_bg': '#eee8d5', 'tree_fg': '#657b83',
    'tree_hover': '#e6dfca', 'tree_sel': '#eee8d5',
    # Dialogs
    'dlg_bg': '#eee8d5', 'dlg_fg': '#657b83',
    'dlg_input_bg': '#fdf6e3', 'dlg_input_fg': '#657b83',
    # Syntax — Solarized accents (same as dark)
    'syn_keyword': '#859900', 'syn_builtin': '#6c71c4',
    'syn_elm11_func': '#268bd2', 'syn_elm11_const': '#2aa198',
    'syn_string': '#2aa198', 'syn_comment': '#93a1a1',
    'syn_number': '#d33682', 'syn_preproc': '#cb4b16',
}

THEMES = {
    'dark':             DARK,
    'light':            LIGHT,
    'solarized_dark':   SOLARIZED_DARK,
    'solarized_light':  SOLARIZED_LIGHT,
}

_current: dict | None = None


def current() -> dict:
    global _current
    if _current is None:
        name = QSettings().value('ui/theme', 'dark')
        _current = THEMES.get(name, DARK)
    return _current


def set_theme(name: str):
    global _current
    _current = THEMES.get(name, DARK)
    QSettings().setValue('ui/theme', name)


def is_dark() -> bool:
    return current()['name'] in ('dark', 'solarized_dark')


def theme_names() -> list[str]:
    """Return display names for all available themes."""
    return ['Afterglow (Dark)', 'Light', 'Solarized Dark', 'Solarized Light']


def theme_ids() -> list[str]:
    """Return internal IDs matching theme_names() order."""
    return ['dark', 'light', 'solarized_dark', 'solarized_light']


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
QScrollBar:vertical {{
    background:{t['scroll_bg']}; width:12px; margin:0;
}}
QScrollBar:horizontal {{
    background:{t['scroll_bg']}; height:12px; margin:0;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background:{t['scroll_handle']}; border-radius:5px; min-height:24px; min-width:24px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background:{t['scroll_handle_hover']};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    background:none; border:none; height:0; width:0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{ background:none; }}
"""


def tree_stylesheet(t: dict) -> str:
    return f"""
QTreeView {{
    background:{t['tree_bg']}; color:{t['tree_fg']};
    border:none; font-size:10pt;
}}
QTreeView::item:hover    {{ background:{t['tree_hover']}; }}
QTreeView::item:selected {{ background:{t['tree_sel']}; color:{t['tab_sel_fg']}; }}
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
