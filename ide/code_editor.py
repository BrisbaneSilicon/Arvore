"""Code editor widget with line numbers and auto-indent."""
import hashlib
import os

from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QTextEdit, QLineEdit, QLabel, QToolButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QRect, QSize, QSettings, QEvent
from PyQt6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QFontMetrics,
    QPalette, QKeyEvent, QTextCursor, QTextCharFormat, QTextDocument,
    QShortcut, QKeySequence,
)
from pathlib import Path

from .highlighter import (
    LuaHighlighter, CHighlighter, MakefileHighlighter,
    SystemVerilogHighlighter, VHDLHighlighter,
)
from .settings import SettingsDialog
from . import theme


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _upload_hash_key(path: Path) -> str:
    # Normalise separators and (on Windows) case so that the same file
    # referenced via different spellings hits the same QSettings entry.
    normalised = os.path.normcase(os.path.normpath(str(path)))
    return f'uploads/hash/{normalised}'

LUA_INDENT_OPENERS  = ('do', 'then', 'else', 'elseif', 'repeat')
LUA_FUNC_STARTS     = ('function',)


class _LineNumberArea(QWidget):
    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor._paint_line_numbers(event)


class _FindBar(QWidget):
    """Inline find bar overlaid on the editor's top-right corner (Ctrl+F).

    Enter / Down → next, Shift+Enter / Up → previous, Esc → close. Typing
    searches incrementally; all matches are highlighted in the editor."""

    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self.editor = editor
        self.setObjectName('findBar')

        self._edit = QLineEdit(self)
        self._edit.setPlaceholderText('Find')
        self._edit.setClearButtonEnabled(True)
        self._count = QLabel('', self)
        self._case = QToolButton(self)
        self._case.setText('Aa')
        self._case.setCheckable(True)
        self._case.setToolTip('Match case')
        self._prev = QToolButton(self)
        self._prev.setText('▲')
        self._prev.setToolTip('Previous (Shift+Enter)')
        self._next = QToolButton(self)
        self._next.setText('▼')
        self._next.setToolTip('Next (Enter)')
        self._close = QToolButton(self)
        self._close.setText('✕')
        self._close.setToolTip('Close (Esc)')

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(4)
        lay.addWidget(self._edit, 1)
        lay.addWidget(self._count)
        lay.addWidget(self._case)
        lay.addWidget(self._prev)
        lay.addWidget(self._next)
        lay.addWidget(self._close)

        self._edit.textChanged.connect(lambda _: self.editor._find_incremental())
        self._prev.clicked.connect(lambda: self.editor._find_step(False))
        self._next.clicked.connect(lambda: self.editor._find_step(True))
        self._case.toggled.connect(lambda _: self.editor._find_incremental())
        self._close.clicked.connect(self.hide_bar)
        self._edit.installEventFilter(self)
        self.hide()

    # ── State accessors ──────────────────────────────────────────────────
    @property
    def query(self) -> str:
        return self._edit.text()

    @property
    def case_sensitive(self) -> bool:
        return self._case.isChecked()

    def set_count(self, idx: int, total: int):
        if not self.query:
            self._count.setText('')
        elif total == 0:
            self._count.setText('No results')
        else:
            self._count.setText(f'{idx}/{total}')

    # ── Show / hide ──────────────────────────────────────────────────────
    def show_bar(self, seed: str = ''):
        if seed:
            self._edit.setText(seed)
        self.show()
        self.raise_()
        self.editor._reposition_find_bar()
        self._edit.setFocus()
        self._edit.selectAll()
        self.editor._find_incremental()

    def hide_bar(self):
        self.hide()
        self.editor._clear_match_highlights()
        self.editor.setFocus()

    # ── Keyboard ─────────────────────────────────────────────────────────
    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            if key == Qt.Key.Key_Escape:
                self.hide_bar()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.editor._find_step(not shift)
                return True
            if key == Qt.Key.Key_Down:
                self.editor._find_step(True)
                return True
            if key == Qt.Key.Key_Up:
                self.editor._find_step(False)
                return True
        return super().eventFilter(obj, event)

    def apply_theme(self):
        t = theme.current()
        self.setStyleSheet(f"""
            QWidget#findBar {{
                background: {t['ed_linenum_bg']};
                border: 1px solid {t['border']};
                border-radius: 4px;
            }}
            QLineEdit {{
                background: {t['ed_bg']}; color: {t['ed_fg']};
                border: 1px solid {t['border']}; border-radius: 3px;
                padding: 2px 4px;
                selection-background-color: {t['selection']};
            }}
            QLabel {{ color: {t['ed_fg']}; }}
            QToolButton {{
                background: transparent; color: {t['ed_fg']};
                border: none; padding: 2px 5px; border-radius: 3px;
            }}
            QToolButton:hover {{ background: {t['ed_curline']}; }}
            QToolButton:checked {{ background: {t['selection']}; }}
        """)


class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit with line numbers, syntax highlighting and auto-indent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path: Path | None = None
        self._highlighter = None
        self._uploaded_revision: int | None = None
        self._match_selections: list = []

        self._lna = _LineNumberArea(self)
        self._find_bar = _FindBar(self)

        self._apply_font()

        self.apply_theme()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.blockCountChanged.connect(self._update_lna_width)
        self.updateRequest.connect(self._update_lna)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        find_sc = QShortcut(QKeySequence.StandardKey.Find, self, self._show_find)
        find_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        self._update_lna_width(0)
        self._highlight_current_line()

    def _apply_font(self):
        """Read font settings and apply to the editor."""
        font = QFont(SettingsDialog.editor_font_family(),
                     SettingsDialog.editor_font_size())
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setFont(font)
        self.setTabStopDistance(4 * QFontMetrics(font).horizontalAdvance(' '))

    def apply_theme(self):
        """Apply current theme colours and font to editor."""
        self._apply_font()
        t = theme.current()
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(t['ed_bg']))
        pal.setColor(QPalette.ColorRole.Text, QColor(t['ed_fg']))
        self.setPalette(pal)
        self._highlight_current_line()
        self._lna.update()
        if hasattr(self, '_find_bar'):
            self._find_bar.apply_theme()
        # Re-create highlighter so it picks up new syntax colours
        if self.file_path:
            self._apply_highlighter(self.file_path)

    # ── Public API ────────────────────────────────────────────────────────

    def set_file(self, path: Path):
        self.file_path = path
        self._apply_highlighter(path)
        text = path.read_text(encoding='utf-8', errors='replace')
        self.setPlainText(text)
        self.document().setModified(False)

        stored_hash = QSettings().value(_upload_hash_key(path), '')
        if stored_hash and stored_hash == _content_hash(text):
            self._uploaded_revision = self.document().revision()
        else:
            self._uploaded_revision = None

    def mark_uploaded(self):
        """Record the current document state as the last-uploaded state."""
        self._uploaded_revision = self.document().revision()
        if self.file_path is not None:
            QSettings().setValue(
                _upload_hash_key(self.file_path),
                _content_hash(self.toPlainText()),
            )

    @property
    def is_stale(self) -> bool:
        """True if the file has never been uploaded, or has been modified since."""
        if self.file_path is None:
            return False
        if self._uploaded_revision is None:
            return True
        return self.document().revision() != self._uploaded_revision

    def save(self) -> bool:
        if self.file_path is None:
            return False
        self.file_path.write_text(self.toPlainText(), encoding='utf-8')
        self.document().setModified(False)
        return True

    def save_as(self, path: Path) -> bool:
        self.file_path = path
        self._apply_highlighter(path)
        return self.save()

    @property
    def is_lua(self) -> bool:
        return bool(self.file_path) and self.file_path.suffix.lower() == '.lua'

    @property
    def is_c(self) -> bool:
        return bool(self.file_path) and self.file_path.suffix.lower() in ('.c', '.h')

    # ── Line number area ─────────────────────────────────────────────────

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 8 + QFontMetrics(self.font()).horizontalAdvance('9') * digits + 8

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._lna.setGeometry(QRect(cr.left(), cr.top(),
                                    self.line_number_area_width(), cr.height()))
        self._reposition_find_bar()

    def _update_lna_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_lna(self, rect, dy):
        if dy:
            self._lna.scroll(0, dy)
        else:
            self._lna.update(0, rect.y(), self._lna.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_lna_width(0)

    def _highlight_current_line(self):
        self._refresh_extra_selections()

    def _refresh_extra_selections(self):
        """Combine the current-line highlight with any find-match highlights."""
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(theme.current()['ed_curline']))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
        # Match highlights are appended last so they paint over the current line.
        extra.extend(self._match_selections)
        self.setExtraSelections(extra)

    def _paint_line_numbers(self, event):
        t = theme.current()
        painter = QPainter(self._lna)
        painter.fillRect(event.rect(), QColor(t['ed_linenum_bg']))

        block        = self.firstVisibleBlock()
        block_num    = block.blockNumber()
        top          = round(self.blockBoundingGeometry(block)
                             .translated(self.contentOffset()).top())
        bottom       = top + round(self.blockBoundingRect(block).height())
        current_line = self.textCursor().blockNumber()
        fm_height    = self.fontMetrics().height()
        lna_width    = self._lna.width()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                color = t['ed_linenum_cur'] if block_num == current_line else t['ed_linenum_fg']
                painter.setPen(QColor(color))
                painter.drawText(0, top, lna_width - 4, fm_height,
                                 Qt.AlignmentFlag.AlignRight, str(block_num + 1))
            block     = block.next()
            top       = bottom
            bottom    = top + round(self.blockBoundingRect(block).height())
            block_num += 1

    # ── Key handling ─────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._handle_return()
            return

        if key == Qt.Key.Key_Tab:
            # Indent selection, or insert spaces
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._indent_selection(cursor, dedent=False)
            else:
                self.insertPlainText('    ')
            return

        if key == Qt.Key.Key_Backtab:
            cursor = self.textCursor()
            self._indent_selection(cursor, dedent=True)
            return

        super().keyPressEvent(event)

    def _handle_return(self):
        cursor   = self.textCursor()
        line     = cursor.block().text()
        stripped = line.strip()
        indent   = len(line) - len(line.lstrip())
        extra    = 0

        if self.is_lua:
            if stripped.endswith(LUA_INDENT_OPENERS) or \
               any(stripped.startswith(f) for f in LUA_FUNC_STARTS):
                extra = 4
        elif self.is_c:
            if stripped.endswith('{'):
                extra = 4

        super().keyPressEvent(
            QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return,
                      Qt.KeyboardModifier.NoModifier))
        self.insertPlainText(' ' * (indent + extra))

    def _indent_selection(self, cursor: QTextCursor, dedent: bool):
        start = cursor.selectionStart()
        end   = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.beginEditBlock()
        while cursor.position() <= end:
            if dedent:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                line = cursor.block().text()
                spaces = min(4, len(line) - len(line.lstrip(' ')))
                for _ in range(spaces):
                    cursor.deleteChar()
            else:
                cursor.insertText('    ')
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    # ── Find (Ctrl+F) ─────────────────────────────────────────────────────

    def _show_find(self):
        """Open the find bar, seeding it with the current single-line selection."""
        cur = self.textCursor()
        seed = cur.selectedText() if cur.hasSelection() else ''
        if ' ' in seed:                    # multi-line selection — don't seed
            seed = ''
        self._find_bar.show_bar(seed)

    def _reposition_find_bar(self):
        if not self._find_bar.isVisible():
            return
        bar = self._find_bar
        w = min(440, max(280, self.viewport().width() - 24))
        bar.setFixedWidth(w)
        bar.adjustSize()
        vsb = self.verticalScrollBar()
        sb = vsb.width() if vsb.isVisible() else 0
        x = self.width() - w - sb - 8
        bar.move(max(self.line_number_area_width() + 4, x), 4)

    def _find_flags(self, backward: bool = False) -> 'QTextDocument.FindFlag':
        flags = QTextDocument.FindFlag(0)
        if self._find_bar.case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def _match_cursors(self) -> list:
        """Every match of the current query, as QTextCursors."""
        text = self._find_bar.query
        if not text:
            return []
        doc = self.document()
        flags = self._find_flags()
        out, cur = [], QTextCursor(doc)
        while True:
            cur = doc.find(text, cur, flags)
            if cur.isNull():
                break
            out.append(cur)
        return out

    def _update_match_highlights(self) -> list:
        cursors = self._match_cursors()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(theme.current()['selection']))
        sels = []
        for c in cursors:
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            sel.cursor = c
            sels.append(sel)
        self._match_selections = sels
        self._refresh_extra_selections()
        return cursors

    def _clear_match_highlights(self):
        self._match_selections = []
        self._refresh_extra_selections()

    def _find_incremental(self):
        """Re-highlight matches and (re)select the one at/after the cursor as
        the query changes."""
        cursors = self._update_match_highlights()
        text = self._find_bar.query
        if text:
            # Search from the start of the current selection so the match under
            # the cursor stays selected as the query grows.
            cur = self.textCursor()
            cur.setPosition(cur.selectionStart())
            self.setTextCursor(cur)
            self._find_step(True, _cursors=cursors)
        else:
            self._find_bar.set_count(0, 0)

    def _find_step(self, forward: bool, _cursors: list | None = None):
        """Move to the next/previous match, wrapping around at the ends."""
        text = self._find_bar.query
        if not text:
            self._find_bar.set_count(0, 0)
            return
        flags = self._find_flags(backward=not forward)
        if not self.find(text, flags):
            cur = self.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start if forward
                             else QTextCursor.MoveOperation.End)
            self.setTextCursor(cur)
            self.find(text, flags)
        cursors = _cursors if _cursors is not None else self._match_cursors()
        self._update_find_count(cursors)

    def _update_find_count(self, cursors: list):
        sel = self.textCursor()
        idx = 0
        if sel.hasSelection():
            start = sel.selectionStart()
            for i, c in enumerate(cursors, 1):
                if c.selectionStart() == start:
                    idx = i
                    break
        self._find_bar.set_count(idx, len(cursors))

    # ── Internal ─────────────────────────────────────────────────────────

    def _apply_highlighter(self, path: Path):
        suffix = path.suffix.lower()
        name = path.name
        if suffix in ('.c', '.h'):
            self._highlighter = CHighlighter(self.document())
        elif suffix in ('.sv', '.svh'):
            self._highlighter = SystemVerilogHighlighter(self.document())
        elif suffix in ('.vhd', '.vhdl'):
            self._highlighter = VHDLHighlighter(self.document())
        elif name == 'Makefile' or suffix in ('.mk',):
            self._highlighter = MakefileHighlighter(self.document())
        else:
            self._highlighter = LuaHighlighter(self.document())
