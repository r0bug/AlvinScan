# AlvinScan - Car Parts Inventory Management System

A comprehensive barcode scanning inventory management system designed for tracking automotive parts (Carquest, Advance Auto Parts, and other brands) across multiple locations with automatic part lookup capabilities.

## Key Features

### Part Lookup & Identification
- **Multi-API Lookup**: Automatically queries multiple sources when scanning
  - UPCitemdb (free, 100 lookups/day)
  - Advance Auto Parts API
  - Configurable additional APIs
- **Web Search Fallback**: DuckDuckGo search when APIs fail
- **Smart Part Matching**: Enter alternate part numbers to find matches
- **Manual Entry**: Add descriptions when automated lookup fails

### Inventory Management
- **Barcode Scanning**: Quick item entry via USB barcode scanner or manual input
- **Smart Re-scan Detection**:
  - Identified items: Just updates quantity (no popup)
  - Unidentified items: Prompts for additional lookup attempts
- **Location Management**: Create and manage multiple storage locations
- **Quantity Tracking**: Automatic increment on repeat scans

### Data Display
- **Enhanced Inventory View**: Shows UPC, Description, Part#, Brand, Attempted Parts, Quantity, Last Scanned
- **Track Lookup Attempts**: See which part numbers have been tried for unidentified items

### Configuration
- **API Settings Panel**: Add, edit, enable/disable, and test API endpoints
- **Persistent Config**: Settings saved to config.json
- **Extensible**: Add new APIs without code changes

### Sync & Export
- **Export/Import Data**: JSON format for data portability
- **Multi-Workstation Support**: Merge data from multiple scanning stations
- **Report Generation**: Inventory summaries and statistics
- **Master Database**: Consolidate multiple station databases

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/r0bug/AlvinScan.git
cd AlvinScan

# Run the application
python3 inventory_scanner.py
```

### Requirements
- Python 3.7+
- Tkinter (usually included with Python)
- No additional packages required for core functionality

### First Run
1. Launch the application
2. Click "Add Location" to create a storage location
3. Select the location from dropdown
4. Start scanning barcodes!

## Usage Workflow

### Scanning New Items
```
Scan UPC → API Lookup (automatic)
    │
    ├── Found → Show results → Apply description
    │
    └── Not Found → Enter alternate part number
                        │
                        ├── Found → Apply to original UPC
                        │
                        ├── Web Search → Select result → Save
                        │
                        ├── Save Anyway → Mark as "Not Identified"
                        │
                        └── Manual Entry → Type description
```

### Re-scanning Items
- **Identified items**: Quantity +1, no popup
- **Unidentified items**: Dialog with options:
  - Quick add quantity
  - Try another part number
  - Web search
  - Manual entry

## API Configuration

Access via **API Settings** button in main window.

### Pre-configured APIs
| API | Type | Notes |
|-----|------|-------|
| UPCitemdb | Free | 100 lookups/day, no key needed |
| Advance Auto Parts | RapidAPI | Requires API key |

### Adding New APIs
1. Click "API Settings"
2. Click "Add API"
3. Configure:
   - **Name**: Display name
   - **Type**: upcitemdb, rapidapi, or generic
   - **URL**: API endpoint
   - **Host**: RapidAPI host (if applicable)
   - **API Key**: Your key
4. Test with "Test" button
5. Save

## File Structure

```
AlvinScan/
├── inventory_scanner.py   # Main application
├── sync_utility.py        # Data sync utilities
├── quick_scan.py          # Quick UPC collector tool
├── upc_collector.py       # Test data collector
├── config.json            # API configuration (created on first run)
├── inventory.db           # SQLite database (created on first run)
├── installer.py           # Installation script
├── run_scanner.sh         # Linux/Mac launcher
├── run_scanner.bat        # Windows launcher
└── *.md                   # Documentation
```

## Database Schema

- **items**: UPC (key), description, additional_info (JSON)
- **locations**: ID, name, description
- **inventory**: Links items to locations with quantities
- **scan_history**: Audit trail of all scans

### Additional Info Fields
```json
{
  "source": "UPCitemdb",
  "brand": "K&N",
  "part_number": "33-2118",
  "category": "Filters",
  "attempted_parts": "54060 | 54060A",
  "price": "67.99"
}
```

## Utilities

### Quick Scan Collector
For gathering test UPCs quickly:
```bash
python3 quick_scan.py
```
- Minimal UI - just scan and save
- Outputs to `upcs.txt`

## Tips

- **Barcode Scanner Setup**: Configure for "keyboard wedge" mode with Enter suffix
- **Alternate Part Numbers**: Look at the package - part numbers often differ from UPC
- **Web Search**: Use brand + model for best results
- **Track Attempts**: "Attempted Parts" column shows what's been tried

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Scanner not working | Ensure scanner adds Enter key after scan |
| API lookup fails | Check API Settings, verify key, test connection |
| Database locked | Close other instances of application |
| No results | Try alternate part number or web search |

## Contributing

1. Fork the repository
2. Create feature branch
3. Submit pull request

## License

This project is provided as-is for inventory management purposes.

---

**Repository**: https://github.com/r0bug/AlvinScan
