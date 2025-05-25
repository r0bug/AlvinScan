# AlvinScan - Inventory Scanner Application

A Python-based barcode scanning inventory management system designed for tracking auto parts across multiple locations.

## Features

- **Barcode Scanning**: Quick entry of items via barcode scanner or manual input
- **Location Management**: Create and manage multiple storage locations
- **Quantity Tracking**: Automatically increments quantity when scanning existing items
- **Additional Information**: Associate extra data (part numbers, notes) with each UPC
- **Multi-Workstation Support**: Sync data between multiple scanning stations
- **Database Storage**: SQLite database for reliable local storage
- **Cross-Platform**: Works on Windows and macOS

## Installation

1. Ensure Python 3.7+ is installed
2. Clone or download this repository
3. No additional dependencies required (uses built-in tkinter)

## Usage

### Running the Scanner

```bash
python inventory_scanner.py
```

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

### Multi-Workstation Sync

Use the sync utility to share data between workstations:

#### Export data from a workstation:
```bash
python sync_utility.py export export_folder/
```

#### Import data to another workstation:
```bash
python sync_utility.py import export_folder/ --merge
```

#### Create master database from multiple exports:
```bash
python sync_utility.py master station1_export/ station2_export/ -o master.db
```

#### Generate inventory report:
```bash
python sync_utility.py report
```

## Database Schema

- **items**: UPC, description, additional info
- **locations**: Location ID, name, description  
- **inventory**: Links items to locations with quantities
- **scan_history**: Audit trail of all scans

## Keyboard Shortcuts

- **Enter**: Scan barcode (when in barcode field)
- **Tab**: Navigate between fields

## Data Storage

- Database file: `inventory.db` (SQLite)
- Export format: JSON files in export directory
- All timestamps in ISO format

## Future Enhancements

The application is designed to support:
- Online API integration for part lookups
- Search by make/model/year
- Excel export functionality
- Advanced reporting features

## Tips

- Keep barcode scanner in "keyboard wedge" mode
- Scanner should add Enter/Return after scan
- Create logical location names (e.g., "Shelf-A1", "Bin-B2")
- Regularly export data for backup
- Use sync utility to consolidate multi-station data