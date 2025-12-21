# EZ IDE

<p align="center">
  <img src="images/EZ_LOGO.jpeg" alt="EZ IDE Logo" width="200">
</p>

<p align="center">
  <strong>A Modern, Themeable IDE for the EZ Programming Language</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#keyboard-shortcuts">Shortcuts</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#license">License</a>
</p>

---

EZ IDE is a full-featured integrated development environment built with Python and PyQt6, specifically designed for developing applications in the EZ programming language. It provides a modern, customizable interface with built-in syntax highlighting, an integrated terminal, file browser, and extensive theming support.

## Features

### 📁 File Browser
- Full-featured file/folder navigation with tree view
- Create, rename, and delete files and folders
- Folder bookmarks for quick project access
- Show/hide hidden files toggle
- Navigation history (back/forward buttons)
- Toggle visibility with `Ctrl+B` or via toolbar

### 📝 Code Editor
- **Tabbed Interface**: Open and work on multiple files simultaneously
- **Syntax Highlighting**: Full EZ language syntax highlighting with customizable colors
- **Line Numbers**: With current line highlighting
- **Smart Editing**: Auto-indent and bracket matching
- **Word Wrap**: Optional word wrapping for long lines
- **Zoom Control**: `Ctrl+Mouse Wheel` or `Ctrl++`/`Ctrl+-` for font size adjustment

### 💻 Integrated Terminal
- Execute shell commands directly within the IDE
- Command history navigation (up/down arrows)
- Quick EZ file execution with `F5`
- Flexible positioning: below or to the right of the editor
- Toggle visibility with `` Ctrl+` `` or via toolbar

### 🎨 Theming System
- **12 Built-in Themes**: Including Dark, Light, Monokai, Nord, Dracula, One Dark, Gruvbox Dark, Tokyo Night, Solarized Light, GitHub Light, Gruvbox Light, and One Light
- **Full Syntax Highlighting**: Customizable colors per theme
- **Custom Themes**: Create your own themes via JSON files
- **Persistent Settings**: All preferences saved to local JSON configuration

### 🐛 Step Debugging
- **REPL-based debugger**: Step through code using the actual EZ interpreter
- **Variable inspection**: Watch variables update as you step
- **Debug highlighting**: Current line highlighted in the editor
- **Simple controls**: F5 to start, F10 to step, Shift+F5 to stop

## Installation

### Prerequisites
- **Python 3.8** or higher
- **EZ language** https://github.com/SchoolyB/EZ installed and available in PATH (for running EZ files)

### Quick Setup

```bash
# Clone or navigate to the IDE directory
cd ez_ide

# Make scripts executable
chmod +x setup.sh run.sh

# Run setup (creates virtual environment and installs dependencies)
./setup.sh
```

## Usage

### Starting the IDE

```bash
# Using the run script (recommended)
./run.sh

# Or manually
source venv/bin/activate
python main.py
```

### Running EZ Files
1. Open an `.ez` file in the editor
2. Press `F5` to run the current file in the integrated terminal
3. Or use **Run → Run File** from the menu

### Configuring the EZ Interpreter
Go to **Run → Select EZ Interpreter** to specify a custom path to your EZ binary if it's not in your system PATH.

## Keyboard Shortcuts

### File Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New File |
| `Ctrl+O` | Open File |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save All |
| `Ctrl+W` | Close Tab |

### Edit Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+F` | Find |
| `Ctrl+G` | Go to Line |
| `Ctrl+,` | Settings |

### View & Run
| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Toggle File Browser |
| `` Ctrl+` `` | Toggle Terminal |
| `F5` | Run Current File |
| `Ctrl++` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Reset Zoom |

### Debugging
| Shortcut | Action |
|----------|--------|
| `F5` | Start Debugging |
| `F10` | Step Over |
| `Shift+F5` | Stop Debugging |
| `Ctrl+Shift+D` | Toggle Debug Panel |

## Configuration

### Settings Location
Settings are stored in platform-specific configuration directories:

| Platform | Path |
|----------|------|
| Linux | `~/.config/ez-ide/settings.json` |
| macOS | `~/.config/ez-ide/settings.json` |
| Windows | `%APPDATA%\EZ-IDE\settings.json` |

### Custom Themes

Create custom themes by placing JSON files in the themes directory:

| Platform | Path |
|----------|------|
| Linux/macOS | `~/.config/ez-ide/themes/` |
| Windows | `%APPDATA%\EZ-IDE\themes\` |

**Example Theme Structure:**
```json
{
  "name": "My Custom Theme",
  "is_dark": true,
  "background": "#1a1a1a",
  "foreground": "#ffffff",
  "accent": "#007acc",
  "syntax": {
    "keyword": "#c586c0",
    "string": "#ce9178",
    "number": "#b5cea8",
    "comment": "#6a9955"
  }
}
```

See the [User Guide](user_guide.md) for detailed documentation on theme customization.

## Project Structure

```
ez_ide/
├── main.py              # Application entry point
├── setup.sh             # Setup script
├── run.sh               # Run script
├── README.md            # This file
├── user_guide.md        # Comprehensive user guide
├── LICENSE              # MIT License
├── images/
│   └── EZ_LOGO.jpeg     # Application icon
├── examples/            # Example EZ programs
│   ├── hello.ez
│   ├── calculator.ez
│   ├── fibonacci.ez
│   └── ...
└── app/
    ├── __init__.py
    ├── main_window.py   # Main IDE window
    ├── settings.py      # Settings management
    ├── themes.py        # Theme manager
    ├── syntax.py        # EZ syntax highlighter
    ├── editor.py        # Code editor widgets
    ├── file_browser.py  # File browser widget
    ├── terminal.py      # Terminal widget
    ├── debug_session.py # Step debugger REPL manager
    └── debug_panel.py   # Debug UI panel
```

## License

MIT License - Copyright (c) 2025 Marshall A Burns

See [LICENSE](LICENSE) for details.

---

<p align="center">
  Part of the <strong>EZ Language</strong> project
</p>
