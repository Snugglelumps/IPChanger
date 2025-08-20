# Build InterfaceInfo objects from psutil.net_if_addrs()
from dataclasses import dataclass, field
from typing import List, Optional
import psutil
import subprocess
import json
import ipaddress


class InterfaceInfo:
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
        dhcp: bool
        ipv4: Optional[List['InterfaceInfo.IPv4Data']]
        ipv6: Optional[List['InterfaceInfo.IPv6Data']]
        gateway: Optional[str] = None
        dns1: Optional[str] = None
        dns2: Optional[str] = None
        status: Optional[str] = None
        important: bool = True
        linklocal: bool = False  # <-- Add link-local flag

    @classmethod
    def get_info(cls):
        def is_link_local(ip):
            return ip.startswith("169.254.")

        # Use the batched info method
        info_map = cls.get_info_light()

        InterfaceInfo = []
        addrs = psutil.net_if_addrs()
        for name, addr_list in addrs.items():
            mac = None
            ipv4s = []
            ipv6s = []
            for addr in addr_list:
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
            ipv4s.sort(key=lambda x: is_link_local(x.address))

            important = cls._is_important(name, mac)
            linklocal = cls._is_linklocal(ipv4s[0]) if ipv4s else False

            # Get all info from the batched map
            iface_info = info_map.get(name, {})
            dhcp = iface_info.get("dhcp", False)
            dns_list = iface_info.get("dns", [])
            gateway = iface_info.get("gateway")
            dns1 = dns_list[0] if len(dns_list) > 0 else None
            dns2 = dns_list[1] if len(dns_list) > 1 else None

            stat = psutil.net_if_stats().get(name)
            status = 'Up' if stat and stat.isup else 'Down'

            iface = cls.Info(
                name=name,
                mac=mac,
                ipv4=ipv4s if ipv4s else None,
                ipv6=ipv6s if ipv6s else None,
                gateway=gateway,
                dns1=dns1,
                dns2=dns2,
                important=important,
                linklocal=linklocal,
                status=status,
                dhcp=dhcp
            )
            InterfaceInfo.append(iface)
        return InterfaceInfo

    @staticmethod
    def _is_important(name, mac) -> bool:
        name_lower = name.lower()
        # Exclude common non-physical adapters by name
        if mac and not any(x in name_lower for x in ["bluetooth", "vpn", "tunnel", "virtual", "wireless", "wi-fi", "wlan", "*"]):
            return True
        return False
    
    @staticmethod
    def _is_linklocal(ipv4: 'IPv4Data') -> bool:
        """Check if the given IPv4 address is link-local."""
        if ipv4.address.startswith("169.254."):
            return True
        return False

    @staticmethod
    def get_status(name: str) -> 'InterfaceInfo.Status':
        stats = psutil.net_if_stats()
        stat = stats.get(name)
        if stat:
            return InterfaceInfo.Status(
                isup=stat.isup,
                speed=stat.speed,
                duplex=stat.duplex,
                mtu=stat.mtu
            )
        else:
            return None

    @classmethod
    def get_change_signature(cls):
        """Return a lightweight tuple for each interface for fast change detection."""
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        sigs = []
        for name, addr_list in addrs.items():
            mac = None
            ipv4 = None
            for addr in addr_list:
                if hasattr(psutil, 'AF_LINK'):
                    mac_family = psutil.AF_LINK
                else:
                    mac_family = 17
                if addr.family == mac_family:
                    mac = addr.address
                elif addr.family == 2:  # AF_INET
                    if not ipv4:
                        ipv4 = (addr.address, addr.netmask)
            stat = stats.get(name)
            isup = stat.isup if stat else None
            sigs.append((name, mac, ipv4, isup))
        return tuple(sigs)

    @staticmethod
    def get_info_light():
        """
        Returns a dict mapping InterfaceAlias to a dict with keys: gateway, dns, dhcp.
        """
        ps_script = """
        $ifaces = Get-NetIPInterface -AddressFamily IPv4 | Select-Object InterfaceAlias, Dhcp
        $dns = Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses -and $_.ServerAddresses.Count -gt 0 } | Select-Object InterfaceAlias, @{Name='DNSServers';Expression={ $_.ServerAddresses -join ',' }}
        $gw = Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object InterfaceAlias, NextHop

        $result = @{}
        foreach ($iface in $ifaces) {
            $alias = $iface.InterfaceAlias
            $result[$alias] = @{
                dhcp = $iface.Dhcp
                dns = $null
                gateway = $null
            }
        }
        foreach ($d in $dns) {
            if ($result.ContainsKey($d.InterfaceAlias)) {
                $result[$d.InterfaceAlias].dns = $d.DNSServers
            }
        }
        foreach ($g in $gw) {
            if ($result.ContainsKey($g.InterfaceAlias)) {
                $result[$g.InterfaceAlias].gateway = $g.NextHop
            }
        }
        $result.GetEnumerator() | ForEach-Object {
            [PSCustomObject]@{
                InterfaceAlias = $_.Key
                Dhcp = $_.Value.dhcp
                DNSServers = $_.Value.dns
                Gateway = $_.Value.gateway
            }
        } | ConvertTo-Json
        """
        cmd = ["powershell", "-Command", ps_script]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(data, dict):
                data = [data]
            info_map = {}
            for entry in data:
                alias = entry.get("InterfaceAlias")
                if alias:
                    dhcp_val = entry.get("Dhcp")
                    if isinstance(dhcp_val, str):
                        dhcp = dhcp_val.lower() == "enabled"
                    elif isinstance(dhcp_val, bool):
                        dhcp = dhcp_val
                    elif isinstance(dhcp_val, int):
                        dhcp = bool(dhcp_val)
                    else:
                        dhcp = False

                    info_map[alias] = {
                        "dhcp": dhcp,
                        "dns": entry.get("DNSServers").split(",") if entry.get("DNSServers") else [],
                        "gateway": entry.get("Gateway")
                    }
            return info_map
        except Exception as e:
            print(f"[DEBUG] _batch_iface_info failed: {e}")
            return {}

class ConfigureInterface:
    def __init__(self, iface_name, ip, netmask, gateway, dns1, dns2):
        self.iface_name = iface_name
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway
        self.dns1 = dns1
        self.dns2 = dns2

    def _ps(self, cmd):
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True
        )

    def _clear_ip_mask_gw(self):
        self._ps(
            f"Get-NetIPAddress -InterfaceAlias '{self.iface_name}' -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false; "
            f"$idx = (Get-NetIPInterface -InterfaceAlias '{self.iface_name}' -AddressFamily IPv4).InterfaceIndex; "
            f"Get-NetRoute -InterfaceIndex $idx -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
            f"Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue"
        )

    def _clear_dns(self):
        self._ps(
            f"Set-DnsClientServerAddress -InterfaceAlias '{self.iface_name}' -Reset"
        )

    def _set_dhcp(self):
        # Check if already DHCP
        try:
            dhcp_cmd = [
                "powershell", "-Command",
                f"(Get-NetIPInterface -InterfaceAlias '{self.iface_name}' -AddressFamily IPv4).Dhcp"
            ]
            dhcp_result = subprocess.run(dhcp_cmd, capture_output=True, text=True, check=True)
            dhcp_status = dhcp_result.stdout.strip()
            if dhcp_status.lower() == "enabled":
                return  # Already DHCP, early exit
        except Exception:
            pass  # If check fails, continue to set

        self._ps(
            f"Set-NetIPInterface -InterfaceAlias '{self.iface_name}' -Dhcp Enabled; "
            f"Set-DnsClientServerAddress -InterfaceAlias '{self.iface_name}' -Reset"
        )

    def _set_static(self):
        # Check if already static (not DHCP)
        try:
            dhcp_cmd = [
                "powershell", "-Command",
                f"(Get-NetIPInterface -InterfaceAlias '{self.iface_name}' -AddressFamily IPv4).Dhcp"
            ]
            dhcp_result = subprocess.run(dhcp_cmd, capture_output=True, text=True, check=True)
            dhcp_status = dhcp_result.stdout.strip()
            if dhcp_status.lower() == "disabled":
                return  # Already static, early exit
        except Exception:
            pass  # If check fails, continue to set

        self._ps(
            f"Set-NetIPInterface -InterfaceAlias '{self.iface_name}' -Dhcp Disabled; "
            f"Set-DnsClientServerAddress -InterfaceAlias '{self.iface_name}' -Reset"
        )

    def _set_ip_mask_gw(self, ip, netmask, gateway=None):
        prefix_len = self.netmask_to_CIDR(netmask)
        cmd = (
            f"New-NetIPAddress -InterfaceAlias '{self.iface_name}' -IPAddress {ip} -PrefixLength {prefix_len}"
        )
        if gateway:
            cmd += f" -DefaultGateway {gateway}"
        self._ps(cmd)

    def _set_dns(self, dns1, dns2=None):
        servers = []
        for dns in (dns1, dns2):
            if dns and dns.strip() and self.is_valid_ipv4_syntax(dns):
                servers.append(dns.strip())
        if not servers:
            return  # No valid DNS servers to set
        servers_str = ",".join(f"'{s}'" for s in servers)
        cmd = f"Set-DnsClientServerAddress -InterfaceAlias '{self.iface_name}' -ServerAddresses @({servers_str})"
        self._ps(cmd)

    @staticmethod
    def is_valid_ipv4_syntax(val):
        val = val.strip() if val else ""
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

    def validate_syntax(self):
        errors = []
        fields = [
            ("IP Address", self.ip),
            ("Netmask", self.netmask),
            ("Gateway", self.gateway),
            ("DNS 1", self.dns1),
            ("DNS 2", self.dns2),
        ]
        for label, val in fields:
            if val and val.strip() and not self.is_valid_ipv4_syntax(val):
                errors.append(f"{label} is not valid IPv4 syntax.")

        # Check that gateway is in the same subnet as IP/mask
        if self.ip and self.netmask and self.gateway:
            try:
                ip_net = ipaddress.IPv4Network(f"{self.ip}/{self.netmask}", strict=False)
                gw_addr = ipaddress.IPv4Address(self.gateway)
                if gw_addr not in ip_net:
                    errors.append("Gateway is not in the same subnet as the IP address.")
            except Exception:
                errors.append("Failed to validate gateway subnet scope.")

        return errors

    @staticmethod
    def netmask_to_CIDR(netmask):
        """Convert dotted netmask to prefix length (e.g., 255.255.255.0 -> 24).
        Took me weeks to learn how to do this back in the day. one line lol"""
        return sum(bin(int(x)).count('1') for x in netmask.split('.')) if netmask else 0

    def iface_compare(self, iface_info):
        """
        Compare this instance's config to the given iface_info (InterfaceInfo.Info).
        Returns a dict of fields that differ: {field: (current, target)}
        """
        diffs = {}

        # Compare IP address (first IPv4 only)
        current_ip = self.ip
        iface_ip = iface_info.ipv4[0].address if iface_info.ipv4 and len(iface_info.ipv4) > 0 else None
        if current_ip != iface_ip:
            diffs['ip'] = (iface_ip, current_ip)

        # Compare netmask (first IPv4 only)
        current_netmask = self.netmask
        iface_netmask = iface_info.ipv4[0].netmask if iface_info.ipv4 and len(iface_info.ipv4) > 0 else None
        if current_netmask != iface_netmask:
            diffs['netmask'] = (iface_netmask, current_netmask)

        # Compare gateway
        current_gw = self.gateway
        iface_gw = iface_info.gateway
        if current_gw != iface_gw:
            diffs['gateway'] = (iface_gw, current_gw)

        # Compare DNS 1
        current_dns1 = self.dns1
        iface_dns1 = iface_info.dns1
        if current_dns1 != iface_dns1:
            diffs['dns1'] = (iface_dns1, current_dns1)

        # Compare DNS 2
        current_dns2 = self.dns2
        iface_dns2 = iface_info.dns2
        if current_dns2 != iface_dns2:
            diffs['dns2'] = (iface_dns2, current_dns2)

        return diffs