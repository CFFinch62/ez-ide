"""
Go Debug Session Manager for EZ IDE
JSON-RPC protocol communication with native Go debugger
"""

import json
import os
import shutil
from typing import Optional, Dict
from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class GoDebugSession(QObject):
    """
    Manages a debug session using the native Go debugger via JSON-RPC protocol

    Communicates with 'ez debugserver' command over stdin/stdout using
    line-delimited JSON messages.
    """

    # Signals - same interface as DebugSession for compatibility
    line_changed = pyqtSignal(int)              # Current line number (1-indexed)
    variable_updated = pyqtSignal(str, str)     # variable name, value
    output_received = pyqtSignal(str)           # Program output (non-debug)
    error_received = pyqtSignal(str)            # Error message
    session_started = pyqtSignal()
    session_ended = pyqtSignal()
    ready_for_step = pyqtSignal()               # Ready for next step

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.process: Optional[QProcess] = None
        self.filepath = ""
        self.working_dir = ""
        self.current_line = 0
        self._supports_step = True

    def supports_step(self) -> bool:
        """Returns True - native debugger always supports stepping"""
        return True

    def _get_ez_interpreter(self) -> Optional[str]:
        """Get the EZ interpreter path"""
        configured = self.settings_manager.settings.ez.interpreter_path
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which('ez')

    def start(self, filepath: str, working_dir: Optional[str] = None) -> bool:
        """
        Start a debug session for the given file

        Args:
            filepath: Path to the .ez file to debug
            working_dir: Working directory to use (defaults to file's directory)

        Returns:
            True if session started successfully, False otherwise
        """
        ez_path = self._get_ez_interpreter()
        if not ez_path:
            self.error_received.emit("EZ interpreter not found. Please configure it in Run → Select EZ Interpreter")
            return False

        self.filepath = filepath
        self.working_dir = working_dir or os.path.dirname(filepath)

        # Create QProcess
        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.working_dir)

        # Connect signals
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)

        # Start debugserver
        self.process.start(ez_path, ['debugserver', filepath])

        if not self.process.waitForStarted(3000):
            self.error_received.emit("Failed to start debugger")
            return False

        # Send initialize command
        self._send_command('initialize', {
            'file': filepath,
            'workingDir': self.working_dir
        })

        self.session_started.emit()
        return True

    def step(self):
        """Execute next statement (step into)"""
        self._send_command('stepInto', {})

    def step_over(self):
        """Execute next statement (step over function calls)"""
        self._send_command('stepOver', {})

    def step_out(self):
        """Continue until return from current function"""
        self._send_command('stepOut', {})

    def continue_execution(self):
        """Continue execution until next breakpoint"""
        self._send_command('continue', {})

    def set_breakpoint(self, file: str, line: int):
        """Set a breakpoint at the specified location"""
        self._send_command('setBreakpoint', {
            'file': file,
            'line': line
        })

    def clear_breakpoint(self, file: str, line: int):
        """Clear a breakpoint at the specified location"""
        self._send_command('clearBreakpoint', {
            'file': file,
            'line': line
        })

    def get_variables(self, frame_index: int = 0):
        """Request variables for the specified frame"""
        self._send_command('getVariables', {'frameIndex': frame_index})

    def get_stack_trace(self):
        """Request the current call stack"""
        self._send_command('getStackTrace', {})

    def stop(self):
        """Stop the debug session"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self._send_command('terminate', {})
            self.process.waitForFinished(1000)
            if self.process.state() == QProcess.ProcessState.Running:
                self.process.kill()
            self.process = None
        self.session_ended.emit()

    def _send_command(self, command: str, params: Dict):
        """Send a JSON-RPC command to the debugger"""
        if not self.process or self.process.state() != QProcess.ProcessState.Running:
            return

        message = {
            'type': 'command',
            'command': command,
            'params': params
        }

        json_str = json.dumps(message) + '\n'
        self.process.write(json_str.encode('utf-8'))

    def _handle_stdout(self):
        """Handle output from the debugger (JSON events)"""
        if not self.process:
            return

        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')

        # Process line-delimited JSON
        for line in data.strip().split('\n'):
            if not line:
                continue

            try:
                message = json.loads(line)
                self._handle_event(message)
            except json.JSONDecodeError as e:
                self.error_received.emit(f"Invalid JSON from debugger: {e}")

    def _handle_stderr(self):
        """Handle stderr from the debugger"""
        if not self.process:
            return

        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        if data.strip():
            self.error_received.emit(data.strip())

    def _handle_event(self, message: Dict):
        """Process an event message from the debugger"""
        if message.get('type') != 'event':
            return

        event = message.get('event')
        data = message.get('data', {})

        if event == 'initialized':
            # Debugger initialized, send start command
            self._send_command('start', {})

        elif event == 'started':
            # Program execution started
            pass

        elif event == 'stopped':
            # Execution paused
            location = data.get('location', {})
            line = location.get('line', 0)
            if line > 0:
                self.current_line = line
                self.line_changed.emit(line)

            # Request variables for current frame
            self.get_variables(0)

            # Ready for next step
            self.ready_for_step.emit()

        elif event == 'output':
            # Program output
            text = data.get('text', '')
            category = data.get('category', 'stdout')
            if category == 'stdout':
                self.output_received.emit(text)
            else:
                self.error_received.emit(text)

        elif event == 'error':
            # Error occurred
            message_text = data.get('message', 'Unknown error')
            self.error_received.emit(message_text)

        elif event == 'variableUpdate':
            # Variable updated
            name = data.get('name', '')
            value = data.get('value', '')
            if name:
                self.variable_updated.emit(name, value)

        elif event == 'variables':
            # Variables response
            variables = data.get('variables', [])
            for var in variables:
                name = var.get('name', '')
                value = var.get('value', '')
                if name:
                    self.variable_updated.emit(name, value)

        elif event == 'stackTrace':
            # Stack trace response (could be used for UI)
            frames = data.get('frames', [])
            # For now, just log it
            # Could emit a separate signal if needed

        elif event == 'breakpointSet':
            # Breakpoint confirmation
            pass

        elif event == 'breakpointCleared':
            # Breakpoint cleared confirmation
            pass

        elif event == 'exited':
            # Program exited
            exit_code = data.get('exitCode', 0)
            if exit_code == 0:
                self.output_received.emit("\n✓ Program completed successfully")
            else:
                self.error_received.emit(f"\n✗ Program exited with code {exit_code}")
            self.session_ended.emit()

        elif event == 'terminated':
            # Debug session terminated
            self.session_ended.emit()

    def _handle_finished(self, exit_code, exit_status):
        """Handle process finished"""
        self.session_ended.emit()

    def _handle_error(self, error):
        """Handle process error"""
        error_messages = {
            QProcess.ProcessError.FailedToStart: "Failed to start debugger",
            QProcess.ProcessError.Crashed: "Debugger crashed",
            QProcess.ProcessError.Timedout: "Debugger timed out",
            QProcess.ProcessError.WriteError: "Error writing to debugger",
            QProcess.ProcessError.ReadError: "Error reading from debugger",
        }

        msg = error_messages.get(error, f"Unknown error: {error}")
        self.error_received.emit(msg)
        self.session_ended.emit()
