"""Code editor widget with line numbers and auto-indent."""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QFontMetrics,
    QPalette, QKeyEvent, QTextCursor, QTextCharFormat,
)
from pathlib import Path

from .highlighter import LuaHighlighter, CHighlighter
from .settings import SettingsDialog
from . import theme

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


class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit with line numbers, syntax highlighting and auto-indent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path: Path | None = None
        self._highlighter = None

        self._lna = _LineNumberArea(self)

        self._apply_font()

        self.apply_theme()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.blockCountChanged.connect(self._update_lna_width)
        self.updateRequest.connect(self._update_lna)
        self.cursorPositionChanged.connect(self._highlight_current_line)

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
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(theme.current()['ed_curline']))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
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

    # ── Internal ─────────────────────────────────────────────────────────

    def _apply_highlighter(self, path: Path):
        suffix = path.suffix.lower()
        if suffix in ('.c', '.h'):
            self._highlighter = CHighlighter(self.document())
        else:
            self._highlighter = LuaHighlighter(self.document())
