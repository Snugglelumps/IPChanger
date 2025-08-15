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
from interfaceinfo import InterfaceInfo
import threading
import time
import subprocess

prev_state = None


'''
    The workflow here is we have a refresh_iface_frames() and detect_change(), both one-shot functions.
    poll_interfaces_loop() uses the detect_change() logic (bool) and wraps refresh_iface_frames() in a loop.
    i.e. if detect_change() returns True, then refresh_iface_frames() is called.
    This is lightweight enough for me to just re-draw all of the iface_frames each time refresh_iface_frames() is called.

    Additionally we manually call refresh_iface_frames() after any 'handler' function that modifies the interface state.
    This is found after the subprocess.run() for each 'handler'.
'''
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
        for iface in InterfaceInfo.get_info()
    )
    changed = current_state != prev_state
    prev_state = current_state
    return changed

def refresh_iface_frames(ui):
    system_ifaces = {iface.name: iface for iface in InterfaceInfo.get_info()}

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

def poll_interfaces_loop(ui, interval=2):
    while True:
        if detect_change(ui):
            refresh_iface_frames(ui)
        time.sleep(interval)

def netmask_to_CIDR(netmask):
    """Convert dotted netmask to prefix length (e.g., 255.255.255.0 -> 24).
    Took me weeks to learn how to do this back in the day. one line lol"""
    return sum(bin(int(x)).count('1') for x in netmask.split('.')) if netmask else 0

def configure_interface(ui):
    pass

def populate_interface_status(ui, selected_frame=None): # I either give the selected frame here or do it in MainUI like the rest of on_select(). I have no idea what I'm doing.
    if selected_frame is None:
        selected_frame = ui.is_selected()
    if not selected_frame or not hasattr(selected_frame, "iface_info"):
        ui.set_info_panel("No interface selected.")
        return

    iface = selected_frame.iface_info
    status = InterfaceInfo.get_status(iface.name)
    if status:
        flap_conversion = {0: "Down", 1: "Up"}
        duplex_conversion = {0: "Unknown", 1: "Half-Duplex", 2: "Full-Duplex"} # should probably do this at the dataclass level imo.
        info_text = (
            f"Status for {iface.name}:\n"
            f"  State: {flap_conversion.get(status.isup, 'No value returned')}\n"
            f"  Speed: {status.speed} Mbps\n"
            f"  Duplex: {duplex_conversion.get(status.duplex, 'No value returned')}\n"
            f"  MTU: {status.mtu}\n"
            f"  DNS 1 : {getattr(iface, 'dns1', 'N/A')}\n"
            f"  DNS 2 : {getattr(iface, 'dns2', 'N/A')}"
        )
        ui.set_info_panel(info_text)
    else:
        ui.set_info_panel(f"No status found for {iface.name}.")

def handle_ui_entries_syntax(ui):
    def is_valid_ipv4_syntax(val):
        val = val.strip()
        if not val:
            return True  # Allow blank (optional field)
        if val.count('.') != 3:
            return False
        if not all(c.isdigit() or c == '.' for c in val):
            return False
        if '..' in val:
            return False
        octets = val.split('.')
        if len(octets) != 4:
            return False
        return all(octet.isdigit() for octet in octets)
    
    errors = []
    fields = [
        ("IP Address", ui.ip_entry.get()),
        ("Netmask", ui.netmask_entry.get()),
        ("Gateway", ui.gateway_entry.get()),
        ("DNS 1", ui.dns1_entry.get()),
        ("DNS 2", ui.dns2_entry.get()),
    ]
    for label, val in fields:
        if val.strip() and not is_valid_ipv4_syntax(val):
            errors.append(f"{label} is not valid IPv4 syntax.")
    return errors

def _ps(cmd):
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True
    )

def handle_dhcp(iface_name):
    _ps(f'Set-NetIPInterface -InterfaceAlias "{iface_name}" -AddressFamily IPv4 -Dhcp Disabled; -Confirm:$false')

def _set_gateway(iface_name, gateway):
    # 1) Try the clean way: set the gateway on the interface's IPv4 config
    r = _ps(
        f'$a = Get-NetIPAddress -InterfaceAlias "{iface_name}" -AddressFamily IPv4 '
        f'-ErrorAction SilentlyContinue | Select -First 1; '
        f'if($a){{ try {{ $a | Set-NetIPAddress -DefaultGateway {gateway} -Confirm:$false -ErrorAction Stop }} '
        f'catch {{ "FALLBACK" }} }} else {{ "NOADDR" }}'
    )
    if "FALLBACK" in r.stdout or "NOADDR" in r.stdout or r.returncode != 0:
        # 2) Fallback: replace the default route for this interface (active + persistent)
        _ps(
            f'$idx = (Get-NetIPInterface -InterfaceAlias "{iface_name}" -AddressFamily IPv4).InterfaceIndex; '
            f'Get-NetRoute -InterfaceIndex $idx -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue '
            f'| Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue; '
            f'foreach($s in "ActiveStore","PersistentStore"){{ '
            f'New-NetRoute -InterfaceIndex $idx -DestinationPrefix "0.0.0.0/0" -NextHop {gateway} '
            f'-RouteMetric 1 -PolicyStore $s -Confirm:$false -ErrorAction SilentlyContinue }}'
        )

def _clear_gateway(iface_name):
    _ps(
        f'$idx = (Get-NetIPInterface -InterfaceAlias "{iface_name}" -AddressFamily IPv4).InterfaceIndex; '
        f'Get-NetRoute -InterfaceIndex $idx -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue '
        f'| Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue; '
        f'Get-NetRoute -InterfaceIndex $idx -DestinationPrefix "0.0.0.0/0" -PolicyStore PersistentStore -ErrorAction SilentlyContinue '
        f'| Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue'
    )

def set_static_ipv4(iface_name, ip, prefix_len):
    _ps(
        f'Set-NetIPInterface -InterfaceAlias "{iface_name}" -AddressFamily IPv4 -Dhcp Disabled; -Confirm:$false'
        f'Get-NetIPAddress -InterfaceAlias "{iface_name}" -AddressFamily IPv4 -ErrorAction SilentlyContinue '
        f'| Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue; '
        f'New-NetIPAddress -InterfaceAlias "{iface_name}" -AddressFamily IPv4 -IPAddress {ip} -PrefixLength {prefix_len}'
    )

def handle_ip_mask_change(iface_name, ui_ip, ui_mask, ui_gateway=None):
    set_static_ipv4(iface_name, ui_ip, netmask_to_CIDR(ui_mask))
    if ui_gateway:
        _set_gateway(iface_name, ui_gateway)
    else:
        _clear_gateway(iface_name)
    refresh_iface_frames(ui)

def handle_gateway_change(iface_name, ui_gateway):
    if ui_gateway:
        _set_gateway(iface_name, ui_gateway)   # set or replace on this iface only
    else:
        _clear_gateway(iface_name)             # remove only this iface’s default route

    refresh_iface_frames(ui)


def handle_dns_change(iface_name, ui_dns1, ui_dns2=None):
    """Set DNS servers using PowerShell."""
    if ui_dns1 or ui_dns2:
        dns_servers = [ui_dns1] if ui_dns1 else []
        if ui_dns2:
            dns_servers.append(ui_dns2)
        servers_str = ",".join(f"'{dns}'" for dns in dns_servers)
        _ps(f"Set-DnsClientServerAddress -InterfaceAlias '{iface_name}' -ServerAddresses @({servers_str})")

    if not ui_dns1 and not ui_dns2:
        _ps(f"Set-DnsClientServerAddress -InterfaceAlias '{iface_name}' -ResetServerAddresses")

    refresh_iface_frames(ui)

def new_button(ui):
    errors = handle_ui_entries_syntax(ui)
    if errors:
        ui.set_info_panel("\n".join(errors))
        return

    selected_frame = ui.is_selected()
    if not selected_frame or not hasattr(selected_frame, "iface_info"):
        ui.set_info_panel("No interface selected.")
        return

    iface = selected_frame.iface_info

    # handle_dhcp(iface.name)
    # Get current system info for this interface
    current_ifaces = {i.name: i for i in InterfaceInfo.get_info()}
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
        handle_ip_mask_change(iface.name, ui_ip, ui_mask)#, ui_gateway if changed_gateway else None)
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
