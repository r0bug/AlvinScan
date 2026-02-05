# Installation Instructions

## Prerequisites

### Python 3
The application requires Python 3.7 or higher.

### Tkinter
Tkinter is Python's standard GUI library but may need separate installation on some systems.

#### Ubuntu/Debian Linux:
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

#### Fedora/RHEL/CentOS:
```bash
sudo dnf install python3-tkinter
```

#### macOS:
Tkinter usually comes pre-installed with Python on macOS. If missing:
```bash
brew install python-tk
```

#### Windows:
Tkinter is included with Python on Windows by default.

## Testing the Installation

1. Test Python:
```bash
python3 --version
```

2. Test Tkinter:
```bash
python3 -c "import tkinter; print('Tkinter is installed')"
```

3. Run the application:
```bash
python3 inventory_scanner.py
```

## Troubleshooting

### "No module named 'tkinter'" error
- Linux: Install python3-tk package (see above)
- macOS: Reinstall Python via Homebrew
- Windows: Reinstall Python from python.org

### Permission errors
Make the scripts executable:
```bash
chmod +x inventory_scanner.py
chmod +x sync_utility.py
```

### Database errors
Ensure you have write permissions in the application directory for the SQLite database.