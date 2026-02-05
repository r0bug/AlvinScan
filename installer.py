#!/usr/bin/env python3
"""
AlvinScan Comprehensive Installer
Installs AlvinScan and all dependencies with a single script
"""

import os
import sys
import subprocess
import platform
import shutil
import urllib.request
import json
from pathlib import Path


class AlvinScanInstaller:
    def __init__(self):
        self.system = platform.system()
        self.python_cmd = sys.executable
        self.install_dir = Path.home() / "AlvinScan"
        self.desktop_dir = Path.home() / "Desktop"
        
    def print_banner(self):
        """Print installation banner"""
        print("=" * 60)
        print("AlvinScan Inventory Management System")
        print("Comprehensive Installer")
        print(f"System: {self.system}")
        print(f"Python: {sys.version}")
        print("=" * 60)
        print()
    
    def check_python_version(self):
        """Ensure Python 3.7+ is installed"""
        if sys.version_info < (3, 7):
            print("ERROR: Python 3.7 or higher is required")
            print(f"Current version: {sys.version}")
            return False
        print("✓ Python version OK")
        return True
    
    def install_pip_packages(self):
        """Install required Python packages"""
        print("\nInstalling Python packages...")
        packages = [
            "tk",  # Usually comes with Python
            "Pillow",  # For image handling
            "pyperclip",  # For clipboard operations
            "python-dateutil",  # For date handling
        ]
        
        for package in packages:
            try:
                print(f"Installing {package}...")
                subprocess.check_call([
                    self.python_cmd, "-m", "pip", "install", "--upgrade", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✓ {package} installed")
            except subprocess.CalledProcessError:
                print(f"✗ Failed to install {package}")
                return False
        
        return True
    
    def create_directories(self):
        """Create necessary directories"""
        print("\nCreating directories...")
        
        dirs = [
            self.install_dir,
            self.install_dir / "data",
            self.install_dir / "exports",
            self.install_dir / "backups",
            self.install_dir / "logs",
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created {dir_path}")
        
        return True
    
    def copy_application_files(self):
        """Copy application files to installation directory"""
        print("\nCopying application files...")
        
        # Get the directory where installer.py is located
        source_dir = Path(__file__).parent
        
        files_to_copy = [
            "inventory_scanner.py",
            "sync_utility.py",
            "requirements.txt",
            "README.md",
            "DOCUMENTATION.md",
            "INSTALL.md",
            "MANUAL_PUSH_INSTRUCTIONS.md",
        ]
        
        for file_name in files_to_copy:
            source_file = source_dir / file_name
            if source_file.exists():
                dest_file = self.install_dir / file_name
                shutil.copy2(source_file, dest_file)
                print(f"✓ Copied {file_name}")
            else:
                print(f"⚠ Warning: {file_name} not found in source directory")
        
        # Copy batch/shell scripts
        if self.system == "Windows":
            script_file = source_dir / "run_scanner.bat"
            if script_file.exists():
                shutil.copy2(script_file, self.install_dir / "run_scanner.bat")
        else:
            script_file = source_dir / "run_scanner.sh"
            if script_file.exists():
                shutil.copy2(script_file, self.install_dir / "run_scanner.sh")
                # Make it executable
                os.chmod(self.install_dir / "run_scanner.sh", 0o755)
        
        return True
    
    def create_desktop_shortcuts(self):
        """Create desktop shortcuts"""
        print("\nCreating desktop shortcuts...")
        
        if self.system == "Windows":
            # Create Windows batch file for desktop
            shortcut_content = f'''@echo off
cd /d "{self.install_dir}"
"{self.python_cmd}" inventory_scanner.py
pause
'''
            shortcut_path = self.desktop_dir / "AlvinScan.bat"
            with open(shortcut_path, 'w') as f:
                f.write(shortcut_content)
            print(f"✓ Created desktop shortcut: {shortcut_path}")
            
            # Create Start Menu shortcut
            start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            if start_menu.exists():
                shutil.copy2(shortcut_path, start_menu / "AlvinScan.bat")
                print("✓ Created Start Menu shortcut")
        
        elif self.system == "Darwin":  # macOS
            # Create macOS app bundle
            app_path = self.desktop_dir / "AlvinScan.app"
            contents_path = app_path / "Contents"
            macos_path = contents_path / "MacOS"
            
            # Create directory structure
            macos_path.mkdir(parents=True, exist_ok=True)
            
            # Create Info.plist
            info_plist = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>AlvinScan</string>
    <key>CFBundleName</key>
    <string>AlvinScan</string>
    <key>CFBundleIdentifier</key>
    <string>com.alvinscan.inventory</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>'''
            with open(contents_path / "Info.plist", 'w') as f:
                f.write(info_plist)
            
            # Create executable script
            exec_script = f'''#!/bin/bash
cd "{self.install_dir}"
"{self.python_cmd}" inventory_scanner.py
'''
            exec_path = macos_path / "AlvinScan"
            with open(exec_path, 'w') as f:
                f.write(exec_script)
            os.chmod(exec_path, 0o755)
            
            print(f"✓ Created macOS app: {app_path}")
        
        else:  # Linux
            # Create .desktop file
            desktop_content = f'''[Desktop Entry]
Name=AlvinScan
Comment=Inventory Management System
Exec={self.python_cmd} {self.install_dir}/inventory_scanner.py
Icon=applications-inventory-management
Terminal=false
Type=Application
Categories=Office;Utility;
'''
            desktop_path = self.desktop_dir / "AlvinScan.desktop"
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            os.chmod(desktop_path, 0o755)
            print(f"✓ Created desktop shortcut: {desktop_path}")
            
            # Copy to applications menu
            apps_dir = Path.home() / ".local" / "share" / "applications"
            if apps_dir.exists():
                shutil.copy2(desktop_path, apps_dir / "AlvinScan.desktop")
                print("✓ Added to applications menu")
        
        return True
    
    def create_uninstaller(self):
        """Create uninstaller script"""
        print("\nCreating uninstaller...")
        
        if self.system == "Windows":
            uninstaller_content = f'''@echo off
echo Uninstalling AlvinScan...
rmdir /s /q "{self.install_dir}"
del "%USERPROFILE%\\Desktop\\AlvinScan.bat"
del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\AlvinScan.bat"
echo Uninstallation complete.
pause
'''
            uninstaller_path = self.install_dir / "uninstall.bat"
        else:
            uninstaller_content = f'''#!/bin/bash
echo "Uninstalling AlvinScan..."
rm -rf "{self.install_dir}"
rm -f "$HOME/Desktop/AlvinScan.desktop"
rm -f "$HOME/Desktop/AlvinScan.app"
rm -f "$HOME/.local/share/applications/AlvinScan.desktop"
echo "Uninstallation complete."
'''
            uninstaller_path = self.install_dir / "uninstall.sh"
        
        with open(uninstaller_path, 'w') as f:
            f.write(uninstaller_content)
        
        if self.system != "Windows":
            os.chmod(uninstaller_path, 0o755)
        
        print(f"✓ Created uninstaller: {uninstaller_path}")
        return True
    
    def test_installation(self):
        """Test the installation"""
        print("\nTesting installation...")
        
        try:
            # Test importing the main module
            sys.path.insert(0, str(self.install_dir))
            import inventory_scanner
            print("✓ Main application module loads correctly")
            
            # Test database creation
            test_db_path = self.install_dir / "data" / "test.db"
            test_db = inventory_scanner.InventoryDatabase(str(test_db_path))
            test_db.close()
            
            if test_db_path.exists():
                test_db_path.unlink()  # Remove test database
                print("✓ Database creation works")
            
            return True
        except Exception as e:
            print(f"✗ Installation test failed: {e}")
            return False
    
    def install(self):
        """Run the complete installation process"""
        self.print_banner()
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Installing Python packages", self.install_pip_packages),
            ("Creating directories", self.create_directories),
            ("Copying application files", self.copy_application_files),
            ("Creating desktop shortcuts", self.create_desktop_shortcuts),
            ("Creating uninstaller", self.create_uninstaller),
            ("Testing installation", self.test_installation),
        ]
        
        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"\n✗ Installation failed at: {step_name}")
                return False
        
        print("\n" + "=" * 60)
        print("✓ Installation completed successfully!")
        print(f"✓ AlvinScan installed to: {self.install_dir}")
        print("✓ Desktop shortcut created")
        print("\nYou can now run AlvinScan from:")
        print(f"  - Desktop shortcut")
        print(f"  - {self.install_dir}")
        print("=" * 60)
        
        return True


def main():
    """Main entry point"""
    installer = AlvinScanInstaller()
    
    # Check if running with admin/sudo privileges (recommended)
    if platform.system() == "Windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("⚠ Warning: Running without administrator privileges")
            print("  Some features may not install correctly")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
    
    try:
        success = installer.install()
        if success:
            input("\nPress Enter to exit...")
        else:
            input("\nInstallation failed. Press Enter to exit...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()