@echo off
REM Quick start script for Inventory Scanner on Windows

echo Starting Inventory Scanner...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.7 or higher from python.org
    pause
    exit /b 1
)

REM Run the scanner
python inventory_scanner.py

REM Keep window open if there's an error
if errorlevel 1 pause