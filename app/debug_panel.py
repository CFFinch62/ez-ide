"""
Debug Panel Widget for EZ IDE
UI for step debugging with variable inspection
"""

import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QToolButton, QLabel, QFrame, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon, QTextCharFormat, QTextCursor

from app.themes import Theme


class DebugToolbar(QFrame):
    """Toolbar with debug control buttons"""
    
    start_clicked = pyqtSignal()
    step_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("debug_toolbar")
        self._setup_ui()
        self._set_state(False)  # Not debugging initially
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Title
        title = QLabel("Debug")
        title.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(title)
        
        # Debugger type indicator
        self.debugger_type_label = QLabel("")
        self.debugger_type_label.setStyleSheet("font-size: 9px; color: gray; font-style: italic;")
        self.debugger_type_label.setToolTip("Debugger type")
        layout.addWidget(self.debugger_type_label)
        
        layout.addSpacing(12)
        
        # Start/Resume button
        self.start_btn = QToolButton()
        self.start_btn.setText("▶ Start")
        self.start_btn.setToolTip("Start debugging (F5)")
        self.start_btn.clicked.connect(self.start_clicked.emit)
        layout.addWidget(self.start_btn)
        
        # Step button
        self.step_btn = QToolButton()
        self.step_btn.setText("→ Step")
        self.step_btn.setToolTip("Step to next statement (F10)")
        self.step_btn.clicked.connect(self.step_clicked.emit)
        layout.addWidget(self.step_btn)
        
        # Stop button
        self.stop_btn = QToolButton()
        self.stop_btn.setText("■ Stop")
        self.stop_btn.setToolTip("Stop debugging (Shift+F5)")
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_btn)

        self.clear_btn = QToolButton()
        self.clear_btn.setText("Clear")
        self.clear_btn.setToolTip("Clear variables and output")
        self.clear_btn.clicked.connect(self.clear_clicked.emit)
        layout.addWidget(self.clear_btn)
        
        layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(self.status_label)
    
    def _set_state(self, debugging: bool):
        """Update button states based on whether debugging is active"""
        self.start_btn.setEnabled(not debugging)
        self.step_btn.setEnabled(debugging)
        self.stop_btn.setEnabled(debugging)
        self.clear_btn.setEnabled(not debugging)
    
    def set_debugging(self, active: bool):
        """Set debugging state"""
        self._set_state(active)
        if active:
            self.start_btn.setText("▶ Resume")
            self.status_label.setText("Debugging")
            self.status_label.setStyleSheet("font-size: 10px; color: #4CAF50;")
        else:
            self.start_btn.setText("▶ Start")
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("font-size: 10px; color: gray;")
    
    def set_status(self, text: str, color: str = "gray"):
        """Set status text"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size: 10px; color: {color};")
    
    def set_step_enabled(self, enabled: bool):
        """Enable or disable the step button"""
        self.step_btn.setEnabled(enabled)
    
    def set_debugger_type(self, icon: str, name: str):
        """Set the debugger type indicator"""
        self.debugger_type_label.setText(f"{icon} {name}")
        self.debugger_type_label.setToolTip(f"Using {name}")


class VariableTree(QTreeWidget):
    """Tree view for displaying variables and their values"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Variable", "Value"])
        self.setColumnWidth(0, 120)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self._variables = {}
    
    def update_variable(self, name: str, value: str):
        """Add or update a variable"""
        self._variables[name] = value
        self._refresh_display()
    
    def clear_variables(self):
        """Clear all variables"""
        self._variables.clear()
        self.clear()
    
    def _refresh_display(self):
        """Refresh the tree display"""
        self.clear()
        for name, value in sorted(self._variables.items()):
            item = QTreeWidgetItem([name, value])
            # Highlight recent changes (could be enhanced with color)
            self.addTopLevelItem(item)
    
    def set_theme(self, theme: Theme):
        """Apply theme styling"""
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {theme.background};
                color: {theme.foreground};
                border: none;
            }}
            QTreeWidget::item:selected {{
                background-color: {theme.browser_item_selected};
            }}
            QHeaderView::section {{
                background-color: {theme.panel_background};
                color: {theme.foreground};
                border: none;
                padding: 4px;
            }}
        """)


class DebugOutput(QPlainTextEdit):
    """Output panel for debug messages and program output with ANSI support"""
    
    # ANSI color code mappings (standard 16 colors)
    ANSI_COLORS = {
        '30': '#000000',  # Black
        '31': '#CD0000',  # Red
        '32': '#00CD00',  # Green
        '33': '#CDCD00',  # Yellow
        '34': '#0000EE',  # Blue
        '35': '#CD00CD',  # Magenta
        '36': '#00CDCD',  # Cyan
        '37': '#E5E5E5',  # White
        '90': '#7F7F7F',  # Bright Black (Gray)
        '91': '#FF0000',  # Bright Red
        '92': '#00FF00',  # Bright Green
        '93': '#FFFF00',  # Bright Yellow
        '94': '#5C5CFF',  # Bright Blue
        '95': '#FF00FF',  # Bright Magenta
        '96': '#00FFFF',  # Bright Cyan
        '97': '#FFFFFF',  # Bright White
    }
    
    # Regex to match ANSI escape sequences
    ANSI_ESCAPE_RE = re.compile(r'\x1b\[([0-9;]*)m')
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(1000)
        self.setPlaceholderText("Debug output will appear here...")
        self._default_format = QTextCharFormat()
        self._current_format = QTextCharFormat()
    
    def append_output(self, text: str, color: QColor = None):
        """Append text with optional color, parsing ANSI codes"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if color:
            # Direct color override - don't parse ANSI
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor.insertText(text + "\n", fmt)
        else:
            # Parse ANSI escape codes
            self._append_with_ansi(cursor, text + "\n")
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def _append_with_ansi(self, cursor, text: str):
        """Parse and render text with ANSI escape codes"""
        pos = 0
        for match in self.ANSI_ESCAPE_RE.finditer(text):
            # Insert text before this escape sequence
            if match.start() > pos:
                cursor.insertText(text[pos:match.start()], self._current_format)
            
            # Process the escape sequence
            codes = match.group(1).split(';') if match.group(1) else ['0']
            self._process_ansi_codes(codes)
            
            pos = match.end()
        
        # Insert remaining text after last escape sequence
        if pos < len(text):
            cursor.insertText(text[pos:], self._current_format)
    
    def _process_ansi_codes(self, codes: list):
        """Process ANSI SGR (Select Graphic Rendition) codes"""
        for code in codes:
            if code == '0' or code == '':
                # Reset to default
                self._current_format = QTextCharFormat(self._default_format)
            elif code == '1':
                # Bold
                self._current_format.setFontWeight(700)
            elif code == '3':
                # Italic
                self._current_format.setFontItalic(True)
            elif code == '4':
                # Underline
                self._current_format.setFontUnderline(True)
            elif code in self.ANSI_COLORS:
                # Foreground color
                self._current_format.setForeground(QColor(self.ANSI_COLORS[code]))
    
    def append_error(self, text: str):
        """Append error message in red"""
        self.append_output(f"[ERROR] {text}", QColor("#FF5555"))
    
    def set_default_color(self, color: QColor):
        """Set the default text color"""
        self._default_format.setForeground(color)
        self._current_format = QTextCharFormat(self._default_format)
    
    def set_theme(self, theme: Theme):
        """Apply theme styling"""
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {theme.terminal_background};
                color: {theme.terminal_foreground};
                border: none;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        self.set_default_color(QColor(theme.terminal_foreground))


class DebugPanel(QWidget):
    """
    Main debug panel widget
    
    Contains:
    - Toolbar with Start/Step/Stop buttons
    - Variable tree for inspecting values
    - Output panel for program output
    """
    
    # Signals forwarded from toolbar
    start_requested = pyqtSignal()
    step_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    
    def __init__(self, theme: Theme = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._setup_ui()
        self._connect_signals()
        if theme:
            self.set_theme(theme)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = DebugToolbar()
        layout.addWidget(self.toolbar)
        
        # Splitter for variables and output
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Variables section
        var_container = QWidget()
        var_layout = QVBoxLayout(var_container)
        var_layout.setContentsMargins(4, 4, 4, 4)
        var_layout.setSpacing(2)
        
        var_label = QLabel("Variables")
        var_label.setStyleSheet("font-weight: bold; font-size: 10px;")
        var_layout.addWidget(var_label)
        
        self.variable_tree = VariableTree()
        var_layout.addWidget(self.variable_tree)
        
        splitter.addWidget(var_container)
        
        # Output section
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(4, 4, 4, 4)
        output_layout.setSpacing(2)
        
        output_label = QLabel("Output")
        output_label.setStyleSheet("font-weight: bold; font-size: 10px;")
        output_layout.addWidget(output_label)
        
        self.output = DebugOutput()
        output_layout.addWidget(self.output)
        
        splitter.addWidget(output_container)
        
        # Set initial sizes (variables 60%, output 40%)
        splitter.setSizes([300, 200])
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect toolbar signals"""
        self.toolbar.start_clicked.connect(self.start_requested.emit)
        self.toolbar.step_clicked.connect(self.step_requested.emit)
        self.toolbar.stop_clicked.connect(self.stop_requested.emit)
        self.toolbar.clear_clicked.connect(self.clear_output_and_variables)
    
    def set_theme(self, theme: Theme):
        """Apply theme to all components"""
        self.theme = theme
        self.variable_tree.set_theme(theme)
        self.output.set_theme(theme)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.panel_background};
            }}
            QLabel {{
                color: {theme.foreground};
            }}
        """)
    
    # Public methods for controlling the panel
    
    def set_debugging(self, active: bool):
        """Update UI for debugging state"""
        self.toolbar.set_debugging(active)
        if not active:
            self.reset()
    
    def set_status(self, text: str, color: str = "gray"):
        """Set status message"""
        self.toolbar.set_status(text, color)
    
    def set_step_enabled(self, enabled: bool):
        """Enable/disable step button"""
        self.toolbar.set_step_enabled(enabled)
    
    def set_debugger_type(self, icon: str, name: str):
        """Set the debugger type indicator"""
        self.toolbar.set_debugger_type(icon, name)
    
    def update_variable(self, name: str, value: str):
        """Update a variable's value"""
        self.variable_tree.update_variable(name, value)
    
    def append_output(self, text: str):
        """Append program output"""
        self.output.append_output(text)
    
    def append_error(self, text: str):
        """Append error message"""
        self.output.append_error(text)

    def clear_output_and_variables(self):
        self.variable_tree.clear_variables()
        self.output.clear()
    
    def reset(self):
        """Reset the panel to initial state"""
        self.variable_tree.clear_variables()
        self.output.clear()
        self.toolbar.set_debugging(False)
