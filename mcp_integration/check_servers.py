#!/usr/bin/env python3
"""Check MCP server availability and health"""

import subprocess
import sys
from typing import Dict, List

def check_server_health() -> Dict[str, any]:
    """Check which MCP servers are available"""
    results = {}
    
    # Check Playwright
    try:
        result = subprocess.run(
            ["npx", "-y", "@playwright/mcp", "--version"],
            capture_output=True, text=True, timeout=10
        )
        version = result.stdout.strip().split('\n')[0] if result.stdout else None
        results["playwright"] = {
            "available": result.returncode == 0 or version,
            "version": version,
            "error": result.stderr.strip() if result.returncode != 0 and not version else None
        }
    except subprocess.TimeoutExpired:
        # Timeout means server started (it's running as daemon)
        results["playwright"] = {"available": True, "version": "running", "error": None}
    except Exception as e:
        results["playwright"] = {"available": False, "version": None, "error": str(e)}
    
    # Check AppleScript
    try:
        result = subprocess.run(
            ["npx", "-y", "@iflow-mcp/applescript-mcp", "--version"],
            capture_output=True, text=True, timeout=10
        )
        version = result.stdout.strip().split('\n')[0] if result.stdout else None
        results["applescript"] = {
            "available": result.returncode == 0 or "server" in result.stdout.lower(),
            "version": version or "running",
            "error": result.stderr.strip() if result.returncode != 0 and not version else None
        }
    except subprocess.TimeoutExpired:
        # Timeout means server started (it's running as daemon)
        results["applescript"] = {"available": True, "version": "running", "error": None}
    except Exception as e:
        results["applescript"] = {"available": False, "version": None, "error": str(e)}
    
    # Check PyAutoGUI
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("mcp-pyautogui-server").version
        results["pyautogui"] = {"available": True, "version": version, "error": None}
    except Exception as e:
        results["pyautogui"] = {"available": False, "version": None, "error": str(e)}
    
    return results

def print_server_status():
    """Print server status in readable format"""
    status = check_server_health()
    
    print("🔍 MCP Server Status:")
    print("=" * 60)
    
    for server, info in status.items():
        status_emoji = "✅" if info["available"] else "❌"
        version = info.get("version", "N/A")
        error = info.get("error", "")
        
        if info["available"]:
            print(f"{status_emoji} {server:15} - Version: {version}")
        else:
            print(f"{status_emoji} {server:15} - Error: {error[:50]}")
    
    available = sum(1 for info in status.values() if info["available"])
    total = len(status)
    
    print("=" * 60)
    print(f"Available: {available}/{total} servers")
    
    if available == 0:
        print("⚠️  No MCP servers available - using local tools only")
        return False
    elif available < total:
        print("⚠️  Some servers missing - partial MCP functionality")
        return True
    else:
        print("✅ All servers available - full MCP functionality")
        return True

def main():
    """Main entry point"""
    success = print_server_status()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
