# Build InterfaceInfo objects from psutil.net_if_addrs()
from dataclasses import dataclass, field
from typing import List, Optional
import psutil


class Interfaces:
    @dataclass
    class IPv4Data:
        address: str
        netmask: Optional[str] = None

    @dataclass
    class IPv6Data:
        address: str
        netmask: Optional[str] = None

    @dataclass
    class Status:
        isup: bool
        speed: int
        duplex: int
        mtu: int

    @dataclass
    class Info:
        name: str
        mac: Optional[str]
        ipv4: Optional[List['Interfaces.IPv4Data']]
        ipv6: Optional[List['Interfaces.IPv6Data']]
        important: bool = True
        flags: List[str] = field(default_factory=list)  # <-- Add flags field

    @classmethod
    def get_info(cls):
        def is_link_local(ip):
            return ip.startswith("169.254.")

        interfaces = []
        addrs = psutil.net_if_addrs()
        for name, addr_list in addrs.items():
            mac = None
            ipv4s = []
            ipv6s = []
            for addr in addr_list:
                # MAC address family: psutil.AF_LINK (if available), else 17
                if hasattr(psutil, 'AF_LINK'):
                    mac_family = psutil.AF_LINK
                else:
                    mac_family = 17
                if addr.family == mac_family:
                    mac = addr.address
                elif addr.family == 2:  # AF_INET
                    ipv4s.append(cls.IPv4Data(address=addr.address, netmask=addr.netmask))
                elif addr.family == 23:  # AF_INET6
                    ipv6s.append(cls.IPv6Data(address=addr.address, netmask=addr.netmask))
            # Sort IPv4s: non-link-local first
            ipv4s.sort(key=lambda x: is_link_local(x.address))
            # Add flags
            flags = []
            if ipv4s:
                if any(is_link_local(ip.address) for ip in ipv4s):
                    flags.append("link-local")
                else:
                    flags.append("non-link-local")
                # You can add more logic here for "static", "dhcp", etc.
            important = cls._is_important(name, mac)
            iface = cls.Info(
                name=name,
                mac=mac,
                ipv4=ipv4s if ipv4s else None,
                ipv6=ipv6s if ipv6s else None,
                important=important,
                flags=flags
            )
            interfaces.append(iface)
        return interfaces

    @staticmethod
    def _is_important(name, mac) -> bool:
        name_lower = name.lower()
        # Exclude common non-physical adapters by name
        if mac and not any(x in name_lower for x in ["bluetooth", "vpn", "tunnel", "virtual", "wireless", "wi-fi", "wlan"]):
            return True
        return False

    @staticmethod
    def get_status(name: str) -> 'Interfaces.Status':
        stats = psutil.net_if_stats()
        stat = stats.get(name)
        if stat:
            return Interfaces.Status(
                isup=stat.isup,
                speed=stat.speed,
                duplex=stat.duplex,
                mtu=stat.mtu
            )
        else:
            return None