import tkinter as tk
from tkinter import font

root = tk.Tk()
field_width = 25
entry_font = font.Font(root=root, font=("TkDefaultFont", 10))  # Use your actual font if different
sample_text = "0" * field_width
pixel_width = entry_font.measure(sample_text)
print(f"Entry width for {field_width} chars: {pixel_width} pixels")
root.destroy()