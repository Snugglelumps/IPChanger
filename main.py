# --- Elevation check and relaunch as admin if needed ---
import sys
import os
import ctypes
# if os.name == 'nt':
#     try:
#         is_admin = ctypes.windll.shell32.IsUserAnAdmin()
#     except Exception:
#         is_admin = False
#     if not is_admin:
#         # Relaunch as admin
#         params = ' '.join([f'"{arg}"' for arg in sys.argv])
#         ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
#         sys.exit(0)

from main_ui import MainUI
from test import Interfaces
import threading
import time
import subprocess

prev_state = None

def detect_change(ui):
    global prev_state
    # Get current system state as a tuple of (name, mac, ipv4, ipv6)
    current_state = tuple(
        (
            iface.name,
            iface.mac,
            tuple((f.address, f.netmask) for f in iface.ipv4) if iface.ipv4 else None,
            tuple((f.address, f.netmask) for f in iface.ipv6) if iface.ipv6 else None,
        )
        for iface in Interfaces.get_info()
    )
    changed = current_state != prev_state
    prev_state = current_state
    return changed

def poll_interfaces(ui):
    system_ifaces = {iface.name: iface for iface in Interfaces.get_info()}

    def do_update():
        for frame in list(ui._paragraph_frames):
            frame.destroy()
        ui._paragraph_frames.clear()

        # Add frames for all current interfaces
        for iface in system_ifaces.values():
            frame = ui.create_iface_frame(iface)
            ui._paragraph_frames.append(frame)
        # Restore selection and update info panel if needed
        if hasattr(ui, 'restore_selection'):
            ui.restore_selection()

    ui.root.after(0, do_update)

def poll_interfaces_loop(ui, interval=0.5):
    while True:
        if detect_change(ui):
            poll_interfaces(ui)
        time.sleep(interval)

def netmask_to_CIDR(netmask):
    """Convert dotted netmask to prefix length (e.g., 255.255.255.0 -> 24).
    Took me weeks to learn how to do this back in the day. one line lol"""
    return sum(bin(int(x)).count('1') for x in netmask.split('.'))

def configure_interface(ui):
    pass

def populate_interface_status(ui, selected_frame=None): # I either give the selected frame here or do it in MainUI like the rest of on_select(). I have no idea what I'm doing.
    if selected_frame is None:
        selected_frame = ui.is_selected()
    if not selected_frame or not hasattr(selected_frame, "iface_info"):
        ui.set_info_panel("No interface selected.")
        return

    iface = selected_frame.iface_info
    status = Interfaces.get_status(iface.name)
    if status:
        flap_conversion = {0: "Down", 1: "Up"}
        duplex_conversion = {0: "Unknown", 1: "Half-Duplex", 2: "Full-Duplex"}
        info_text = (
            f"Status for {iface.name}:\n"
            f"  State: {flap_conversion.get(status.isup, 'No value returned')}\n"
            f"  Speed: {status.speed} Mbps\n"
            f"  Duplex: {duplex_conversion.get(status.duplex, 'No value returned')}\n"
            f"  MTU: {status.mtu}"
        )
        ui.set_info_panel(info_text)
    else:
        ui.set_info_panel(f"No status found for {iface.name}.")

def handle_ip_mask_change(iface_name, ui_ip, ui_mask, ui_gateway=None):
    """Set IP and mask (and optionally gateway) using PowerShell."""
    # Remove all existing IPv4 addresses
    remove_cmd = [
        "powershell", "-Command",
        f"Get-NetIPAddress -InterfaceAlias '{iface_name}' -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false"
    ]
    subprocess.run(remove_cmd, capture_output=True)

    # Set new IP and mask (and optionally gateway)
    set_cmd = [
        "powershell", "-Command",
        f"New-NetIPAddress -InterfaceAlias '{iface_name}' -IPAddress {ui_ip} -PrefixLength {netmask_to_CIDR(ui_mask)}"
    ]
    if ui_gateway:
        set_cmd[-1] += f" -DefaultGateway {ui_gateway}"
    subprocess.run(set_cmd, capture_output=True)
    #poll_interfaces(ui)

def handle_gateway_change(iface_name, ui_gateway):
    """Set gateway using PowerShell."""
    set_gw_cmd = [
        "powershell", "-Command",
        f"Set-NetIPAddress -InterfaceAlias '{iface_name}' -DefaultGateway {ui_gateway}"
    ]
    subprocess.run(set_gw_cmd, capture_output=True)
    #poll_interfaces(ui)

def handle_dns_change(iface_name, ui_dns1, ui_dns2=None):
    """Set DNS servers using PowerShell."""
    dns_servers = [ui_dns1] if ui_dns1 else []
    if ui_dns2:
        dns_servers.append(ui_dns2)
    servers_str = ",".join(f"'{dns}'" for dns in dns_servers)
    set_dns_cmd = [
        "powershell", "-Command",
        f"Set-DnsClientServerAddress -InterfaceAlias '{iface_name}' -ServerAddresses @({servers_str})"
    ]
    subprocess.run(set_dns_cmd, capture_output=True)
    #poll_interfaces(ui)

def new_button(ui):
    selected_frame = ui.is_selected()
    if not selected_frame or not hasattr(selected_frame, "iface_info"):
        ui.set_info_panel("No interface selected.")
        return

    iface = selected_frame.iface_info

    # Get current system info for this interface
    current_ifaces = {i.name: i for i in Interfaces.get_info()}
    current = current_ifaces.get(iface.name)
    if not current:
        ui.set_info_panel(f"Interface {iface.name} not found in system.")
        return

    # Gather current system values
    sys_ip = current.ipv4[0].address if current.ipv4 else None
    sys_mask = current.ipv4[0].netmask if current.ipv4 else None
    sys_gateway = getattr(current, "gateway", None)
    sys_dns1 = getattr(current, "dns1", None)
    sys_dns2 = getattr(current, "dns2", None)

    # Gather UI values (treat empty as None)
    def norm(val):
        return val.strip() if val and val.strip() else None

    ui_ip = norm(ui.ip_entry.get())
    ui_mask = norm(ui.netmask_entry.get())
    ui_gateway = norm(ui.gateway_entry.get())
    ui_dns1 = norm(ui.dns1_entry.get())
    ui_dns2 = norm(ui.dns2_entry.get())

    # Track what needs to be changed
    changed_ip_mask = (sys_ip != ui_ip or sys_mask != ui_mask)
    changed_gateway = (sys_gateway != ui_gateway)
    changed_dns = (sys_dns1 != ui_dns1 or sys_dns2 != ui_dns2)

    # Apply changes as needed
    if changed_ip_mask:
        handle_ip_mask_change(iface.name, ui_ip, ui_mask, ui_gateway if changed_gateway else None)
    elif changed_gateway:
        handle_gateway_change(iface.name, ui_gateway)
    if changed_dns:
        handle_dns_change(iface.name, ui_dns1, ui_dns2)

    # Build a report for the user
    diffs = []
    if changed_ip_mask:
        diffs.append("IP/Netmask changed.")
    if changed_gateway:
        diffs.append("Gateway changed.")
    if changed_dns:
        diffs.append("DNS changed.")
    if not (changed_ip_mask or changed_gateway or changed_dns):
        msg = "All settings match between system and UI."
    else:
        msg = "Applied changes:\n" + "\n".join(diffs)
    ui.set_info_panel(msg)

if __name__ == "__main__":
    ui = MainUI()
    print("UI initialized")  # Add this line
    ui.set_cfg_command(lambda: new_button(ui))
    ui.set_on_select_callback(lambda frame: populate_interface_status(ui, frame))

    # Schedule the polling thread to start after the mainloop is running
    def start_polling():
        t = threading.Thread(target=poll_interfaces_loop, args=(ui,), daemon=True)
        t.start()
    ui.root.after(100, start_polling)
    ui.run()
