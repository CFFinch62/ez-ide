# EZ IDE User Guide

A comprehensive guide to using EZ IDE for developing EZ language applications.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [The Main Interface](#the-main-interface)
3. [File Browser](#file-browser)
4. [Code Editor](#code-editor)
5. [Integrated Terminal](#integrated-terminal)
6. [Running EZ Programs](#running-ez-programs)
7. [Step Debugging](#step-debugging)
8. [Theming](#theming)
9. [Keyboard Shortcuts](#keyboard-shortcuts)
10. [Configuration](#configuration)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: Version 3.8 or higher
- **EZ Interpreter**: Must be installed and accessible in your system PATH

### Installation

1. **Clone or Download** the EZ IDE project to your local machine

2. **Make Scripts Executable** (Linux/macOS):
   ```bash
   chmod +x setup.sh run.sh
   ```

3. **Run the Setup Script**:
   ```bash
   ./setup.sh
   ```
   This creates a Python virtual environment and installs PyQt6 and other dependencies.

4. **Launch the IDE**:
   ```bash
   ./run.sh
   ```

### First Launch

On first launch, EZ IDE will:
- Create a configuration directory in your system's standard config location
- Initialize default settings
- Apply the default theme (Dark)

---

## The Main Interface

EZ IDE features a modern, three-panel layout:

```
┌─────────────────────────────────────────────────────────────┐
│  Menu Bar │ Toolbar                                         │
├───────────┬─────────────────────────────────────────────────┤
│           │                                                 │
│   File    │          Code Editor (Tabbed)                   │
│  Browser  │                                                 │
│           │                                                 │
│           ├─────────────────────────────────────────────────┤
│           │          Terminal                               │
│           │                                                 │
└───────────┴─────────────────────────────────────────────────┘
│                       Status Bar                            │
└─────────────────────────────────────────────────────────────┘
```

### Menu Bar

- **File**: New, Open, Save, Recent Files, Exit
- **Edit**: Undo, Redo, Cut, Copy, Paste, Find, Go to Line
- **View**: Toggle File Browser, Toggle Terminal, Terminal Position, Themes, Word Wrap
- **Run**: Run File, Select EZ Interpreter
- **Debug**: Start Debugging, Step Over, Stop Debugging, Toggle Debug Panel
- **Settings**: Open Settings dialog
- **Help**: Documentation, About

### Toolbar

Quick access buttons for:
- Toggle File Browser visibility
- Toggle Terminal visibility
- Run current file
- Start debugging (🐛)

### Status Bar

Displays:
- Current file path
- Cursor position (Line:Column)
- File encoding
- EZ interpreter status

---

## File Browser

The file browser provides full project navigation capabilities.

### Basic Navigation

- **Single Click**: Select a file or folder
- **Double Click**: Open a file in the editor / Expand or collapse a folder
- **Back/Forward Buttons**: Navigate through your browsing history

### Context Menu (Right-Click)

Right-click on files or folders to access:

| Action | Description |
|--------|-------------|
| **New File** | Create a new file in the selected location |
| **New Folder** | Create a new folder |
| **Rename** | Rename the selected item |
| **Delete** | Delete the selected item (with confirmation) |
| **Open in Terminal** | Open a terminal at the selected folder's location |

### Bookmarks

Create bookmarks for quick access to frequently used folders:

1. Navigate to the desired folder
2. Right-click and select **Add to Bookmarks**
3. Access bookmarks from the Bookmarks panel above the file tree

To remove a bookmark, right-click it and select **Remove Bookmark**.

### Hidden Files

Toggle the visibility of hidden files (files starting with `.`):
- **View → Show Hidden Files** in the menu
- Or use the toolbar button

### Toggling Visibility

- Press `Ctrl+B` to show/hide the file browser
- Or use **View → Toggle File Browser**
- Or click the file browser button in the toolbar

---

## Code Editor

The code editor is the heart of EZ IDE, featuring syntax highlighting optimized for the EZ language.

### Tabs

- **Open Multiple Files**: Each file opens in its own tab
- **Close Tab**: Click the `×` on the tab or press `Ctrl+W`
- **Modified Indicator**: Unsaved files show a `•` after the filename
- **Reorder Tabs**: Drag and drop tabs to reorder them

### Syntax Highlighting

EZ IDE provides syntax highlighting for:
- **Keywords**: `let`, `func`, `if`, `else`, `for`, `while`, `return`, `struct`, `enum`, etc.
- **Built-in Types**: `int`, `float`, `string`, `bool`, `array`, `map`, etc.
- **Strings**: Single and double-quoted strings
- **Numbers**: Integer and floating-point literals
- **Comments**: Single-line (`//`) and multi-line (`/* */`)
- **Operators**: Arithmetic, comparison, and logical operators

### Editor Features

| Feature | Description |
|---------|-------------|
| **Line Numbers** | Displayed on the left margin |
| **Current Line Highlight** | The active line is highlighted |
| **Auto-indent** | Maintains indentation when pressing Enter |
| **Bracket Matching** | Matching brackets are highlighted |
| **Word Wrap** | Toggle with **View → Word Wrap** |

### Zooming

Adjust the editor font size:
- **Zoom In**: `Ctrl++` or `Ctrl+Mouse Wheel Up`
- **Zoom Out**: `Ctrl+-` or `Ctrl+Mouse Wheel Down`
- **Reset Zoom**: `Ctrl+0`

### Find and Replace

Press `Ctrl+F` to open the Find dialog:
- Enter search text
- Use **Find Next** / **Find Previous** buttons
- Toggle case sensitivity

### Go to Line

Press `Ctrl+G` to jump to a specific line number.

---

## Integrated Terminal

The integrated terminal allows you to run commands without leaving the IDE.

### Features

- **Shell Access**: Full access to your system shell (bash, zsh, etc.)
- **Command History**: Use `Up`/`Down` arrows to navigate previous commands
- **Working Directory**: Automatically syncs with the file browser's current folder

### Positioning

Change the terminal position via **View → Terminal Position**:
- **Bottom**: Below the code editor (default)
- **Right**: To the right of the code editor

### Toggling Visibility

- Press `` Ctrl+` `` to show/hide the terminal
- Or use **View → Toggle Terminal**
- Or click the terminal button in the toolbar

### Terminal Controls

- **Clear**: Clears the terminal output (keeps current directory)
- **Restart**: Restarts the terminal session

---

## Running EZ Programs

### Quick Run

The fastest way to run the current EZ file:

1. Open an `.ez` file in the editor
2. Press `F5`
3. The program runs in the integrated terminal

### From Menu

Use **Run → Run File** to execute the current file.

### Selecting the EZ Interpreter

If the EZ binary is not in your system PATH, or you want to use a different version:

1. Go to **Run → Select EZ Interpreter**
2. Browse to the EZ binary location
3. The selected interpreter is saved to your settings

---

## Step Debugging

EZ IDE includes powerful debugging capabilities with automatic detection of the best available debugger.

### Debugger Types

The IDE automatically detects and uses the best available debugger:

| Type | Icon | Features | Performance |
|------|------|----------|-------------|
| **Native Debugger** | 🟢 | Full features: Step Into/Over/Out, Breakpoints, Call Stack, Variables | Fast |
| **REPL Debugger** | 🟡 | Limited features: Step, Variables | Slower |

The debugger type is shown in the debug panel header.

### Starting a Debug Session

1. **Open an EZ file** in the editor
2. **Start debugging** using any of these methods:
   - Press `F5`
   - Click **🐛 Debug** in the toolbar
   - Use **Debug → Start Debugging** from the menu
3. **The Debug Panel** opens on the right side

### Debug Panel

The debug panel contains three main sections:

#### Toolbar
- **Debugger Type Indicator**: Shows which debugger is active (🟢 Native or 🟡 REPL)
- **▶ Start/Resume**: Begin or continue debugging
- **→ Step**: Execute next statement
- **■ Stop**: End the debug session
- **Clear**: Clear variables and output
- **Status**: Shows current line or state

#### Variables Panel
- Displays all variables in the current scope
- Shows variable name, value, and type
- Updates automatically as you step through code
- Highlights recently changed variables

#### Output Panel
- Shows program output during debugging
- Displays error messages in red
- Supports ANSI color codes
- Auto-scrolls to latest output

### Debugging Controls

| Action | Shortcut | Description |
|--------|----------|-------------|
| **Start Debugging** | `F5` | Begin debugging the current file |
| **Step Into** | `F10` | Execute next statement, entering function calls |
| **Step Over** | `F10` | Execute next statement, skipping over function calls |
| **Step Out** | `Shift+F11` | Run until return from current function |
| **Continue** | `F5` (while debugging) | Run until next breakpoint |
| **Stop Debugging** | `Shift+F5` | End the debug session |
| **Toggle Debug Panel** | `Ctrl+Shift+D` | Show/hide the debug panel |

> **Note**: Step Into/Over/Out are only available with the Native Debugger (🟢). The REPL Debugger (🟡) only supports basic stepping.

### Debug Highlighting

During debugging:
- **Current line** is highlighted with a yellow background
- **Editor automatically scrolls** to keep the current line visible
- **Line numbers** show the execution position

### Using the Native Debugger (🟢)

The native debugger provides full debugging features:

#### Setting Breakpoints
1. Click in the left margin next to a line number
2. A red dot appears indicating a breakpoint
3. Program execution will pause when reaching this line

#### Stepping Through Code
- **Step Into** (`F10`): Steps into function calls to debug them
- **Step Over** (`F10`): Executes function calls without stepping into them
- **Step Out** (`Shift+F11`): Runs until the current function returns

#### Viewing the Call Stack
The call stack panel shows:
- Current function and line
- All calling functions
- Click any frame to view its variables

#### Variable Inspection
- All variables in the current scope are shown
- Expand complex types (arrays, maps, structs) to see contents
- Hover over variables in the editor to see their values

### Using the REPL Debugger (🟡)

The REPL debugger is a fallback with limited features:

#### How It Works
- Parses your code into individual statements
- Sends each statement to the EZ REPL
- Automatically inspects variables after each step
- Shows variable values in the Variables panel

#### Stepping Through Code
- Click **→ Step** or press `F10` to execute the next statement
- Variables update automatically
- Output appears in the Output panel

#### Limitations
- **No breakpoints**: Must step through from the beginning
- **No Step Into/Over/Out**: Only basic stepping
- **No call stack**: Limited function call information
- **Slower**: Parses and sends statements individually
- **Relative imports**: May not work with relative imports

### Debug Workflow Example

1. **Open your EZ file**:
   ```ez
   import @std
   using std
   
   do main() {
       temp x int = 10
       temp y int = 20
       temp sum int = x + y
       println("Sum: ${sum}")
   }
   ```

2. **Start debugging** (F5)
   - Debug panel opens
   - Debugger type is shown (🟢 or 🟡)
   - Execution pauses at first statement

3. **Step through code** (F10)
   - Line `temp x int = 10` executes
   - Variable `x` appears in Variables panel with value `10`
   
4. **Continue stepping**
   - Line `temp y int = 20` executes
   - Variable `y` appears with value `20`
   - Line `temp sum int = x + y` executes
   - Variable `sum` appears with value `30`

5. **View output**
   - Line `println("Sum: ${sum}")` executes
   - Output "Sum: 30" appears in Output panel

6. **Stop debugging** (Shift+F5)
   - Debug session ends
   - Highlighting is cleared
   - Variables remain visible for review

### Debugging Tips

#### For Best Results
- **Use the Native Debugger** when available (🟢)
- **Save your file** before debugging
- **Check the debugger type** in the debug panel header
- **Use breakpoints** to skip to specific locations (Native only)

#### Common Issues

**Debugger not starting:**
- Ensure EZ interpreter is installed and in PATH
- Check **Run → Select EZ Interpreter** if needed
- Verify the file has no syntax errors

**Variables not showing:**
- Ensure you're using `temp` or `const` to declare variables
- Check that the statement has executed (step past it)
- For REPL debugger, ensure `import @std` is present

**Slow debugging:**
- REPL debugger (🟡) is slower than Native (🟢)
- Consider using the Native debugger if available
- For large programs, use breakpoints to skip sections

**Relative imports failing:**
- REPL debugger doesn't support relative imports
- Use absolute imports or the Native debugger

### Advanced Features (Native Debugger Only)

#### Conditional Breakpoints
Set breakpoints that only trigger when a condition is true:
1. Right-click on a breakpoint
2. Select "Edit Breakpoint"
3. Enter a condition (e.g., `x > 10`)

> **Note**: This feature may not be available in all versions.

#### Watch Expressions
Monitor specific expressions as you debug:
1. Open the Watch panel
2. Add an expression (e.g., `x + y`)
3. Value updates as you step through code

> **Note**: This feature may not be available in all versions.

### Selecting the Debugger

The IDE automatically selects the best debugger, but you can influence this:

1. **Install EZ with debugger support**:
   - Use the latest EZ version with `ez debugserver` command
   - The IDE will automatically detect and use the Native debugger

2. **Check debugger type**:
   - Look at the debug panel header
   - 🟢 = Native (full features)
   - 🟡 = REPL (limited features)

3. **Configure EZ interpreter**:
   - Go to **Run → Select EZ Interpreter**
   - Choose the EZ binary with debugger support
   - Restart the IDE to re-detect capabilities

### Troubleshooting Debugging

**Debug panel not showing:**
- Press `Ctrl+Shift+D` to toggle visibility
- Or use **Debug → Toggle Debug Panel**

**Debugger hangs:**
- Click **■ Stop** to end the session
- If unresponsive, restart the IDE
- Check for infinite loops in your code

**Variables not updating:**
- Ensure you've stepped past the variable declaration
- For REPL debugger, check that `import @std` is present
- Try restarting the debug session

**Breakpoints not working:**
- Breakpoints only work with Native debugger (🟢)
- Ensure the line has executable code
- Check that the file path is correct

For more debugging information, see the [Debugger Integration Guide](docs/DEBUGGER_INTEGRATION.md).

---

## Theming

EZ IDE supports extensive theming with 12 built-in themes.

### Built-in Themes

**Dark Themes:**
- Dark (default)
- Monokai
- Nord
- Dracula
- One Dark
- Gruvbox Dark
- Tokyo Night

**Light Themes:**
- Light
- Solarized Light
- GitHub Light
- Gruvbox Light
- One Light

### Changing Themes

1. Go to **View → Theme** in the menu
2. Select your desired theme
3. The theme is applied immediately and saved to settings

### Custom Themes

Create your own themes by adding JSON files to the themes directory.

**Theme Directory Locations:**
| Platform | Path |
|----------|------|
| Linux/macOS | `~/.config/ez-ide/themes/` |
| Windows | `%APPDATA%\EZ-IDE\themes\` |

**Theme JSON Structure:**

```json
{
  "name": "My Custom Theme",
  "is_dark": true,
  "background": "#1e1e2e",
  "foreground": "#cdd6f4",
  "accent": "#89b4fa",
  "accent_hover": "#b4befe",
  "panel_background": "#181825",
  "panel_border": "#313244",
  "editor_background": "#1e1e2e",
  "editor_foreground": "#cdd6f4",
  "editor_line_highlight": "#313244",
  "editor_selection": "#45475a",
  "line_number": "#6c7086",
  "line_number_active": "#cdd6f4",
  "tab_background": "#181825",
  "tab_active_background": "#1e1e2e",
  "tab_hover_background": "#313244",
  "tab_border": "#313244",
  "scrollbar_thumb": "#45475a",
  "scrollbar_track": "#1e1e2e",
  "menu_background": "#1e1e2e",
  "menu_hover": "#313244",
  "menu_border": "#45475a",
  "toolbar_background": "#1e1e2e",
  "statusbar_background": "#181825",
  "statusbar_foreground": "#a6adc8",
  "button_background": "#313244",
  "button_foreground": "#cdd6f4",
  "button_hover": "#45475a",
  "button_pressed": "#585b70",
  "input_background": "#313244",
  "input_border": "#45475a",
  "input_focus_border": "#89b4fa",
  "success": "#a6e3a1",
  "warning": "#f9e2af",
  "error": "#f38ba8",
  "info": "#89b4fa",
  "syntax": {
    "keyword": "#cba6f7",
    "builtin": "#f9e2af",
    "type": "#f9e2af",
    "string": "#a6e3a1",
    "number": "#fab387",
    "comment": "#6c7086",
    "operator": "#89dceb",
    "function": "#89b4fa",
    "variable": "#f38ba8",
    "constant": "#fab387",
    "identifier": "#cdd6f4"
  }
}
```

Themes are automatically loaded on IDE startup.

---

## Keyboard Shortcuts

### File Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New File |
| `Ctrl+O` | Open File |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save All Open Files |
| `Ctrl+W` | Close Current Tab |

### Edit Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+X` | Cut |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+A` | Select All |
| `Ctrl+F` | Find |
| `Ctrl+G` | Go to Line |

### View & Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Toggle File Browser |
| `` Ctrl+` `` | Toggle Terminal |
| `Ctrl++` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Reset Zoom |

### Running Code

| Shortcut | Action |
|----------|--------|
| `F5` | Run Current File / Start Debugging |

### Debugging

| Shortcut | Action |
|----------|--------|
| `F5` | Start Debugging |
| `F10` | Step Over |
| `Shift+F5` | Stop Debugging |
| `Ctrl+Shift+D` | Toggle Debug Panel |

### Settings

| Shortcut | Action |
|----------|--------|
| `Ctrl+,` | Open Settings |

---

## Configuration

### Settings Dialog

Access settings via **Settings → Preferences** or press `Ctrl+,`:

- **Editor Settings**: Font family, font size, tab size, word wrap
- **Theme Selection**: Choose from available themes
- **Terminal Position**: Bottom or Right
- **File Browser Settings**: Show hidden files
- **EZ Interpreter Path**: Custom path to EZ binary

### Settings File Location

Settings are stored as JSON in:

| Platform | Path |
|----------|------|
| Linux | `~/.config/ez-ide/settings.json` |
| macOS | `~/.config/ez-ide/settings.json` |
| Windows | `%APPDATA%\EZ-IDE\settings.json` |

### Manual Settings Editing

You can manually edit `settings.json` if needed:

```json
{
  "theme": "Dark",
  "font_family": "JetBrains Mono",
  "font_size": 13,
  "tab_size": 4,
  "word_wrap": false,
  "show_hidden_files": false,
  "terminal_position": "bottom",
  "recent_files": [],
  "bookmarks": [],
  "ez_interpreter_path": ""
}
```

---

## Troubleshooting

### IDE Won't Start

**Symptom**: Running `./run.sh` produces an error or nothing happens.

**Solutions**:
1. Ensure Python 3.8+ is installed: `python3 --version`
2. Re-run setup: `./setup.sh`
3. Check for PyQt6 installation: `source venv/bin/activate && pip list | grep PyQt6`

### Syntax Highlighting Not Working

**Symptom**: EZ files appear as plain text.

**Solutions**:
1. Ensure the file has `.ez` extension
2. Try restarting the IDE
3. Check if the theme's syntax colors are properly configured

### EZ Programs Won't Run

**Symptom**: Pressing F5 shows "EZ interpreter not found" or similar error.

**Solutions**:
1. Verify EZ is installed: `which ez` or `ez --version`
2. If EZ is not in PATH, set the interpreter path:
   - Go to **Run → Select EZ Interpreter**
   - Browse to the EZ binary location
3. Restart the IDE after changing the interpreter path

### Terminal Not Responding

**Symptom**: Terminal appears frozen or won't accept input.

**Solutions**:
1. Click the **Restart** button in the terminal
2. Toggle terminal visibility with `` Ctrl+` `` twice
3. Restart the IDE

### Theme Not Applying

**Symptom**: Custom theme not appearing or not loading correctly.

**Solutions**:
1. Verify JSON syntax is valid in your theme file
2. Ensure all required fields are present
3. Check the theme is in the correct directory
4. Look for error messages in the terminal where EZ IDE was launched

### Settings Not Saving

**Symptom**: Settings reset after restarting the IDE.

**Solutions**:
1. Check write permissions on the config directory
2. Ensure the settings file isn't corrupted (valid JSON)
3. Try deleting `settings.json` to reset to defaults

---

## Getting Help

- **Documentation**: This user guide and the [README](README.md)
- **EZ Language Docs**: Refer to the main EZ language documentation
- **Examples**: Check the `examples/` folder for sample EZ programs

---

*EZ IDE - Part of the EZ Language Project*
*MIT License - Copyright (c) 2025 Marshall A Burns*
