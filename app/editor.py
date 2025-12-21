"""
Code Editor Widget for EZ IDE
Tabbed code editor with syntax highlighting, line numbers, and editing features
"""

import os
from pathlib import Path
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QTabWidget,
    QLabel, QFrame, QMessageBox, QFileDialog, QMenu, QTextEdit
)
from PyQt6.QtCore import (
    Qt, QRect, QSize, pyqtSignal, QTimer, QRegularExpression
)
from PyQt6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QFontMetrics, QTextCursor,
    QKeySequence, QAction, QPaintEvent, QTextCharFormat, QTextDocument,
    QKeyEvent, QWheelEvent
)

from app.settings import SettingsManager
from app.themes import Theme, ThemeManager
from app.syntax import EZHighlighter, GenericHighlighter


class LineNumberArea(QWidget):
    """Line number display widget"""
    
    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self.code_editor = editor
    
    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)
    
    def paintEvent(self, event: QPaintEvent):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Single file code editor with line numbers and syntax highlighting"""
    
    modified_changed = pyqtSignal(bool)
    cursor_position_changed = pyqtSignal(int, int)  # line, column
    
    def __init__(self, theme: Theme, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.settings_manager = settings
        self.file_path: Optional[str] = None
        self._highlighter: Optional[EZHighlighter] = None
        self._debug_line: int = -1  # Current debug line (-1 = not debugging)
        
        self._setup_editor()
        self._setup_line_numbers()
        self._setup_connections()
        self._apply_theme()
    
    def _setup_editor(self):
        """Set up editor configuration"""
        settings = self.settings_manager.settings.editor
        
        # Font
        font = QFont(settings.font_family, settings.font_size)
        font.setFixedPitch(True)
        self.setFont(font)
        
        # Tab width
        metrics = QFontMetrics(font)
        self.setTabStopDistance(metrics.horizontalAdvance(' ') * settings.tab_width)
        
        # Word wrap
        if settings.word_wrap:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Cursor width
        self.setCursorWidth(2)
    
    def _setup_line_numbers(self):
        """Set up line number area"""
        self.line_number_area = LineNumberArea(self)
        
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        self.update_line_number_area_width(0)
        self.highlight_current_line()
    
    def _setup_connections(self):
        """Set up signal connections"""
        self.modificationChanged.connect(self.modified_changed.emit)
        self.cursorPositionChanged.connect(self._emit_cursor_position)
    
    def _apply_theme(self):
        """Apply theme colors to editor"""
        settings = self.settings_manager.settings.editor
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.theme.editor_background};
                color: {self.theme.editor_foreground};
                selection-background-color: {self.theme.editor_selection};
                border: none;
                font-family: "{settings.font_family}";
                font-size: {settings.font_size}pt;
            }}
        """)
        
        # Update line numbers
        self.line_number_area.update()
        self.highlight_current_line()
    
    def set_theme(self, theme: Theme):
        """Update the theme"""
        self.theme = theme
        self._apply_theme()
        if self._highlighter:
            self._highlighter.set_theme(theme)
    
    def refresh_settings(self):
        """Re-apply all settings from settings manager"""
        settings = self.settings_manager.settings.editor
        
        # Re-apply theme which now includes font settings in stylesheet
        self._apply_theme()
        
        # Also set font programmatically for line number area
        font = QFont(settings.font_family, settings.font_size)
        font.setFixedPitch(True)
        self.line_number_area.setFont(font)
        
        # Tab width
        self._update_tab_width()
        
        # Word wrap
        if settings.word_wrap:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Line numbers - update width
        self.update_line_number_area_width(0)
        self.line_number_area.update()
        
        # Current line highlight (already called in _apply_theme but call again to be sure)
        self.highlight_current_line()
        
        # Force repaint
        self.viewport().update()
        self.update()
    
    def line_number_area_width(self) -> int:
        """Calculate width needed for line numbers"""
        if not self.settings_manager.settings.editor.show_line_numbers:
            return 0
        
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        # Minimum 4 digits width + padding
        digits = max(4, digits)
        space = 16 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self, _):
        """Update the viewport margin for line numbers"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect: QRect, dy: int):
        """Update line number area on scroll"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), 
                                         self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
    
    def resizeEvent(self, event):
        """Handle resize to update line number area"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )
    
    def line_number_area_paint_event(self, event: QPaintEvent):
        """Paint line numbers"""
        if not self.settings_manager.settings.editor.show_line_numbers:
            return
        
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(self.theme.editor_gutter_bg))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        current_line = self.textCursor().blockNumber()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                
                if block_number == current_line:
                    painter.setPen(QColor(self.theme.editor_foreground))
                else:
                    painter.setPen(QColor(self.theme.editor_gutter_fg))
                
                painter.drawText(
                    0, top,
                    self.line_number_area.width() - 8, 
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number
                )
            
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
    
    def highlight_current_line(self):
        """Highlight the current line and debug line"""
        extra_selections = []
        
        # Debug line highlight (takes precedence)
        if self._debug_line > 0:
            block = self.document().findBlockByLineNumber(self._debug_line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                # Use a distinctive yellow/orange color for debug line
                debug_color = QColor("#3d3d00")  # Dark yellow background
                selection.format.setBackground(debug_color)
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                extra_selections.append(selection)
        
        # Current cursor line highlight (if not on debug line)
        if (self.settings_manager.settings.editor.highlight_current_line and 
            not self.isReadOnly()):
            current_block = self.textCursor().blockNumber()
            if self._debug_line <= 0 or current_block != self._debug_line - 1:
                selection = QTextEdit.ExtraSelection()
                line_color = QColor(self.theme.editor_line_highlight)
                selection.format.setBackground(line_color)
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                selection.cursor = self.textCursor()
                selection.cursor.clearSelection()
                extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
    def _emit_cursor_position(self):
        """Emit cursor position signal"""
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.cursor_position_changed.emit(line, column)
    
    def set_debug_line(self, line: int):
        """
        Set the current debug line (1-indexed)
        
        Args:
            line: Line number to highlight, or -1 to clear
        """
        self._debug_line = line
        self.highlight_current_line()
        
        # Scroll to the debug line if valid
        if line > 0:
            block = self.document().findBlockByLineNumber(line - 1)
            if block.isValid():
                cursor = QTextCursor(block)
                self.setTextCursor(cursor)
                self.centerCursor()
    
    def clear_debug_line(self):
        """Clear the debug line highlight"""
        self._debug_line = -1
        self.highlight_current_line()
    
    def set_file(self, filepath: str):
        """Load a file into the editor"""
        self.file_path = filepath
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.setPlainText(content)
            self.document().setModified(False)
            
            # Set up appropriate highlighter
            self._setup_highlighter(filepath)
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    content = f.read()
                self.setPlainText(content)
                self.document().setModified(False)
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Could not read file: {e}")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Could not open file: {e}")
    
    def _setup_highlighter(self, filepath: str):
        """Set up syntax highlighter based on file extension"""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == '.ez':
            self._highlighter = EZHighlighter(self.document(), self.theme)
        else:
            # Use generic highlighter for other files
            self._highlighter = GenericHighlighter(self.document(), self.theme, ext)
    
    def save_file(self, filepath: str = None) -> bool:
        """Save the file"""
        if filepath:
            self.file_path = filepath
        
        if not self.file_path:
            return False
        
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            self.document().setModified(False)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Could not save file: {e}")
            return False
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        settings = self.settings_manager.settings.editor
        
        # Auto-indent on Enter
        if event.key() == Qt.Key.Key_Return and settings.auto_indent:
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            
            # Get leading whitespace
            indent = ""
            for char in text:
                if char in (' ', '\t'):
                    indent += char
                else:
                    break
            
            # Check if line ends with { to add extra indent
            stripped = text.rstrip()
            if stripped.endswith('{'):
                if settings.use_spaces:
                    indent += ' ' * settings.tab_width
                else:
                    indent += '\t'
            
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        
        # Tab handling
        if event.key() == Qt.Key.Key_Tab:
            if settings.use_spaces:
                self.insertPlainText(' ' * settings.tab_width)
            else:
                self.insertPlainText('\t')
            return
        
        # Bracket matching - auto-close brackets
        if settings.bracket_matching:
            brackets = {'{': '}', '[': ']', '(': ')', '"': '"', "'": "'"}
            text = event.text()
            if text in brackets:
                cursor = self.textCursor()
                cursor.insertText(text + brackets[text])
                cursor.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(cursor)
                return
        
        super().keyPressEvent(event)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zoom"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def zoom_in(self):
        """Increase font size"""
        font = self.font()
        size = font.pointSize()
        if size < 48:
            font.setPointSize(size + 1)
            self.setFont(font)
            self._update_tab_width()
    
    def zoom_out(self):
        """Decrease font size"""
        font = self.font()
        size = font.pointSize()
        if size > 6:
            font.setPointSize(size - 1)
            self.setFont(font)
            self._update_tab_width()
    
    def reset_zoom(self):
        """Reset to default font size"""
        size = self.settings_manager.settings.editor.font_size
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self._update_tab_width()
    
    def _update_tab_width(self):
        """Update tab stop distance after font change"""
        tab_width = self.settings_manager.settings.editor.tab_width
        metrics = QFontMetrics(self.font())
        self.setTabStopDistance(metrics.horizontalAdvance(' ') * tab_width)


class EditorTabs(QTabWidget):
    """Tabbed editor widget managing multiple code editors"""
    
    file_opened = pyqtSignal(str)
    file_saved = pyqtSignal(str)
    file_closed = pyqtSignal(str)
    current_file_changed = pyqtSignal(str)
    cursor_position_changed = pyqtSignal(int, int)
    
    def __init__(self, settings: SettingsManager, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.theme_manager = theme_manager
        self.editors: Dict[str, CodeEditor] = {}  # filepath -> editor
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Set up the tab widget"""
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setUsesScrollButtons(True)
        
        # Enable context menu on tabs
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
    def _setup_connections(self):
        """Set up signal connections"""
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_current_changed)
        self.customContextMenuRequested.connect(self._show_tab_context_menu)
    
    def open_file(self, filepath: str):
        """Open a file in a new or existing tab"""
        filepath = os.path.abspath(filepath)
        
        # Check if already open
        if filepath in self.editors:
            # Switch to existing tab
            for i in range(self.count()):
                if self.widget(i) == self.editors[filepath]:
                    self.setCurrentIndex(i)
                    return
        
        # Create new editor
        editor = CodeEditor(
            self.theme_manager.get_current_theme(),
            self.settings,
            self
        )
        editor.set_file(filepath)
        editor.modified_changed.connect(lambda m: self._on_modified_changed(filepath, m))
        editor.cursor_position_changed.connect(self.cursor_position_changed.emit)
        
        # Add tab
        self.editors[filepath] = editor
        filename = os.path.basename(filepath)
        index = self.addTab(editor, filename)
        self.setTabToolTip(index, filepath)
        self.setCurrentIndex(index)
        
        # Add to recent files
        self.settings.add_recent_file(filepath)
        
        self.file_opened.emit(filepath)
    
    def new_file(self, initial_content: str = ""):
        """Create a new untitled file"""
        # Find unique untitled name
        count = 1
        while True:
            name = f"Untitled-{count}"
            filepath = f"__untitled_{count}__"
            if filepath not in self.editors:
                break
            count += 1
        
        editor = CodeEditor(
            self.theme_manager.get_current_theme(),
            self.settings,
            self
        )
        editor.setPlainText(initial_content)
        editor.modified_changed.connect(lambda m: self._on_modified_changed(filepath, m))
        editor.cursor_position_changed.connect(self.cursor_position_changed.emit)
        
        # Set up EZ highlighter by default for new files
        editor._highlighter = EZHighlighter(editor.document(), editor.theme)
        
        self.editors[filepath] = editor
        index = self.addTab(editor, name)
        self.setCurrentIndex(index)
    
    def save_current(self) -> bool:
        """Save the current file"""
        editor = self.currentWidget()
        if not isinstance(editor, CodeEditor):
            return False
        
        # Find filepath for this editor
        filepath = None
        for path, ed in self.editors.items():
            if ed == editor:
                filepath = path
                break
        
        if filepath and filepath.startswith("__untitled_"):
            # Need to save as
            return self.save_current_as()
        
        if editor.save_file():
            self.file_saved.emit(filepath)
            return True
        return False
    
    def save_current_as(self) -> bool:
        """Save current file with new name"""
        editor = self.currentWidget()
        if not isinstance(editor, CodeEditor):
            return False
        
        # Find old filepath
        old_filepath = None
        for path, ed in self.editors.items():
            if ed == editor:
                old_filepath = path
                break
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save As",
            str(Path.home()),
            "EZ Files (*.ez);;All Files (*)"
        )
        
        if filepath:
            # Update references
            if old_filepath in self.editors:
                del self.editors[old_filepath]
            self.editors[filepath] = editor
            
            # Update tab
            index = self.currentIndex()
            self.setTabText(index, os.path.basename(filepath))
            self.setTabToolTip(index, filepath)
            
            if editor.save_file(filepath):
                self.file_saved.emit(filepath)
                self.settings.add_recent_file(filepath)
                return True
        
        return False
    
    def save_all(self):
        """Save all open files"""
        for filepath, editor in self.editors.items():
            if not filepath.startswith("__untitled_"):
                if editor.document().isModified():
                    editor.save_file()
                    self.file_saved.emit(filepath)
    
    def close_tab(self, index: int) -> bool:
        """Close a tab, prompting to save if modified"""
        editor = self.widget(index)
        if not isinstance(editor, CodeEditor):
            self.removeTab(index)
            return True
        
        # Find filepath
        filepath = None
        for path, ed in self.editors.items():
            if ed == editor:
                filepath = path
                break
        
        # Check if modified
        if editor.document().isModified():
            name = os.path.basename(filepath) if filepath else "Untitled"
            reply = QMessageBox.question(
                self, "Save Changes",
                f"'{name}' has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            elif reply == QMessageBox.StandardButton.Save:
                if filepath and filepath.startswith("__untitled_"):
                    if not self.save_current_as():
                        return False
                else:
                    if not editor.save_file():
                        return False
        
        # Remove from editors dict
        if filepath in self.editors:
            del self.editors[filepath]
        
        self.removeTab(index)
        self.file_closed.emit(filepath or "")
        return True
    
    def close_all_tabs(self) -> bool:
        """Close all tabs"""
        while self.count() > 0:
            if not self.close_tab(0):
                return False
        return True
    
    def _on_current_changed(self, index: int):
        """Handle current tab change"""
        if index < 0:
            self.current_file_changed.emit("")
            return
        
        editor = self.widget(index)
        if isinstance(editor, CodeEditor):
            for filepath, ed in self.editors.items():
                if ed == editor:
                    self.current_file_changed.emit(filepath)
                    return
    
    def _on_modified_changed(self, filepath: str, modified: bool):
        """Update tab title when modified state changes"""
        if filepath not in self.editors:
            return
        
        editor = self.editors[filepath]
        for i in range(self.count()):
            if self.widget(i) == editor:
                name = os.path.basename(filepath)
                if filepath.startswith("__untitled_"):
                    name = f"Untitled-{filepath.split('_')[2]}"
                if modified:
                    name = "• " + name
                self.setTabText(i, name)
                break
    
    def _show_tab_context_menu(self, pos):
        """Show context menu for tabs"""
        index = self.tabBar().tabAt(pos)
        if index < 0:
            return
        
        menu = QMenu(self)
        
        close_action = menu.addAction("Close")
        close_action.triggered.connect(lambda: self.close_tab(index))
        
        close_others = menu.addAction("Close Others")
        close_others.triggered.connect(lambda: self._close_other_tabs(index))
        
        close_all = menu.addAction("Close All")
        close_all.triggered.connect(self.close_all_tabs)
        
        menu.addSeparator()
        
        copy_path = menu.addAction("Copy Path")
        copy_path.triggered.connect(lambda: self._copy_tab_path(index))
        
        menu.exec(self.tabBar().mapToGlobal(pos))
    
    def _close_other_tabs(self, keep_index: int):
        """Close all tabs except the specified one"""
        # Close tabs after keep_index first (in reverse)
        for i in range(self.count() - 1, keep_index, -1):
            if not self.close_tab(i):
                return
        # Close tabs before keep_index (always removing index 0)
        for i in range(keep_index):
            if not self.close_tab(0):
                return
    
    def _copy_tab_path(self, index: int):
        """Copy the file path of a tab to clipboard"""
        editor = self.widget(index)
        for filepath, ed in self.editors.items():
            if ed == editor and not filepath.startswith("__untitled_"):
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(filepath)
                return
    
    def get_current_editor(self) -> Optional[CodeEditor]:
        """Get the current editor widget"""
        widget = self.currentWidget()
        if isinstance(widget, CodeEditor):
            return widget
        return None
    
    def get_current_filepath(self) -> Optional[str]:
        """Get filepath of current tab"""
        editor = self.currentWidget()
        for filepath, ed in self.editors.items():
            if ed == editor:
                return filepath if not filepath.startswith("__untitled_") else None
        return None
    
    def get_editor_for_file(self, filepath: str) -> Optional[CodeEditor]:
        """Get the editor for a specific filepath"""
        filepath = os.path.abspath(filepath)
        return self.editors.get(filepath)
    
    def set_theme(self, theme: Theme):
        """Update theme for all editors"""
        for editor in self.editors.values():
            editor.set_theme(theme)
    
    def refresh_settings(self):
        """Refresh settings for all editors"""
        for editor in self.editors.values():
            editor.refresh_settings()
    
    def goto_line(self, line: int):
        """Go to a specific line in the current editor"""
        editor = self.get_current_editor()
        if editor:
            block = editor.document().findBlockByLineNumber(line - 1)
            if block.isValid():
                cursor = QTextCursor(block)
                editor.setTextCursor(cursor)
                editor.centerCursor()
