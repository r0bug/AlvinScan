#!/bin/bash

echo "========================================"
echo "AlvinScan Inventory Management System"
echo "Unix/Linux/macOS Installer"
echo "========================================"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

echo "Running installer..."
python3 installer.py

echo ""
echo "Press Enter to exit..."
read