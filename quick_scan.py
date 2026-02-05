#!/usr/bin/env python3
"""Quick scan - just dump UPCs to file"""

import tkinter as tk
from pathlib import Path

output = Path(__file__).parent / "upcs.txt"

root = tk.Tk()
root.title(f"Quick Scan → {output.name}")
root.geometry("400x150")

var = tk.StringVar()
count = [sum(1 for _ in open(output)) if output.exists() else 0]

label = tk.Label(root, text=f"Scanned: {count[0]}", font=('Arial', 24))
label.pack(pady=20)

entry = tk.Entry(root, textvariable=var, font=('Arial', 18), width=25)
entry.pack()
entry.focus()

def scan(e):
    upc = var.get().strip()
    if upc:
        with open(output, 'a') as f:
            f.write(upc + '\n')
        count[0] += 1
        label.config(text=f"Scanned: {count[0]}")
        var.set("")

entry.bind('<Return>', scan)
root.mainloop()
