# Remove all existing IPv4 addresses
Get-NetIPAddress -InterfaceAlias "DUT" -AddressFamily IPv4 | Remove-NetIPAddress -Confirm:$false

# Disable DHCP
Set-NetIPInterface -InterfaceAlias "DUT" -Dhcp Disabled

# Set new static IP and mask
New-NetIPAddress -InterfaceAlias "DUT" -IPAddress 192.168.1.100 -PrefixLength 24