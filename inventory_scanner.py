#!/usr/bin/env python3
"""
Inventory Scanner - Main Application
Barcode scanning inventory management system
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
from pathlib import Path
import sqlite3
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import uuid
import platform
import subprocess
import urllib.request
import urllib.parse
import threading
from sync_utility import InventorySync

# Default API Configuration
DEFAULT_CONFIG = {
    "apis": [
        {
            "name": "UPCitemdb",
            "enabled": True,
            "type": "upcitemdb",
            "url": "https://api.upcitemdb.com/prod/trial/lookup",
            "api_key": "",
            "description": "Free UPC lookup (100/day)"
        },
        {
            "name": "Advance Auto Parts",
            "enabled": True,
            "type": "rapidapi",
            "url": "https://advance-auto-parts.p.rapidapi.com/search",
            "host": "advance-auto-parts.p.rapidapi.com",
            "api_key": "df8d614511mshbabf889bf929182p164553jsndb840498eb21",
            "description": "Advance Auto Parts / Carquest"
        }
    ]
}


class ConfigManager:
    """Manages application configuration"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            script_dir = Path(__file__).parent.resolve()
            config_path = script_dir / "config.json"
        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Load config from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        """Save config to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_apis(self) -> List[dict]:
        """Get list of configured APIs"""
        return self.config.get('apis', [])

    def get_enabled_apis(self) -> List[dict]:
        """Get list of enabled APIs"""
        return [api for api in self.get_apis() if api.get('enabled', True)]

    def add_api(self, api_config: dict):
        """Add a new API configuration"""
        self.config.setdefault('apis', []).append(api_config)
        self.save_config()

    def update_api(self, index: int, api_config: dict):
        """Update an existing API configuration"""
        if 0 <= index < len(self.config.get('apis', [])):
            self.config['apis'][index] = api_config
            self.save_config()

    def delete_api(self, index: int):
        """Delete an API configuration"""
        if 0 <= index < len(self.config.get('apis', [])):
            del self.config['apis'][index]
            self.save_config()


# Global config manager
config_manager = ConfigManager()


class WebSearcher:
    """Handles web search for parts"""

    @staticmethod
    def search_duckduckgo(query: str, max_results: int = 8) -> List[Dict]:
        """Search DuckDuckGo and return results"""
        results = []
        try:
            # Use DuckDuckGo HTML search (no API key needed)
            encoded_query = urllib.parse.quote(f"{query} auto parts")
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', errors='ignore')

                # Simple parsing of DuckDuckGo HTML results
                import re

                # Find result blocks
                result_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
                snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</a>'

                links = re.findall(result_pattern, html)
                snippets = re.findall(snippet_pattern, html)

                for i, (link, title) in enumerate(links[:max_results]):
                    # Clean up the redirect URL
                    if 'uddg=' in link:
                        actual_url = urllib.parse.unquote(link.split('uddg=')[1].split('&')[0])
                    else:
                        actual_url = link

                    snippet = snippets[i] if i < len(snippets) else ''
                    # Clean HTML tags from snippet
                    snippet = re.sub(r'<[^>]+>', '', snippet)

                    results.append({
                        'title': title.strip(),
                        'url': actual_url,
                        'snippet': snippet.strip()[:200]
                    })

        except Exception as e:
            print(f"DuckDuckGo search error: {e}")

        return results

    @staticmethod
    def fetch_page_text(url: str, max_length: int = 2000) -> str:
        """Fetch a page and extract readable text"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

                import re
                # Remove script and style tags
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

                # Extract title
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else ''

                # Remove all HTML tags
                text = re.sub(r'<[^>]+>', ' ', html)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()

                return f"Title: {title}\n\n{text[:max_length]}"

        except Exception as e:
            return f"Error fetching page: {e}"


class PartLookup:
    """Handles part lookups from multiple APIs"""

    @staticmethod
    def lookup_upcitemdb(code: str, api_config: dict) -> Optional[Dict]:
        """Lookup UPC in UPCitemdb (free, 100/day)"""
        try:
            base_url = api_config.get('url', 'https://api.upcitemdb.com/prod/trial/lookup')
            url = f"{base_url}?upc={code}"
            req = urllib.request.Request(url)

            # Add API key header if provided
            if api_config.get('api_key'):
                req.add_header('Authorization', f"Bearer {api_config['api_key']}")

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get('items'):
                    item = data['items'][0]
                    return {
                        'source': api_config.get('name', 'UPCitemdb'),
                        'title': item.get('title', ''),
                        'brand': item.get('brand', ''),
                        'model': item.get('model', ''),
                        'description': item.get('description', ''),
                        'category': item.get('category', ''),
                    }
        except Exception as e:
            print(f"{api_config.get('name', 'UPCitemdb')} error: {e}")
        return None

    @staticmethod
    def lookup_rapidapi(code: str, api_config: dict) -> Optional[Dict]:
        """Lookup part using RapidAPI-based service"""
        try:
            encoded = urllib.parse.quote(code)
            base_url = api_config.get('url', '')
            url = f"{base_url}?keyword={encoded}"
            req = urllib.request.Request(url)
            req.add_header('x-rapidapi-host', api_config.get('host', ''))
            req.add_header('x-rapidapi-key', api_config.get('api_key', ''))

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get('status') == 'success' and data.get('products'):
                    product = data['products'][0]
                    return {
                        'source': api_config.get('name', 'RapidAPI'),
                        'title': product.get('productName', ''),
                        'brand': product.get('manufacturerName', ''),
                        'model': product.get('partNumber', ''),
                        'description': product.get('category', ''),
                        'category': product.get('category', ''),
                        'price': product.get('regularPrice'),
                        'warranty': product.get('warrantyDetails', ''),
                    }
        except Exception as e:
            print(f"{api_config.get('name', 'RapidAPI')} error: {e}")
        return None

    @staticmethod
    def lookup_generic(code: str, api_config: dict) -> Optional[Dict]:
        """Generic lookup for custom APIs"""
        try:
            encoded = urllib.parse.quote(code)
            base_url = api_config.get('url', '')
            param_name = api_config.get('param_name', 'q')
            url = f"{base_url}?{param_name}={encoded}"
            req = urllib.request.Request(url)

            # Add headers
            if api_config.get('api_key'):
                header_name = api_config.get('api_key_header', 'Authorization')
                req.add_header(header_name, api_config['api_key'])

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Try to extract common fields
                if data:
                    return {
                        'source': api_config.get('name', 'Custom API'),
                        'title': str(data)[:100],
                        'brand': '',
                        'model': code,
                        'description': '',
                        'category': '',
                    }
        except Exception as e:
            print(f"{api_config.get('name', 'Custom API')} error: {e}")
        return None

    @staticmethod
    def lookup_single(code: str, api_config: dict) -> Optional[Dict]:
        """Lookup using a single API based on its type"""
        api_type = api_config.get('type', 'generic')

        if api_type == 'upcitemdb':
            return PartLookup.lookup_upcitemdb(code, api_config)
        elif api_type == 'rapidapi':
            return PartLookup.lookup_rapidapi(code, api_config)
        else:
            return PartLookup.lookup_generic(code, api_config)

    @staticmethod
    def lookup_all(code: str) -> List[Dict]:
        """Lookup code in all enabled APIs"""
        results = []

        for api_config in config_manager.get_enabled_apis():
            result = PartLookup.lookup_single(code, api_config)
            if result:
                results.append(result)

        return results


@dataclass
class InventoryItem:
    """Represents an inventory item"""
    upc: str
    description: str = ""
    additional_info: Dict[str, str] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if self.additional_info is None:
            self.additional_info = {}


@dataclass
class LocationInventory:
    """Represents inventory at a specific location"""
    item_upc: str
    location_id: str
    quantity: int
    last_scanned: str = ""
    
    def __post_init__(self):
        if not self.last_scanned:
            self.last_scanned = datetime.now().isoformat()


class InventoryDatabase:
    """Handles all database operations"""
    
    def __init__(self, db_path: str = "inventory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()
        
        # Create locations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                upc TEXT PRIMARY KEY,
                description TEXT,
                additional_info TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create inventory table (items at locations)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_upc TEXT NOT NULL,
                location_id TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                last_scanned TEXT NOT NULL,
                FOREIGN KEY (item_upc) REFERENCES items(upc),
                FOREIGN KEY (location_id) REFERENCES locations(id),
                UNIQUE(item_upc, location_id)
            )
        ''')
        
        # Create scan history table for audit trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_upc TEXT NOT NULL,
                location_id TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity_change INTEGER,
                scanned_at TEXT NOT NULL,
                workstation_id TEXT
            )
        ''')
        
        self.conn.commit()
    
    def add_location(self, name: str, description: str = "") -> str:
        """Add a new location"""
        location_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO locations (id, name, description, created_at)
                VALUES (?, ?, ?, ?)
            ''', (location_id, name, description, datetime.now().isoformat()))
            self.conn.commit()
            return location_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Location '{name}' already exists")
    
    def get_locations(self) -> List[Dict]:
        """Get all locations"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM locations ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]
    
    def add_or_update_item(self, upc: str, description: str = "", additional_info: Dict = None) -> None:
        """Add or update an item"""
        cursor = self.conn.cursor()
        info_json = json.dumps(additional_info or {})
        
        cursor.execute('''
            INSERT INTO items (upc, description, additional_info, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(upc) DO UPDATE SET
                description = COALESCE(excluded.description, description),
                additional_info = excluded.additional_info,
                updated_at = excluded.updated_at
        ''', (upc, description, info_json, datetime.now().isoformat(), datetime.now().isoformat()))
        self.conn.commit()
    
    def scan_item(self, upc: str, location_id: str, quantity: int = 1) -> None:
        """Scan an item at a location"""
        cursor = self.conn.cursor()
        
        # First ensure the item exists
        cursor.execute('SELECT upc FROM items WHERE upc = ?', (upc,))
        if not cursor.fetchone():
            self.add_or_update_item(upc)
        
        # Update inventory
        cursor.execute('''
            INSERT INTO inventory (item_upc, location_id, quantity, last_scanned)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(item_upc, location_id) DO UPDATE SET
                quantity = quantity + ?,
                last_scanned = ?
        ''', (upc, location_id, quantity, datetime.now().isoformat(), quantity, datetime.now().isoformat()))
        
        # Log scan history
        cursor.execute('''
            INSERT INTO scan_history (item_upc, location_id, action, quantity_change, scanned_at, workstation_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (upc, location_id, 'scan', quantity, datetime.now().isoformat(), os.environ.get('COMPUTERNAME', 'unknown')))
        
        self.conn.commit()
    
    def get_inventory_by_location(self, location_id: str) -> List[Dict]:
        """Get all inventory for a location"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT i.*, inv.quantity, inv.last_scanned
            FROM inventory inv
            JOIN items i ON inv.item_upc = i.upc
            WHERE inv.location_id = ?
            ORDER BY inv.last_scanned DESC
        ''', (location_id,))
        
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            if item['additional_info']:
                item['additional_info'] = json.loads(item['additional_info'])
            results.append(item)
        return results
    
    def get_item_locations(self, upc: str) -> List[Dict]:
        """Get all locations where an item exists"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT l.*, inv.quantity, inv.last_scanned
            FROM inventory inv
            JOIN locations l ON inv.location_id = l.id
            WHERE inv.item_upc = ?
            ORDER BY inv.quantity DESC
        ''', (upc,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_item_info(self, upc: str, additional_info: Dict[str, str]) -> None:
        """Update additional info for an item"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE items 
            SET additional_info = ?, updated_at = ?
            WHERE upc = ?
        ''', (json.dumps(additional_info), datetime.now().isoformat(), upc))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class InventoryScanner(tk.Tk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Inventory Scanner")
        self.geometry("800x600")
        
        # Initialize database with absolute path relative to script location
        script_dir = Path(__file__).parent.resolve()
        db_path = script_dir / "inventory.db"
        self.db = InventoryDatabase(str(db_path))
        
        # Current scanning location
        self.current_location_id = None
        
        # Setup UI
        self.setup_ui()
        
        # Load locations
        self.refresh_locations()
        
        # Bind enter key to scan
        self.bind('<Return>', lambda e: self.scan_barcode())
    
    def setup_ui(self):
        """Setup the user interface"""
        # Top frame for location selection
        top_frame = ttk.Frame(self, padding="10")
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(top_frame, text="Current Location:").grid(row=0, column=0, padx=5)
        
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(top_frame, textvariable=self.location_var, state="readonly", width=30)
        self.location_combo.grid(row=0, column=1, padx=5)
        self.location_combo.bind('<<ComboboxSelected>>', self.on_location_changed)
        
        ttk.Button(top_frame, text="Add Location", command=self.add_location_dialog).grid(row=0, column=2, padx=5)
        
        # Scanning frame
        scan_frame = ttk.LabelFrame(self, text="Barcode Scanning", padding="10")
        scan_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        ttk.Label(scan_frame, text="Scan Barcode:").grid(row=0, column=0, padx=5)
        
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(scan_frame, textvariable=self.barcode_var, width=40)
        self.barcode_entry.grid(row=0, column=1, padx=5)
        self.barcode_entry.focus()
        
        ttk.Button(scan_frame, text="Scan", command=self.scan_barcode).grid(row=0, column=2, padx=5)
        ttk.Button(scan_frame, text="Lookup Only", command=self.lookup_only).grid(row=0, column=3, padx=5)
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(scan_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, columnspan=3, pady=5)
        
        # Inventory display frame
        inv_frame = ttk.LabelFrame(self, text="Current Location Inventory", padding="10")
        inv_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        
        # Create treeview for inventory display
        self.tree = ttk.Treeview(inv_frame, columns=('UPC', 'Description', 'Part#', 'Brand', 'Attempted', 'Quantity', 'Last Scanned'), show='tree headings')
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure columns
        self.tree.column('#0', width=0, stretch=False)
        self.tree.column('UPC', width=120)
        self.tree.column('Description', width=180)
        self.tree.column('Part#', width=90)
        self.tree.column('Brand', width=80)
        self.tree.column('Attempted', width=150)
        self.tree.column('Quantity', width=50)
        self.tree.column('Last Scanned', width=120)

        self.tree.heading('UPC', text='UPC')
        self.tree.heading('Description', text='Description')
        self.tree.heading('Part#', text='Part #')
        self.tree.heading('Brand', text='Brand')
        self.tree.heading('Attempted', text='Attempted Parts')
        self.tree.heading('Quantity', text='Qty')
        self.tree.heading('Last Scanned', text='Last Scanned')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(inv_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Bottom buttons
        button_frame = ttk.Frame(self, padding="10")
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="Add Item Info", command=self.add_item_info_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="View All Locations", command=self.view_all_locations).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_inventory).pack(side=tk.LEFT, padx=5)
        
        # Sync operations frame
        sync_frame = ttk.LabelFrame(self, text="Sync Operations", padding="10")
        sync_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        ttk.Button(sync_frame, text="Export Data", command=self.export_data_dialog).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(sync_frame, text="Import Data", command=self.import_data_dialog).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(sync_frame, text="Generate Report", command=self.generate_report_dialog).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(sync_frame, text="Create Master DB", command=self.create_master_db_dialog).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(sync_frame, text="API Settings", command=self.show_api_settings).grid(row=0, column=4, padx=5, pady=5)
        
        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        inv_frame.columnconfigure(0, weight=1)
        inv_frame.rowconfigure(0, weight=1)
    
    def refresh_locations(self):
        """Refresh the locations dropdown"""
        locations = self.db.get_locations()
        self.location_combo['values'] = [loc['name'] for loc in locations]
        
        if locations and not self.current_location_id:
            self.location_combo.current(0)
            self.on_location_changed(None)
    
    def on_location_changed(self, event):
        """Handle location selection change"""
        selected_name = self.location_var.get()
        locations = self.db.get_locations()
        
        for loc in locations:
            if loc['name'] == selected_name:
                self.current_location_id = loc['id']
                self.refresh_inventory()
                break
    
    def scan_barcode(self):
        """Handle barcode scanning"""
        barcode = self.barcode_var.get().strip()

        if not barcode:
            return

        if not self.current_location_id:
            messagebox.showerror("Error", "Please select a location first")
            return

        try:
            # Check if item already exists and has been identified
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT description, additional_info FROM items WHERE upc = ?', (barcode,))
            existing = cursor.fetchone()

            if existing:
                desc = existing['description'] or ''
                add_info_str = existing['additional_info'] or '{}'
                add_info = json.loads(add_info_str) if add_info_str else {}
                attempted_parts = add_info.get('attempted_parts', '').split(' | ') if add_info.get('attempted_parts') else []

                # Check if item is identified (has real description, not "Not Identified" or empty)
                is_identified = desc and desc != "Not Identified" and desc != "No description"

                if is_identified:
                    # Item is identified - just update quantity
                    self.db.scan_item(barcode, self.current_location_id)
                    self.status_var.set(f"Added: {desc[:40]}... (Qty +1)")
                    self.barcode_var.set("")
                    self.refresh_inventory()
                    self.after(2000, lambda: self.status_var.set(""))
                else:
                    # Item exists but NOT identified - show dialog to try more lookups or add qty
                    self.db.scan_item(barcode, self.current_location_id)
                    self.barcode_var.set("")
                    self.refresh_inventory()
                    self.show_unidentified_item_dialog(barcode, attempted_parts)
            else:
                # New item - scan and do API lookup
                self.db.scan_item(barcode, self.current_location_id)
                self.status_var.set(f"Scanned: {barcode} - Looking up...")
                self.barcode_var.set("")
                self.refresh_inventory()

                # Trigger API lookup in background thread
                self.after(100, lambda: self.lookup_part_async(barcode))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan item: {str(e)}")

    def show_unidentified_item_dialog(self, upc: str, previous_attempts: List[str] = None):
        """Show dialog for previously scanned but unidentified item"""
        if previous_attempts is None:
            previous_attempts = []

        dialog = tk.Toplevel(self)
        dialog.title("Unidentified Item")
        dialog.geometry("500x350")
        dialog.transient(self)

        ttk.Label(dialog, text=f"UPC: {upc}",
                  font=('TkDefaultFont', 11, 'bold')).pack(pady=10)

        ttk.Label(dialog, text="This item has not been identified yet.",
                  foreground="orange").pack(pady=5)

        # Show previous attempts
        if previous_attempts:
            attempts_text = f"Previous attempts: {', '.join(previous_attempts)}"
            ttk.Label(dialog, text=attempts_text, foreground="gray").pack(pady=2)

        # Quantity section
        qty_frame = ttk.LabelFrame(dialog, text="Quick Add Quantity", padding=10)
        qty_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(qty_frame, text="Add quantity:").pack(side=tk.LEFT, padx=5)
        qty_var = tk.StringVar(value="1")
        qty_entry = ttk.Entry(qty_frame, textvariable=qty_var, width=10)
        qty_entry.pack(side=tk.LEFT, padx=5)

        def add_qty_only():
            try:
                qty = int(qty_var.get()) - 1  # -1 because we already added 1 in scan_barcode
                if qty > 0:
                    self.db.scan_item(upc, self.current_location_id, qty)
                    self.refresh_inventory()
                dialog.destroy()
                total = int(qty_var.get())
                self.status_var.set(f"Added {total} to: {upc}")
                self.after(2000, lambda: self.status_var.set(""))
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")

        ttk.Button(qty_frame, text="Add & Close", command=add_qty_only).pack(side=tk.LEFT, padx=10)

        # Lookup section
        lookup_frame = ttk.LabelFrame(dialog, text="Try Another Part Number", padding=10)
        lookup_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(lookup_frame, text="Part number:").pack(side=tk.LEFT, padx=5)
        part_var = tk.StringVar()
        part_entry = ttk.Entry(lookup_frame, textvariable=part_var, width=20)
        part_entry.pack(side=tk.LEFT, padx=5)

        status_label = ttk.Label(dialog, text="")
        status_label.pack(pady=5)

        def do_lookup():
            part_num = part_var.get().strip()
            if not part_num:
                status_label.config(text="Please enter a part number")
                return

            if part_num not in previous_attempts:
                previous_attempts.append(part_num)

            status_label.config(text=f"Looking up {part_num}...")
            dialog.update()

            results = PartLookup.lookup_all(part_num)

            if results:
                dialog.destroy()
                self.show_lookup_results_for_upc(upc, part_num, results, add_to_inventory=True)
            else:
                # Update attempted_parts in database
                additional_info = {'attempted_parts': ' | '.join(previous_attempts), 'source': 'Not Found'}
                self.db.update_item_info(upc, additional_info)
                status_label.config(text=f"No results for '{part_num}' - try another")
                part_var.set("")
                part_entry.focus()

        ttk.Button(lookup_frame, text="Lookup", command=do_lookup).pack(side=tk.LEFT, padx=5)

        # Bind Enter key
        part_entry.bind('<Return>', lambda e: do_lookup())

        # Bottom buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)

        def save_not_identified():
            # Save with attempted parts
            cursor = self.db.conn.cursor()
            cursor.execute(
                'UPDATE items SET description = ?, updated_at = ? WHERE upc = ?',
                ("Not Identified", datetime.now().isoformat(), upc)
            )
            if previous_attempts:
                additional_info = {'attempted_parts': ' | '.join(previous_attempts), 'source': 'Not Found'}
                self.db.update_item_info(upc, additional_info)
            self.refresh_inventory()
            dialog.destroy()
            self.status_var.set(f"Saved as Not Identified: {upc}")
            self.after(2000, lambda: self.status_var.set(""))

        def manual_entry():
            dialog.destroy()
            self.manual_description_entry(upc, True, previous_attempts)

        def web_search():
            search_term = part_var.get().strip() or (previous_attempts[-1] if previous_attempts else upc)
            dialog.destroy()
            self.show_web_search_dialog(upc, search_term, previous_attempts, add_to_inventory=True)

        ttk.Button(button_frame, text="Web Search", command=web_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save as Not Identified", command=save_not_identified).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Manual", command=manual_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def lookup_only(self):
        """Lookup a code without adding to inventory"""
        barcode = self.barcode_var.get().strip()

        if not barcode:
            messagebox.showinfo("Info", "Enter a UPC or part number to lookup")
            return

        self.status_var.set(f"Looking up: {barcode}...")
        self.barcode_var.set("")

        # Trigger API lookup in background thread
        self.after(100, lambda: self.lookup_part_async(barcode, add_to_inventory=False))

    def lookup_part_async(self, barcode: str, add_to_inventory: bool = True):
        """Lookup part info asynchronously"""
        def do_lookup():
            results = PartLookup.lookup_all(barcode)
            # Schedule UI update on main thread
            self.after(0, lambda: self.show_lookup_results(barcode, results, add_to_inventory))

        thread = threading.Thread(target=do_lookup, daemon=True)
        thread.start()

    def show_lookup_results(self, barcode: str, results: List[Dict], add_to_inventory: bool = True):
        """Show lookup results and allow user to apply"""
        if not results:
            # No results - prompt for alternate part number
            self.prompt_alternate_lookup(barcode, add_to_inventory)
            return

    def prompt_alternate_lookup(self, original_upc: str, add_to_inventory: bool = True, attempted_parts: List[str] = None):
        """Prompt user for alternate part number when UPC lookup fails"""
        if attempted_parts is None:
            attempted_parts = []

        dialog = tk.Toplevel(self)
        dialog.title("No Results Found")
        dialog.geometry("500x280")
        dialog.transient(self)

        ttk.Label(dialog, text=f"No results found for: {original_upc}",
                  font=('TkDefaultFont', 10, 'bold')).pack(pady=10)

        # Show attempted parts if any
        if attempted_parts:
            attempts_text = f"Attempted: {', '.join(attempted_parts)}"
            ttk.Label(dialog, text=attempts_text, foreground="gray").pack(pady=2)

        ttk.Label(dialog, text="Enter an alternate part number to lookup:").pack(pady=5)

        part_var = tk.StringVar()
        part_entry = ttk.Entry(dialog, textvariable=part_var, width=30)
        part_entry.pack(pady=5)
        part_entry.focus()

        status_label = ttk.Label(dialog, text="")
        status_label.pack(pady=5)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def do_alternate_lookup():
            part_num = part_var.get().strip()
            if not part_num:
                status_label.config(text="Please enter a part number")
                return

            # Track this attempt
            if part_num not in attempted_parts:
                attempted_parts.append(part_num)

            status_label.config(text=f"Looking up {part_num}...")
            dialog.update()

            # Lookup the alternate part number
            results = PartLookup.lookup_all(part_num)

            if results:
                dialog.destroy()
                # Show results with original UPC as the key to store
                self.show_lookup_results_for_upc(original_upc, part_num, results, add_to_inventory)
            else:
                status_label.config(text=f"No results for '{part_num}' - try another or Save Anyway")
                part_var.set("")
                part_entry.focus()

        def save_anyway():
            """Save with 'Not Identified' and store attempted part numbers"""
            dialog.destroy()
            if add_to_inventory and attempted_parts:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    'UPDATE items SET description = ?, updated_at = ? WHERE upc = ?',
                    ("Not Identified", datetime.now().isoformat(), original_upc)
                )

                additional_info = {
                    'source': 'Not Found',
                    'attempted_parts': ' | '.join(attempted_parts),
                }
                self.db.update_item_info(original_upc, additional_info)
                self.refresh_inventory()
                self.status_var.set(f"Saved: Not Identified ({', '.join(attempted_parts)})")
            else:
                self.status_var.set(f"Scanned: {original_upc} - Not Identified")
            self.after(3000, lambda: self.status_var.set(""))

        def manual_entry():
            dialog.destroy()
            self.manual_description_entry(original_upc, add_to_inventory, attempted_parts)

        def skip():
            dialog.destroy()
            self.status_var.set(f"Scanned: {original_upc} - No description")
            self.after(2000, lambda: self.status_var.set(""))

        # Bind Enter key to lookup
        part_entry.bind('<Return>', lambda e: do_alternate_lookup())

        def web_search():
            part_num = part_var.get().strip() or original_upc
            dialog.destroy()
            self.show_web_search_dialog(original_upc, part_num, attempted_parts, add_to_inventory)

        ttk.Button(button_frame, text="Lookup", command=do_alternate_lookup).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Web Search", command=web_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Anyway", command=save_anyway).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Manual", command=manual_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Skip", command=skip).pack(side=tk.LEFT, padx=5)

    def show_web_search_dialog(self, original_upc: str, search_term: str, attempted_parts: List[str] = None, add_to_inventory: bool = True):
        """Show web search results dialog"""
        if attempted_parts is None:
            attempted_parts = []

        dialog = tk.Toplevel(self)
        dialog.title("Web Search Results")
        dialog.geometry("750x550")
        dialog.transient(self)

        # Search frame
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(search_frame, text=f"UPC: {original_upc}", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)

        ttk.Label(search_frame, text="  Search:").pack(side=tk.LEFT, padx=(20, 5))
        search_var = tk.StringVar(value=search_term)
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT)

        status_label = ttk.Label(dialog, text="Searching...")
        status_label.pack(pady=5)

        # Results list
        results_frame = ttk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        results_list = tk.Listbox(results_frame, height=10, width=80)
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_list.yview)
        results_list.configure(yscrollcommand=results_scrollbar.set)

        results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Store search results
        search_results = []

        def do_search():
            nonlocal search_results
            query = search_var.get().strip()
            if not query:
                return

            status_label.config(text=f"Searching for '{query}'...")
            dialog.update()

            results_list.delete(0, tk.END)
            search_results = WebSearcher.search_duckduckgo(query)

            if search_results:
                status_label.config(text=f"Found {len(search_results)} results - select one to view")
                for i, result in enumerate(search_results):
                    results_list.insert(tk.END, f"{i+1}. {result['title'][:70]}")
            else:
                status_label.config(text="No results found - try different search terms")

        ttk.Button(search_frame, text="Search", command=do_search).pack(side=tk.LEFT, padx=5)
        search_entry.bind('<Return>', lambda e: do_search())

        # Page content display
        content_frame = ttk.LabelFrame(dialog, text="Page Content (select result above)", padding=5)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        content_text = tk.Text(content_frame, height=8, wrap=tk.WORD)
        content_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=content_text.yview)
        content_text.configure(yscrollcommand=content_scrollbar.set)

        content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Description entry
        desc_frame = ttk.Frame(dialog)
        desc_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(desc_frame, text="Description:").pack(side=tk.LEFT)
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(desc_frame, textvariable=desc_var, width=60)
        desc_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def on_result_select(event):
            selection = results_list.curselection()
            if not selection or not search_results:
                return

            idx = selection[0]
            result = search_results[idx]

            status_label.config(text=f"Fetching: {result['url'][:50]}...")
            dialog.update()

            # Fetch page content
            page_text = WebSearcher.fetch_page_text(result['url'])

            content_text.delete(1.0, tk.END)
            content_text.insert(tk.END, f"URL: {result['url']}\n\n")
            content_text.insert(tk.END, f"Snippet: {result['snippet']}\n\n")
            content_text.insert(tk.END, "-" * 50 + "\n\n")
            content_text.insert(tk.END, page_text)

            # Pre-fill description with title
            desc_var.set(result['title'][:200])
            status_label.config(text="Edit description below and click Save")

        results_list.bind('<<ListboxSelect>>', on_result_select)

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def save_description():
            desc = desc_var.get().strip()
            if not desc:
                messagebox.showerror("Error", "Please enter a description")
                return

            if add_to_inventory:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    'UPDATE items SET description = ?, updated_at = ? WHERE upc = ?',
                    (desc[:200], datetime.now().isoformat(), original_upc)
                )

                # Save additional info
                additional_info = {
                    'source': 'Web Search',
                    'search_term': search_var.get().strip(),
                }
                if attempted_parts:
                    additional_info['attempted_parts'] = ' | '.join(attempted_parts)

                self.db.update_item_info(original_upc, additional_info)
                self.refresh_inventory()

            self.status_var.set(f"Saved: {desc[:50]}...")
            dialog.destroy()
            self.after(2000, lambda: self.status_var.set(""))

        def back_to_lookup():
            dialog.destroy()
            self.prompt_alternate_lookup(original_upc, add_to_inventory, attempted_parts)

        def open_in_browser():
            selection = results_list.curselection()
            if selection and search_results:
                url = search_results[selection[0]]['url']
                import webbrowser
                webbrowser.open(url)

        ttk.Button(btn_frame, text="Save Description", command=save_description).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Open in Browser", command=open_in_browser).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Back to Lookup", command=back_to_lookup).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Start initial search
        dialog.after(100, do_search)

    def manual_description_entry(self, upc: str, add_to_inventory: bool = True, attempted_parts: List[str] = None):
        """Allow manual entry of description when no API results"""
        if attempted_parts is None:
            attempted_parts = []

        dialog = tk.Toplevel(self)
        dialog.title(f"Manual Entry for: {upc}")
        dialog.geometry("450x300")
        dialog.transient(self)

        ttk.Label(dialog, text=f"UPC: {upc}", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)

        # Show attempted parts if any
        if attempted_parts:
            attempts_text = f"Attempted lookups: {', '.join(attempted_parts)}"
            ttk.Label(dialog, text=attempts_text, foreground="gray").pack(pady=2)

        ttk.Label(dialog, text="Description:").pack(anchor=tk.W, padx=20)
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(dialog, textvariable=desc_var, width=50)
        desc_entry.pack(padx=20, pady=5)
        desc_entry.focus()

        ttk.Label(dialog, text="Part Number (optional):").pack(anchor=tk.W, padx=20)
        part_var = tk.StringVar(value=attempted_parts[-1] if attempted_parts else "")
        ttk.Entry(dialog, textvariable=part_var, width=30).pack(anchor=tk.W, padx=20, pady=5)

        ttk.Label(dialog, text="Brand (optional):").pack(anchor=tk.W, padx=20)
        brand_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=brand_var, width=30).pack(anchor=tk.W, padx=20, pady=5)

        def save_manual():
            desc = desc_var.get().strip()
            if not desc:
                messagebox.showerror("Error", "Description is required")
                return

            if add_to_inventory:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    'UPDATE items SET description = ?, updated_at = ? WHERE upc = ?',
                    (desc, datetime.now().isoformat(), upc)
                )

                additional_info = {'source': 'Manual Entry'}
                if part_var.get().strip():
                    additional_info['part_number'] = part_var.get().strip()
                if brand_var.get().strip():
                    additional_info['brand'] = brand_var.get().strip()
                if attempted_parts:
                    additional_info['attempted_parts'] = ' | '.join(attempted_parts)

                self.db.update_item_info(upc, additional_info)
                self.refresh_inventory()

            self.status_var.set(f"Saved: {desc[:50]}...")
            dialog.destroy()
            self.after(2000, lambda: self.status_var.set(""))

        ttk.Button(dialog, text="Save", command=save_manual).pack(pady=15)

    def show_lookup_results_for_upc(self, original_upc: str, searched_part: str, results: List[Dict], add_to_inventory: bool = True):
        """Show lookup results and store with original UPC as key"""

        # Create results dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Results for: {searched_part}")
        dialog.geometry("600x450")
        dialog.transient(self)

        ttk.Label(dialog, text=f"UPC: {original_upc}  |  Searched: {searched_part}",
                  font=('TkDefaultFont', 10, 'bold')).pack(pady=5)
        ttk.Label(dialog, text=f"Found {len(results)} result(s)",
                  font=('TkDefaultFont', 9)).pack(pady=5)

        # Results frame with scrollbar
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        results_frame = ttk.Frame(canvas)

        results_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=results_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        selected_result = tk.StringVar()

        for i, result in enumerate(results):
            frame = ttk.LabelFrame(results_frame, text=f"Source: {result['source']}", padding=10)
            frame.pack(fill=tk.X, padx=10, pady=5)

            # Radio button to select this result
            rb = ttk.Radiobutton(frame, text="Use this result", variable=selected_result, value=str(i))
            rb.grid(row=0, column=0, columnspan=2, sticky=tk.W)

            row = 1
            if result.get('title'):
                ttk.Label(frame, text="Title:", font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0, sticky=tk.W)
                ttk.Label(frame, text=result['title'][:80], wraplength=450).grid(row=row, column=1, sticky=tk.W)
                row += 1

            if result.get('brand'):
                ttk.Label(frame, text="Brand:", font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0, sticky=tk.W)
                ttk.Label(frame, text=result['brand']).grid(row=row, column=1, sticky=tk.W)
                row += 1

            if result.get('model'):
                ttk.Label(frame, text="Part #:", font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0, sticky=tk.W)
                ttk.Label(frame, text=result['model']).grid(row=row, column=1, sticky=tk.W)
                row += 1

            if result.get('category'):
                ttk.Label(frame, text="Category:", font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0, sticky=tk.W)
                ttk.Label(frame, text=result['category']).grid(row=row, column=1, sticky=tk.W)
                row += 1

            if result.get('price'):
                ttk.Label(frame, text="Price:", font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=0, sticky=tk.W)
                ttk.Label(frame, text=f"${result['price']}").grid(row=row, column=1, sticky=tk.W)
                row += 1

        # Select first result by default
        if results:
            selected_result.set("0")

        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def apply_result():
            idx = selected_result.get()
            if idx:
                result = results[int(idx)]
                # Build description from result
                desc_parts = []
                if result.get('brand'):
                    desc_parts.append(result['brand'])
                if result.get('model'):
                    desc_parts.append(result['model'])
                if result.get('title'):
                    desc_parts.append(result['title'])

                description = ' - '.join(desc_parts) if desc_parts else result.get('title', '')

                if add_to_inventory:
                    # Update item description in database - use ORIGINAL UPC as key
                    cursor = self.db.conn.cursor()
                    cursor.execute(
                        'UPDATE items SET description = ?, updated_at = ? WHERE upc = ?',
                        (description[:200], datetime.now().isoformat(), original_upc)
                    )

                    # Store additional info including the searched part number
                    additional_info = {
                        'source': result['source'],
                        'searched_part': searched_part,
                        'brand': result.get('brand', ''),
                        'part_number': result.get('model', ''),
                        'category': result.get('category', ''),
                    }
                    if result.get('price'):
                        additional_info['price'] = str(result['price'])
                    if result.get('warranty'):
                        additional_info['warranty'] = result['warranty']

                    self.db.update_item_info(original_upc, additional_info)
                    self.refresh_inventory()
                    self.status_var.set(f"Applied: {description[:50]}...")
                else:
                    # Just show the info (lookup only mode)
                    self.status_var.set(f"Found: {description[:60]}...")

                dialog.destroy()
                self.after(3000, lambda: self.status_var.set(""))

        def skip_result():
            dialog.destroy()
            self.status_var.set(f"Scanned: {original_upc}")
            self.after(2000, lambda: self.status_var.set(""))

        ttk.Button(button_frame, text="Apply Selected", command=apply_result).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Skip", command=skip_result).pack(side=tk.LEFT, padx=10)
    
    def refresh_inventory(self):
        """Refresh the inventory display"""
        if not self.current_location_id:
            return

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load inventory
        inventory = self.db.get_inventory_by_location(self.current_location_id)

        for item in inventory:
            last_scan = datetime.fromisoformat(item['last_scanned']).strftime('%Y-%m-%d %H:%M')
            # Extract additional info
            add_info = item.get('additional_info', {}) or {}
            part_num = add_info.get('part_number', '') or add_info.get('searched_part', '')
            brand = add_info.get('brand', '')
            attempted = add_info.get('attempted_parts', '')

            self.tree.insert('', 'end', values=(
                item['upc'],
                item['description'] or 'No description',
                part_num,
                brand,
                attempted,
                item['quantity'],
                last_scan
            ))
    
    def add_location_dialog(self):
        """Show dialog to add a new location"""
        dialog = tk.Toplevel(self)
        dialog.title("Add Location")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="Location Name:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        name_entry.focus()
        
        ttk.Label(dialog, text="Description:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(dialog, textvariable=desc_var, width=30)
        desc_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def save_location():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Location name is required")
                return
            
            try:
                self.db.add_location(name, desc_var.get())
                self.refresh_locations()
                dialog.destroy()
                
                # Select the new location
                self.location_var.set(name)
                self.on_location_changed(None)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(dialog, text="Save", command=save_location).grid(row=2, column=0, columnspan=2, pady=20)
    
    def add_item_info_dialog(self):
        """Show dialog to add additional info to an item"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select an item from the inventory")
            return
        
        item_values = self.tree.item(selected[0])['values']
        upc = item_values[0]
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Add Info for UPC: {upc}")
        dialog.geometry("500x400")
        
        # Get current item info
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM items WHERE upc = ?', (upc,))
        item = dict(cursor.fetchone())
        current_info = json.loads(item['additional_info']) if item['additional_info'] else {}
        
        # Description field
        ttk.Label(dialog, text="Description:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        desc_var = tk.StringVar(value=item['description'])
        desc_entry = ttk.Entry(dialog, textvariable=desc_var, width=40)
        desc_entry.grid(row=0, column=1, padx=10, pady=10)
        
        # Additional fields frame
        fields_frame = ttk.LabelFrame(dialog, text="Additional Fields", padding="10")
        fields_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Store field entries
        field_entries = {}
        
        # Display existing fields
        row = 0
        for key, value in current_info.items():
            ttk.Label(fields_frame, text=f"{key}:").grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
            var = tk.StringVar(value=value)
            entry = ttk.Entry(fields_frame, textvariable=var, width=30)
            entry.grid(row=row, column=1, padx=5, pady=2)
            field_entries[key] = var
            row += 1
        
        # Add new field section
        ttk.Label(fields_frame, text="Add New Field:").grid(row=row, column=0, padx=5, pady=10, sticky=tk.W)
        
        new_key_var = tk.StringVar()
        new_value_var = tk.StringVar()
        
        ttk.Entry(fields_frame, textvariable=new_key_var, width=15).grid(row=row+1, column=0, padx=5, pady=2)
        ttk.Entry(fields_frame, textvariable=new_value_var, width=30).grid(row=row+1, column=1, padx=5, pady=2)
        
        def save_info():
            # Update description
            self.db.conn.cursor().execute(
                'UPDATE items SET description = ?, updated_at = ? WHERE upc = ?',
                (desc_var.get(), datetime.now().isoformat(), upc)
            )
            
            # Collect all additional info
            additional_info = {}
            for key, var in field_entries.items():
                if var.get().strip():
                    additional_info[key] = var.get().strip()
            
            # Add new field if provided
            if new_key_var.get().strip() and new_value_var.get().strip():
                additional_info[new_key_var.get().strip()] = new_value_var.get().strip()
            
            # Update additional info
            self.db.update_item_info(upc, additional_info)
            self.refresh_inventory()
            dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_info).grid(row=2, column=0, columnspan=2, pady=20)
        
        dialog.columnconfigure(1, weight=1)
        dialog.rowconfigure(1, weight=1)
    
    def view_all_locations(self):
        """Show all locations where items are stored"""
        dialog = tk.Toplevel(self)
        dialog.title("All Locations Summary")
        dialog.geometry("600x400")
        
        tree = ttk.Treeview(dialog, columns=('Location', 'Total Items', 'Total Quantity'), show='tree headings')
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tree.column('#0', width=0, stretch=False)
        tree.column('Location', width=200)
        tree.column('Total Items', width=150)
        tree.column('Total Quantity', width=150)
        
        tree.heading('Location', text='Location')
        tree.heading('Total Items', text='Unique Items')
        tree.heading('Total Quantity', text='Total Quantity')
        
        # Get summary data
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT l.name, COUNT(DISTINCT inv.item_upc) as item_count, SUM(inv.quantity) as total_qty
            FROM locations l
            LEFT JOIN inventory inv ON l.id = inv.location_id
            GROUP BY l.id, l.name
            ORDER BY l.name
        ''')
        
        for row in cursor.fetchall():
            tree.insert('', 'end', values=(row['name'], row['item_count'] or 0, row['total_qty'] or 0))
    
    def export_data_dialog(self):
        """Show dialog for exporting data"""
        dialog = tk.Toplevel(self)
        dialog.title("Export Data")
        dialog.geometry("500x300")
        
        # Export path selection
        ttk.Label(dialog, text="Export Directory:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        path_var = tk.StringVar(value=str(Path.home() / "AlvinScan_Export"))
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=40)
        path_entry.grid(row=0, column=1, padx=10, pady=10)
        
        def browse_path():
            directory = filedialog.askdirectory(initialdir=Path.home())
            if directory:
                path_var.set(directory)
        
        ttk.Button(dialog, text="Browse", command=browse_path).grid(row=0, column=2, padx=5)
        
        # Date filter
        ttk.Label(dialog, text="Export changes since:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        
        filter_var = tk.BooleanVar()
        filter_check = ttk.Checkbutton(dialog, text="Enable date filter", variable=filter_var)
        filter_check.grid(row=1, column=1, sticky=tk.W)
        
        date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        date_entry = ttk.Entry(dialog, textvariable=date_var, width=15)
        date_entry.grid(row=2, column=1, padx=10, sticky=tk.W)
        
        def export_data():
            export_path = path_var.get()
            if not export_path:
                messagebox.showerror("Error", "Please select an export directory")
                return
            
            try:
                sync = InventorySync(self.db.db_path)
                since_date = date_var.get() if filter_var.get() else None
                sync.export_data(export_path, since_date)
                sync.close()
                
                messagebox.showinfo("Success", f"Data exported successfully to:\n{export_path}")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export data:\n{str(e)}")
        
        ttk.Button(dialog, text="Export", command=export_data).grid(row=3, column=0, columnspan=3, pady=20)
    
    def import_data_dialog(self):
        """Show dialog for importing data"""
        dialog = tk.Toplevel(self)
        dialog.title("Import Data")
        dialog.geometry("500x250")
        
        # Import path selection
        ttk.Label(dialog, text="Import Directory:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        path_var = tk.StringVar()
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=40)
        path_entry.grid(row=0, column=1, padx=10, pady=10)
        
        def browse_path():
            directory = filedialog.askdirectory(initialdir=Path.home())
            if directory:
                path_var.set(directory)
        
        ttk.Button(dialog, text="Browse", command=browse_path).grid(row=0, column=2, padx=5)
        
        # Merge option
        merge_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Merge data (unchecked = replace)", variable=merge_var).grid(
            row=1, column=0, columnspan=3, padx=10, pady=10
        )
        
        # Warning label
        warning_label = ttk.Label(dialog, text="⚠️ Warning: Import will modify your database. Consider backing up first.", 
                                 foreground="red")
        warning_label.grid(row=2, column=0, columnspan=3, padx=10, pady=5)
        
        def import_data():
            import_path = path_var.get()
            if not import_path:
                messagebox.showerror("Error", "Please select an import directory")
                return
            
            # Check if metadata.json exists
            if not Path(import_path, 'metadata.json').exists():
                messagebox.showerror("Error", "Invalid import directory. No metadata.json found.")
                return
            
            if messagebox.askyesno("Confirm Import", 
                                  "Are you sure you want to import data?\nThis will modify your database."):
                try:
                    sync = InventorySync(self.db.db_path)
                    sync.import_data(import_path, merge_var.get())
                    sync.close()
                    
                    self.refresh_inventory()
                    messagebox.showinfo("Success", "Data imported successfully!")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Import Error", f"Failed to import data:\n{str(e)}")
        
        ttk.Button(dialog, text="Import", command=import_data).grid(row=3, column=0, columnspan=3, pady=20)
    
    def generate_report_dialog(self):
        """Show dialog for generating reports"""
        dialog = tk.Toplevel(self)
        dialog.title("Generate Report")
        dialog.geometry("500x200")
        
        # Output file selection
        ttk.Label(dialog, text="Report File:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        default_path = str(Path.home() / f"AlvinScan_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        path_var = tk.StringVar(value=default_path)
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=40)
        path_entry.grid(row=0, column=1, padx=10, pady=10)
        
        def browse_path():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=Path(path_var.get()).name
            )
            if file_path:
                path_var.set(file_path)
        
        ttk.Button(dialog, text="Browse", command=browse_path).grid(row=0, column=2, padx=5)
        
        # Open after generation option
        open_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Open report after generation", variable=open_var).grid(
            row=1, column=0, columnspan=3, padx=10, pady=10
        )
        
        def generate_report():
            output_file = path_var.get()
            if not output_file:
                messagebox.showerror("Error", "Please specify an output file")
                return
            
            try:
                sync = InventorySync(self.db.db_path)
                sync.generate_report(output_file)
                sync.close()
                
                messagebox.showinfo("Success", f"Report generated successfully:\n{output_file}")
                
                if open_var.get():
                    # Open the report file
                    if platform.system() == "Windows":
                        os.startfile(output_file)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", output_file])
                    else:  # Linux
                        subprocess.run(["xdg-open", output_file])
                
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Report Error", f"Failed to generate report:\n{str(e)}")
        
        ttk.Button(dialog, text="Generate Report", command=generate_report).grid(row=2, column=0, columnspan=3, pady=20)
    
    def create_master_db_dialog(self):
        """Show dialog for creating master database"""
        dialog = tk.Toplevel(self)
        dialog.title("Create Master Database")
        dialog.geometry("600x400")
        
        # Instructions
        instructions = ttk.Label(dialog, text="Select multiple export directories to merge into a master database:")
        instructions.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        
        # Source directories list
        ttk.Label(dialog, text="Source Directories:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.NW)
        
        # Listbox for directories
        source_list = tk.Listbox(dialog, height=8, width=50)
        source_list.grid(row=1, column=1, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL)
        scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
        source_list.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=source_list.yview)
        
        # Buttons for list management
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=1, pady=5)
        
        def add_directory():
            directory = filedialog.askdirectory(initialdir=Path.home())
            if directory and Path(directory, 'metadata.json').exists():
                source_list.insert(tk.END, directory)
            elif directory:
                messagebox.showerror("Error", "Invalid export directory. No metadata.json found.")
        
        def remove_directory():
            selection = source_list.curselection()
            if selection:
                source_list.delete(selection[0])
        
        ttk.Button(button_frame, text="Add Directory", command=add_directory).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=remove_directory).pack(side=tk.LEFT, padx=5)
        
        # Output database selection
        ttk.Label(dialog, text="Master Database:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        
        output_var = tk.StringVar(value=str(Path.home() / "AlvinScan_Master.db"))
        output_entry = ttk.Entry(dialog, textvariable=output_var, width=40)
        output_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def browse_output():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                initialfile="AlvinScan_Master.db"
            )
            if file_path:
                output_var.set(file_path)
        
        ttk.Button(dialog, text="Browse", command=browse_output).grid(row=3, column=2, padx=5)
        
        def create_master():
            source_dirs = list(source_list.get(0, tk.END))
            if not source_dirs:
                messagebox.showerror("Error", "Please add at least one source directory")
                return
            
            output_db = output_var.get()
            if not output_db:
                messagebox.showerror("Error", "Please specify an output database file")
                return
            
            try:
                sync = InventorySync()
                sync.create_master_db(source_dirs, output_db)
                sync.close()
                
                messagebox.showinfo("Success", f"Master database created successfully:\n{output_db}")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Master DB Error", f"Failed to create master database:\n{str(e)}")
        
        ttk.Button(dialog, text="Create Master Database", command=create_master).grid(
            row=4, column=0, columnspan=3, pady=20
        )
        
        # Configure grid weights
        dialog.columnconfigure(1, weight=1)
        dialog.rowconfigure(1, weight=1)
    
    def show_api_settings(self):
        """Show API configuration dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("API Settings")
        dialog.geometry("700x500")
        dialog.transient(self)

        ttk.Label(dialog, text="Configure API Endpoints",
                  font=('TkDefaultFont', 12, 'bold')).pack(pady=10)

        # API list frame
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview for APIs
        columns = ('Name', 'Type', 'Enabled', 'Description')
        api_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        api_tree.heading('Name', text='Name')
        api_tree.heading('Type', text='Type')
        api_tree.heading('Enabled', text='Enabled')
        api_tree.heading('Description', text='Description')

        api_tree.column('Name', width=150)
        api_tree.column('Type', width=80)
        api_tree.column('Enabled', width=60)
        api_tree.column('Description', width=300)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=api_tree.yview)
        api_tree.configure(yscrollcommand=scrollbar.set)

        api_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_api_list():
            for item in api_tree.get_children():
                api_tree.delete(item)
            for i, api in enumerate(config_manager.get_apis()):
                api_tree.insert('', 'end', iid=str(i), values=(
                    api.get('name', ''),
                    api.get('type', 'generic'),
                    'Yes' if api.get('enabled', True) else 'No',
                    api.get('description', '')
                ))

        refresh_api_list()

        # Buttons frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def add_api():
            self.show_api_edit_dialog(dialog, None, refresh_api_list)

        def edit_api():
            selected = api_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Please select an API to edit")
                return
            idx = int(selected[0])
            self.show_api_edit_dialog(dialog, idx, refresh_api_list)

        def delete_api():
            selected = api_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Please select an API to delete")
                return
            idx = int(selected[0])
            api = config_manager.get_apis()[idx]
            if messagebox.askyesno("Confirm Delete", f"Delete API '{api.get('name')}'?"):
                config_manager.delete_api(idx)
                refresh_api_list()

        def toggle_api():
            selected = api_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Please select an API to toggle")
                return
            idx = int(selected[0])
            apis = config_manager.get_apis()
            apis[idx]['enabled'] = not apis[idx].get('enabled', True)
            config_manager.save_config()
            refresh_api_list()

        def test_api():
            selected = api_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Please select an API to test")
                return
            idx = int(selected[0])
            api = config_manager.get_apis()[idx]

            # Test with a known UPC
            test_code = "024844038791"  # K&N air filter
            result = PartLookup.lookup_single(test_code, api)

            if result:
                messagebox.showinfo("Test Success",
                    f"API: {api.get('name')}\n"
                    f"Test code: {test_code}\n\n"
                    f"Result: {result.get('title', 'No title')[:100]}")
            else:
                messagebox.showwarning("Test Failed",
                    f"API: {api.get('name')}\n"
                    f"Test code: {test_code}\n\n"
                    f"No results returned. Check API configuration.")

        ttk.Button(btn_frame, text="Add API", command=add_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit", command=edit_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete", command=delete_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Enable/Disable", command=toggle_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Test", command=test_api).pack(side=tk.LEFT, padx=5)

        # Double-click to edit
        api_tree.bind('<Double-1>', lambda e: edit_api())

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def show_api_edit_dialog(self, parent, api_index: Optional[int], refresh_callback):
        """Show dialog to add or edit an API"""
        is_new = api_index is None
        api = {} if is_new else config_manager.get_apis()[api_index].copy()

        dialog = tk.Toplevel(parent)
        dialog.title("Add API" if is_new else "Edit API")
        dialog.geometry("500x450")
        dialog.transient(parent)

        # Form fields
        fields_frame = ttk.Frame(dialog, padding=10)
        fields_frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        ttk.Label(fields_frame, text="Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=api.get('name', ''))
        ttk.Entry(fields_frame, textvariable=name_var, width=40).grid(row=row, column=1, pady=5)
        row += 1

        ttk.Label(fields_frame, text="Type:").grid(row=row, column=0, sticky=tk.W, pady=5)
        type_var = tk.StringVar(value=api.get('type', 'generic'))
        type_combo = ttk.Combobox(fields_frame, textvariable=type_var, values=['upcitemdb', 'rapidapi', 'generic'], width=37)
        type_combo.grid(row=row, column=1, pady=5)
        row += 1

        ttk.Label(fields_frame, text="URL:").grid(row=row, column=0, sticky=tk.W, pady=5)
        url_var = tk.StringVar(value=api.get('url', ''))
        ttk.Entry(fields_frame, textvariable=url_var, width=40).grid(row=row, column=1, pady=5)
        row += 1

        ttk.Label(fields_frame, text="Host (RapidAPI):").grid(row=row, column=0, sticky=tk.W, pady=5)
        host_var = tk.StringVar(value=api.get('host', ''))
        ttk.Entry(fields_frame, textvariable=host_var, width=40).grid(row=row, column=1, pady=5)
        row += 1

        ttk.Label(fields_frame, text="API Key:").grid(row=row, column=0, sticky=tk.W, pady=5)
        key_var = tk.StringVar(value=api.get('api_key', ''))
        ttk.Entry(fields_frame, textvariable=key_var, width=40, show='*').grid(row=row, column=1, pady=5)
        row += 1

        ttk.Label(fields_frame, text="Query Param (generic):").grid(row=row, column=0, sticky=tk.W, pady=5)
        param_var = tk.StringVar(value=api.get('param_name', 'q'))
        ttk.Entry(fields_frame, textvariable=param_var, width=40).grid(row=row, column=1, pady=5)
        row += 1

        ttk.Label(fields_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, pady=5)
        desc_var = tk.StringVar(value=api.get('description', ''))
        ttk.Entry(fields_frame, textvariable=desc_var, width=40).grid(row=row, column=1, pady=5)
        row += 1

        enabled_var = tk.BooleanVar(value=api.get('enabled', True))
        ttk.Checkbutton(fields_frame, text="Enabled", variable=enabled_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Help text
        help_text = """
Type Guide:
• upcitemdb - For UPCitemdb.com API (uses ?upc= parameter)
• rapidapi - For RapidAPI services (uses x-rapidapi headers)
• generic - Custom API (configure param name and headers)
        """
        ttk.Label(fields_frame, text=help_text, foreground='gray').grid(row=row, column=0, columnspan=2, pady=10)

        def save():
            if not name_var.get().strip():
                messagebox.showerror("Error", "Name is required")
                return

            new_api = {
                'name': name_var.get().strip(),
                'type': type_var.get(),
                'url': url_var.get().strip(),
                'host': host_var.get().strip(),
                'api_key': key_var.get().strip(),
                'param_name': param_var.get().strip() or 'q',
                'description': desc_var.get().strip(),
                'enabled': enabled_var.get()
            }

            if is_new:
                config_manager.add_api(new_api)
            else:
                config_manager.update_api(api_index, new_api)

            refresh_callback()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def on_closing(self):
        """Handle window closing"""
        self.db.close()
        self.destroy()


def main():
    """Main entry point"""
    app = InventoryScanner()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()