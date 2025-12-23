import json


def test_mcp_registry_registers_expected_tools():
    from core.mcp_registry import MCPToolRegistry

    r = MCPToolRegistry()
    assert "find_image_on_screen" in r._tools
    assert "capture_screen_region" in r._tools


def test_mcp_registry_execute_unknown_tool_returns_error_string():
    from core.mcp_registry import MCPToolRegistry

    r = MCPToolRegistry()
    out = r.execute("__does_not_exist__", {})
    assert isinstance(out, str)
    assert out.startswith("Error: Tool")


def test_mcp_registry_execute_returns_json_for_known_tool():
    from core.mcp_registry import MCPToolRegistry

    r = MCPToolRegistry()
    out = r.execute("find_image_on_screen", {"template_path": "", "tolerance": 0.9})
    payload = json.loads(out)
    assert payload["status"] == "error"
