# EZ IDE Debugger Integration

## Overview

The EZ IDE provides two debugger implementations to support different versions of the EZ interpreter:

1. **Native Go Debugger** (`GoDebugSession`) - Full-featured debugger using JSON-RPC protocol
2. **REPL Debugger** (`DebugSession`) - Fallback debugger using the EZ REPL

The IDE automatically detects which debugger to use based on the EZ interpreter version.

## Debugger Detection

### Automatic Selection

When the IDE starts, it automatically detects the best available debugger:

```python
from app.debugger_utils import detect_debugger_support

# Detect capabilities
ez_path = '/path/to/ez'
capabilities = detect_debugger_support(ez_path)

if capabilities.type == 'native':
    # Use GoDebugSession
    session = GoDebugSession(settings, parent)
elif capabilities.type == 'repl':
    # Use DebugSession (fallback)
    session = DebugSession(settings, parent)
else:
    # No debugger available
    pass
```

### Debugger Capabilities

| Feature | Native Debugger | REPL Debugger |
|---------|----------------|---------------|
| Step Into/Over/Out | ✅ | ✅ (Step only) |
| Breakpoints | ✅ | ❌ |
| Call Stack | ✅ | ❌ |
| Variable Inspection | ✅ | ✅ |
| Performance | Fast | Slower |
| Relative Imports | ✅ | ❌ |

## Native Go Debugger

### Architecture

The native debugger communicates with `ez debugserver` using JSON-RPC over stdin/stdout:

```
┌─────────────┐         JSON-RPC         ┌──────────────┐
│             │◄────────────────────────►│              │
│   EZ IDE    │   (stdin/stdout)         │ ez debugserver│
│             │                          │              │
└─────────────┘                          └──────────────┘
```

### Implementation (`app/go_debug_session.py`)

```python
class GoDebugSession(QObject):
    \"\"\"Manages debug session using native Go debugger\"\"\"
    
    # Signals
    line_changed = pyqtSignal(int)
    variable_updated = pyqtSignal(str, str)
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    session_started = pyqtSignal()
    session_ended = pyqtSignal()
    ready_for_step = pyqtSignal()
    
    def start(self, filepath: str, working_dir: str = None) -> bool:
        \"\"\"Start debug session\"\"\"
        self.process = QProcess(self)
        self.process.start('ez', ['debugserver', filepath])
        
        # Send initialize command
        self._send_command('initialize', {
            'file': filepath,
            'workingDir': working_dir
        })
        
    def _send_command(self, command: str, params: dict):
        \"\"\"Send JSON-RPC command\"\"\"
        message = {
            'type': 'command',
            'command': command,
            'params': params
        }
        json_str = json.dumps(message) + '\\n'
        self.process.write(json_str.encode('utf-8'))
    
    def _handle_event(self, message: dict):
        \"\"\"Handle event from debugger\"\"\"
        event = message.get('event')
        data = message.get('data', {})
        
        if event == 'stopped':
            line = data.get('location', {}).get('line', 0)
            self.line_changed.emit(line)
            self.get_variables(0)
        elif event == 'variables':
            for var in data.get('variables', []):
                self.variable_updated.emit(var['name'], var['value'])
```

### Protocol Messages

#### Commands (IDE → Debugger)

**Initialize**:
```json
{
  \"type\": \"command\",
  \"command\": \"initialize\",
  \"params\": {
    \"file\": \"/path/to/file.ez\",
    \"workingDir\": \"/path/to/project\"
  }
}
```

**Step Into**:
```json
{
  \"type\": \"command\",
  \"command\": \"stepInto\",
  \"params\": {}
}
```

**Set Breakpoint**:
```json
{
  \"type\": \"command\",
  \"command\": \"setBreakpoint\",
  \"params\": {
    \"file\": \"/path/to/file.ez\",
    \"line\": 15
  }
}
```

#### Events (Debugger → IDE)

**Stopped**:
```json
{
  \"type\": \"event\",
  \"event\": \"stopped\",
  \"data\": {
    \"location\": {
      \"file\": \"/path/to/file.ez\",
      \"line\": 11,
      \"column\": 1
    }
  }
}
```

**Variables**:
```json
{
  \"type\": \"event\",
  \"event\": \"variables\",
  \"data\": {
    \"variables\": [
      {\"name\": \"x\", \"value\": \"10\", \"type\": \"int\"},
      {\"name\": \"y\", \"value\": \"20\", \"type\": \"int\"}
    ]
  }
}
```

## REPL Debugger

### Architecture

The REPL debugger sends EZ statements one at a time to `ez repl`:

```
┌─────────────┐                          ┌──────────────┐
│             │   Statement by statement │              │
│   EZ IDE    │─────────────────────────►│   ez repl    │
│             │◄─────────────────────────│              │
└─────────────┘   Output + debug prints  └──────────────┘
```

### Implementation (`app/debug_session.py`)

```python
class DebugSession(QObject):
    \"\"\"REPL-based debugger (fallback)\"\"\"
    
    def start(self, filepath: str, working_dir: str = None) -> bool:
        \"\"\"Parse file and start REPL\"\"\"
        # Parse source into statements
        setup, main = self._parse_statements(source)
        
        # Start REPL
        self.process = QProcess(self)
        self.process.start('ez', ['repl'])
        
        # Send setup statements (imports, functions)
        for stmt in setup:
            self._send_to_repl(stmt)
        
        # Ready to step through main
        self.main_statements = main
        self.current_index = 0
    
    def step(self) -> bool:
        \"\"\"Execute next statement\"\"\"
        if self.current_index >= len(self.main_statements):
            return False
        
        stmt = self.main_statements[self.current_index]
        
        # Send statement to REPL
        self._send_to_repl(stmt.text)
        
        # Inject debug print for variables
        if stmt.variables_modified:
            debug_print = self._generate_debug_print(stmt.variables_modified)
            self._send_to_repl(debug_print)
        
        self.current_index += 1
        self.line_changed.emit(stmt.line_number)
        return True
```

### Limitations

- **No Breakpoints**: Cannot set breakpoints
- **No Call Stack**: Limited call stack information
- **No Relative Imports**: Fails with relative imports
- **Slower**: Parses and sends statements individually

## Debug Panel UI

### Components

The debug panel (`app/debug_panel.py`) consists of:

1. **Toolbar**:
   - Debugger type indicator (🟢 Native / 🟡 REPL)
   - Start/Stop buttons
   - Step button
   - Status label

2. **Variable Tree**:
   - Displays all variables in current scope
   - Shows name, value, and type
   - Updates in real-time

3. **Output Panel**:
   - Program output
   - Error messages
   - ANSI color support

### Usage

```python
# Set debugger type indicator
debug_panel.set_debugger_type('🟢', 'Native Debugger')

# Update variable
debug_panel.update_variable('x', '10')

# Show output
debug_panel.append_output('Hello, World!')

# Show error
debug_panel.append_error('Division by zero')
```

## Main Window Integration

### Debug Session Setup

```python
class EZIDEMainWindow(QMainWindow):
    def _setup_debug(self):
        # Detect debugger
        ez_path = self.settings.settings.ez.interpreter_path
        capabilities = detect_debugger_support(ez_path)
        
        # Create appropriate session
        if capabilities.type == 'native':
            self.debug_session = GoDebugSession(self.settings, self)
        else:
            self.debug_session = DebugSession(self.settings, self)
        
        # Connect signals
        self.debug_session.line_changed.connect(self._on_debug_line_changed)
        self.debug_session.variable_updated.connect(self._on_debug_variable_updated)
        # ... more connections
        
        # Update UI
        icon = get_debugger_icon(capabilities.type)
        name = get_debugger_display_name(capabilities.type)
        self.debug_panel.set_debugger_type(icon, name)
```

### Debug Controls

```python
def _debug_start(self):
    \"\"\"Start debugging current file\"\"\"
    filepath = self.editor_tabs.get_current_filepath()
    self.debug_session.start(filepath)

def _debug_step(self):
    \"\"\"Step to next statement\"\"\"
    self.debug_session.step()

def _debug_stop(self):
    \"\"\"Stop debugging\"\"\"
    self.debug_session.stop()
```

## Troubleshooting

### Native Debugger Not Detected

**Problem**: IDE uses REPL debugger even though `ez debugserver` is available.

**Solution**:
1. Check EZ interpreter path in settings
2. Verify `ez debugserver` works from command line:
   ```bash
   ez debugserver --help
   ```
3. Restart IDE to re-detect debugger

### Variables Not Updating

**Problem**: Variable panel doesn't show updated values.

**Solution**:
- **Native**: Check JSON-RPC communication in terminal
- **REPL**: Verify debug print injection is working

### Debugger Hangs

**Problem**: Debugger stops responding.

**Solution**:
1. Click Stop button
2. If unresponsive, restart IDE
3. Check for infinite loops in code

### Relative Imports Fail

**Problem**: \"Cannot use relative imports\" error.

**Solution**:
- This is a REPL debugger limitation
- Use native debugger (requires EZ with debugserver support)
- Or use absolute imports

## Performance Tips

### Native Debugger
- Fast and responsive
- Minimal overhead
- Suitable for large programs

### REPL Debugger
- Slower due to statement-by-statement execution
- Best for small programs
- Consider using native debugger for better performance

## Advanced Features

### Custom Debugger Path

Set a custom EZ interpreter path:

1. Go to **Run → Select EZ Interpreter**
2. Browse to your EZ binary
3. IDE will re-detect debugger capabilities

### Debugger Logs

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- JSON-RPC messages
- REPL communication
- Debug events

## API Reference

### `debugger_utils.py`

```python
def detect_debugger_support(ez_path: str) -> DebuggerCapabilities
def get_ez_version(ez_path: str) -> Optional[str]
def test_debugserver_available(ez_path: str) -> bool
def get_debugger_display_name(debugger_type: DebuggerType) -> str
def get_debugger_icon(debugger_type: DebuggerType) -> str
```

### `go_debug_session.py`

```python
class GoDebugSession(QObject):
    def start(filepath: str, working_dir: str = None) -> bool
    def step()
    def step_over()
    def step_out()
    def continue_execution()
    def set_breakpoint(file: str, line: int)
    def clear_breakpoint(file: str, line: int)
    def get_variables(frame_index: int = 0)
    def get_stack_trace()
    def stop()
```

### `debug_session.py`

```python
class DebugSession(QObject):
    def start(filepath: str, working_dir: str = None) -> bool
    def step() -> bool
    def stop()
    def is_running() -> bool
    def current_line() -> int
    def get_variables() -> dict
```

## Contributing

To improve debugger integration:

1. Test with different EZ versions
2. Report bugs with debug logs
3. Suggest UI improvements
4. Add new features

## See Also

- [EZ Debugger Documentation](../EZ/DEBUGGER.md) - Complete debugger specification
- [User Guide](user_guide.md) - IDE usage guide
- [EZ Language Documentation](https://github.com/marshallburns/ez) - EZ language reference

---

**Last Updated**: 2026-01-06
