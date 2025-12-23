#!/usr/bin/env python3
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.mcp_registry import MCPToolRegistry

def test_mcp_switching():
    print("🚀 Starting Dual MCP Client Verification...")
    registry = MCPToolRegistry()
    
    # 1. Check current client
    active_client = registry.get_active_mcp_client_name()
    print(f"📍 Initial active client: {active_client}")
    
    # 2. List tools for current client
    print("\n--- Tools for initial client ---")
    tools_list = registry.list_tools()
    # Check if we see client-specific markers
    if "--- Tools from" in tools_list:
        print("✅ Found dynamic MCP tools section.")
    else:
        print("⚠️ Dynamic MCP tools section not found.")
    
    # 3. Switch to the other client
    from mcp_integration.core.mcp_client_manager import MCPClientType
    current_type = registry._mcp_client_manager.active_client
    new_type = "continue" if current_type.value == "open_mcp" else "open_mcp"
    
    print(f"\n🔄 Switching to {new_type}...")
    success = registry.set_mcp_client(new_type)
    if success:
        print(f"✅ Successfully switched to {registry.get_active_mcp_client_name()}")
    else:
        print(f"❌ Failed to switch to {new_type}")
        return

    # 4. List tools for new client
    print(f"\n--- Tools for {registry.get_active_mcp_client_name()} ---")
    tools_list_new = registry.list_tools()
    if f"Tools from {registry.get_active_mcp_client_name()}" in tools_list_new:
        print(f"✅ Correctly identified tools from {registry.get_active_mcp_client_name()}")
    else:
        print(f"⚠️ Dynamic tools section for {registry.get_active_mcp_client_name()} not found.")

    print("\n✨ Verification complete.")

if __name__ == "__main__":
    test_mcp_switching()
