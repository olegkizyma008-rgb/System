"""Plugin creation tool for Trinity System.

Handles automatic plugin scaffolding and Doctor Vibe integration.
"""

from typing import Dict, Any, Optional
import os
from pathlib import Path
import re


PLUGIN_TEMPLATE = '''"""{{PLUGIN_NAME}} - Trinity System Plugin

{{DESCRIPTION}}
"""

from typing import Dict, Any
from plugins import PluginMeta


# Plugin metadata
PLUGIN_META = PluginMeta(
    name="{{PLUGIN_NAME}}",
    version="0.1.0",
    description="{{DESCRIPTION}}",
    author="Trinity System",
    dependencies=[]
)


def register(registry) -> None:
    """Register plugin tools with MCP tool registry.
    
    Args:
        registry: MCPToolRegistry instance
    """
    # Example tool registration:
    # registry.register_tool(
    #     "my_tool_name",
    #     my_tool_function,
    #     description="Tool description"
    # )
    pass


def initialize() -> bool:
    """Initialize plugin (optional hook).
    
    Returns:
        True if initialization successful, False otherwise
    """
    return True


def cleanup() -> None:
    """Cleanup plugin resources (optional hook)."""
    pass
'''

README_TEMPLATE = '''# {{PLUGIN_NAME}}

{{DESCRIPTION}}

## Installation

This plugin is automatically discovered by Trinity.

## Usage

{{USAGE_INSTRUCTIONS}}

## Development

Created by Trinity System using Doctor Vibe workflow.

## License

Part of Trinity System
'''

TEST_TEMPLATE = '''"""Tests for {{PLUGIN_NAME}} plugin."""

import pytest


def test_plugin_meta():
    """Test plugin metadata is properly defined."""
    from plugins.{{PLUGIN_DIR}}.plugin import PLUGIN_META
    
    assert PLUGIN_META.name == "{{PLUGIN_NAME}}"
    assert PLUGIN_META.version
    assert PLUGIN_META.description


def test_plugin_register():
    """Test plugin registration."""
    from plugins.{{PLUGIN_DIR}}.plugin import register
    
    # Mock registry
    class MockRegistry:
        def __init__(self):
            self.tools = []
        
        def register_tool(self, name, func, description):
            self.tools.append({"name": name, "func": func, "description": description})
    
    registry = MockRegistry()
    register(registry)
    
    # Add assertions based on your plugin's tools
    # assert len(registry.tools) > 0
'''


def sanitize_plugin_name(name: str) -> str:
    """Sanitize plugin name to valid Python identifier."""
    # Remove special characters, convert to snake_case
    name = re.sub(r'[^\w\s-]', '', name.lower())
    name = re.sub(r'[-\s]+', '_', name)
    return name


def create_plugin_structure(
    plugin_name: str,
    description: str = "",
    plugins_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Create plugin directory structure.
    
    Args:
        plugin_name: Human-readable plugin name
        description: Plugin description
        plugins_dir: Optional custom plugins directory path
        
    Returns:
        Dictionary with status and created paths
    """
    if plugins_dir is None:
        plugins_dir = Path(__file__).parent
    
    # Sanitize plugin name for directory/module
    plugin_dir_name = sanitize_plugin_name(plugin_name)
    plugin_path = plugins_dir / plugin_dir_name
    
    # Check if plugin already exists
    if plugin_path.exists():
        return {
            "status": "error",
            "error": f"Plugin directory already exists: {plugin_path}",
            "path": str(plugin_path)
        }
    
    try:
        # Create directory structure
        plugin_path.mkdir(parents=True, exist_ok=True)
        (plugin_path / "tests").mkdir(exist_ok=True)
        
        # Create __init__.py
        (plugin_path / "__init__.py").write_text(
            f'"""{{plugin_name}} plugin."""\n\nfrom .plugin import PLUGIN_META, register\n\n__all__ = ["PLUGIN_META", "register"]\n'
        )
        
        # Create plugin.py from template
        plugin_content = PLUGIN_TEMPLATE.replace("{{PLUGIN_NAME}}", plugin_name)
        plugin_content = plugin_content.replace("{{DESCRIPTION}}", description or f"{plugin_name} plugin for Trinity System")
        (plugin_path / "plugin.py").write_text(plugin_content)
        
        # Create README.md
        readme_content = README_TEMPLATE.replace("{{PLUGIN_NAME}}", plugin_name)
        readme_content = readme_content.replace("{{DESCRIPTION}}", description or f"{plugin_name} plugin for Trinity System")
        readme_content = readme_content.replace("{{USAGE_INSTRUCTIONS}}", "TODO: Add usage instructions")
        (plugin_path / "README.md").write_text(readme_content)
        
        # Create test file
        test_content = TEST_TEMPLATE.replace("{{PLUGIN_NAME}}", plugin_name)
        test_content = test_content.replace("{{PLUGIN_DIR}}", plugin_dir_name)
        (plugin_path / "tests" / "test_plugin.py").write_text(test_content)
        
        return {
            "status": "success",
            "plugin_name": plugin_name,
            "plugin_dir": plugin_dir_name,
            "path": str(plugin_path),
            "files_created": [
                str(plugin_path / "__init__.py"),
                str(plugin_path / "plugin.py"),
                str(plugin_path / "README.md"),
                str(plugin_path / "tests" / "test_plugin.py")
            ]
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "path": str(plugin_path)
        }


def tool_create_plugin(plugin_name: str, description: str = "") -> Dict[str, Any]:
    """Tool function for creating a new plugin.
    
    This is registered with Trinity's MCP registry and can be called by LLMs.
    
    Args:
        plugin_name: Name of the plugin to create
        description: Optional description of the plugin
        
    Returns:
        Dictionary with creation status and details
    """
    result = create_plugin_structure(plugin_name, description)
    
    if result.get("status") == "success":
        # Add hint about Doctor Vibe workflow
        result["message"] = (
            f"✅ Plugin '{plugin_name}' scaffolding created at {result['path']}. "
            f"Doctor Vibe will now handle development in DEV mode. "
            f"Use TRINITY_DEV_BY_VIBE=1 to enable pre-emptive pause and diff preview."
        )
    
    return result
