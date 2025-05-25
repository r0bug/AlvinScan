# AlvinScan - Complete Documentation

## Overview

AlvinScan is a barcode-based inventory management system designed specifically for tracking automotive parts across multiple storage locations. It's built with Python and provides a simple GUI interface for rapid barcode scanning and inventory tracking.

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: Version 3.7 or higher
- **Memory**: 4GB RAM (8GB recommended)
- **Storage**: 100MB for application + database growth
- **Display**: 1024x768 minimum resolution

### Hardware Requirements
- **Barcode Scanner**: Any USB barcode scanner that operates in keyboard wedge mode
- **Network**: Not required for standalone operation; needed only for multi-workstation sync

## Installation Guide

### Windows Installation

1. **Install Python**
   - Download Python from [python.org](https://www.python.org/downloads/)
   - During installation, CHECK "Add Python to PATH"
   - Choose "Install Now"

2. **Download AlvinScan**
   - Clone or download the repository from GitHub
   - Extract to a folder like `C:\AlvinScan`

3. **Verify Installation**
   - Open Command Prompt (cmd)
   - Type: `python --version`
   - Should show Python 3.7 or higher

4. **Run AlvinScan**
   - Double-click `run_scanner.bat` in the AlvinScan folder
   - Or open Command Prompt and run:
     ```cmd
     cd C:\AlvinScan
     python inventory_scanner.py
     ```

### macOS Installation

1. **Install Python** (if not already installed)
   - Open Terminal
   - Install Homebrew if needed:
     ```bash
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```
   - Install Python:
     ```bash
     brew install python3
     ```

2. **Install Tkinter** (if needed)
   ```bash
   brew install python-tk
   ```

3. **Download AlvinScan**
   ```bash
   git clone https://github.com/r0bug/AlvinScan.git
   cd AlvinScan
   ```

4. **Run AlvinScan**
   ```bash
   ./run_scanner.sh
   ```
   Or:
   ```bash
   python3 inventory_scanner.py
   ```

### Linux Installation (Ubuntu/Debian)

1. **Install Python and Tkinter**
   ```bash
   sudo apt update
   sudo apt install python3 python3-tk git
   ```

2. **Download AlvinScan**
   ```bash
   git clone https://github.com/r0bug/AlvinScan.git
   cd AlvinScan
   ```

3. **Make scripts executable**
   ```bash
   chmod +x run_scanner.sh
   chmod +x sync_utility.py
   ```

4. **Run AlvinScan**
   ```bash
   ./run_scanner.sh
   ```

## User Guide

### First Time Setup

1. **Launch the Application**
   - Run the application using the appropriate method for your OS
   - The main window will appear with an empty inventory

2. **Create Your First Location**
   - Click "Add Location" button
   - Enter a location name (e.g., "Shelf-A1", "Storage-Bin-5")
   - Optionally add a description
   - Click Save

3. **Configure Your Barcode Scanner**
   - Ensure scanner is in "keyboard wedge" mode
   - Scanner should be configured to add Enter/Return after each scan
   - Test by scanning into a text editor first

### Daily Operations

#### Scanning Items

1. **Select Location**
   - Choose the current location from the dropdown
   - This is where scanned items will be placed

2. **Scan Barcodes**
   - Click in the "Scan Barcode" field
   - Scan the item's barcode
   - The item will be added with quantity 1
   - If item exists at location, quantity increments

3. **Manual Entry**
   - Type the barcode number if scanner fails
   - Press Enter or click Scan button

#### Managing Item Information

1. **Add Description/Info**
   - Select an item in the inventory list
   - Click "Add Item Info"
   - Add description and any custom fields:
     - Part numbers
     - Manufacturer codes
     - Vehicle compatibility notes
     - Condition notes

2. **View Item Locations**
   - Click "View All Locations"
   - See summary of all locations and quantities

### Multi-Workstation Setup

#### Setting Up Multiple Stations

1. **Install AlvinScan on each workstation**
2. **Each station maintains its own database**
3. **Designate one computer as the "master"**

#### Syncing Data

1. **Export from Workstation**
   ```bash
   python sync_utility.py export station1_export/
   ```

2. **Transfer Export Folder**
   - Copy the export folder to master computer
   - Use USB drive, network share, or cloud storage

3. **Import to Master**
   ```bash
   python sync_utility.py import station1_export/ --merge
   ```

4. **Create Master Database**
   ```bash
   python sync_utility.py master station1/ station2/ station3/ -o master.db
   ```

### Reports and Analysis

#### Generate Inventory Report
```bash
python sync_utility.py report -o inventory_report.txt
```

The report includes:
- Total unique items
- Items by location
- Top items by quantity
- Location summaries

### Database Management

#### Backup Database
- Copy `inventory.db` to backup location
- Recommended: Daily backups

#### View Database Directly
- Use SQLite browser tools
- Database location: `inventory.db` in application folder

## Troubleshooting

### Common Issues

1. **"No module named 'tkinter'"**
   - **Windows**: Reinstall Python with default options
   - **macOS**: `brew install python-tk`
   - **Linux**: `sudo apt install python3-tk`

2. **Scanner Not Working**
   - Check USB connection
   - Verify scanner is in keyboard wedge mode
   - Test in notepad/text editor
   - Check scanner manual for configuration

3. **Database Locked Error**
   - Close other instances of AlvinScan
   - Check file permissions
   - Ensure not on read-only drive

4. **Can't See Inventory After Scanning**
   - Verify correct location is selected
   - Click Refresh button
   - Check if item was scanned to different location

### Performance Tips

1. **Regular Maintenance**
   - Export and backup data weekly
   - Archive old scan history quarterly

2. **Scanner Setup**
   - Disable scanner beep for faster scanning
   - Use scanner stand for hands-free operation
   - Keep scanner lens clean

3. **Efficient Workflow**
   - Organize items by location before scanning
   - Scan all items for one location at once
   - Add descriptions in batches

## Advanced Features

### Custom Fields

Add any additional fields to items:
- Cross-reference numbers
- Supplier codes
- Purchase dates
- Cost information
- Condition grades

### Data Export Formats

The sync utility exports to JSON format, which can be:
- Imported to Excel
- Processed with Python scripts
- Converted to CSV
- Integrated with other systems

### Extending the Application

The codebase is designed for expansion:
- API integration for part lookups
- Barcode label printing
- Advanced search features
- Web interface
- Mobile app companion

## Best Practices

1. **Location Naming**
   - Use consistent naming scheme
   - Include physical references (Row-Shelf-Bin)
   - Avoid special characters

2. **Scanning Workflow**
   - Scan items as they're placed
   - Verify location before scanning batch
   - Regular spot checks for accuracy

3. **Data Management**
   - Daily backups
   - Weekly exports for multi-station setups
   - Monthly master database consolidation

## Support and Updates

- **GitHub Repository**: https://github.com/r0bug/AlvinScan
- **Issue Reporting**: Use GitHub Issues
- **Feature Requests**: Submit via GitHub Issues

## License

This software is provided as-is for inventory management purposes. See LICENSE file for details.

## Future Roadmap

Planned enhancements:
- Web API integration for part information
- Make/Model/Year search capabilities
- Barcode label printing
- Cloud synchronization
- Mobile companion app
- Advanced reporting dashboard