"""
Main Window for EZ IDE
The primary application window integrating all components
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFrame, QLabel, QToolBar, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QInputDialog, QMessageBox, QDockWidget,
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QPushButton, QDialogButtonBox, QTabWidget,
    QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QAction, QKeySequence, QIcon, QCloseEvent, QFont
)

from app.settings import SettingsManager
from app.themes import ThemeManager, Theme
from app.file_browser import FileBrowserWidget
from app.editor import EditorTabs
from app.terminal import TerminalWidget
from app.debug_session import DebugSession
from app.go_debug_session import GoDebugSession
from app.debug_panel import DebugPanel
from app.debugger_utils import detect_debugger_support, get_debugger_display_name, get_debugger_icon


class SettingsDialog(QDialog):
    """Settings dialog for configuring the IDE"""
    
    settings_applied = pyqtSignal()  # Emitted when settings are applied
    
    def __init__(self, settings: SettingsManager, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.theme_manager = theme_manager
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for different settings categories
        tabs = QTabWidget()
        
        # Editor settings
        editor_tab = QWidget()
        editor_layout = QFormLayout(editor_tab)
        
        self.font_family = QLineEdit(self.settings.settings.editor.font_family)
        editor_layout.addRow("Font Family:", self.font_family)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 48)
        self.font_size.setValue(self.settings.settings.editor.font_size)
        editor_layout.addRow("Font Size:", self.font_size)
        
        self.tab_width = QSpinBox()
        self.tab_width.setRange(1, 8)
        self.tab_width.setValue(self.settings.settings.editor.tab_width)
        editor_layout.addRow("Tab Width:", self.tab_width)
        
        self.use_spaces = QCheckBox("Use spaces instead of tabs")
        self.use_spaces.setChecked(self.settings.settings.editor.use_spaces)
        editor_layout.addRow("", self.use_spaces)
        
        self.show_line_numbers = QCheckBox("Show line numbers")
        self.show_line_numbers.setChecked(self.settings.settings.editor.show_line_numbers)
        editor_layout.addRow("", self.show_line_numbers)
        
        self.word_wrap = QCheckBox("Word wrap")
        self.word_wrap.setChecked(self.settings.settings.editor.word_wrap)
        editor_layout.addRow("", self.word_wrap)
        
        self.highlight_line = QCheckBox("Highlight current line")
        self.highlight_line.setChecked(self.settings.settings.editor.highlight_current_line)
        editor_layout.addRow("", self.highlight_line)
        
        self.bracket_matching = QCheckBox("Auto-close brackets")
        self.bracket_matching.setChecked(self.settings.settings.editor.bracket_matching)
        editor_layout.addRow("", self.bracket_matching)
        
        tabs.addTab(editor_tab, "Editor")
        
        # Theme settings
        theme_tab = QWidget()
        theme_layout = QFormLayout(theme_tab)
        
        self.theme_combo = QComboBox()
        themes = self.theme_manager.get_available_themes()
        self.theme_combo.addItems([t.title() for t in themes])
        current_theme = self.settings.settings.theme.current_theme
        for i, t in enumerate(themes):
            if t == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        theme_layout.addRow("Theme:", self.theme_combo)
        
        tabs.addTab(theme_tab, "Appearance")
        
        # Terminal settings
        terminal_tab = QWidget()
        terminal_layout = QFormLayout(terminal_tab)
        
        self.terminal_font = QLineEdit(self.settings.settings.terminal.font_family)
        terminal_layout.addRow("Font Family:", self.terminal_font)
        
        self.terminal_font_size = QSpinBox()
        self.terminal_font_size.setRange(6, 48)
        self.terminal_font_size.setValue(self.settings.settings.terminal.font_size)
        terminal_layout.addRow("Font Size:", self.terminal_font_size)
        
        self.terminal_position = QComboBox()
        self.terminal_position.addItems(["Bottom", "Right"])
        if self.settings.settings.terminal.position == "right":
            self.terminal_position.setCurrentIndex(1)
        terminal_layout.addRow("Position:", self.terminal_position)
        
        tabs.addTab(terminal_tab, "Terminal")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)
        
        layout.addWidget(buttons)
    
    def _apply(self):
        """Apply settings without closing"""
        # Editor settings
        self.settings.settings.editor.font_family = self.font_family.text()
        self.settings.settings.editor.font_size = self.font_size.value()
        self.settings.settings.editor.tab_width = self.tab_width.value()
        self.settings.settings.editor.use_spaces = self.use_spaces.isChecked()
        self.settings.settings.editor.show_line_numbers = self.show_line_numbers.isChecked()
        self.settings.settings.editor.word_wrap = self.word_wrap.isChecked()
        self.settings.settings.editor.highlight_current_line = self.highlight_line.isChecked()
        self.settings.settings.editor.bracket_matching = self.bracket_matching.isChecked()
        
        # Theme
        themes = self.theme_manager.get_available_themes()
        theme_name = themes[self.theme_combo.currentIndex()]
        self.theme_manager.set_theme(theme_name)
        
        # Terminal settings
        self.settings.settings.terminal.font_family = self.terminal_font.text()
        self.settings.settings.terminal.font_size = self.terminal_font_size.value()
        self.settings.settings.terminal.position = self.terminal_position.currentText().lower()
        
        self.settings.save()
        
        # Notify parent to refresh UI
        self.settings_applied.emit()
    
    def _save_and_close(self):
        """Save settings and close dialog"""
        self._apply()
        self.accept()


class GotoLineDialog(QDialog):
    """Dialog for going to a specific line"""
    
    def __init__(self, max_line: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Go to Line")
        self.setFixedSize(250, 100)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.line_input = QSpinBox()
        self.line_input.setRange(1, max_line)
        self.line_input.setValue(1)
        form.addRow("Line number:", self.line_input)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_line(self) -> int:
        return self.line_input.value()


class EZIDEMainWindow(QMainWindow):
    """Main IDE window"""
    
    def __init__(self, settings: SettingsManager, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.theme_manager = theme_manager
        
        self.setWindowTitle("EZ IDE")
        self._restore_window_state()
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_shortcuts()
        self._setup_connections()
        self._setup_debug()
    
    def _restore_window_state(self):
        """Restore window size and state"""
        ws = self.settings.settings.window
        self.resize(ws.width, ws.height)
        if ws.maximized:
            self.showMaximized()
    
    def _setup_ui(self):
        """Set up the main UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File browser - added directly to splitter
        self.file_browser = FileBrowserWidget(self.settings)
        self.file_browser.setMinimumWidth(150)
        self.file_browser.setMaximumWidth(500)
        
        self.main_splitter.addWidget(self.file_browser)
        
        # Editor and terminal area
        self.editor_terminal_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Editor tabs
        self.editor_tabs = EditorTabs(self.settings, self.theme_manager)
        self.editor_terminal_splitter.addWidget(self.editor_tabs)
        
        # Terminal
        self.terminal = TerminalWidget(
            self.settings, 
            self.theme_manager.get_current_theme()
        )
        self.terminal.setMinimumHeight(100)
        
        # Terminal container
        self.terminal_container = QFrame()
        terminal_layout = QVBoxLayout(self.terminal_container)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.addWidget(self.terminal)
        
        self.editor_terminal_splitter.addWidget(self.terminal_container)
        
        # Set initial splitter sizes
        self.editor_terminal_splitter.setSizes([600, 200])
        
        self.main_splitter.addWidget(self.editor_terminal_splitter)
        
        # Set splitter sizes from settings
        ws = self.settings.settings.window
        self.main_splitter.setSizes([ws.file_browser_width, 1000])
        
        # Apply visibility settings
        if not ws.file_browser_visible:
            self.file_browser.hide()
        if not self.settings.settings.terminal.visible:
            self.terminal_container.hide()
        
        main_layout.addWidget(self.main_splitter)
        
        # Debug panel (initially hidden)
        self.debug_panel = DebugPanel(self.theme_manager.get_current_theme())
        self.debug_panel.setMinimumWidth(250)
        self.debug_panel.setMaximumWidth(400)
        self.debug_panel.hide()
        self.main_splitter.addWidget(self.debug_panel)
        
        # Handle terminal position (bottom vs right)
        self._update_terminal_position()
    
    def _update_terminal_position(self):
        """Update terminal position based on settings"""
        pos = self.settings.settings.terminal.position
        
        # Remove terminal from current parent
        self.terminal_container.setParent(None)
        
        if pos == "right":
            # Add terminal to main horizontal splitter
            self.editor_terminal_splitter.setOrientation(Qt.Orientation.Horizontal)
        else:
            # Keep terminal below editor (vertical)
            self.editor_terminal_splitter.setOrientation(Qt.Orientation.Vertical)
        
        self.editor_terminal_splitter.addWidget(self.terminal_container)
        
        # Update sizes
        if pos == "right":
            self.editor_terminal_splitter.setSizes([
                800, 
                self.settings.settings.window.terminal_width
            ])
        else:
            self.editor_terminal_splitter.setSizes([
                600, 
                self.settings.settings.window.terminal_height
            ])
    
    def _setup_menus(self):
        """Set up the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = file_menu.addAction("&New File")
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_file)
        
        open_action = file_menu.addAction("&Open...")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        
        open_folder_action = file_menu.addAction("Open &Folder...")
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self._open_folder)
        
        file_menu.addSeparator()
        
        save_action = file_menu.addAction("&Save")
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        
        save_as_action = file_menu.addAction("Save &As...")
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_file_as)
        
        save_all_action = file_menu.addAction("Save A&ll")
        save_all_action.setShortcut("Ctrl+Shift+S")
        save_all_action.triggered.connect(self.editor_tabs.save_all)
        
        file_menu.addSeparator()
        
        close_action = file_menu.addAction("&Close")
        close_action.setShortcut(QKeySequence.StandardKey.Close)
        close_action.triggered.connect(self._close_current_tab)
        
        close_all_action = file_menu.addAction("Close All")
        close_all_action.setShortcut("Ctrl+Shift+W")
        close_all_action.triggered.connect(self.editor_tabs.close_all_tabs)
        
        file_menu.addSeparator()
        
        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = edit_menu.addAction("&Undo")
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        
        redo_action = edit_menu.addAction("&Redo")
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        
        edit_menu.addSeparator()
        
        cut_action = edit_menu.addAction("Cu&t")
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self._cut)
        
        copy_action = edit_menu.addAction("&Copy")
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._copy)
        
        paste_action = edit_menu.addAction("&Paste")
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._paste)
        
        edit_menu.addSeparator()
        
        select_all_action = edit_menu.addAction("Select &All")
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._select_all)
        
        edit_menu.addSeparator()
        
        find_action = edit_menu.addAction("&Find...")
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self._find)
        
        goto_action = edit_menu.addAction("&Go to Line...")
        goto_action.setShortcut("Ctrl+G")
        goto_action.triggered.connect(self._goto_line)
        
        edit_menu.addSeparator()
        
        settings_action = edit_menu.addAction("&Settings...")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        self.toggle_browser_action = view_menu.addAction("Toggle &File Browser")
        self.toggle_browser_action.setShortcut("Ctrl+B")
        self.toggle_browser_action.setCheckable(True)
        self.toggle_browser_action.setChecked(self.settings.settings.window.file_browser_visible)
        self.toggle_browser_action.triggered.connect(self._toggle_file_browser)
        
        self.toggle_terminal_action = view_menu.addAction("Toggle &Terminal")
        self.toggle_terminal_action.setShortcut("Ctrl+`")
        self.toggle_terminal_action.setCheckable(True)
        self.toggle_terminal_action.setChecked(self.settings.settings.terminal.visible)
        self.toggle_terminal_action.triggered.connect(self._toggle_terminal)
        
        open_external_term_action = view_menu.addAction("Open &External Terminal")
        open_external_term_action.setShortcut("Ctrl+Shift+T")
        open_external_term_action.triggered.connect(self._open_external_terminal)
        
        view_menu.addSeparator()
        
        terminal_position_menu = view_menu.addMenu("Terminal Position")
        
        terminal_bottom = terminal_position_menu.addAction("Bottom")
        terminal_bottom.setCheckable(True)
        terminal_bottom.setChecked(self.settings.settings.terminal.position == "bottom")
        terminal_bottom.triggered.connect(lambda: self._set_terminal_position("bottom"))
        
        terminal_right = terminal_position_menu.addAction("Right")
        terminal_right.setCheckable(True)
        terminal_right.setChecked(self.settings.settings.terminal.position == "right")
        terminal_right.triggered.connect(lambda: self._set_terminal_position("right"))
        
        self.terminal_position_actions = [terminal_bottom, terminal_right]
        
        view_menu.addSeparator()
        
        zoom_in_action = view_menu.addAction("Zoom &In")
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        
        zoom_out_action = view_menu.addAction("Zoom &Out")
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out)
        
        zoom_reset_action = view_menu.addAction("Reset Zoom")
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self._zoom_reset)
        
        view_menu.addSeparator()
        
        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")
        self.theme_actions = []
        for theme_name in self.theme_manager.get_available_themes():
            action = theme_menu.addAction(theme_name.title())
            action.setCheckable(True)
            action.setChecked(theme_name == self.settings.settings.theme.current_theme)
            action.triggered.connect(lambda checked, t=theme_name: self._set_theme(t))
            self.theme_actions.append((theme_name, action))
        
        # Run menu
        run_menu = menubar.addMenu("&Run")
        
        run_file_action = run_menu.addAction("&Run Current File")
        run_file_action.setShortcut("F5")
        run_file_action.triggered.connect(self._run_current_file)
        
        run_menu.addSeparator()
        
        select_interpreter_action = run_menu.addAction("Select EZ &Interpreter...")
        select_interpreter_action.triggered.connect(self._select_ez_interpreter)
        
        # Debug menu
        debug_menu = menubar.addMenu("&Debug")
        
        self.debug_start_action = debug_menu.addAction("&Start Debugging")
        self.debug_start_action.setShortcut("F5")
        self.debug_start_action.triggered.connect(self._debug_start)
        
        self.debug_step_action = debug_menu.addAction("Step &Over")
        self.debug_step_action.setShortcut("F10")
        self.debug_step_action.setEnabled(False)
        self.debug_step_action.triggered.connect(self._debug_step)
        
        self.debug_stop_action = debug_menu.addAction("S&top Debugging")
        self.debug_stop_action.setShortcut("Shift+F5")
        self.debug_stop_action.setEnabled(False)
        self.debug_stop_action.triggered.connect(self._debug_stop)
        
        debug_menu.addSeparator()
        
        self.toggle_debug_panel_action = debug_menu.addAction("Toggle Debug &Panel")
        self.toggle_debug_panel_action.setShortcut("Ctrl+Shift+D")
        self.toggle_debug_panel_action.setCheckable(True)
        self.toggle_debug_panel_action.triggered.connect(self._toggle_debug_panel)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = help_menu.addAction("&About EZ IDE")
        about_action.triggered.connect(self._show_about)
        
        docs_action = help_menu.addAction("EZ &Documentation")
        docs_action.triggered.connect(self._open_docs)
    
    def _setup_toolbar(self):
        """Set up the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)
        
        # Set font with emoji support
        toolbar_font = QFont()
        toolbar_font.setFamilies(["Sans", "Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji"])
        toolbar.setFont(toolbar_font)
        
        # New file
        new_btn = toolbar.addAction("📄 New")
        new_btn.setToolTip("New File (Ctrl+N)")
        new_btn.triggered.connect(self._new_file)
        
        # Open file
        open_btn = toolbar.addAction("📂 Open")
        open_btn.setToolTip("Open File (Ctrl+O)")
        open_btn.triggered.connect(self._open_file)
        
        # Save
        save_btn = toolbar.addAction("💾 Save")
        save_btn.setToolTip("Save (Ctrl+S)")
        save_btn.triggered.connect(self._save_file)
        
        toolbar.addSeparator()
        
        # Run
        run_btn = toolbar.addAction("▶️ Run")
        run_btn.setToolTip("Run Current File (F5)")
        run_btn.triggered.connect(self._run_current_file)
        
        toolbar.addSeparator()
        
        # Toggle browser
        browser_btn = toolbar.addAction("📁 Browser")
        browser_btn.setToolTip("Toggle File Browser (Ctrl+B)")
        browser_btn.setCheckable(True)
        browser_btn.setChecked(self.settings.settings.window.file_browser_visible)
        browser_btn.triggered.connect(self._toggle_file_browser)
        self.browser_toolbar_btn = browser_btn
        
        # Toggle terminal
        terminal_btn = toolbar.addAction("💻 Terminal")
        terminal_btn.setToolTip("Toggle Terminal (Ctrl+`)")
        terminal_btn.setCheckable(True)
        terminal_btn.setChecked(self.settings.settings.terminal.visible)
        terminal_btn.triggered.connect(self._toggle_terminal)
        self.terminal_toolbar_btn = terminal_btn
        
        # External Terminal
        ext_term_btn = toolbar.addAction("📟 Ext. Term")
        ext_term_btn.setToolTip("Open External Terminal (Ctrl+Shift+T)")
        ext_term_btn.triggered.connect(self._open_external_terminal)
        
        toolbar.addSeparator()
        
        # Debug button
        debug_btn = toolbar.addAction("🐛 Debug")
        debug_btn.setToolTip("Start Debugging (F5)")
        debug_btn.triggered.connect(self._debug_start)
    
    def _setup_statusbar(self):
        """Set up the status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # File info label
        self.file_info_label = QLabel("Ready")
        self.statusbar.addWidget(self.file_info_label)
        
        self.statusbar.addPermanentWidget(QLabel(""))  # Spacer
        
        # Cursor position
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.statusbar.addPermanentWidget(self.cursor_label)
        
        # Encoding
        self.encoding_label = QLabel("UTF-8")
        self.statusbar.addPermanentWidget(self.encoding_label)
    
    def _setup_shortcuts(self):
        """Set up additional keyboard shortcuts"""
        pass  # Most shortcuts are set through menu actions
    
    def _setup_connections(self):
        """Set up signal connections"""
        # File browser
        self.file_browser.file_opened.connect(self.editor_tabs.open_file)
        
        # Editor tabs
        self.editor_tabs.current_file_changed.connect(self._on_current_file_changed)
        self.editor_tabs.cursor_position_changed.connect(self._on_cursor_position_changed)
        self.editor_tabs.file_saved.connect(lambda f: self.statusbar.showMessage(f"Saved: {f}", 3000))
    
    def _update_recent_files_menu(self):
        """Update the recent files submenu"""
        self.recent_menu.clear()
        
        for filepath in self.settings.settings.recent_files[:10]:
            if os.path.exists(filepath):
                action = self.recent_menu.addAction(os.path.basename(filepath))
                action.setToolTip(filepath)
                action.triggered.connect(lambda checked, f=filepath: self.editor_tabs.open_file(f))
        
        if self.recent_menu.isEmpty():
            self.recent_menu.addAction("No recent files").setEnabled(False)
        else:
            self.recent_menu.addSeparator()
            clear_action = self.recent_menu.addAction("Clear Recent Files")
            clear_action.triggered.connect(self._clear_recent_files)
    
    def _clear_recent_files(self):
        """Clear recent files list"""
        self.settings.settings.recent_files = []
        self.settings.save()
        self._update_recent_files_menu()
    
    # File operations
    def _new_file(self):
        self.editor_tabs.new_file()
    
    def _open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File",
            self.file_browser.current_root or str(Path.home()),
            "EZ Files (*.ez);;All Files (*)"
        )
        if filepath:
            self.editor_tabs.open_file(filepath)
    
    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Open Folder",
            str(Path.home())
        )
        if folder:
            self.file_browser.navigate_to(folder)
    
    def _save_file(self):
        self.editor_tabs.save_current()
    
    def _save_file_as(self):
        self.editor_tabs.save_current_as()
    
    def _close_current_tab(self):
        index = self.editor_tabs.currentIndex()
        if index >= 0:
            self.editor_tabs.close_tab(index)
    
    # Edit operations
    def _undo(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.undo()
    
    def _redo(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.redo()
    
    def _cut(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.cut()
    
    def _copy(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.copy()
    
    def _paste(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.paste()
    
    def _select_all(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.selectAll()
    
    def _find(self):
        # Simple find implementation - could be enhanced
        editor = self.editor_tabs.get_current_editor()
        if not editor:
            return
        
        text, ok = QInputDialog.getText(self, "Find", "Search for:")
        if ok and text:
            cursor = editor.textCursor()
            doc = editor.document()
            found = doc.find(text, cursor)
            if not found.isNull():
                editor.setTextCursor(found)
            else:
                # Try from beginning
                found = doc.find(text)
                if not found.isNull():
                    editor.setTextCursor(found)
                else:
                    self.statusbar.showMessage(f"'{text}' not found", 3000)
    
    def _goto_line(self):
        editor = self.editor_tabs.get_current_editor()
        if not editor:
            return
        
        max_line = editor.blockCount()
        dialog = GotoLineDialog(max_line, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.editor_tabs.goto_line(dialog.get_line())
    
    def _show_settings(self):
        dialog = SettingsDialog(self.settings, self.theme_manager, self)
        dialog.settings_applied.connect(self._apply_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Also refresh on OK
            self._apply_settings()
    
    def _apply_settings(self):
        """Apply settings changes to UI"""
        theme = self.theme_manager.get_current_theme()
        
        # Update stylesheet
        QApplication.instance().setStyleSheet(
            self.theme_manager.get_current_stylesheet()
        )
        
        # Update editor themes and settings
        self.editor_tabs.set_theme(theme)
        self.editor_tabs.refresh_settings()
        
        # Update terminal theme and settings
        self.terminal.set_theme(theme)
        self.terminal._apply_theme()  # Refresh terminal with new font settings
        
        # Update terminal position
        self._update_terminal_position()
        
        # Update theme menu checkmarks
        current = self.settings.settings.theme.current_theme
        for name, action in self.theme_actions:
            action.setChecked(name == current)
    
    # View operations
    def _toggle_file_browser(self):
        visible = self.file_browser.isVisible()
        self.file_browser.setVisible(not visible)
        self.settings.settings.window.file_browser_visible = not visible
        self.settings.save()
        
        self.toggle_browser_action.setChecked(not visible)
        self.browser_toolbar_btn.setChecked(not visible)
    
    def _toggle_terminal(self):
        visible = self.terminal_container.isVisible()
        self.terminal_container.setVisible(not visible)
        self.settings.settings.terminal.visible = not visible
        self.settings.save()
        
        self.toggle_terminal_action.setChecked(not visible)
        self.terminal_toolbar_btn.setChecked(not visible)
        
        if not visible:
            self.terminal.focus_input()
    
    def _set_terminal_position(self, position: str):
        self.settings.settings.terminal.position = position
        self.settings.save()
        self._update_terminal_position()
        
        # Update menu checkmarks
        for action in self.terminal_position_actions:
            action.setChecked(action.text().lower() == position)

    def _open_external_terminal(self):
        """Open an external terminal window in the current directory"""
        # Determine working directory
        cwd = self.file_browser.current_root
        if not cwd or not os.path.isdir(cwd):
            cwd = str(Path.home())
            
        try:
            if sys.platform == 'win32':
                # Windows
                subprocess.Popen(f'start cmd /K "cd /d {cwd}"', shell=True)
                
            elif sys.platform == 'darwin':
                # macOS
                subprocess.Popen(['open', '-a', 'Terminal', cwd])
                
            else:
                # Linux / Unix
                self._open_linux_terminal(cwd)
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to launch terminal:\n{str(e)}"
            )

    def _open_linux_terminal(self, cwd):
        """Helper to open Linux terminal"""
        # Detect available terminal emulator
        terminals = [
            'gnome-terminal',
            'konsole', 
            'xfce4-terminal',
            'mate-terminal',
            'terminator',
            'xterm',
            'urxvt',
            'rxvt',
            'x-terminal-emulator'
        ]
        
        terminal_cmd = None
        for term in terminals:
            if shutil.which(term):
                terminal_cmd = term
                break
        
        if not terminal_cmd:
            QMessageBox.warning(
                self, 
                "Terminal Not Found", 
                "Could not detect a supported external terminal emulator.\n"
                "Please install gnome-terminal, konsole, xterm, or ensure 'x-terminal-emulator' is configured."
            )
            return
            
        # Construct command based on terminal type
        if terminal_cmd == 'gnome-terminal':
            subprocess.Popen([terminal_cmd, '--working-directory', cwd])
        elif terminal_cmd == 'konsole':
                subprocess.Popen([terminal_cmd, '--workdir', cwd])
        elif terminal_cmd == 'xfce4-terminal':
            subprocess.Popen([terminal_cmd, '--working-directory', cwd])
        elif terminal_cmd == 'mate-terminal':
            subprocess.Popen([terminal_cmd, '--working-directory', cwd])
        else:
            # Fallback for xterm and others that don't always support working-dir flags nicely
            # But usually start in CWD if we pass cwd param to Popen
            subprocess.Popen([terminal_cmd], cwd=cwd)
    
    def _zoom_in(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.zoom_in()
    
    def _zoom_out(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.zoom_out()
    
    def _zoom_reset(self):
        editor = self.editor_tabs.get_current_editor()
        if editor:
            editor.reset_zoom()
    
    def _set_theme(self, theme_name: str):
        self.theme_manager.set_theme(theme_name)
        self._apply_settings()
    
    # Run operations
    def _run_current_file(self):
        filepath = self.editor_tabs.get_current_filepath()
        if filepath and filepath.endswith('.ez'):
            # Save first
            self.editor_tabs.save_current()
            
            # Show terminal if hidden
            if not self.terminal_container.isVisible():
                self._toggle_terminal()
            
            # Run in terminal
            self.terminal.run_ez_file(filepath)
        else:
            self.statusbar.showMessage("No EZ file to run", 3000)
    
    def _select_ez_interpreter(self):
        """Open dialog to select EZ interpreter binary"""
        current = self.settings.settings.ez.interpreter_path
        start_dir = os.path.dirname(current) if current else "/usr/local/bin"
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select EZ Interpreter",
            start_dir,
            "Executables (*);;All Files (*)"
        )
        
        if filepath:
            # Verify it's executable
            if os.access(filepath, os.X_OK):
                self.settings.settings.ez.interpreter_path = filepath
                self.settings.save()
                self.statusbar.showMessage(f"EZ interpreter set to: {filepath}", 5000)
            else:
                QMessageBox.warning(
                    self, "Invalid Selection",
                    f"The selected file is not executable:\n{filepath}"
                )
    
    # Status updates
    def _on_current_file_changed(self, filepath: str):
        if filepath and not filepath.startswith("__untitled_"):
            self.file_info_label.setText(filepath)
        else:
            self.file_info_label.setText("Untitled")
        
        self._update_recent_files_menu()
    
    def _on_cursor_position_changed(self, line: int, column: int):
        self.cursor_label.setText(f"Ln {line}, Col {column}")
    
    # Help
    def _show_about(self):
        QMessageBox.about(
            self, "About EZ IDE",
            "<h2>EZ IDE</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A modern IDE for the EZ programming language.</p>"
            "<p>Built with Python and PyQt6</p>"
            "<hr>"
            "<p>IDE (c) 2025 Chuck Finch - Fragillidae Software</p>"
            "<p>EZ Language © 2025 Marshall A Burns</p>"
        )
    
    def _open_docs(self):
        import webbrowser
        webbrowser.open("https://schoolyb.github.io/language.ez/docs")
    
    # Window events
    def closeEvent(self, event: QCloseEvent):
        """Handle window close"""
        # Ask to save unsaved files
        if not self.editor_tabs.close_all_tabs():
            event.ignore()
            return
        
        # Save window state
        ws = self.settings.settings.window
        ws.maximized = self.isMaximized()
        if not ws.maximized:
            ws.width = self.width()
            ws.height = self.height()
        
        # Save splitter sizes
        sizes = self.main_splitter.sizes()
        if len(sizes) >= 2:
            ws.file_browser_width = sizes[0]
        
        sizes = self.editor_terminal_splitter.sizes()
        if len(sizes) >= 2:
            if self.settings.settings.terminal.position == "right":
                ws.terminal_width = sizes[1]
            else:
                ws.terminal_height = sizes[1]
        
        self.settings.save()
        event.accept()
    
    # Debug operations
    def _setup_debug(self):
        """Initialize the debug session and connect signals"""
        # Detect best available debugger
        ez_path = self.settings.settings.ez.interpreter_path
        if not ez_path or not os.path.isfile(ez_path):
            ez_path = shutil.which('ez')
        
        self.debugger_capabilities = detect_debugger_support(ez_path or '')
        
        # Create appropriate debug session based on capabilities
        if self.debugger_capabilities.type == 'native':
            self.debug_session = GoDebugSession(self.settings, self)
            self.statusbar.showMessage(
                f"{get_debugger_icon('native')} Using Native Debugger", 3000
            )
        else:
            self.debug_session = DebugSession(self.settings, self)
            if self.debugger_capabilities.type == 'repl':
                self.statusbar.showMessage(
                    f"{get_debugger_icon('repl')} Using REPL Debugger (Limited Features)", 3000
                )
            else:
                self.statusbar.showMessage(
                    f"{get_debugger_icon('none')} Debugger not available", 3000
                )
        
        self._debug_filepath = None  # Track the file being debugged
        self._debugger_type = self.debugger_capabilities.type
        
        # Connect debug session signals
        self.debug_session.session_started.connect(self._on_debug_started)
        self.debug_session.session_ended.connect(self._on_debug_ended)
        self.debug_session.line_changed.connect(self._on_debug_line_changed)
        self.debug_session.variable_updated.connect(self._on_debug_variable_updated)
        self.debug_session.output_received.connect(self._on_debug_output)
        self.debug_session.error_received.connect(self._on_debug_error)
        self.debug_session.ready_for_step.connect(self._on_debug_ready)
        
        # Connect debug panel signals
        self.debug_panel.start_requested.connect(self._debug_start)
        self.debug_panel.step_requested.connect(self._debug_step)
        self.debug_panel.stop_requested.connect(self._debug_stop)
        
        # Set debugger type indicator in panel
        debugger_icon = get_debugger_icon(self._debugger_type)
        debugger_name = get_debugger_display_name(self._debugger_type)
        self.debug_panel.set_debugger_type(debugger_icon, debugger_name)
    
    def _toggle_debug_panel(self):
        """Toggle visibility of the debug panel"""
        visible = self.debug_panel.isVisible()
        self.debug_panel.setVisible(not visible)
        self.toggle_debug_panel_action.setChecked(not visible)
    
    def _debug_start(self):
        """Start debugging the current file"""
        filepath = self.editor_tabs.get_current_filepath()
        if not filepath or not filepath.endswith('.ez'):
            self.statusbar.showMessage("No EZ file to debug", 3000)
            return
        
        # Save the file first
        self.editor_tabs.save_current()
        
        # Show debug panel
        if not self.debug_panel.isVisible():
            self.debug_panel.show()
            self.toggle_debug_panel_action.setChecked(True)
        
        # Clear previous debug output for fresh start
        self.debug_panel.reset()
        
        # Start the debug session
        self._debug_filepath = filepath
        working_dir = os.path.dirname(filepath)
        root = getattr(self.file_browser, 'current_root', None)
        if root and os.path.isdir(root):
            try:
                root_abs = os.path.abspath(root)
                file_abs = os.path.abspath(filepath)
                if os.path.commonpath([root_abs, file_abs]) == root_abs:
                    working_dir = root_abs
            except ValueError:
                pass

        if self.debug_session.start(filepath, working_dir=working_dir):
            self.statusbar.showMessage(f"Debugging: {os.path.basename(filepath)}", 0)
    
    def _debug_step(self):
        """Execute next statement"""
        if self.debug_session.is_running:
            self.debug_panel.set_step_enabled(False)  # Disable until ready
            has_more = self.debug_session.step()
            if not has_more:
                self._debug_stop()
    
    def _debug_stop(self):
        """Stop the debug session"""
        if self.debug_session.is_running:
            self.debug_session.stop()
        
        # Clear debug line highlight
        if self._debug_filepath:
            editor = self.editor_tabs.get_editor_for_file(self._debug_filepath)
            if editor:
                editor.clear_debug_line()
        
        self._debug_filepath = None
        # Just update toolbar, don't reset output so user can see final results
        self.debug_panel.toolbar.set_debugging(False)
        self.statusbar.showMessage("Debug session ended", 3000)
    
    def _on_debug_started(self):
        """Handle debug session start"""
        self.debug_panel.set_debugging(True)
        # Don't reset here - we want to keep accumulating output
        self.debug_start_action.setEnabled(False)
        supports_step = True
        try:
            supports_step = self.debug_session.supports_step()
        except AttributeError:
            supports_step = True

        self.debug_step_action.setEnabled(supports_step)
        self.debug_panel.set_step_enabled(supports_step)
        if not supports_step:
            self.debug_panel.set_status("Running (no stepping)", "gray")
        self.debug_stop_action.setEnabled(True)
    
    def _on_debug_ended(self):
        """Handle debug session end"""
        # Just update toolbar state, don't clear output so user can see final results
        self.debug_panel.toolbar.set_debugging(False)
        self.debug_start_action.setEnabled(True)
        self.debug_step_action.setEnabled(False)
        self.debug_stop_action.setEnabled(False)
        
        # Clear debug line
        if self._debug_filepath:
            editor = self.editor_tabs.get_editor_for_file(self._debug_filepath)
            if editor:
                editor.clear_debug_line()
    
    def _on_debug_line_changed(self, line: int):
        """Handle debug line change"""
        if self._debug_filepath and line > 0:
            editor = self.editor_tabs.get_editor_for_file(self._debug_filepath)
            if editor:
                editor.set_debug_line(line)
            self.debug_panel.set_status(f"Line {line}", "#4CAF50")
    
    def _on_debug_variable_updated(self, name: str, value: str):
        """Handle variable value update"""
        self.debug_panel.update_variable(name, value)
    
    def _on_debug_output(self, text: str):
        """Handle program output during debug"""
        self.debug_panel.append_output(text)
    
    def _on_debug_error(self, message: str):
        """Handle debug error"""
        self.debug_panel.append_error(message)
        self.statusbar.showMessage(f"Debug error: {message}", 5000)
    
    def _on_debug_ready(self):
        """Handle debug session ready for next step"""
        self.debug_panel.set_step_enabled(True)
