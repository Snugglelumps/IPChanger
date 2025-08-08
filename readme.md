# Alex's IP Changer

A Windows desktop tool for viewing and managing your network interface IP addresses, built with Python and Tkinter.

---

## Key Design Principles

- **Transparency:**  
  All interfaces and their addresses are shown to the user. We **never filter** interfaces or IP addresses—if it's on your system, you'll see it.

- **Sorting, Not Filtering:**  
  Link-local (APIPA) addresses (e.g., `169.254.x.x`) are **sorted to the end** of each interface's address list, but never hidden. This helps you focus on the most relevant addresses while keeping all information visible.

- **Polling for Changes:**  
  The application uses a background polling loop to regularly check for changes in your system's network interfaces. This ensures the UI is always up-to-date, even if interfaces are added, removed, or reconfigured outside the app.

- **No OS Hooks or Filtering:**  
  We do **not** use Windows hooks, WMI event subscriptions, or any platform-specific event listeners. This keeps the app robust, portable, and compatible with PyInstaller for standalone builds.

- **Safe Updates:**  
  All UI updates are performed on the main thread using Tkinter's `after` method, ensuring thread safety and stability.

---

## User Experience

- **All Interfaces Shown:**  
  Every network interface detected by the system is displayed, including physical, virtual, VPN, and Bluetooth adapters.

- **Multiple Addresses Supported:**  
  Interfaces with multiple IP addresses (static, DHCP, link-local) are fully supported. You can view and select among all assigned addresses.

- **Link-Local Awareness:**  
  If an interface has a link-local address, a clear notice is shown explaining what it is and what will happen if you set a static IP (the link-local will be removed).

- **No Surprises:**  
  The app never hides or auto-removes addresses without your action. When you set a static IP, all other addresses (including link-local) are removed **only as part of your explicit change**.

---

## Technical Highlights

- **Interface Data Collection:**  
  Uses `psutil` to gather all interface and address information.
- **Sorting Logic:**  
  Link-local addresses are sorted last in the address list for each interface.
- **Polling Loop:**  
  Regularly checks for system-level changes and updates the UI accordingly.
- **UI Responsiveness:**  
  All UI changes are scheduled on the main thread for safety.
- **No Filtering:**  
  No interface or address is ever hidden from the user... that we know of.

---

## Why This Approach?

- **Maximum User Control:**  
  You always see the full picture of your network configuration.
- **Reliability:**  
  Polling is robust and works across all supported Windows versions, even when system events are unavailable.
- **Simplicity:**  
  No complex OS hooks or dependencies—just Python, Tkinter, and psutil.

---