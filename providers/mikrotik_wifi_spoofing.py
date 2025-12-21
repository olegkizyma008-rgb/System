#!/usr/bin/env python3
"""
MikroTik WiFi Network Spoofing Module
Randomly changes guest WiFi SSID, IP subnet, and local MAC address on macOS
"""

import subprocess
import random
import string
import json
from typing import Dict, Tuple, Optional
from datetime import datetime
import sys


class MikroTikWiFiSpoofing:
    """Manage WiFi spoofing on MikroTik modem and macOS MAC address"""
    
    # MikroTik connection details
    MIKROTIK_HOST = "192.168.88.1"
    MIKROTIK_USER = "admin"
    MIKROTIK_SSH_KEY = "~/.ssh/id_ed25519"
    
    # WiFi configuration
    GUEST_WIFI_INTERFACE = "ether2"  # Guest WiFi interface on MikroTik
    GUEST_WIFI_PASSWORD = "00000000"  # Fixed password as requested
    
    # IP range for guest network (will randomize the subnet)
    BASE_IP_RANGE = "10"  # Will generate 10.x.y.z networks
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.log_file = "/tmp/mikrotik_wifi_spoof.log"
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and optionally to console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def generate_random_ssid(self, prefix: str = "Guest") -> str:
        """Generate random WiFi SSID name"""
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        ssid = f"{prefix}_{random_suffix}"
        return ssid
    
    def generate_random_subnet(self) -> str:
        """Generate random private subnet (10.x.y.0/24)"""
        second_octet = random.randint(1, 254)
        third_octet = random.randint(1, 254)
        return f"10.{second_octet}.{third_octet}"
    
    def generate_random_mac(self) -> str:
        """Generate random local MAC address for macOS (unicast, locally administered)"""
        # Format: x2:xx:xx:xx:xx:xx where x2 means second bit is 1 (locally administered)
        mac = [
            0x02,  # Locally administered, unicast
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
        ]
        return ':'.join(f'{x:02x}' for x in mac)
    
    def ssh_command(self, command: str) -> Tuple[bool, str]:
        """Execute SSH command on MikroTik"""
        try:
            full_cmd = [
                "ssh",
                "-i", self.MIKROTIK_SSH_KEY,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                f"{self.MIKROTIK_USER}@{self.MIKROTIK_HOST}",
                command
            ]
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            return False, "SSH command timed out"
        except Exception as e:
            return False, str(e)
    
    def update_mikrotik_guest_wifi(self, new_ssid: str, new_subnet: str) -> bool:
        """Update guest WiFi SSID and IP network on MikroTik"""
        try:
            self.log(f"Updating MikroTik WiFi: SSID={new_ssid}, Subnet={new_subnet}")
            
            # Update wireless interface SSID
            cmd_ssid = f'/interface wireless set [find name="{self.GUEST_WIFI_INTERFACE}"] ssid="{new_ssid}"'
            success, output = self.ssh_command(cmd_ssid)
            
            if not success:
                self.log(f"Failed to update SSID: {output}", "ERROR")
                return False
            
            # Update IP address pool
            pool_name = "guest_pool"
            new_pool_range = f"{new_subnet}.100-{new_subnet}.200"
            
            cmd_pool = f'/ip pool set [find name="{pool_name}"] ranges="{new_pool_range}"'
            success, output = self.ssh_command(cmd_pool)
            
            if not success:
                # Try to create pool if it doesn't exist
                cmd_create = f'/ip pool add name="{pool_name}" ranges="{new_pool_range}"'
                success, output = self.ssh_command(cmd_create)
                
                if not success:
                    self.log(f"Failed to update IP pool: {output}", "ERROR")
                    return False
            
            # Update DHCP server
            cmd_dhcp = f'/ip dhcp-server set [find name="guest_dhcp"] address-pool="{pool_name}"'
            self.ssh_command(cmd_dhcp)  # Non-critical
            
            self.log(f"Successfully updated MikroTik WiFi", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Error updating MikroTik: {str(e)}", "ERROR")
            return False
    
    def change_mac_address(self, new_mac: str) -> bool:
        """Change MAC address on macOS (requires sudo)"""
        try:
            self.log(f"Changing MAC address to {new_mac}")
            
            # Get primary network interface
            result = subprocess.run(
                ["route", "get", "default"],
                capture_output=True,
                text=True
            )
            
            # Parse interface from output
            interface = None
            for line in result.stdout.split('\n'):
                if 'interface:' in line:
                    interface = line.split(':')[1].strip()
                    break
            
            if not interface:
                # Fallback to en0 or en1
                interfaces = ["en0", "en1", "en2"]
                for iface in interfaces:
                    result = subprocess.run(
                        ["ifconfig", iface],
                        capture_output=True
                    )
                    if result.returncode == 0:
                        interface = iface
                        break
            
            if not interface:
                self.log("Could not determine network interface", "ERROR")
                return False
            
            self.log(f"Using network interface: {interface}")
            
            # Change MAC address (requires sudo)
            cmd = f"sudo ifconfig {interface} ether {new_mac}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log(f"Successfully changed MAC address on {interface}", "SUCCESS")
                return True
            else:
                self.log(f"Failed to change MAC address: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Error changing MAC address: {str(e)}", "ERROR")
            return False
    
    def spoof_all(self) -> Dict[str, str]:
        """Execute complete spoofing process"""
        self.log("=== Starting WiFi and MAC Spoofing ===", "INFO")
        
        # Generate new values
        new_ssid = self.generate_random_ssid()
        new_subnet = self.generate_random_subnet()
        new_mac = self.generate_random_mac()
        
        self.log(f"Generated new SSID: {new_ssid}")
        self.log(f"Generated new Subnet: {new_subnet}.0/24")
        self.log(f"Generated new MAC: {new_mac}")
        
        result = {
            "ssid": new_ssid,
            "subnet": new_subnet,
            "mac": new_mac,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update MikroTik
        if not self.update_mikrotik_guest_wifi(new_ssid, new_subnet):
            self.log("Failed to update MikroTik, skipping MAC change", "WARNING")
            result["status"] = "partial"
            return result
        
        # Change local MAC address
        if not self.change_mac_address(new_mac):
            self.log("Failed to change MAC address", "WARNING")
            result["status"] = "partial"
            return result
        
        result["status"] = "success"
        self.log("=== Spoofing completed successfully ===", "SUCCESS")
        return result
    
    def verify_connection(self) -> bool:
        """Verify SSH connection to MikroTik"""
        success, output = self.ssh_command("system identity print")
        if success:
            self.log(f"MikroTik connection verified: {output}")
            return True
        else:
            self.log(f"Failed to connect to MikroTik: {output}", "ERROR")
            return False
    
    def get_status(self) -> Dict:
        """Get current WiFi status from MikroTik"""
        try:
            success, output = self.ssh_command(
                '/interface wireless print where disabled=no'
            )
            
            if not success:
                return {"error": "Could not retrieve status"}
            
            return {
                "mikrotik_status": output,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MikroTik WiFi and MAC Address Spoofing"
    )
    parser.add_argument(
        "--spoof",
        action="store_true",
        help="Execute complete spoofing process"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify connection to MikroTik"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current WiFi status"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    spoofing = MikroTikWiFiSpoofing(verbose=args.verbose)
    
    if args.verify:
        success = spoofing.verify_connection()
        result = {"verified": success}
    elif args.status:
        result = spoofing.get_status()
    elif args.spoof:
        result = spoofing.spoof_all()
    else:
        parser.print_help()
        return 1
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    
    return 0 if result.get("status") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
