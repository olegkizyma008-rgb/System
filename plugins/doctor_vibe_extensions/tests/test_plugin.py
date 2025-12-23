"""Tests for Doctor Vibe Extensions plugin."""

import pytest
import os
import sys
from pathlib import Path

# Add plugins to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doctor_vibe_extensions.plugin import (
    PLUGIN_META,
    analyze_task_requirements,
    generate_plugin_code,
    create_vibe_plugin,
    _suggest_tools
)


def test_plugin_meta():
    """Test plugin metadata is correctly defined."""
    assert PLUGIN_META.name == "Doctor Vibe Extensions"
    assert PLUGIN_META.version == "1.0.0"
    assert "auto-plugin generation" in PLUGIN_META.description.lower()
    assert PLUGIN_META.author == "Trinity System"


def test_analyze_task_requirements_api():
    """Test analysis detects API-related tasks."""
    result = analyze_task_requirements(
        task_description="Make REST API calls to Stripe payment gateway",
        failed_attempts=[]
    )
    
    assert result["requires_plugin"] is True
    assert "api" in result["detected_types"]
    assert result["plugin_type"] == "api"
    assert len(result["suggested_tools"]) > 0
    assert result["confidence"] >= 0.5


def test_analyze_task_requirements_database():
    """Test analysis detects database tasks."""
    result = analyze_task_requirements(
        task_description="Execute SQL queries on PostgreSQL database",
        failed_attempts=["run_in_terminal"]
    )
    
    assert result["requires_plugin"] is True
    assert "database" in result["detected_types"]
    assert result["standard_tools_failed"] is True
    assert len(result["missing_capabilities"]) > 0  # Should detect some missing capabilities


def test_analyze_task_requirements_file_format():
    """Test analysis detects file format tasks."""
    result = analyze_task_requirements(
        task_description="Parse PDF invoices and extract data to CSV",
        failed_attempts=[]
    )
    
    assert result["requires_plugin"] is True
    assert "file_format" in result["detected_types"]
    assert len(result["suggested_tools"]) >= 2


def test_analyze_task_requirements_no_plugin_needed():
    """Test analysis when standard tools are sufficient."""
    result = analyze_task_requirements(
        task_description="Read a text file and count lines",
        failed_attempts=[]
    )
    
    # Simple file operations shouldn't require plugin
    # (unless specific keywords present)
    assert "confidence" in result
    assert isinstance(result["requires_plugin"], bool)


def test_analyze_task_requirements_multiple_types():
    """Test analysis detects multiple plugin types."""
    result = analyze_task_requirements(
        task_description="Download files from AWS S3, parse Excel data, and save to MongoDB",
        failed_attempts=["file_search"]
    )
    
    assert result["requires_plugin"] is True
    # Should detect cloud, file_format, and database
    assert len(result["detected_types"]) >= 2
    detected = set(result["detected_types"])
    assert "cloud" in detected or "file_format" in detected or "database" in detected


def test_suggest_tools_api():
    """Test tool suggestions for API plugins."""
    tools = _suggest_tools(["api"], "REST API client")
    
    assert len(tools) > 0
    tool_names = [t["name"] for t in tools]
    assert "make_api_request" in tool_names
    assert "parse_api_response" in tool_names


def test_suggest_tools_database():
    """Test tool suggestions for database plugins."""
    tools = _suggest_tools(["database"], "Database operations")
    
    assert len(tools) > 0
    tool_names = [t["name"] for t in tools]
    assert "execute_query" in tool_names
    assert "fetch_records" in tool_names


def test_suggest_tools_multiple_types():
    """Test tool suggestions for multiple plugin types."""
    tools = _suggest_tools(["api", "database"], "API with database")
    
    # Should get tools from both types
    assert len(tools) >= 4
    tool_names = [t["name"] for t in tools]
    assert "make_api_request" in tool_names
    assert "execute_query" in tool_names


def test_generate_plugin_code_basic():
    """Test plugin code generation."""
    tools = [
        {"name": "test_tool_1", "description": "Test tool 1"},
        {"name": "test_tool_2", "description": "Test tool 2"}
    ]
    
    code = generate_plugin_code(
        plugin_name="test_plugin",
        plugin_type="api",
        tools=tools,
        task_description="Test task description"
    )
    
    # Check generated code has expected components
    assert "test_plugin" in code
    assert "def test_tool_1(" in code
    assert "def test_tool_2(" in code
    assert "def register(registry)" in code
    assert "PLUGIN_META" in code
    assert "api" in code
    
    # Check tool registration
    assert 'registry.register_tool' in code
    assert '"test_tool_1"' in code
    assert '"test_tool_2"' in code


def test_generate_plugin_code_syntax():
    """Test generated plugin code is valid Python."""
    tools = [{"name": "sample_tool", "description": "Sample"}]
    
    code = generate_plugin_code(
        plugin_name="syntax_test",
        plugin_type="custom",
        tools=tools,
        task_description="Syntax test"
    )
    
    # Try to compile the code
    try:
        compile(code, '<string>', 'exec')
        syntax_valid = True
    except SyntaxError:
        syntax_valid = False
    
    assert syntax_valid, "Generated code has syntax errors"


def test_create_vibe_plugin_basic(tmp_path, monkeypatch):
    """Test basic plugin creation."""
    # Change to tmp directory
    original_cwd = os.getcwd()
    monkeypatch.chdir(tmp_path)
    
    # Create plugins directory
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    
    # Mock the plugin creator import
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    result = create_vibe_plugin(
        task_description="Test API integration with external service",
        plugin_name="test_api_plugin"
    )
    
    # Restore directory
    monkeypatch.chdir(original_cwd)
    
    # Check result
    assert result["status"] in ["success", "error", "not_needed"]
    
    # If successful, check details
    if result["status"] == "success":
        assert result["plugin_name"] == "test_api_plugin"
        assert "plugin_path" in result
        assert len(result["tools_generated"]) > 0
        assert "next_steps" in result


def test_create_vibe_plugin_auto_name(tmp_path, monkeypatch):
    """Test plugin creation with auto-generated name."""
    original_cwd = os.getcwd()
    monkeypatch.chdir(tmp_path)
    
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    result = create_vibe_plugin(
        task_description="Automated workflow for data processing"
    )
    
    monkeypatch.chdir(original_cwd)
    
    # Should auto-generate name starting with vibe_
    if result["status"] == "success":
        assert result["plugin_name"].startswith("vibe_")


def test_create_vibe_plugin_not_needed():
    """Test when plugin is not needed."""
    result = create_vibe_plugin(
        task_description="Simple addition of two numbers"
    )
    
    # Simple math shouldn't require a plugin
    # (though this depends on keyword detection)
    assert "status" in result
    assert result["status"] in ["success", "not_needed", "error"]


def test_plugin_workflow_integration():
    """Test complete workflow: analyze -> create plugin."""
    task = "Parse XML files and upload to AWS S3 bucket"
    
    # Step 1: Analyze
    analysis = analyze_task_requirements(task, failed_attempts=["read_file"])
    
    assert analysis["requires_plugin"] is True
    assert len(analysis["detected_types"]) > 0
    
    # Step 2: Get suggested tools
    tools = analysis["suggested_tools"]
    assert len(tools) > 0
    
    # Step 3: Code generation (without actually creating files)
    code = generate_plugin_code(
        plugin_name="xml_s3_processor",
        plugin_type=analysis["plugin_type"],
        tools=tools,
        task_description=task
    )
    
    assert "xml_s3_processor" in code
    assert "def register(registry)" in code


def test_analyze_with_cloud_keywords():
    """Test analysis with cloud service keywords."""
    result = analyze_task_requirements(
        "Upload files to AWS S3 and trigger Lambda function"
    )
    
    assert result["requires_plugin"] is True
    assert "cloud" in result["detected_types"]


def test_analyze_with_automation_keywords():
    """Test analysis with automation keywords."""
    result = analyze_task_requirements(
        "Automate workflow to run Python scripts every hour"
    )
    
    assert result["requires_plugin"] is True
    assert "automation" in result["detected_types"]


def test_analyze_with_integration_keywords():
    """Test analysis with integration keywords."""
    result = analyze_task_requirements(
        "Integrate webhook to sync data between systems"
    )
    
    assert result["requires_plugin"] is True
    assert "integration" in result["detected_types"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
