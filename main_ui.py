import tkinter as tk

class MainUI:
    def is_selected(self):
        """
        Return the currently selected paragraph frame, or None if nothing is selected.
        """
        return self._selected_frame
    x1 = 15  # Class attribute for overview frame x position
    x2 = 365
    x3 = 565

    y1 = 15
    y2 = 65
    y3 = 115

    field_width = 30


    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Main UI")
        self.root.geometry("865x700")

        # Overview region frame using place for x position
        self.overview_frame = tk.Frame(self.root, width=300, height=670)
        self.overview_frame.place(x=self.x1, y=self.y1, width=300, height=670)
        self.overview_frame.pack_propagate(True)

        # Simple container for paragraph frames (no scroll)
        self.inner_frame = tk.Frame(self.overview_frame, background="#f6f6f6", bd=2, relief=tk.GROOVE)
        self.inner_frame.pack(fill=tk.BOTH, expand=True)

        # Add a top spacer inside the paragraph frames container
        self.top_spacer = tk.Frame(self.inner_frame, height=4, bg="#f6f6f6")
        self.top_spacer.pack(fill=tk.X)

        self._paragraph_frames = []
        self._selected_frame = None
        self._selected_alias = None  # Remember selected interface alias

        # Add labeled entry fields at specified positions
        self.ip_label = tk.Label(self.root, text="IP Address:")
        self.ip_label.place(x=self.x2, y=self.y1)
        self.ip_entry = tk.Entry(self.root, width=self.field_width)
        self.ip_entry.place(x=self.x2, y=self.y1+20)

        self.netmask_label = tk.Label(self.root, text="Netmask:")
        self.netmask_label.place(x=self.x3, y=self.y1)
        self.netmask_entry = tk.Entry(self.root, width=self.field_width)
        self.netmask_entry.place(x=self.x3, y=self.y1+20)

        self.gateway_label = tk.Label(self.root, text="Gateway:")
        self.gateway_label.place(x=self.x2, y=self.y2)
        self.gateway_entry = tk.Entry(self.root, width=self.field_width)
        self.gateway_entry.place(x=self.x2, y=self.y2+20)

        self.dns1_label = tk.Label(self.root, text="DNS 1:")
        self.dns1_label.place(x=self.x2, y=self.y3)
        self.dns1_entry = tk.Entry(self.root, width=self.field_width)
        self.dns1_entry.place(x=self.x2, y=self.y3+20)

        self.dns2_label = tk.Label(self.root, text="DNS 2:")
        self.dns2_label.place(x=self.x3, y=self.y3)
        self.dns2_entry = tk.Entry(self.root, width=self.field_width)
        self.dns2_entry.place(x=self.x3, y=self.y3+20)

        # Info panel for selected interface
        self.info_panel = tk.Frame(self.root, bg="#e0e0e0", bd=2, relief=tk.SUNKEN)
        self.info_panel.place(x=415, y=400, width=340, height=200)

        self.info_label = tk.Label(self.info_panel, text="", bg="#e0e0e0", anchor="nw", justify="left")
        self.info_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Warning/info label at the bottom (initially hidden)
        self.extra_info = tk.Label(
            self.root,
            text="",
            fg="#b22222",  # dark red for warning
            bg="#f0f0f0",
            anchor="w",
            justify="left",
            wraplength=700  # <-- Set wraplength to desired width in pixels
        )
        self.extra_info.place(x=self.x2, y=570, width=770, height=30)
        self.extra_info.place_forget()  # Hide by default

        # Add CFG button (place it wherever you want, here next to IP Address label)
        self.cfg_button = tk.Button(self.root, text="Configure Interface")
        self.cfg_button.place(x=self.x2 + 150, y=250, width=150)  # Adjust x/y as needed

    def insert_iface_frame(self, info, iface_info=None, important=False):
        """
        Insert a paragraph (IP info chunk) as a selectable Frame in the overview_frame.
        info: str (should be a full paragraph for one interface)
        iface_info: the data object for this interface
        important: bool (optional, can highlight differently)
        """
        bg_color = "#ffffff" if important else "#e0e0e0"
        fg_color = "#000000" if important else "#888888"
        frame = tk.Frame(self.inner_frame, bd=2, relief=tk.RIDGE, background=bg_color)
        label = tk.Label(frame, text=info, justify=tk.LEFT, anchor="w", background=bg_color, foreground=fg_color)
        label.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        frame.pack(fill=tk.X, padx=8, pady=4)
        frame._original_bg = bg_color
        label._original_bg = bg_color
        self._paragraph_frames.append(frame)

        # Attach the iface_info object to the frame
        frame.iface_info = iface_info

        def on_select(event, f=frame):
            self._select_frame(f)
            self.update_info(f)
        frame.bind("<Button-1>", on_select, add="+")
        label.bind("<Button-1>", on_select, add="+")

        return frame

    def _select_frame(self, frame):
        if self._selected_frame:
            # Only try to configure if the widget still exists
            if self._selected_frame.winfo_exists():
                orig_bg = getattr(self._selected_frame, '_original_bg', "#ffffff")
                self._selected_frame.configure(background=orig_bg)
                for child in self._selected_frame.winfo_children():
                    child_orig_bg = getattr(child, '_original_bg', orig_bg)
                    child.configure(background=child_orig_bg)
        frame.configure(background="#cce6ff")
        for child in frame.winfo_children():
            child.configure(background="#cce6ff")
        self._selected_frame = frame
        # Remember the alias of the selected interface
        iface = getattr(frame, 'iface_info', None)
        if iface:
            self._selected_alias = iface.name
    def restore_selection(self):
        """Restore selection to the frame with the remembered alias, if it exists."""
        if self._selected_alias:
            for frame in self._paragraph_frames:
                iface = getattr(frame, 'iface_info', None)
                if iface and iface.name == self._selected_alias:
                    self._select_frame(frame)
                    self.update_info(frame)
                    break

    def toggle_bottom_info(self, show=False, text=""):
        """Show or hide the bottom info/warning label."""
        if show:
            self.extra_info.config(text=text)
            self.extra_info.place(x=self.x2-30, y=640, width=700, height=60)
        else:
            self.extra_info.place_forget()

    def update_info(self, frame):
        """Populate the info fields and info panel using the iface_info attached to the frame."""
        iface = getattr(frame, 'iface_info', None)
        if iface:
            # Set the entry fields
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, iface.ipv4[0].address if iface.ipv4 else '')
            self.netmask_entry.delete(0, tk.END)
            self.netmask_entry.insert(0, iface.ipv4[0].netmask if iface.ipv4 else '')
            self.gateway_entry.delete(0, tk.END)
            self.gateway_entry.insert(0, iface.gateway or '')  # Placeholder
            self.dns1_entry.delete(0, tk.END)
            self.dns1_entry.insert(0, iface.dns1 or '')     # Placeholder
            self.dns2_entry.delete(0, tk.END)
            self.dns2_entry.insert(0, iface.dns2 or '')     # Placeholder

            # Set the info panel with all relevant iface data
            label_width = 8
            info_lines = [
                f"{'Alias:'.ljust(label_width)} {iface.name}",
                f"{'MAC:'.ljust(label_width)} {iface.mac or ''}",
                f"{'IP:'.ljust(label_width)} {iface.ipv4[0].address if iface.ipv4 else ''}",
                f"{'Netmask:'.ljust(label_width)} {iface.ipv4[0].netmask if iface.ipv4 else ''}",
                f"{'Gateway:'.ljust(label_width)} {iface.gateway or ''}",
                f"{'DNS1:'.ljust(label_width)} {iface.dns1 or ''}",
                f"{'DNS2:'.ljust(label_width)} {iface.dns2 or ''}"
            ]
            self.info_label.config(font=('Courier', 10), text="\n".join(info_lines))

            # Show/hide bottom info label if link-local present
            has_link_local = iface.flags and "link-local" in iface.flags
            if has_link_local:
                self.toggle_bottom_info(
                    show=True,
                    text=(
                        "Notice: This interface has a link-local (APIPA) address (169.254.x.x).\n"
                        "A link-local address is automatically assigned when DHCP fails.\n"
                        "When you set a static IP with this application, any link-local address will be removed.\n"
                    )
                )
            else:
                self.toggle_bottom_info(show=False)

    def set_cfg_command(self, func):
        """Set the command (callback) for the CFG button."""
        self.cfg_button.config(command=func)

    def run(self):
        self.root.mainloop()
