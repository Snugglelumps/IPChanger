
import psutil
import win32com.client
import socket
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class InterfaceInfo:
    iface: str
    adapter_type: int
    desc: str
    status: str
    speed: int
    ipv4: str
    netmask: str
    mac: str
    important: bool


class IPUtil:
    @staticmethod
    def get_interfaces() -> List[dict]:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        wmi_info = IPUtil._get_wmi_info()
        interfaces = []
        for iface, addr_list in addrs.items():
            if iface not in wmi_info:
                print(f"[DEBUG] Skipping '{iface}': not in WMI NetConnectionIDs")
                continue
            if iface not in stats:
                print(f"[DEBUG] Skipping '{iface}': not in psutil stats")
                continue
            adapter_type, desc = wmi_info[iface]
            mac, ipv4, netmask = IPUtil._get_addr_info(addr_list)
            if not mac:
                print(f"[DEBUG] Skipping '{iface}': no valid MAC address")
                continue
            important = IPUtil._is_important(adapter_type, desc)
            stat = stats[iface]
            status = 'Up' if stat.isup else 'Down'
            speed = stat.speed
            info = InterfaceInfo(
                iface=iface,
                adapter_type=adapter_type,
                desc=desc,
                important=important,
                status=status,
                speed=speed,
                ipv4=ipv4,
                netmask=netmask,
                mac=mac
            )
            print(f"[DEBUG] Added interface: {iface} ({desc})")
            interfaces.append(asdict(info))
        return interfaces

    @staticmethod
    def _is_important(adapter_type, desc) -> bool:
        desc_lower = desc.lower()
        # AdapterTypeID == 0 is Ethernet 802.3
        if adapter_type == 0 and not any(x in desc_lower for x in ["bluetooth", "vpn", "tunnel", "virtual", "wireless", "wi-fi", "wlan"]):
            return True
        return False

    @staticmethod
    def _get_wmi_info():
        wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        svc = wmi.ConnectServer('.', 'root\\cimv2')
        adapters = svc.ExecQuery("SELECT NetConnectionID, AdapterTypeID, Description FROM Win32_NetworkAdapter WHERE NetConnectionID IS NOT NULL")
        info = {}
        for adapter in adapters:
            info[str(adapter.NetConnectionID)] = (adapter.AdapterTypeID, str(adapter.Description))
        return info

    @staticmethod
    def _get_addr_info(addr_list):
        if hasattr(psutil, 'AF_LINK'):
            mac_family = psutil.AF_LINK
        else:
            mac_family = 17
        mac = None
        ipv4 = None
        netmask = None
        for addr in addr_list:
            if addr.family == mac_family:
                mac = addr.address
            elif addr.family == socket.AF_INET:
                ipv4 = addr.address
                netmask = addr.netmask
        if mac is not None and len(mac.split(":")) == 6:
            return mac, ipv4, netmask
        return None, None, None


print("\n[DEBUG] --- psutil.net_if_addrs() ---")
import pprint
pprint.pprint(psutil.net_if_addrs())

print("\n[DEBUG] --- psutil.net_if_stats() ---")
pprint.pprint(psutil.net_if_stats())

print("\n[DEBUG] --- WMI NetConnectionID Info ---")
wmi_info = IPUtil._get_wmi_info()
pprint.pprint(wmi_info)

print("\n[DEBUG] --- get_interfaces() result ---")
print(IPUtil.get_interfaces())