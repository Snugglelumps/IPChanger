import subprocess
import re
import sys

# # Print default gateway using PowerShell
# try:
#     gw_cmd = [
#         "powershell", "-Command",
#         "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object InterfaceAlias, NextHop)"
#     ]
#     gw_result = subprocess.run(gw_cmd, capture_output=True, text=True, check=True)
#     gateway = gw_result.stdout.strip()
#     print(f"Default Gateway: {gateway}")
# except Exception as e:
#     print(f"Failed to get gateway: {e}")

# # Print DNS servers using PowerShell
# try:
#     dns_cmd = [
#         "powershell", "-Command",
#         "(Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses -and $_.ServerAddresses.Count -gt 0 } | Select-Object InterfaceAlias, @{Name='DNSServers';Expression={ $_.ServerAddresses -join ',' }})"
#     ]
#     dns_result = subprocess.run(dns_cmd, capture_output=True, text=True, check=True)
#     dns_servers = dns_result.stdout.strip()
#     print(f"DNS Servers: {dns_servers}")
# except Exception as e:
#     print(f"Failed to get DNS servers: {e}")

# Remove all existing IPv4 addresses from 'Ethernet 2' before setting new IP/gateway
try:
    iface_name = 'Ethernet 2'
    remove_cmd = [
        "powershell", "-Command",
        f"Get-NetIPAddress -InterfaceAlias '{iface_name}' -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false"
    ]
    print(f"Removing all IPv4 addresses from {iface_name}: {remove_cmd}")
    result = subprocess.run(remove_cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    if result.returncode == 0:
        print(f"Successfully removed all IPv4 addresses from {iface_name}.")
    else:
        print(f"Failed to remove IPv4 addresses from {iface_name}.")
except Exception as e:
    print(f"Exception while removing IPv4 addresses: {e}")

# Remove all existing default gateways from 'Ethernet 2'
try:
    iface_name = 'Ethernet 2'
    remove_gw_cmd = [
        "powershell", "-Command",
        f"Get-NetRoute -InterfaceAlias '{iface_name}' -DestinationPrefix '0.0.0.0/0' | Remove-NetRoute -Confirm:$false"
    ]
    print(f"Removing all default gateways from {iface_name}: {remove_gw_cmd}")
    result = subprocess.run(remove_gw_cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    if result.returncode == 0:
        print(f"Successfully removed all default gateways from {iface_name}.")
    else:
        print(f"Failed to remove default gateways from {iface_name}.")
except Exception as e:
    print(f"Exception while removing default gateways: {e}")

# Set the gateway for 'Ethernet 2' to 192.168.50.1 (example)
try:
    iface_name = 'Ethernet 2'
    new_gateway = '192.168.50.1'  # Change as needed
    ip = '192.168.50.100'        # Example IP in the same subnet
    prefixlen = 24               # Example prefix length for 255.255.255.0
    set_cmd = [
        "powershell", "-Command",
        f"New-NetIPAddress -InterfaceAlias '{iface_name}' -IPAddress {ip} -PrefixLength {prefixlen} -DefaultGateway {new_gateway}"
    ]
    print(f"Setting gateway for {iface_name}: {set_cmd}")
    result = subprocess.run(set_cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    if result.returncode == 0:
        print(f"Successfully set gateway for {iface_name}.")
    else:
        print(f"Failed to set gateway for {iface_name}.")
except Exception as e:
    print(f"Exception while setting gateway: {e}")
