# AutoLISP Function Manager & Executor

A powerful and user-friendly GUI application to manage, explore, and execute AutoLISP functions directly from your `.lisp` files.

## Features

- **Automatic Scanning**: Automatically scans for `.lisp` files in the current or a selected directory.
- **Dynamic Parsing**: Extracts function names, parameter lists, and docstrings from LISP definitions.
- **Rich Navigation**: Navigate through your functions using a multi-level tree structure (File -> Function).
- **Function Details**: View function signatures, documentation, and collapsible source code snippets.
- **Dynamic Execution**: Automatically generates a parameter input dialog based on the function's signature.
- **Robustness**: Integrated retry mechanisms with exponential backoff to handle AutoCAD response delays.
- **Modern UI**: Clean, light-themed interface with 1080p+ DPI scaling support.
- **Search & Filter**: Real-time filtering of functions by name or documentation.
- **Results Management**: View, copy, and save function execution results.

## Getting Started

### Prerequisites

- **Python 3.x**: Ensure you have Python installed.
- **Tkinter**: Included by default with most Python installations.

### Installation

No installation is required. This is a single-file application. If you need any dependencies (like `pywin32` for actual AutoCAD COM communication), you can install them via:

```bash
pip install pywin32
```

*(Note: The current version uses simulated execution. Integration with AutoCAD requires appropriate COM setup.)*

### Running the Application

Simply run the script using Python:

```bash
python retry_decorator.py
```

Or, on Unix-like systems (if applicable):

```bash
chmod +x retry_decorator.py
./retry_decorator.py
```

## GUI Overview

1. **Toolbar**:
   - `📂 Load Directory`: Browse and select a directory containing `.lisp` files.
   - `🔄 Refresh`: Re-scan the current directory for changes.
   - `Search`: Real-time filtering of functions.
2. **Navigation Panel (Left)**: Shows all files and their contained functions.
3. **Details Panel (Right)**:
   - Function Signature and Documentation.
   - `Show Source Code`: Toggle the display of the function's LISP source.
   - `🚀 Execute Function`: Opens a dialog to input parameters and run the function.
4. **Status Bar (Bottom)**: Displays the currently selected function and execution results.

## Development

- **Pattern**: Model-View-Controller (MVC).
- **Coding Style**: PEP8 compliant.
- **Comments**: Comprehensive documentation (≥ 30% coverage).
- **Error Handling**: 100% exception capture for all file and execution operations.

## License

MIT License.
