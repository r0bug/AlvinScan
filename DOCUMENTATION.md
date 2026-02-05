# AlvinScan - Complete Documentation

## Overview

AlvinScan is a barcode-based inventory management system designed specifically for tracking automotive parts (Carquest, Advance Auto Parts, Driveworks, and other brands) across multiple storage locations. It features automatic part identification through multiple API sources and web search capabilities.

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: Version 3.7 or higher
- **Memory**: 4GB RAM
- **Storage**: 100MB for application + database growth
- **Display**: 1024x768 minimum resolution
- **Network**: Required for API lookups and web search

### Hardware
- **Barcode Scanner**: Any USB barcode scanner in keyboard wedge mode
- **Recommended**: Scanner with auto-Enter suffix configuration

## Installation

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-tk git
git clone https://github.com/r0bug/AlvinScan.git
cd AlvinScan
python3 inventory_scanner.py
```

### macOS
```bash
brew install python3 python-tk
git clone https://github.com/r0bug/AlvinScan.git
cd AlvinScan
python3 inventory_scanner.py
```

### Windows
1. Install Python from [python.org](https://python.org) (check "Add to PATH")
2. Download/clone repository
3. Run `python inventory_scanner.py` or double-click `run_scanner.bat`

## Features

### 1. Multi-Source Part Lookup

When you scan a barcode, AlvinScan automatically queries multiple sources:

#### API Sources (Configurable)
| Source | Type | Rate Limit | Best For |
|--------|------|------------|----------|
| UPCitemdb | Free | 100/day | UPC barcodes |
| Advance Auto Parts | RapidAPI | Per plan | Part numbers, keywords |
| Custom APIs | Configurable | Varies | Your specific needs |

#### Web Search Fallback
- Uses DuckDuckGo when APIs return no results
- Searches "[part number] auto parts"
- Shows results with snippets
- Fetches page content for description extraction

### 2. Smart Scanning Logic

```
┌─────────────────────────────────────────────────────────────┐
│                    SCAN BARCODE                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Item exists in DB?   │
              └────────────────────────┘
                    │           │
                   YES          NO
                    │           │
                    ▼           ▼
         ┌──────────────┐  ┌──────────────────┐
         │ Is Identified?│  │ Add to inventory │
         └──────────────┘  │ + API Lookup     │
           │         │     └──────────────────┘
          YES        NO              │
           │         │               ▼
           ▼         ▼     ┌──────────────────┐
    ┌──────────┐ ┌─────────────────┐          │
    │ Qty +1   │ │ Unidentified    │  Results found?
    │ No popup │ │ Item Dialog     │          │
    └──────────┘ └─────────────────┘   YES    NO
                       │                │      │
                       ▼                ▼      ▼
              • Quick add qty    Show results  Alternate
              • Try part number               lookup dialog
              • Web search
              • Manual entry
```

### 3. Alternate Part Number Lookup

When UPC lookup fails:
1. Dialog prompts for alternate part number (printed on package)
2. Enter part number (e.g., "DW-EV128")
3. System queries all APIs with part number
4. If found, description saved under **original UPC**
5. If not found, try another or use Web Search

### 4. Web Search Integration

When APIs fail:
1. Click "Web Search" button
2. Auto-searches DuckDuckGo for part
3. Results displayed with titles and snippets
4. Click result to fetch page content
5. Title pre-fills description field
6. Edit and save

### 5. Unidentified Item Handling

For items that can't be identified:
- **Save Anyway**: Marks as "Not Identified", stores attempted part numbers
- **Manual Entry**: Type your own description
- **Track Attempts**: All tried part numbers stored in `attempted_parts` field

### 6. Enhanced Display

Main inventory shows 7 columns:
| Column | Description |
|--------|-------------|
| UPC | Barcode number |
| Description | Product name/description |
| Part # | Identified part number |
| Brand | Manufacturer |
| Attempted Parts | Part numbers tried for unidentified items |
| Qty | Quantity at location |
| Last Scanned | Timestamp |

### 7. API Configuration

Access: Main Window → **API Settings** button

#### API Types
- **upcitemdb**: For UPCitemdb-style APIs (uses `?upc=` parameter)
- **rapidapi**: For RapidAPI services (uses `x-rapidapi-*` headers)
- **generic**: Custom APIs (configurable parameter names)

#### Adding a New API
1. Click "Add API"
2. Fill in fields:
   - **Name**: Display name
   - **Type**: Select from dropdown
   - **URL**: Base endpoint URL
   - **Host**: RapidAPI host (if applicable)
   - **API Key**: Your authentication key
   - **Query Param**: Parameter name for search term (generic type)
   - **Description**: Notes about the API
3. Check "Enabled"
4. Click "Test" to verify
5. Click "Save"

#### Configuration File
Settings stored in `config.json`:
```json
{
  "apis": [
    {
      "name": "UPCitemdb",
      "enabled": true,
      "type": "upcitemdb",
      "url": "https://api.upcitemdb.com/prod/trial/lookup",
      "api_key": "",
      "description": "Free UPC lookup (100/day)"
    },
    {
      "name": "Advance Auto Parts",
      "enabled": true,
      "type": "rapidapi",
      "url": "https://advance-auto-parts.p.rapidapi.com/search",
      "host": "advance-auto-parts.p.rapidapi.com",
      "api_key": "YOUR_KEY_HERE",
      "description": "Advance Auto Parts / Carquest"
    }
  ]
}
```

## Database Structure

### Tables

#### items
| Column | Type | Description |
|--------|------|-------------|
| upc | TEXT (PK) | Barcode number |
| description | TEXT | Product description |
| additional_info | TEXT (JSON) | Extended attributes |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

#### locations
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | UUID |
| name | TEXT | Location name |
| description | TEXT | Notes |
| created_at | TEXT | ISO timestamp |

#### inventory
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-increment |
| item_upc | TEXT (FK) | Links to items |
| location_id | TEXT (FK) | Links to locations |
| quantity | INTEGER | Count |
| last_scanned | TEXT | ISO timestamp |

#### scan_history
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-increment |
| item_upc | TEXT | Barcode |
| location_id | TEXT | Location |
| action | TEXT | 'scan' |
| quantity_change | INTEGER | Change amount |
| scanned_at | TEXT | ISO timestamp |
| workstation_id | TEXT | Computer name |

### Additional Info JSON Structure
```json
{
  "source": "UPCitemdb | Advance Auto Parts | Web Search | Manual Entry | Not Found",
  "brand": "K&N",
  "part_number": "33-2118",
  "searched_part": "33-2118",
  "category": "Filters",
  "price": "67.99",
  "warranty": "LIMITED LIFETIME",
  "attempted_parts": "54060 | 54060A | 54060-B",
  "search_term": "K&N air filter camaro"
}
```

## Utilities

### Quick Scan Collector (`quick_scan.py`)
Minimal tool for rapidly collecting UPCs:
```bash
python3 quick_scan.py
```
- Single entry field
- Auto-saves to `upcs.txt`
- Shows running count
- No validation, no lookup

### UPC Collector (`upc_collector.py`)
Extended collector with list management:
```bash
python3 upc_collector.py
```
- Shows collected UPCs in list
- Delete selected
- Clear all
- Persistent storage

## Multi-Workstation Sync

### Export Data
1. Click "Export Data"
2. Choose directory
3. Optional: Filter by date
4. Creates JSON files

### Import Data
1. Click "Import Data"
2. Select export directory
3. Choose merge or replace
4. Confirm

### Create Master Database
1. Click "Create Master DB"
2. Add export directories from each workstation
3. Specify output file
4. Creates consolidated database

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Scan/submit barcode |
| Tab | Navigate fields |
| Double-click | Edit selected item |

## Troubleshooting

### API Issues
| Problem | Solution |
|---------|----------|
| "No results" for all scans | Check internet connection |
| API returns errors | Verify API key in settings |
| Rate limited | UPCitemdb: wait or upgrade plan |
| Wrong results | Try alternate part number |

### Scanner Issues
| Problem | Solution |
|---------|----------|
| Scanner not detected | Check USB connection |
| Scans go to wrong field | Click barcode entry first |
| No Enter after scan | Configure scanner settings |
| Partial barcodes | Clean scanner lens |

### Database Issues
| Problem | Solution |
|---------|----------|
| "Database locked" | Close other instances |
| Data not saving | Check disk space |
| Corrupted database | Restore from backup |

## Best Practices

### Scanning Workflow
1. Select location FIRST
2. Scan all items for that location
3. Move to next location
4. Export data daily

### Part Identification
1. Let auto-lookup run first
2. If no results, check package for part number
3. Try part number lookup
4. Use web search as fallback
5. Manual entry as last resort

### Data Management
- Export weekly for backup
- Track "Not Identified" items for later research
- Consolidate master DB monthly

## API Rate Limits & Costs

| API | Free Tier | Paid Options |
|-----|-----------|--------------|
| UPCitemdb | 100/day | Plans available |
| Advance Auto Parts | Per RapidAPI plan | Check RapidAPI |

## Support

- **Repository**: https://github.com/r0bug/AlvinScan
- **Issues**: GitHub Issues
- **Feature Requests**: GitHub Issues

## Version History

### Current Version
- Multi-API lookup system
- Web search fallback
- Smart re-scan detection
- Configurable API settings
- Enhanced display with Part#, Brand, Attempted Parts
- Quick scan utilities

---

*Documentation last updated: February 2026*
