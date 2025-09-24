import tkinter as tk
from tkinter import font

class MainUI:
    # --- Class attributes ---
    main_width = 650
    main_height = 700
    overview_frame_width = 250
    overview_frame_height = main_height - 20

    field_width = 25
    field_width_pixels = field_width * 7  # Approximate pixel width (7 pixels per character) for default font

    x1 = 10  # Class attribute for overview frame x position
    x2 = x1 + overview_frame_width + 20
    x3 = main_width - field_width_pixels

    y1 = 10
    y2 = 65
    y3 = 115

    # --- Initialization ---
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Alex's IP Changer: Version 2.0")
        self.root.geometry(f"{self.main_width}x{self.main_height}")

        # Overview region frame using place for x position
        self.overview_frame = tk.Frame(self.root, width=self.overview_frame_width, height=self.overview_frame_height)
        self.overview_frame.place(x=self.x1, y=self.y1, width=self.overview_frame_width, height=self.overview_frame_height)
        self.overview_frame.pack_propagate(True)

        # Scrollable container for paragraph frames
        self.canvas = tk.Canvas(self.overview_frame, background="#f6f6f6", bd=2, relief=tk.GROOVE, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.overview_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.inner_frame = tk.Frame(self.canvas, background="#f6f6f6")
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        def _on_frame_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.inner_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.inner_frame_id, width=event.width)
        self.canvas.bind("<Configure>", _on_canvas_configure)

        # Optional: enable mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

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
        self.info_panel.place(x=self.x2, y=300, width=self.main_width - self.x2 - 20, height=142)

        self.info_label = tk.Label(self.info_panel, text="", bg="#e0e0e0", anchor="nw", justify="left")
        self.info_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add CFG button (place it wherever you want, here next to IP Address label)
        button_width = 150
        center_x = (self.main_width - self.x2 - 20) // 2
        button_x = self.x2 + center_x - (button_width // 2)
        self.cfg_button = tk.Button(self.root, text="Configure Interface")
        self.cfg_button.place(x=button_x, y=250, width=button_width)

        # Info button at the bottom right
        self.info_button = tk.Button(self.root, text="Info", command=self.show_info_window)
        self.info_button.place(x=self.main_width - 90, y=self.main_height - 40, width=80, height=30)  # Adjust x/y as needed

        self._on_select_callback = None
        self.info_window_open = False

    # --- Public methods ---

    def run(self):
        self.root.mainloop()

    def set_on_select_callback(self, func):
        self._on_select_callback = func

    def set_cfg_command(self, func):
        self.cfg_button.config(command=func)

    def set_info_panel(self, text):
        self.info_label.config(text=text)

    def is_selected(self):
        return self._selected_frame

    def restore_selection(self):
        if self._selected_alias:
            for frame in self._paragraph_frames:
                iface = getattr(frame, 'iface_info', None)
                if iface and iface.name == self._selected_alias:
                    self._select_frame(frame)
                    break

    def insert_iface_frame(self, info, iface_info=None):
        """
        Insert a paragraph (IP info chunk) as a selectable Frame in the overview_frame.
        info: str (should be a full paragraph for one interface)
        iface_info: the data object for this interface
        important: bool (optional, can highlight differently)
        """
        important = getattr(iface_info, "important", False)
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
            if self._on_select_callback:
                self._on_select_callback(f)
        frame.bind("<Button-1>", on_select, add="+")
        label.bind("<Button-1>", on_select, add="+")

        return frame

    def create_iface_frame(self, iface):
        ipv4_str = ', '.join(f.address for f in iface.ipv4) if iface.ipv4 else 'N/A'
        netmask_str = ', '.join(f.netmask or 'N/A' for f in iface.ipv4) if iface.ipv4 else 'N/A'
        ipv6_str = ', '.join(f.address for f in iface.ipv6) if iface.ipv6 else 'N/A'
        mac_str = iface.mac if iface.mac else 'N/A'
        linklocal_str = " (link local)" if getattr(iface, "linklocal", False) else ""
        paragraph = (
            f"Interface: {iface.name}\n"
            f"  IPv4: {ipv4_str}{linklocal_str}\n"
            f"  Netmask: {netmask_str}\n"
            f"  IPv6: {ipv6_str}\n"
            f"  MAC: {mac_str}\n"
        )
        frame = self.insert_iface_frame(paragraph, iface_info=iface)
        frame.iface_info = iface
        return frame

    def refresh_ifaces(self, iface_list):
        """Redraw all interface frames from a list of iface objects."""
        for frame in list(self._paragraph_frames):
            frame.destroy()
        self._paragraph_frames.clear()
        for iface in iface_list:
            self.create_iface_frame(iface)
        if hasattr(self, 'restore_selection'):
            self.restore_selection()

    def refresh_entries(self, iface):
        """Populate the info fields and info panel using the iface_info attached to the frame."""
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

    def refresh_status(self, iface, status):
        """Update the info panel from an iface object."""
        if status:
            flap_conversion = {0: "Down", 1: "Up"}
            duplex_conversion = {0: "Unknown", 1: "Half-Duplex", 2: "Full-Duplex"}
            info_text = (
                f"Status for {iface.name}:\n"
                f"  State: {flap_conversion.get(status.isup, 'No value returned')}\n"
                f"  Speed: {status.speed} Mbps\n"
                f"  Duplex: {duplex_conversion.get(status.duplex, 'No value returned')}\n"
                f"  DHCP: {'Enabled' if getattr(iface, 'dhcp', False) else 'Disabled'}\n"
            )
            self.set_info_panel(info_text)
        else:
            self.set_info_panel(f"No status found for {iface.name}.")

    # --- Private methods ---

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

    def set_snake_callback(self, func):
        """Set the callback for the Snake button in the info window."""
        self._snake_callback = func

    def show_info_window(self):
        if self.info_window_open:
            return  # Already open, do nothing

        self.info_window_open = True
        info_win = tk.Toplevel(self.root)
        info_win.title("Information")
        info_window_width = 400
        info_window_height = 500  # Increased to fit the button
        info_win.geometry(f"{info_window_width}x{info_window_height}")  # Adjust size as needed

        bold = font.Font(size=10, weight="bold")
        APIPA_y = 275
        APIPA_x = 30

        # Bold (link-local)
        linklocal_label = tk.Label(info_win, text="(link-local)", font=bold, justify="left", anchor="nw")
        linklocal_label.place(x=APIPA_x, y=APIPA_y)

        # The rest of the APIPA text
        APIPA_text = (
            "Indicates an interface has a link-local address (169.254.x.x). "
            "When you set an IP with this application any link-local address "
            "will be removed. "
            "\n"
            "\n"
            "Link-local (APIPA) addresses are automatically assigned by "
            "Windows when DHCP fails, or the interface is misconfigured, "
            "down, or disconnected."
        )
        APIPA_label = tk.Label(info_win, text=APIPA_text, wraplength=info_window_width - 2 * APIPA_x, justify="left", anchor="nw")
        APIPA_label.place(x=APIPA_x, y=APIPA_y + 20)

        # CIDR to Netmask table
        cidr_table = [
            ("/8",   " 255.0.0.0"),
            ("/16",  " 255.255.0.0"),
            ("/24",  " 255.255.255.0"),
            ("/25",  " 255.255.255.128"),
            ("/26",  " 255.255.255.192"),
            ("/27",  " 255.255.255.224"),
            ("/28",  " 255.255.255.240"),
            ("/29",  " 255.255.255.248"),
            ("/30",  " 255.255.255.252"),
            ("/32",  " 255.255.255.255"),
        ]

        table_font = font.Font(info_win, family="Courier", size=10)
        longest_row = max([f"{cidr:<5}  {netmask}" for cidr, netmask in cidr_table], key=len)
        table_width = table_font.measure(longest_row)
        CIDR_table_x = (info_window_width - table_width) // 2

        table_header = tk.Label(info_win, text="CIDR    Netmask", font=("consolas", 10, "bold"), anchor="w", justify="center")
        table_header.place(x=CIDR_table_x, y=10)

        for i, (cidr, netmask) in enumerate(cidr_table):
            row = f"{cidr:<5}  {netmask}"
            row_label = tk.Label(info_win, text=row, font=("consolas", 10), anchor="w", justify="center")
            row_label.place(x=CIDR_table_x, y=40 + i*20)

        # --- Snake Button ---
        snake_btn = tk.Button(info_win, text="Snake", command=lambda: self._snake_callback() if hasattr(self, "_snake_callback") and self._snake_callback else None)
        snake_btn.place(x=(info_window_width - 100)//2, y=450, width=100, height=30)

        def on_close():
            self.info_window_open = False
            info_win.destroy()

        info_win.protocol("WM_DELETE_WINDOW", on_close)
