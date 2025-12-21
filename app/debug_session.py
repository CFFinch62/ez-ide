"""
Debug Session Manager for EZ IDE
REPL-based step debugger with automatic variable inspection
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QTimer


class StatementType(Enum):
    """Types of EZ statements"""
    IMPORT = auto()
    VARIABLE_DECL = auto()
    CONST_DECL = auto()
    ASSIGNMENT = auto()
    EXPRESSION = auto()
    FUNCTION_DEF = auto()
    BLOCK = auto()  # if, while, for, etc.
    OTHER = auto()


@dataclass
class ParsedStatement:
    """A parsed EZ statement with metadata"""
    text: str
    line_number: int
    end_line: int
    statement_type: StatementType
    variables_modified: List[str]


class DebugSession(QObject):
    """
    Manages a debug session using the EZ REPL
    
    Sends statements one at a time and injects debug print statements
    after any statement that creates or modifies variables.
    """
    
    # Signals
    line_changed = pyqtSignal(int)              # Current line number
    variable_updated = pyqtSignal(str, str)     # variable name, value
    output_received = pyqtSignal(str)           # Program output (non-debug)
    error_received = pyqtSignal(str)            # Error message
    session_started = pyqtSignal()
    session_ended = pyqtSignal()
    ready_for_step = pyqtSignal()               # Ready for next step
    
    # Patterns for parsing EZ code
    IMPORT_PATTERN = re.compile(r'^\s*import\s+')
    VAR_DECL_PATTERN = re.compile(r'^\s*(temp|const)\s+(\w+)\s+')
    ASSIGN_PATTERN = re.compile(r'^\s*(\w+)\s*(\+|-|\*|/|%)?=\s*')
    FUNC_DEF_PATTERN = re.compile(r'^\s*do\s+(\w+)\s*\(')
    BLOCK_START_PATTERN = re.compile(r'^\s*(if|otherwise|while|loop|for|for_each|when)\s+')
    
    # Pattern for extracting debug output
    DEBUG_OUTPUT_PATTERN = re.compile(r'\[DEBUG\]\s*(.+)')
    DEBUG_VAR_PATTERN = re.compile(r'(\w+)\s*=\s*(.+?)(?:,\s*|$)')
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.process: Optional[QProcess] = None
        self.setup_statements: List[ParsedStatement] = []  # imports, funcs, globals
        self.statements: List[ParsedStatement] = []        # main body statements
        self.current_index = 0
        self.tracked_variables: Dict[str, str] = {}
        self.source_code = ""
        self.working_dir = ""
        self._pending_output = ""
        self._waiting_for_response = False
        self._step_timer = QTimer(self)
        self._step_timer.setSingleShot(True)
        self._step_timer.timeout.connect(self._check_ready)
    
    def _get_ez_interpreter(self) -> Optional[str]:
        """Get the EZ interpreter path"""
        configured = self.settings_manager.settings.ez.interpreter_path
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which('ez')
    
    def start(self, filepath: str) -> bool:
        """
        Start a debug session for the given file
        
        Args:
            filepath: Path to the .ez file to debug
            
        Returns:
            True if session started successfully
        """
        if not filepath or not os.path.exists(filepath):
            self.error_received.emit(f"File not found: {filepath}")
            return False
        
        ez_cmd = self._get_ez_interpreter()
        if not ez_cmd:
            self.error_received.emit(
                "EZ interpreter not found. Configure via Run > Select EZ Interpreter"
            )
            return False
        
        # Read and parse the source file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
        except Exception as e:
            self.error_received.emit(f"Error reading file: {e}")
            return False
        
        self.working_dir = os.path.dirname(filepath)
        
        # Parse statements - separates setup code from steppable main body
        self.setup_statements, self.statements = self._parse_statements(self.source_code)
        if not self.statements:
            self.error_received.emit("No statements found in main procedure")
            return False
        
        # Start REPL process
        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.working_dir)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        
        self.process.start(ez_cmd, ['repl'])
        
        if not self.process.waitForStarted(5000):
            self.error_received.emit("Failed to start EZ REPL")
            return False
        
        self.current_index = 0
        self.tracked_variables.clear()
        self._waiting_for_response = False
        
        # Wait a moment for REPL to initialize
        QTimer.singleShot(200, self._repl_ready)
        
        return True
    
    def _repl_ready(self):
        """Called when REPL is ready"""
        # Clear any initial REPL output (welcome message, etc)
        if self.process:
            self.process.readAllStandardOutput()
        
        # Send all setup statements (imports, function defs, globals) first
        for setup_stmt in self.setup_statements:
            self._send_to_repl(setup_stmt.text)
        
        # Give MORE time for setup to process - imports and function defs need time
        # 500ms base + 200ms per setup statement
        setup_time = 500 + (200 * len(self.setup_statements))
        QTimer.singleShot(setup_time, self._setup_complete)
    
    def _setup_complete(self):
        """Called after setup statements are sent"""
        # Don't clear output here - it may race with first step's output
        # Setup output is typically just function definitions echoed back
        
        self.session_started.emit()
        
        # Emit first line of main body
        if self.statements:
            self.line_changed.emit(self.statements[0].line_number)
        
        self.ready_for_step.emit()
    
    def step(self) -> bool:
        """
        Execute the next statement
        
        Returns:
            True if there are more statements, False if finished
        """
        if not self.process or self.process.state() != QProcess.ProcessState.Running:
            self.error_received.emit("Debug session not running")
            return False
        
        if self.current_index >= len(self.statements):
            self.stop()
            return False
        
        if self._waiting_for_response:
            return True  # Still processing previous step
        
        stmt = self.statements[self.current_index]
        
        # For block statements, inject debug prints inside the block
        if stmt.statement_type == StatementType.BLOCK:
            modified_text = self._inject_debug_prints_into_block(stmt.text)
            self._send_to_repl(modified_text)
        else:
            # Send the statement
            self._send_to_repl(stmt.text)
            
            # If this statement modifies variables, send debug print after
            if stmt.variables_modified:
                debug_print = self._generate_debug_print(stmt.variables_modified)
                self._send_to_repl(debug_print)
        
        self._waiting_for_response = True
        self._step_timer.start(200)  # Check for completion after 200ms
        
        return self.current_index < len(self.statements) - 1
    
    def _check_ready(self):
        """Check if we're ready for the next step"""
        if not self._waiting_for_response:
            return
            
        # Read any output that arrived but hasn't been processed yet
        if self.process:
            data = self.process.readAllStandardOutput()
            if data:
                text = bytes(data).decode('utf-8', errors='replace')
                self._pending_output += text
        
        # Process all accumulated output
        self._process_pending_output()
        
        # Bounds check before accessing statements
        if self.current_index >= len(self.statements):
            self._waiting_for_response = False
            self.line_changed.emit(-1)
            self.ready_for_step.emit()
            return
        
        self.current_index += 1
        
        # Emit line change for next statement
        if self.current_index < len(self.statements):
            next_stmt = self.statements[self.current_index]
            self.line_changed.emit(next_stmt.line_number)
        else:
            # Finished
            self.line_changed.emit(-1)
        
        self._waiting_for_response = False
        self.ready_for_step.emit()
    
    def stop(self):
        """Stop the debug session"""
        if self.process:
            # Send exit command
            self._send_to_repl("exit")
            self.process.waitForFinished(1000)
            
            if self.process.state() == QProcess.ProcessState.Running:
                self.process.kill()
            
            self.process = None
        
        self.statements.clear()
        self.current_index = 0
        self.tracked_variables.clear()
        self.session_ended.emit()
    
    def _send_to_repl(self, text: str):
        """Send a line to the REPL"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            data = (text + "\n").encode('utf-8')
            self.process.write(data)
    
    def _on_output(self):
        """Handle output from the REPL"""
        if not self.process:
            return
        
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        self._pending_output += text
    
    def _process_pending_output(self):
        """Process accumulated output"""
        if not self._pending_output:
            return
        
        lines = self._pending_output.split('\n')
        self._pending_output = ""
        
        for line in lines:
            # Strip REPL prompts from the line (they can appear multiple times)
            # Remove all >> and .. prompts from the line
            cleaned = line
            
            # Remove leading prompts iteratively
            while True:
                s = cleaned.strip()
                if s.startswith('>>'):
                    idx = cleaned.find('>>')
                    cleaned = cleaned[idx+2:].lstrip(' ')
                elif s.startswith('..'):
                    idx = cleaned.find('..')
                    cleaned = cleaned[idx+2:].lstrip(' ')
                else:
                    break
            
            stripped = cleaned.strip()
            
            # Skip REPL header and welcome messages
            if stripped.startswith('EZ Language') or stripped.startswith("Type 'help'") or stripped == 'Goodbye!':
                continue
            
            # Check for debug output - parse AND display
            debug_match = self.DEBUG_OUTPUT_PATTERN.match(stripped)
            if debug_match:
                var_string = debug_match.group(1)
                # Parse variable assignments for the variable tree
                for var_match in self.DEBUG_VAR_PATTERN.finditer(var_string):
                    name = var_match.group(1)
                    value = var_match.group(2).strip()
                    self.tracked_variables[name] = value
                    self.variable_updated.emit(name, value)
                # Also show the debug line in output
                self.output_received.emit(stripped)
            else:
                # Regular program output (including empty lines from println(""))
                self.output_received.emit(stripped)
    
    def _on_finished(self, exit_code: int, exit_status):
        """Handle REPL process finishing"""
        self.session_ended.emit()
    
    def _on_error(self, error):
        """Handle process error"""
        error_messages = {
            QProcess.ProcessError.FailedToStart: "Failed to start REPL",
            QProcess.ProcessError.Crashed: "REPL crashed",
            QProcess.ProcessError.Timedout: "REPL timed out",
        }
        msg = error_messages.get(error, f"Process error: {error}")
        self.error_received.emit(msg)
        self.session_ended.emit()
    
    def _parse_statements(self, source: str) -> Tuple[List[ParsedStatement], List[ParsedStatement]]:
        """
        Parse source code into setup statements and steppable main statements
        
        Returns:
            Tuple of (setup_statements, main_statements)
            - setup: imports, function defs, globals - sent to REPL before stepping
            - main: statements inside main procedure - stepped through
        """
        setup_statements = []
        main_statements = []
        lines = source.split('\n')
        i = 0
        in_multiline_comment = False
        
        # Pattern to detect main procedure
        main_pattern = re.compile(r'^\s*do\s+main\s*\(')
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Handle multi-line comments /* */
            if in_multiline_comment:
                if '*/' in line:
                    in_multiline_comment = False
                i += 1
                continue
            
            if stripped.startswith('/*'):
                in_multiline_comment = True
                if '*/' in stripped:
                    in_multiline_comment = False
                i += 1
                continue
            
            # Skip empty lines and single-line comments
            if not stripped or stripped.startswith('//'):
                i += 1
                continue
            
            # Check for main procedure - parse its body as steppable statements
            if main_pattern.match(stripped):
                main_stmts, end_line = self._parse_main_procedure(lines, i)
                main_statements.extend(main_stmts)
                i = end_line + 1
                continue
            
            # Everything else is setup (imports, function defs, globals)
            
            # Check for other function definitions - treat as single block
            if self.FUNC_DEF_PATTERN.match(stripped):
                start_line = i
                block_text, end_line = self._read_block(lines, i)
                
                setup_statements.append(ParsedStatement(
                    text=block_text,
                    line_number=start_line + 1,
                    end_line=end_line + 1,
                    statement_type=StatementType.FUNCTION_DEF,
                    variables_modified=[]
                ))
                i = end_line + 1
                continue
            
            # Check for control flow blocks at top level (unusual but handle it)
            if self.BLOCK_START_PATTERN.match(stripped):
                start_line = i
                block_text, end_line = self._read_block(lines, i)
                
                setup_statements.append(ParsedStatement(
                    text=block_text,
                    line_number=start_line + 1,
                    end_line=end_line + 1,
                    statement_type=StatementType.BLOCK,
                    variables_modified=[]
                ))
                i = end_line + 1
                continue
            
            # Single-line statements (imports, global vars, using statements)
            stmt_type, variables = self._analyze_statement(stripped)
            
            setup_statements.append(ParsedStatement(
                text=stripped,
                line_number=i + 1,
                end_line=i + 1,
                statement_type=stmt_type,
                variables_modified=variables
            ))
            i += 1
        
        return setup_statements, main_statements
    
    def _parse_main_procedure(self, lines: List[str], start: int) -> Tuple[List[ParsedStatement], int]:
        """
        Parse the main procedure body into individual steppable statements
        
        Returns list of statements and the ending line index
        """
        statements = []
        i = start
        brace_count = 0
        in_body = False
        in_multiline_comment = False
        
        # First, find the opening brace
        while i < len(lines):
            line = lines[i]
            
            if '{' in line:
                brace_count += line.count('{')
                brace_count -= line.count('}')
                in_body = True
                i += 1
                break
            i += 1
        
        # Now parse statements inside the main body
        while i < len(lines) and brace_count > 0:
            line = lines[i]
            stripped = line.strip()
            
            # Handle multi-line comments /* */
            if in_multiline_comment:
                if '*/' in line:
                    in_multiline_comment = False
                i += 1
                continue
            
            if stripped.startswith('/*'):
                in_multiline_comment = True
                if '*/' in stripped:
                    in_multiline_comment = False
                i += 1
                continue
            
            # Skip empty lines and single-line comments FIRST (before brace counting)
            if not stripped or stripped.startswith('//'):
                i += 1
                continue
            
            # Track braces (only on non-comment lines)
            brace_count += line.count('{')
            brace_count -= line.count('}')
            
            # If we hit the closing brace, we're done
            if brace_count <= 0:
                break
            
            # Skip lone closing braces
            if stripped == '}':
                i += 1
                continue
            
            # Check for nested blocks (if, while, etc.) - treat as single unit
            if self.BLOCK_START_PATTERN.match(stripped):
                start_line = i
                block_text, end_line = self._read_block(lines, i)
                variables = self._extract_variables_from_block(block_text)
                
                statements.append(ParsedStatement(
                    text=block_text,
                    line_number=start_line + 1,
                    end_line=end_line + 1,
                    statement_type=StatementType.BLOCK,
                    variables_modified=variables
                ))
                
                # Recalculate brace count after block
                block_opens = block_text.count('{')
                block_closes = block_text.count('}')
                
                i = end_line + 1
                continue
            
            # Regular statement inside main
            stmt_type, variables = self._analyze_statement(stripped)
            
            statements.append(ParsedStatement(
                text=stripped,
                line_number=i + 1,
                end_line=i + 1,
                statement_type=stmt_type,
                variables_modified=variables
            ))
            i += 1
        
        return statements, i
    
    def _read_block(self, lines: List[str], start: int) -> Tuple[str, int]:
        """Read a block starting at the given line until braces are balanced"""
        block_lines = []
        brace_count = 0
        i = start
        
        while i < len(lines):
            line = lines[i]
            block_lines.append(line)
            
            brace_count += line.count('{')
            brace_count -= line.count('}')
            
            if brace_count <= 0 and '{' in ''.join(block_lines):
                break
            
            i += 1
        
        return '\n'.join(block_lines), i
    
    def _analyze_statement(self, text: str) -> Tuple[StatementType, List[str]]:
        """Analyze a single-line statement"""
        variables = []
        
        # Import statement
        if self.IMPORT_PATTERN.match(text):
            return StatementType.IMPORT, []
        
        # Variable declaration: temp name type = value
        var_match = self.VAR_DECL_PATTERN.match(text)
        if var_match:
            keyword = var_match.group(1)
            var_name = var_match.group(2)
            variables.append(var_name)
            stmt_type = (StatementType.CONST_DECL 
                        if keyword == 'const' 
                        else StatementType.VARIABLE_DECL)
            return stmt_type, variables
        
        # Assignment: name = value or name += value etc.
        assign_match = self.ASSIGN_PATTERN.match(text)
        if assign_match:
            var_name = assign_match.group(1)
            # Make sure it's not a comparison (==)
            if not text.strip().startswith(var_name + ' =='):
                variables.append(var_name)
                return StatementType.ASSIGNMENT, variables
        
        return StatementType.EXPRESSION, []
    
    def _extract_variables_from_block(self, block_text: str) -> List[str]:
        """
        Extract variables that are modified within a block
        
        Scans the block for variable declarations and assignments
        """
        variables = set()
        
        for line in block_text.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            
            # Check for variable declaration
            var_match = self.VAR_DECL_PATTERN.match(stripped)
            if var_match:
                variables.add(var_match.group(2))
                continue
            
            # Check for assignment
            assign_match = self.ASSIGN_PATTERN.match(stripped)
            if assign_match:
                var_name = assign_match.group(1)
                # Avoid false positives like == comparisons
                if not stripped.startswith(var_name + ' =='):
                    variables.add(var_name)
        
        return list(variables)
    
    def _inject_debug_prints_into_block(self, block_text: str) -> str:
        """
        Inject debug print statements after lines that modify variables
        
        This allows variable tracking even inside blocks/loops
        """
        lines = block_text.split('\n')
        result_lines = []
        
        for line in lines:
            result_lines.append(line)
            stripped = line.strip()
            
            if not stripped or stripped.startswith('//') or stripped in ['{', '}']:
                continue
            
            # Get indent of current line for proper formatting
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            
            # Check for variable declaration
            var_match = self.VAR_DECL_PATTERN.match(stripped)
            if var_match:
                var_name = var_match.group(2)
                debug_line = f'{indent_str}std.println("[DEBUG] {var_name} = ${{{var_name}}}")'
                result_lines.append(debug_line)
                continue
            
            # Check for assignment (not inside other expressions)
            assign_match = self.ASSIGN_PATTERN.match(stripped)
            if assign_match:
                var_name = assign_match.group(1)
                if not stripped.startswith(var_name + ' =='):
                    debug_line = f'{indent_str}std.println("[DEBUG] {var_name} = ${{{var_name}}}")'
                    result_lines.append(debug_line)
        
        return '\n'.join(result_lines)
    
    def _generate_debug_print(self, variables: List[str]) -> str:
        """Generate a debug print statement for the given variables"""
        if not variables:
            return ""
        
        parts = [f'{name} = ${{{name}}}' for name in variables]
        return f'std.println("[DEBUG] {", ".join(parts)}")'
    
    @property
    def is_running(self) -> bool:
        """Check if debug session is active"""
        return (self.process is not None and 
                self.process.state() == QProcess.ProcessState.Running)
    
    @property 
    def current_line(self) -> int:
        """Get current line number (1-indexed) or -1 if not running"""
        if not self.is_running or self.current_index >= len(self.statements):
            return -1
        return self.statements[self.current_index].line_number
    
    @property
    def has_more_statements(self) -> bool:
        """Check if there are more statements to execute"""
        return self.current_index < len(self.statements)
    
    def get_variables(self) -> Dict[str, str]:
        """Get all tracked variables and their current values"""
        return dict(self.tracked_variables)
