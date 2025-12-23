"""Tests for Test Vibe Plugin plugin."""

import pytest


def test_plugin_meta():
    """Test plugin metadata is properly defined."""
    from plugins.test_vibe_plugin.plugin import PLUGIN_META
    
    assert PLUGIN_META.name == "Test Vibe Plugin"
    assert PLUGIN_META.version
    assert PLUGIN_META.description


def test_plugin_register():
    """Test plugin registration."""
    from plugins.test_vibe_plugin.plugin import register
    
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
