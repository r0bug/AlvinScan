# AlvinScan - Inventory Management System

A comprehensive barcode scanning inventory management system designed for tracking items across multiple locations with full graphical interface for all operations.

## Features

- **Barcode Scanning**: Quick item entry via barcode scanner or manual input
- **Location Management**: Create and manage multiple storage locations
- **Quantity Tracking**: Automatically increments quantity when scanning existing items
- **Additional Information**: Associate extra data (part numbers, notes) with each UPC
- **Multi-Workstation Support**: Sync data between multiple scanning stations
- **Full UI Coverage**: All operations available through graphical interface
- **Database Storage**: SQLite database for reliable local storage
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **One-Click Install**: Comprehensive installer for easy setup

## Quick Installation

### Windows
1. Download the AlvinScan folder
2. Double-click `install_windows.bat`
3. Follow the installer prompts
4. Launch from desktop shortcut

### Linux/macOS
1. Download the AlvinScan folder
2. Open terminal in the AlvinScan directory
3. Run: `./install_unix.sh`
4. Follow the installer prompts
5. Launch from desktop shortcut

## Manual Installation

1. Ensure Python 3.7+ is installed
2. Clone or download this repository
3. Install optional dependencies:
   ```bash
   pip install Pillow pyperclip python-dateutil
   ```
4. Run the application:
   - Windows: `python inventory_scanner.py` or double-click `run_scanner.bat`
   - Linux/Mac: `python3 inventory_scanner.py` or run `./run_scanner.sh`

## Usage

### Basic Workflow

1. **Select/Create Location**: Choose a location from dropdown or create new one
2. **Scan Items**: 
   - Click in the barcode field
   - Scan barcode with scanner (or type manually)
   - Press Enter or click Scan
   - Item quantity increments if already exists at location
3. **Add Item Information**: 
   - Select item in inventory list
   - Click "Add Item Info"
   - Add description and custom fields
4. **View Inventory**: Current location inventory displays in main window

### Sync Operations (New UI Features)

All sync operations are now available through the main application UI:

- **Export Data**: 
  - Click "Export Data" button
  - Choose export directory
  - Optionally filter by date
  - Data exported as JSON files

- **Import Data**: 
  - Click "Import Data" button
  - Select import directory
  - Choose merge or replace mode
  - Confirm import operation

- **Generate Report**: 
  - Click "Generate Report" button
  - Choose output file location
  - Report auto-opens after generation
  - Includes inventory summaries and statistics

- **Create Master DB**: 
  - Click "Create Master DB" button
  - Add multiple export directories
  - Specify output database file
  - Merges all workstation data

### Multi-Workstation Setup

For setups with multiple scanning stations:

1. **Each Workstation**: Export data regularly using Export Data button
2. **Central Computer**: Use Create Master DB to merge all exports
3. **Distribution**: Import master database back to each workstation

### Command Line Usage (Optional)

The sync utility can still be used from command line if preferred:

```bash
# Export data
python sync_utility.py export export_folder/

# Import data
python sync_utility.py import export_folder/ --merge

# Create master database
python sync_utility.py master station1/ station2/ -o master.db

# Generate report
python sync_utility.py report -o inventory_report.txt
```

## Database Schema

- **items**: UPC, description, additional info
- **locations**: Location ID, name, description  
- **inventory**: Links items to locations with quantities
- **scan_history**: Audit trail of all scans

## Keyboard Shortcuts

- **Enter**: Scan barcode (when in barcode field)
- **Tab**: Navigate between fields

## File Structure

- `inventory_scanner.py` - Main application with full UI
- `sync_utility.py` - Data synchronization utilities
- `installer.py` - Comprehensive installer script
- `install_windows.bat` - Windows quick installer
- `install_unix.sh` - Linux/macOS quick installer
- `inventory.db` - SQLite database (created on first run)
- `run_scanner.bat` - Windows launcher
- `run_scanner.sh` - Unix/Linux/macOS launcher

## What's New in This Version

- **Comprehensive Installer**: Single-click installation with all dependencies
- **Desktop Integration**: Automatic shortcut creation
- **Full UI Coverage**: All command-line features now in GUI
- **Export/Import Dialogs**: User-friendly data synchronization
- **Report Generation**: One-click reports with auto-open
- **Master Database Dialog**: Easy merging of multiple data sources
- **Date Filtering**: Export only recent changes
- **Progress Feedback**: Clear success/error messages

## Data Storage

- Database file: `inventory.db` (SQLite)
- Export format: JSON files in export directory
- All timestamps in ISO format
- Automatic backups when creating master database

## Tips

- Keep barcode scanner in "keyboard wedge" mode
- Scanner should add Enter/Return after scan
- Create logical location names (e.g., "Shelf-A1", "Bin-B2")
- Use Export Data regularly for backup
- Test sync operations with sample data first

## Troubleshooting

- **Scanner not working**: Ensure scanner adds Enter key after scan
- **Import fails**: Check that metadata.json exists in import directory
- **Database locked**: Close other instances of the application
- **Missing dependencies**: Run installer or install manually with pip

## License

This project is provided as-is for inventory management purposes.