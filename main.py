
# --- Elevation check and relaunch as admin if needed ---
import sys
import os
import ctypes
if os.name == 'nt':
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False
    if not is_admin:
        # Relaunch as admin
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

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

    # Restore selection if possible
    if hasattr(ui, 'restore_selection'):
        ui.restore_selection()


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
    """Convert dotted netmask to prefix length (e.g., 255.255.255.0 -> 24).
    Took me weeks to learn how to do this back in the day. one line lol"""
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
    dns = ui.dns_entry.get().strip() if hasattr(ui, 'dns_entry') else ''

    if not ip or not netmask:
        # Optionally show an error to the user
        return

    prefixlen = netmask_to_CIDR(netmask)

    # Try PowerShell first (Windows 8/10/11)

    try:
        # Remove existing gateway if it differs from the UI value
        if gateway and iface.gateway and gateway != iface.gateway:
            remove_gw_cmd = [
                "powershell", "-Command",
                f"Get-NetIPAddress -InterfaceAlias '{iface_name}' -AddressFamily IPv4 | Where-Object {{$_.DefaultGateway -eq '{iface.gateway}'}} | Remove-NetIPAddress -Confirm:$false"
            ]
            print(f"Removing old gateway: {remove_gw_cmd}")
            subprocess.run(remove_gw_cmd, capture_output=True, check=True)

        # Remove all existing IPv4 addresses (as before)
        remove_cmd = [
            "powershell", "-Command",
            f"Get-NetIPAddress -InterfaceAlias '{iface_name}' -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false"
        ]
        subprocess.run(remove_cmd, capture_output=True, check=True)

        # Set new IP and gateway
        set_cmd = [
            "powershell", "-Command",
            f"New-NetIPAddress -InterfaceAlias '{iface_name}' -IPAddress {ip} -PrefixLength {prefixlen}"
        ]
        if gateway:
            set_cmd[-1] += f" -DefaultGateway {gateway}"
        print(f"Setting new IP/gateway: {set_cmd}")
        subprocess.run(set_cmd, capture_output=True, check=True)

        # Set DNS if provided
        if dns:
            # Accept comma or space separated DNS entries
            dns_servers = [d.strip() for d in dns.replace(';',',').replace(' ', ',').split(',') if d.strip()]
            if dns_servers:
                dns_cmd = [
                    "powershell", "-Command",
                    f"Set-DnsClientServerAddress -InterfaceAlias '{iface_name}' -ServerAddresses {','.join([f'\"{d}\"' for d in dns_servers])}"
                ]
                print(f"Setting DNS: {dns_cmd}")
                subprocess.run(dns_cmd, capture_output=True, check=True)
        return
    except Exception as e:
        print(f"Error setting IP/gateway/DNS: {e}")
        pass  # Fallback to netsh

    # Fallback to netsh I have no idea what support looks like for Windows 7 and older, I honestly dont know if our primary attempt will work all the time.
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

def new_button(ui):
    print("New button clicked")

if __name__ == "__main__":
    ui = MainUI()

    # Set the CFG button to use set_ip_from_ui as its callback
    ui.set_cfg_command(lambda: new_button(ui))

    # Schedule the polling thread to start after the mainloop is running
    def start_polling():
        t = threading.Thread(target=poll_interfaces, args=(ui,), daemon=True)
        t.start()
    ui.root.after(100, start_polling)
    ui.run()
