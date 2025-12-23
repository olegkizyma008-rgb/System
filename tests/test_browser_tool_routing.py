import pytest
import json
from unittest.mock import MagicMock, patch
from core.mcp_registry import MCPToolRegistry

def test_browser_tool_routing_priority():
    # Setup registry
    registry = MCPToolRegistry()
    
    # Mock legacy provider
    mock_provider = MagicMock()
    mock_provider._connected = True
    mock_provider.execute.return_value = {"content": [{"type": "text", "text": "navigated"}]}
    registry._external_providers["playwright"] = mock_provider
    
    # Mock manager
    mock_manager = MagicMock()
    registry._mcp_client_manager = mock_manager
    
    # Execute browser tool
    result = registry.execute("browser_open_url", {"url": "https://test.com"})
    
    # Should call persistent provider first
    mock_provider.execute.assert_called_once()
    assert "navigated" in result
    
    # Should NOT call manager
    mock_manager.execute.assert_not_called()

def test_open_mcp_client_error_handling():
    from mcp_integration.core.open_mcp_client import OpenMCPClient
    client = OpenMCPClient()
    client._connected = True
    
    # Simulate first matched server for a tool
    client._mcp_servers = {"test": {"command": "echo", "args": ["hello"]}}
    
    with patch("subprocess.run") as mock_run:
        # Case 1: Empty stdout
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = client.execute_tool("test.tool", {})
        assert not res["success"]
        assert "empty stdout" in res["error"]
        
        # Case 2: Invalid JSON
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        res = client.execute_tool("test.tool", {})
        assert not res["success"]
        assert "parse JSON" in res["error"]
        
        # Case 3: Proper JSON error
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"error": "tool error"}), stderr="")
        res = client.execute_tool("test.tool", {})
        assert not res["success"]
        assert res["data"] == "tool error"
