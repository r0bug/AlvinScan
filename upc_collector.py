#!/usr/bin/env python3
"""Quick UPC Collector - Gather test barcodes"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

class UPCCollector(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("UPC Collector")
        self.geometry("500x400")

        # Output file
        self.output_file = Path(__file__).parent / "collected_upcs.txt"
        self.upcs = []

        # Load existing
        if self.output_file.exists():
            self.upcs = [line.strip() for line in self.output_file.read_text().splitlines() if line.strip()]

        self.setup_ui()

    def setup_ui(self):
        # Scan entry
        scan_frame = ttk.Frame(self, padding=10)
        scan_frame.pack(fill=tk.X)

        ttk.Label(scan_frame, text="Scan UPC:", font=('TkDefaultFont', 12)).pack(side=tk.LEFT)

        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(scan_frame, textvariable=self.entry_var, width=30, font=('TkDefaultFont', 14))
        self.entry.pack(side=tk.LEFT, padx=10)
        self.entry.focus()
        self.entry.bind('<Return>', lambda e: self.add_upc())

        # Count label
        self.count_var = tk.StringVar(value=f"Collected: {len(self.upcs)}")
        ttk.Label(self, textvariable=self.count_var, font=('TkDefaultFont', 14, 'bold')).pack(pady=10)

        # List
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.listbox = tk.Listbox(list_frame, font=('TkDefaultFont', 11))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load existing into listbox
        for upc in self.upcs:
            self.listbox.insert(tk.END, upc)
        self.listbox.see(tk.END)

        # Buttons
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save & Exit", command=self.save_and_exit).pack(side=tk.RIGHT, padx=5)

        # Status
        self.status_var = tk.StringVar(value=f"Saving to: {self.output_file}")
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(pady=5)

    def add_upc(self):
        upc = self.entry_var.get().strip()
        if upc:
            self.upcs.append(upc)
            self.listbox.insert(tk.END, upc)
            self.listbox.see(tk.END)
            self.entry_var.set("")
            self.count_var.set(f"Collected: {len(self.upcs)}")
            self.save()

    def delete_selected(self):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.listbox.delete(idx)
            del self.upcs[idx]
            self.count_var.set(f"Collected: {len(self.upcs)}")
            self.save()

    def clear_all(self):
        if messagebox.askyesno("Confirm", "Clear all collected UPCs?"):
            self.upcs = []
            self.listbox.delete(0, tk.END)
            self.count_var.set(f"Collected: {len(self.upcs)}")
            self.save()

    def save(self):
        self.output_file.write_text('\n'.join(self.upcs))

    def save_and_exit(self):
        self.save()
        self.destroy()

if __name__ == "__main__":
    app = UPCCollector()
    app.mainloop()
