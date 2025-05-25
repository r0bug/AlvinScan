#!/usr/bin/env python3
"""
Sync Utility - For syncing data between workstations
Handles export/import of inventory data for multi-workstation setups
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
import shutil
import argparse


class InventorySync:
    """Handles syncing inventory data between workstations"""
    
    def __init__(self, db_path: str = "inventory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def export_data(self, export_path: str, since_date: str = None) -> None:
        """Export inventory data to JSON files"""
        export_dir = Path(export_path)
        export_dir.mkdir(exist_ok=True)
        
        # Export metadata
        metadata = {
            'export_date': datetime.now().isoformat(),
            'workstation': os.environ.get('COMPUTERNAME', 'unknown'),
            'since_date': since_date
        }
        
        with open(export_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Export locations
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM locations')
        locations = [dict(row) for row in cursor.fetchall()]
        
        with open(export_dir / 'locations.json', 'w') as f:
            json.dump(locations, f, indent=2)
        
        # Export items
        cursor.execute('SELECT * FROM items')
        items = [dict(row) for row in cursor.fetchall()]
        
        with open(export_dir / 'items.json', 'w') as f:
            json.dump(items, f, indent=2)
        
        # Export inventory with optional date filter
        if since_date:
            cursor.execute('''
                SELECT * FROM inventory 
                WHERE last_scanned >= ?
            ''', (since_date,))
        else:
            cursor.execute('SELECT * FROM inventory')
        
        inventory = [dict(row) for row in cursor.fetchall()]
        
        with open(export_dir / 'inventory.json', 'w') as f:
            json.dump(inventory, f, indent=2)
        
        # Export scan history with optional date filter
        if since_date:
            cursor.execute('''
                SELECT * FROM scan_history 
                WHERE scanned_at >= ?
            ''', (since_date,))
        else:
            cursor.execute('SELECT * FROM scan_history')
        
        scan_history = [dict(row) for row in cursor.fetchall()]
        
        with open(export_dir / 'scan_history.json', 'w') as f:
            json.dump(scan_history, f, indent=2)
        
        print(f"Data exported to {export_dir}")
        print(f"- Locations: {len(locations)}")
        print(f"- Items: {len(items)}")
        print(f"- Inventory entries: {len(inventory)}")
        print(f"- Scan history: {len(scan_history)}")
    
    def import_data(self, import_path: str, merge: bool = True) -> None:
        """Import inventory data from JSON files"""
        import_dir = Path(import_path)
        
        if not import_dir.exists():
            raise ValueError(f"Import directory {import_dir} does not exist")
        
        # Read metadata
        with open(import_dir / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        
        print(f"Importing data from {metadata['workstation']} exported on {metadata['export_date']}")
        
        # Import locations
        with open(import_dir / 'locations.json', 'r') as f:
            locations = json.load(f)
        
        cursor = self.conn.cursor()
        for loc in locations:
            if merge:
                cursor.execute('''
                    INSERT OR IGNORE INTO locations (id, name, description, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (loc['id'], loc['name'], loc['description'], loc['created_at']))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO locations (id, name, description, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (loc['id'], loc['name'], loc['description'], loc['created_at']))
        
        # Import items
        with open(import_dir / 'items.json', 'r') as f:
            items = json.load(f)
        
        for item in items:
            if merge:
                # Merge: only update if newer
                cursor.execute('''
                    INSERT INTO items (upc, description, additional_info, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(upc) DO UPDATE SET
                        description = CASE 
                            WHEN excluded.updated_at > items.updated_at 
                            THEN excluded.description 
                            ELSE items.description 
                        END,
                        additional_info = CASE 
                            WHEN excluded.updated_at > items.updated_at 
                            THEN excluded.additional_info 
                            ELSE items.additional_info 
                        END,
                        updated_at = CASE 
                            WHEN excluded.updated_at > items.updated_at 
                            THEN excluded.updated_at 
                            ELSE items.updated_at 
                        END
                ''', (item['upc'], item['description'], item['additional_info'], 
                      item['created_at'], item['updated_at']))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO items (upc, description, additional_info, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (item['upc'], item['description'], item['additional_info'], 
                      item['created_at'], item['updated_at']))
        
        # Import inventory
        with open(import_dir / 'inventory.json', 'r') as f:
            inventory = json.load(f)
        
        for inv in inventory:
            if merge:
                # For merge, add quantities
                cursor.execute('''
                    INSERT INTO inventory (item_upc, location_id, quantity, last_scanned)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(item_upc, location_id) DO UPDATE SET
                        quantity = inventory.quantity + excluded.quantity,
                        last_scanned = CASE 
                            WHEN excluded.last_scanned > inventory.last_scanned 
                            THEN excluded.last_scanned 
                            ELSE inventory.last_scanned 
                        END
                ''', (inv['item_upc'], inv['location_id'], inv['quantity'], inv['last_scanned']))
            else:
                # Replace mode
                cursor.execute('''
                    INSERT OR REPLACE INTO inventory (item_upc, location_id, quantity, last_scanned)
                    VALUES (?, ?, ?, ?)
                ''', (inv['item_upc'], inv['location_id'], inv['quantity'], inv['last_scanned']))
        
        # Import scan history
        with open(import_dir / 'scan_history.json', 'r') as f:
            scan_history = json.load(f)
        
        for scan in scan_history:
            cursor.execute('''
                INSERT INTO scan_history (item_upc, location_id, action, quantity_change, scanned_at, workstation_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (scan['item_upc'], scan['location_id'], scan['action'], 
                  scan['quantity_change'], scan['scanned_at'], scan['workstation_id']))
        
        self.conn.commit()
        
        print(f"Import completed:")
        print(f"- Locations: {len(locations)}")
        print(f"- Items: {len(items)}")
        print(f"- Inventory entries: {len(inventory)}")
        print(f"- Scan history: {len(scan_history)}")
    
    def create_master_db(self, source_dirs: list, output_db: str) -> None:
        """Create a master database from multiple workstation exports"""
        # Create new master database
        if os.path.exists(output_db):
            backup_name = f"{output_db}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(output_db, backup_name)
            print(f"Backed up existing database to {backup_name}")
        
        # Initialize new database
        from inventory_scanner import InventoryDatabase
        master_db = InventoryDatabase(output_db)
        master_db.close()
        
        # Create sync instance for master
        master_sync = InventorySync(output_db)
        
        # Import all source directories
        for source_dir in source_dirs:
            print(f"\nImporting from {source_dir}...")
            try:
                master_sync.import_data(source_dir, merge=True)
            except Exception as e:
                print(f"Error importing {source_dir}: {e}")
        
        master_sync.close()
        print(f"\nMaster database created at {output_db}")
    
    def generate_report(self, output_file: str = "inventory_report.txt") -> None:
        """Generate a summary report of the inventory"""
        cursor = self.conn.cursor()
        
        with open(output_file, 'w') as f:
            f.write("INVENTORY SUMMARY REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            # Total statistics
            cursor.execute('SELECT COUNT(*) as count FROM items')
            total_items = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM locations')
            total_locations = cursor.fetchone()['count']
            
            cursor.execute('SELECT SUM(quantity) as total FROM inventory')
            total_quantity = cursor.fetchone()['total'] or 0
            
            f.write(f"Total Unique Items: {total_items}\n")
            f.write(f"Total Locations: {total_locations}\n")
            f.write(f"Total Quantity in Stock: {total_quantity}\n\n")
            
            # Items by location
            f.write("INVENTORY BY LOCATION\n")
            f.write("-" * 60 + "\n")
            
            cursor.execute('''
                SELECT l.name, COUNT(DISTINCT inv.item_upc) as items, SUM(inv.quantity) as qty
                FROM locations l
                LEFT JOIN inventory inv ON l.id = inv.location_id
                GROUP BY l.id, l.name
                ORDER BY l.name
            ''')
            
            for row in cursor.fetchall():
                f.write(f"\n{row['name']}:\n")
                f.write(f"  Unique Items: {row['items'] or 0}\n")
                f.write(f"  Total Quantity: {row['qty'] or 0}\n")
            
            # Top items by quantity
            f.write("\n\nTOP 20 ITEMS BY QUANTITY\n")
            f.write("-" * 60 + "\n")
            
            cursor.execute('''
                SELECT i.upc, i.description, SUM(inv.quantity) as total_qty
                FROM items i
                JOIN inventory inv ON i.upc = inv.item_upc
                GROUP BY i.upc
                ORDER BY total_qty DESC
                LIMIT 20
            ''')
            
            for row in cursor.fetchall():
                desc = row['description'] or 'No description'
                f.write(f"{row['upc']}: {desc[:40]} - Qty: {row['total_qty']}\n")
        
        print(f"Report generated: {output_file}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Command line interface for sync utility"""
    parser = argparse.ArgumentParser(description='Inventory Sync Utility')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export inventory data')
    export_parser.add_argument('path', help='Export directory path')
    export_parser.add_argument('--since', help='Export changes since date (YYYY-MM-DD)')
    export_parser.add_argument('--db', default='inventory.db', help='Database file')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import inventory data')
    import_parser.add_argument('path', help='Import directory path')
    import_parser.add_argument('--merge', action='store_true', help='Merge data instead of replace')
    import_parser.add_argument('--db', default='inventory.db', help='Database file')
    
    # Master command
    master_parser = subparsers.add_parser('master', help='Create master database')
    master_parser.add_argument('sources', nargs='+', help='Source export directories')
    master_parser.add_argument('-o', '--output', default='master_inventory.db', help='Output database file')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate inventory report')
    report_parser.add_argument('-o', '--output', default='inventory_report.txt', help='Output report file')
    report_parser.add_argument('--db', default='inventory.db', help='Database file')
    
    args = parser.parse_args()
    
    if args.command == 'export':
        sync = InventorySync(args.db)
        sync.export_data(args.path, args.since)
        sync.close()
    
    elif args.command == 'import':
        sync = InventorySync(args.db)
        sync.import_data(args.path, args.merge)
        sync.close()
    
    elif args.command == 'master':
        sync = InventorySync()
        sync.create_master_db(args.sources, args.output)
    
    elif args.command == 'report':
        sync = InventorySync(args.db)
        sync.generate_report(args.output)
        sync.close()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()