"""Tests for Example Data Processor plugin."""

import pytest
import json


def test_plugin_meta():
    """Test plugin metadata is properly defined."""
    from plugins.example_data_processor.plugin import PLUGIN_META
    
    assert PLUGIN_META.name == "Example Data Processor"
    assert PLUGIN_META.version == "0.1.0"
    assert PLUGIN_META.description


def test_plugin_register():
    """Test plugin registration."""
    from plugins.example_data_processor.plugin import register
    
    # Mock registry
    class MockRegistry:
        def __init__(self):
            self.tools = []
        
        def register_tool(self, name, func, description):
            self.tools.append({"name": name, "func": func, "description": description})
    
    registry = MockRegistry()
    register(registry)
    
    assert len(registry.tools) == 1
    assert registry.tools[0]["name"] == "example_process_json"


def test_process_json_data_success():
    """Test JSON processing with valid data."""
    from plugins.example_data_processor.plugin import process_json_data
    
    test_data = json.dumps({"key1": "value1", "key2": "value2", "count": 42})
    result = process_json_data(test_data)
    
    assert result["status"] == "success"
    assert set(result["keys"]) == {"key1", "key2", "count"}
    assert result["length"] == 3


def test_process_json_data_invalid():
    """Test JSON processing with invalid data."""
    from plugins.example_data_processor.plugin import process_json_data
    
    result = process_json_data("invalid json{")
    
    assert result["status"] == "error"
    assert "error" in result


def test_process_json_data_list():
    """Test JSON processing with list data."""
    from plugins.example_data_processor.plugin import process_json_data
    
    test_data = json.dumps([1, 2, 3, 4, 5])
    result = process_json_data(test_data)
    
    assert result["status"] == "success"
    assert result["length"] == 5
    assert result["keys"] is None  # Lists don't have keys
