import sys
import os

# Add repo root to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from mcp_integration.core.mcp_client_manager import get_mcp_client_manager, MCPClientType

def test_mcp_auto_resolution():
    print("🚀 Testing MCP Auto-Resolution...")
    mgr = get_mcp_client_manager()
    
    # 1. Test Manual Mode
    mgr.switch_client(MCPClientType.OPEN_MCP, save=False)
    print(f"Manual mode (OPEN_MCP): Resolved = {mgr.resolve_client_type('DEV')}")
    assert mgr.resolve_client_type("DEV") == MCPClientType.OPEN_MCP
    
    # 2. Test Auto Mode
    mgr.switch_client(MCPClientType.AUTO, save=False)
    print(f"Auto mode: Active = {mgr.active_client}")
    
    # 2a. DEV task
    resolved_dev = mgr.resolve_client_type("DEV")
    print(f"  Task context 'DEV' -> Resolved: {resolved_dev}")
    assert resolved_dev == MCPClientType.CONTINUE
    
    # 2b. General task
    resolved_general = mgr.resolve_client_type("GENERAL")
    print(f"  Task context 'GENERAL' -> Resolved: {resolved_general}")
    assert resolved_general == MCPClientType.OPEN_MCP
    
    # 2c. No context
    resolved_none = mgr.resolve_client_type(None)
    print(f"  No context -> Resolved: {resolved_none}")
    assert resolved_none == MCPClientType.OPEN_MCP

    print("\n✅ MCP Auto-Resolution Verification Successful!")

if __name__ == "__main__":
    test_mcp_auto_resolution()
