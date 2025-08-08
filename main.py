from main_ui import MainUI
from test import Interfaces
import threading
import time
import subprocess



def create_iface_paragraph(ui, iface):
    ipv4_str = ', '.join(f.address for f in iface.ipv4) if iface.ipv4 else 'N/A'
    netmask_str = ', '.join(f.netmask or 'N/A' for f in iface.ipv4) if iface.ipv4 else 'N/A'
    ipv6_str = ', '.join(f.address for f in iface.ipv6) if iface.ipv6 else 'N/A'
    mac_str = iface.mac if iface.mac else 'N/A'
    paragraph = (
        f"Interface: {iface.name}\n"
        f"  IPv4: {ipv4_str}\n"
        f"  Netmask: {netmask_str}\n"
        f"  IPv6: {ipv6_str}\n"
        f"  MAC: {mac_str}"
    )
    frame = ui.insert_iface_frame(paragraph, important=iface.important)
    frame.iface_info = iface
    return frame

def create_iface_paragraphs(ui):
    # Clear previous frames
    for frame in getattr(ui, '_paragraph_frames', []):
        frame.destroy()
    ui._paragraph_frames.clear()

    iface_infos = Interfaces.get_info()
    if not iface_infos:
        ui.insert_iface_frame("No interfaces found.", important=False)
        return

    for iface in iface_infos:
        create_iface_paragraph(ui, iface)


def poll_interfaces(ui, interval=2):
    prev_state = None
    while True:
        iface_infos = Interfaces.get_info()
        state = tuple(
            (
                iface.name,
                iface.mac,
                tuple((f.address, f.netmask) for f in iface.ipv4) if iface.ipv4 else None,
                tuple((f.address, f.netmask) for f in iface.ipv6) if iface.ipv6 else None,
            )
            for iface in iface_infos
        )
        if state != prev_state:
            def refresh_and_populate():
                create_iface_paragraphs(ui)
                try:
                    selected = ui.is_selected()
                    if selected:
                        ui.populate_fields_from_frame(selected)
                except Exception as e:
                    # Optionally log or print the error
                    pass
            ui.root.after(0, refresh_and_populate)
            prev_state = state
        time.sleep(interval)

def netmask_to_CIDR(netmask):
    """Convert dotted netmask to prefix length (e.g., 255.255.255.0 -> 24)."""
    return sum(bin(int(x)).count('1') for x in netmask.split('.'))

def set_ip_from_ui(ui):
    """Set the IP address of the selected interface using the entry fields in the UI."""
    selected_frame = ui.is_selected()
    if not selected_frame or not hasattr(selected_frame, "iface_info"):
        return  # No interface selected

    iface = selected_frame.iface_info
    iface_name = iface.name

    ip = ui.ip_entry.get().strip()
    netmask = ui.netmask_entry.get().strip()
    gateway = ui.gateway_entry.get().strip()

    if not ip or not netmask:
        # Optionally show an error to the user
        return

    prefixlen = netmask_to_CIDR(netmask)

    # Try PowerShell first (Windows 8/10/11)
    try:
        # Remove all existing IPv4 addresses
        remove_cmd = [
            "powershell", "-Command",
            f"Get-NetIPAddress -InterfaceAlias '{iface_name}' -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false"
        ]
        subprocess.run(remove_cmd, capture_output=True, check=True)

        # Set new IP
        set_cmd = [
            "powershell", "-Command",
            f"New-NetIPAddress -InterfaceAlias '{iface_name}' -IPAddress {ip} -PrefixLength {prefixlen}"
        ]
        if gateway:
            set_cmd[-1] += f" -DefaultGateway {gateway}"
        subprocess.run(set_cmd, capture_output=True, check=True)
        return
    except Exception:
        pass  # Fallback to netsh

    # Fallback to netsh (Windows 7 and older)
    try:
        cmd = [
            "netsh", "interface", "ip", "set", "address",
            f'name={iface_name}', "static", ip, netmask
        ]
        if gateway:
            cmd.append(gateway)
        subprocess.run(cmd, capture_output=True, check=True)
    except Exception as e:
        # Optionally show an error to the user
        print("Failed to set IP:", e)

if __name__ == "__main__":
    ui = MainUI()

    # Set the CFG button to use set_ip_from_ui as its callback
    ui.set_cfg_command(lambda: set_ip_from_ui(ui))

    # Schedule the polling thread to start after the mainloop is running
    def start_polling():
        t = threading.Thread(target=poll_interfaces, args=(ui,), daemon=True)
        t.start()
    ui.root.after(100, start_polling)
    ui.run()
