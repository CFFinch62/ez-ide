"""
Terminal Widget for EZ IDE
Integrated terminal emulator with customizable position
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit,
    QPushButton, QFrame, QLabel, QToolButton, QMenu, QComboBox
)
from PyQt6.QtCore import (
    Qt, QProcess, pyqtSignal, QTimer, QByteArray
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCursor, QKeyEvent, QTextCharFormat
)

from app.settings import SettingsManager
from app.themes import Theme


class TerminalOutput(QPlainTextEdit):
    """Terminal output display widget with ANSI escape code support"""
    
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
        self.setMaximumBlockCount(10000)  # Limit scrollback
        self._default_format = QTextCharFormat()
        self._current_format = QTextCharFormat()
        
        # Disable word wrap to preserve preformatted text alignment
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    
    def set_terminal_font(self, font_family: str, font_size: int):
        """Set the terminal font with proper monospace/fixed-pitch settings"""
        font = QFont(font_family, font_size)
        font.setFixedPitch(True)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.document().setDefaultFont(font)
    
    def append_output(self, text: str, color: QColor = None):
        """Append text to the terminal output, parsing ANSI codes"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if color:
            # Direct color override - don't parse ANSI
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor.insertText(text, fmt)
        else:
            # Parse ANSI escape codes
            self._append_with_ansi(cursor, text)
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def _append_with_ansi(self, cursor: QTextCursor, text: str):
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
    
    def set_default_color(self, color: QColor):
        """Set the default text color"""
        self._default_format.setForeground(color)
        self._current_format = QTextCharFormat(self._default_format)


class TerminalInput(QLineEdit):
    """Terminal command input field"""
    
    command_entered = pyqtSignal(str)
    history_up = pyqtSignal()
    history_down = pyqtSignal()
    tab_pressed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Enter command...")
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle special keys"""
        # Handle both main Enter (Key_Return) and numpad Enter (Key_Enter)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            command = self.text()
            self.clear()
            self.command_entered.emit(command)
        elif event.key() == Qt.Key.Key_Up:
            self.history_up.emit()
        elif event.key() == Qt.Key.Key_Down:
            self.history_down.emit()
        elif event.key() == Qt.Key.Key_Tab:
            self.tab_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class TerminalWidget(QWidget):
    """Integrated terminal widget"""
    
    command_executed = pyqtSignal(str)  # command
    directory_changed = pyqtSignal(str)  # new directory
    
    def __init__(self, settings: SettingsManager, theme: Theme = None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings
        self.theme = theme
        
        self.process: Optional[QProcess] = None
        self.current_dir = str(Path.home())
        self.command_history: list = []
        self.history_index = -1
        
        # Track the currently running command process for interactive input
        self.running_process: Optional[QProcess] = None
        
        self._setup_ui()
        self._setup_connections()
        self._apply_theme()
        self._start_shell()
    
    def _setup_ui(self):
        """Set up the terminal UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header/toolbar
        header = QFrame()
        header.setObjectName("terminal_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        title = QLabel("Terminal")
        title.setStyleSheet("font-weight: bold; font-size: 11px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Current directory display
        self.dir_label = QLabel()
        self.dir_label.setStyleSheet("font-size: 10px; opacity: 0.7;")
        header_layout.addWidget(self.dir_label)
        
        header_layout.addSpacing(8)
        
        # Shell selector
        self.shell_combo = QComboBox()
        self.shell_combo.setMaximumWidth(100)
        self._populate_shells()
        header_layout.addWidget(self.shell_combo)
        
        # Clear button
        clear_btn = QToolButton()
        clear_btn.setText("Clear")
        clear_btn.clicked.connect(self.clear_output)
        header_layout.addWidget(clear_btn)
        
        # Restart button
        restart_btn = QToolButton()
        restart_btn.setText("Restart")
        restart_btn.clicked.connect(self.restart_shell)
        header_layout.addWidget(restart_btn)
        
        layout.addWidget(header)
        
        # Terminal output
        self.output = TerminalOutput()
        layout.addWidget(self.output)
        
        # Input area
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 4, 8, 4)
        
        self.prompt_label = QLabel("$")
        self.prompt_label.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(self.prompt_label)
        
        self.input = TerminalInput()
        input_layout.addWidget(self.input)
        
        layout.addWidget(input_frame)
    
    def _populate_shells(self):
        """Populate available shells"""
        shells = []
        
        if sys.platform == 'win32':
            shells = ['cmd', 'powershell']
            if shutil.which('wsl'):
                shells.append('wsl')
        else:
            # Unix-like
            for shell in ['bash', 'zsh', 'sh', 'fish']:
                if shutil.which(shell):
                    shells.append(shell)
        
        self.shell_combo.addItems(shells)
        
        # Set default from settings
        default_shell = self.settings_manager.settings.terminal.shell
        if default_shell and default_shell in shells:
            self.shell_combo.setCurrentText(default_shell)
    
    def _setup_connections(self):
        """Set up signal connections"""
        self.input.command_entered.connect(self._execute_command)
        self.input.history_up.connect(self._history_up)
        self.input.history_down.connect(self._history_down)
        self.shell_combo.currentTextChanged.connect(self._on_shell_changed)
    
    def _apply_theme(self):
        """Apply theme to terminal"""
        if not self.theme:
            from app.themes import DARK_THEME
            self.theme = DARK_THEME
        
        self.output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.theme.terminal_background};
                color: {self.theme.terminal_foreground};
                border: none;
            }}
        """)
        
        # Set font programmatically for proper monospace rendering of Unicode
        self.output.set_terminal_font(
            self.settings_manager.settings.terminal.font_family,
            self.settings_manager.settings.terminal.font_size
        )
        
        self.output.set_default_color(QColor(self.theme.terminal_foreground))
        
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme.terminal_background};
                color: {self.theme.terminal_foreground};
                border: none;
                font-family: "{self.settings_manager.settings.terminal.font_family}";
                font-size: {self.settings_manager.settings.terminal.font_size}pt;
            }}
        """)
    
    def set_theme(self, theme: Theme):
        """Update the theme"""
        self.theme = theme
        self._apply_theme()
    
    def _start_shell(self):
        """Start the shell process"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
        
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output_ready)
        self.process.finished.connect(self._on_process_finished)
        self.process.errorOccurred.connect(self._on_process_error)
        
        self.process.setWorkingDirectory(self.current_dir)
        self._update_dir_label()
        
        # We don't actually start an interactive shell session
        # Instead, we run commands individually
        self.output.append_output(f"Terminal ready. Working directory: {self.current_dir}\n", 
                                   QColor(self.theme.info))
    
    def _execute_command(self, command: str):
        """Execute a command or send input to running process"""
        if not command.strip() and not self.running_process:
            return
        
        # If there's a running process, send input to it instead
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            self._send_input_to_process(command)
            return
        
        # Add to history
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Show command in output
        self.output.append_output(f"$ {command}\n", QColor(self.theme.accent))
        
        # Handle built-in commands
        if command.strip().startswith('cd '):
            self._handle_cd(command.strip()[3:].strip())
            return
        elif command.strip() == 'cd':
            self._handle_cd(str(Path.home()))
            return
        elif command.strip() == 'clear':
            self.clear_output()
            return
        elif command.strip() == 'pwd':
            self.output.append_output(f"{self.current_dir}\n")
            return
        
        # Run external command
        self._run_command(command)
    
    def _send_input_to_process(self, text: str):
        """Send input to the currently running process"""
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            # Echo the input in the terminal
            self.output.append_output(f"{text}\n", QColor(self.theme.terminal_foreground))
            # Send the input with newline to the process stdin
            input_bytes = (text + "\n").encode('utf-8')
            self.running_process.write(input_bytes)
    
    def _handle_cd(self, path: str):
        """Handle cd command"""
        # Handle ~ for home directory
        if path.startswith('~'):
            path = str(Path.home()) + path[1:]
        
        # Make absolute
        if not os.path.isabs(path):
            path = os.path.join(self.current_dir, path)
        
        # Normalize
        path = os.path.normpath(path)
        
        if os.path.isdir(path):
            self.current_dir = path
            self._update_dir_label()
            self.output.append_output(f"Changed directory to: {path}\n", 
                                       QColor(self.theme.success))
            self.directory_changed.emit(path)
        else:
            self.output.append_output(f"Directory not found: {path}\n", 
                                       QColor(self.theme.error))
    
    def _run_command(self, command: str):
        """Run an external command asynchronously with interactive support"""
        shell = self.shell_combo.currentText()
        
        if sys.platform == 'win32':
            if shell == 'cmd':
                args = ['/c', command]
                program = 'cmd'
            elif shell == 'powershell':
                args = ['-Command', command]
                program = 'powershell'
            else:
                args = ['-c', command]
                program = shell
        else:
            args = ['-c', command]
            program = shell if shell else '/bin/sh'
        
        # Clean up any previous running process
        if self.running_process:
            self.running_process.deleteLater()
        
        process = QProcess(self)
        process.setWorkingDirectory(self.current_dir)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        # Store as the running process for interactive input
        self.running_process = process
        
        # Update prompt to indicate we're in a running program
        self.prompt_label.setText(">")
        self.input.setPlaceholderText("Enter input for program (or Ctrl+C to stop)...")
        
        # Capture output asynchronously
        process.readyReadStandardOutput.connect(
            lambda: self._on_command_output(process)
        )
        process.finished.connect(
            lambda code, status: self._on_command_finished(code, status, process)
        )
        
        process.start(program, args)
        
        # Don't wait - let it run asynchronously
        self.command_executed.emit(command)
    
    def _on_command_output(self, process: QProcess):
        """Handle command output"""
        data = process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        self.output.append_output(text)
    
    def _on_command_finished(self, exit_code: int, exit_status, process: QProcess = None):
        """Handle command completion"""
        # Clear the running process if this was it
        if process and process == self.running_process:
            self.running_process = None
            # Reset prompt back to normal (with safety check for widget deletion)
            try:
                self.prompt_label.setText("$")
                self.input.setPlaceholderText("Enter command...")
            except RuntimeError:
                # Widget was deleted, ignore
                pass
        
        if exit_code != 0:
            try:
                self.output.append_output(f"\nProcess exited with code {exit_code}\n",
                                           QColor(self.theme.warning))
            except RuntimeError:
                pass
    
    def _on_output_ready(self):
        """Handle output from shell process"""
        if self.process:
            data = self.process.readAllStandardOutput()
            text = bytes(data).decode('utf-8', errors='replace')
            self.output.append_output(text)
    
    def _on_process_finished(self, exit_code: int, exit_status):
        """Handle shell process finishing"""
        self.output.append_output(f"\nShell exited with code {exit_code}\n",
                                   QColor(self.theme.warning))
    
    def _on_process_error(self, error):
        """Handle process errors"""
        error_msg = {
            QProcess.ProcessError.FailedToStart: "Failed to start",
            QProcess.ProcessError.Crashed: "Process crashed",
            QProcess.ProcessError.Timedout: "Process timed out",
            QProcess.ProcessError.WriteError: "Write error",
            QProcess.ProcessError.ReadError: "Read error",
            QProcess.ProcessError.UnknownError: "Unknown error"
        }.get(error, str(error))
        
        self.output.append_output(f"\nProcess error: {error_msg}\n",
                                   QColor(self.theme.error))
    
    def _update_dir_label(self):
        """Update the directory label"""
        # Shorten path for display
        path = self.current_dir
        home = str(Path.home())
        if path.startswith(home):
            path = "~" + path[len(home):]
        
        # Truncate if too long
        max_len = 40
        if len(path) > max_len:
            path = "..." + path[-(max_len-3):]
        
        self.dir_label.setText(path)
    
    def _history_up(self):
        """Navigate up in command history"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.input.setText(self.command_history[self.history_index])
    
    def _history_down(self):
        """Navigate down in command history"""
        if self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.input.setText(self.command_history[self.history_index])
            else:
                self.history_index = len(self.command_history)
                self.input.clear()
    
    def _on_shell_changed(self, shell: str):
        """Handle shell selection change"""
        self.settings_manager.settings.terminal.shell = shell
        self.settings_manager.save()
        self.clear_output()
        self._start_shell()
    
    def clear_output(self):
        """Clear the terminal output"""
        # Kill any running process and reset prompt
        self._stop_running_process()
        self.output.clear()
        self.output.append_output(f"Terminal ready. Working directory: {self.current_dir}\n",
                                   QColor(self.theme.info))
    
    def restart_shell(self):
        """Restart the shell"""
        # Kill any running process and reset prompt
        self._stop_running_process()
        self.clear_output()
        self._start_shell()
    
    def _stop_running_process(self):
        """Stop any running process and reset the prompt"""
        if self.running_process and self.running_process.state() == QProcess.ProcessState.Running:
            self.running_process.kill()
            self.running_process.waitForFinished(1000)
        self.running_process = None
        # Reset prompt back to normal
        try:
            self.prompt_label.setText("$")
            self.input.setPlaceholderText("Enter command...")
        except RuntimeError:
            # Widget was deleted, ignore
            pass
    
    def set_working_directory(self, path: str):
        """Set the working directory"""
        if os.path.isdir(path):
            self.current_dir = path
            self._update_dir_label()
            self.output.append_output(f"Working directory: {path}\n",
                                       QColor(self.theme.info))
    
    def _get_ez_interpreter(self) -> Optional[str]:
        """Get the EZ interpreter path from settings or PATH"""
        # Check configured path first
        configured = self.settings_manager.settings.ez.interpreter_path
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        
        # Fall back to PATH
        return shutil.which('ez')
    
    def run_ez_file(self, filepath: str):
        """Run an EZ file"""
        if not filepath or not os.path.exists(filepath):
            return
        
        ez_cmd = self._get_ez_interpreter()
        if not ez_cmd:
            self.output.append_output(
                "Error: EZ interpreter not found.\n"
                "Configure via: Run > Select EZ Interpreter\n"
                "Or install EZ: make install (from project root)\n",
                QColor(self.theme.error)
            )
            return
        
        # Set directory to file's directory
        file_dir = os.path.dirname(filepath)
        self.set_working_directory(file_dir)
        
        # Run the file
        command = f'"{ez_cmd}" "{filepath}"'
        self._execute_command(command)
    
    def focus_input(self):
        """Focus the input field"""
        self.input.setFocus()
