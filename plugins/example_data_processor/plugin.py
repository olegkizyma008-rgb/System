"""Example Data Processor - Trinity System Plugin

This is an example plugin showing how to create custom tools for Trinity.
"""

from typing import Dict, Any
from plugins import PluginMeta


# Plugin metadata
PLUGIN_META = PluginMeta(
    name="Example Data Processor",
    version="0.1.0",
    description="Example plugin demonstrating Trinity plugin development workflow",
    author="Trinity System",
    dependencies=[]
)


def process_json_data(data: str) -> Dict[str, Any]:
    """Example tool: Process JSON data.
    
    Args:
        data: JSON string to process
        
    Returns:
        Dictionary with processing results
    """
    try:
        import json
        parsed = json.loads(data)
        return {
            "tool": "process_json_data",
            "status": "success",
            "keys": list(parsed.keys()) if isinstance(parsed, dict) else None,
            "length": len(parsed) if isinstance(parsed, (list, dict)) else None
        }
    except Exception as e:
        return {
            "tool": "process_json_data",
            "status": "error",
            "error": str(e)
        }


def register(registry) -> None:
    """Register plugin tools with MCP tool registry.
    
    Args:
        registry: MCPToolRegistry instance
    """
    registry.register_tool(
        "example_process_json",
        process_json_data,
        description="Example tool: Process and analyze JSON data. Args: data (str)"
    )


def initialize() -> bool:
    """Initialize plugin (optional hook).
    
    Returns:
        True if initialization successful, False otherwise
    """
    print("✅ [Example Data Processor] Plugin initialized")
    return True


def cleanup() -> None:
    """Cleanup plugin resources (optional hook)."""
    print("🔄 [Example Data Processor] Plugin cleanup")
