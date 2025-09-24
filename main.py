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
from interfacemanager import InterfaceInfo, ConfigureInterface
import threading
import time
from not_snake_game import SnakeGame
import tkinter as tk 

prev_state = None

def build_interface(ui, iface):
    """Create and return a ConfigureInterface instance with attributes set from the UI."""
    def norm(val):
        return val.strip() if val and val.strip() else None

    return ConfigureInterface(
        iface_name=iface.name,
        ip=norm(ui.ip_entry.get()),
        netmask=norm(ui.netmask_entry.get()),
        gateway=norm(ui.gateway_entry.get()),
        dns1=norm(ui.dns1_entry.get()),
        dns2=norm(ui.dns2_entry.get())
    )

def has_syntax_errors(interface):
    errors = interface.validate_syntax()
    if errors:
        ui.set_info_panel("Input error:\n" + "\n".join(errors))
        return True
    else:
        ui.set_info_panel("All fields are valid!")
        return False

def fade_in_info(ui, selected_frame=None):
    def worker():
        time.sleep(10)
        ui.root.after(0, lambda: update_ui(ui))
    threading.Thread(target=worker, daemon=True).start()

def cfg_button(ui):
    t0 = time.time()
    try:
        interface = build_interface(ui, ui.is_selected().iface_info)
        if has_syntax_errors(interface):
            return
        diffs = interface.iface_compare(ui.is_selected().iface_info)

        if not diffs:
            ui.set_info_panel("No changes detected.")
            fade_in_info(ui, ui.is_selected())
            return

        # Show what will be reconfigured
        diff_labels = (
            ('ip', "IP"),
            ('netmask', "Netmask"),
            ('gateway', "Gateway"),
            ('dns1', "DNS 1"),
            ('dns2', "DNS 2"),
        )
        changed = [f"{label}: {getattr(interface, field)}" for field, label in diff_labels if field in diffs]
        ui.set_info_panel("Reconfiguring " + ", ".join(changed) + ".")
        ui.root.update_idletasks()  # <-- Force redraw before blocking

        # Apply changes
        if any(field in diffs for field in ['ip', 'netmask', 'gateway']):
            interface._set_static()
            interface._clear_ip_mask_gw()
            interface._set_ip_mask_gw(interface.ip, interface.netmask, interface.gateway)
        if any(field in diffs for field in ['dns1', 'dns2']):
            interface._clear_dns()
            interface._set_dns(interface.dns1, interface.dns2)

        update_ui(ui)
        fade_in_info(ui, ui.is_selected())
        print(interface)
    except Exception as e:
        ui.set_info_panel(f"An error occurred:\n{e}")

    system_ifaces = {iface.name: iface for iface in InterfaceInfo.get_info()}

    def do_update():
        ui.refresh_ifaces(list(system_ifaces.values()))
        selected = ui.is_selected()
        if selected and hasattr(selected, "iface_info"):
            iface_name = selected.iface_info.name
            fresh_info = system_ifaces.get(iface_name)
            if fresh_info:
                ui.refresh_entries(fresh_info)
                ui.refresh_status(fresh_info, InterfaceInfo.get_status(fresh_info.name))
            else:
                ui.set_info_panel("No interface selected.")
        ui.set_info_panel(f"Configuration took {time.time() - t0:.2f} seconds")
    ui.root.after(0, do_update)

def update_ui(ui):
    iface_list = InterfaceInfo.get_info()
    ui.refresh_ifaces(iface_list)
    selected = ui.is_selected()
    if selected and hasattr(selected, "iface_info"):
        iface = next((i for i in iface_list if i.name == selected.iface_info.name), None)
        if iface:
            ui.refresh_entries(iface)
            ui.refresh_status(iface, InterfaceInfo.get_status(iface.name))

def open_snake():
    snake_win = tk.Toplevel(ui.root)
    snake_win.title("Snake")
    SnakeGame(snake_win)

if __name__ == "__main__":
    ui = MainUI()
    print("UI initialized")
    update_ui(ui)
    ui.set_cfg_command(lambda: (cfg_button(ui)))
    ui.set_on_select_callback(lambda frame: (
        ui.refresh_entries(frame.iface_info),
        ui.refresh_status(
            frame.iface_info,
            InterfaceInfo.get_status(frame.iface_info.name)
        )
    ))
    ui.set_snake_callback(open_snake)
    ui.run()
