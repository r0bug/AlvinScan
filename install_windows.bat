@echo off
title AlvinScan Installer
echo ========================================
echo AlvinScan Inventory Management System
echo Windows Installer
echo ========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org
    pause
    exit /b 1
)

echo Running installer...
python installer.py

pause