#!/bin/bash
# Quick start script for Inventory Scanner

echo "Starting Inventory Scanner..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if tkinter is available
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "Error: tkinter is not installed."
    echo "Please install tkinter:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  Fedora/RHEL: sudo dnf install python3-tkinter"
    echo "  macOS: brew install python-tk"
    exit 1
fi

# Run the scanner
python3 inventory_scanner.py