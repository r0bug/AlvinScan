#!/usr/bin/env python3
"""
Inventory Scanner - Main Application
Barcode scanning inventory management system
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from pathlib import Path
import sqlite3
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import uuid


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
        
        # Initialize database
        self.db = InventoryDatabase()
        
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
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(scan_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, columnspan=3, pady=5)
        
        # Inventory display frame
        inv_frame = ttk.LabelFrame(self, text="Current Location Inventory", padding="10")
        inv_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        
        # Create treeview for inventory display
        self.tree = ttk.Treeview(inv_frame, columns=('UPC', 'Description', 'Quantity', 'Last Scanned'), show='tree headings')
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure columns
        self.tree.column('#0', width=0, stretch=False)
        self.tree.column('UPC', width=150)
        self.tree.column('Description', width=250)
        self.tree.column('Quantity', width=80)
        self.tree.column('Last Scanned', width=150)
        
        self.tree.heading('UPC', text='UPC')
        self.tree.heading('Description', text='Description')
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
            self.db.scan_item(barcode, self.current_location_id)
            self.status_var.set(f"Scanned: {barcode}")
            self.barcode_var.set("")
            self.refresh_inventory()
            
            # Show notification
            self.after(2000, lambda: self.status_var.set(""))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan item: {str(e)}")
    
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
            self.tree.insert('', 'end', values=(
                item['upc'],
                item['description'] or 'No description',
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