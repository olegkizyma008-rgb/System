"""Doctor Vibe Extensions - Auto-Generated Plugin System

This plugin enables Doctor Vibe to automatically create and register
specialized plugins when standard tools cannot accomplish a task.

When Doctor Vibe encounters a task that requires capabilities not available
in the current toolset, it will:
1. Analyze the requirements
2. Generate a custom plugin with necessary tools
3. Register the plugin dynamically
4. Execute the task using the new plugin
5. Optionally save the plugin for future use
"""

from typing import Dict, Any, Optional, List
import os
import sys
from pathlib import Path
from plugins import PluginMeta


# Plugin metadata
PLUGIN_META = PluginMeta(
    name="Doctor Vibe Extensions",
    version="1.0.0",
    description="Auto-plugin generation system for Doctor Vibe to extend capabilities on-demand",
    author="Trinity System",
    dependencies=[]
)


def analyze_task_requirements(task_description: str, failed_attempts: List[str] = None) -> Dict[str, Any]:
    """Analyze task to determine what plugin capabilities are needed.
    
    Args:
        task_description: Description of the task to accomplish
        failed_attempts: List of previous failed attempts (tool names/errors)
        
    Returns:
        Dictionary with requirements analysis:
        {
            "requires_plugin": bool,
            "plugin_type": str,
            "missing_capabilities": List[str],
            "suggested_tools": List[Dict],
            "confidence": float
        }
    """
    # Keywords that indicate need for specialized plugins
    plugin_indicators = {
        "api": ["api", "rest", "graphql", "endpoint", "http request"],
        "database": ["database", "sql", "query", "table", "mongodb", "postgres"],
        "file_format": ["pdf", "excel", "csv", "json", "xml", "yaml", "parse"],
        "cloud": ["aws", "azure", "gcp", "s3", "cloud"],
        "automation": ["automate", "workflow", "pipeline", "cron"],
        "integration": ["integrate", "sync", "webhook", "oauth"],
        "data_processing": ["transform", "filter", "aggregate", "analyze data"],
    }
    
    task_lower = task_description.lower()
    detected_types = []
    missing_capabilities = []
    
    # Check for indicators
    for plugin_type, keywords in plugin_indicators.items():
        if any(kw in task_lower for kw in keywords):
            detected_types.append(plugin_type)
            missing_capabilities.extend([kw for kw in keywords if kw in task_lower])
    
    # Check if standard tools failed
    standard_tools_failed = bool(failed_attempts and len(failed_attempts) > 0)
    
    requires_plugin = len(detected_types) > 0 or standard_tools_failed
    
    return {
        "requires_plugin": requires_plugin,
        "plugin_type": detected_types[0] if detected_types else "custom",
        "detected_types": detected_types,
        "missing_capabilities": list(set(missing_capabilities)),
        "suggested_tools": _suggest_tools(detected_types, task_description),
        "confidence": 0.8 if detected_types else 0.5,
        "standard_tools_failed": standard_tools_failed
    }


def _suggest_tools(plugin_types: List[str], task_description: str) -> List[Dict[str, str]]:
    """Suggest tool functions to include in generated plugin."""
    suggestions = []
    
    tool_templates = {
        "api": [
            {"name": "make_api_request", "description": "Make HTTP API request with auth"},
            {"name": "parse_api_response", "description": "Parse and validate API response"}
        ],
        "database": [
            {"name": "execute_query", "description": "Execute database query safely"},
            {"name": "fetch_records", "description": "Fetch records with filtering"}
        ],
        "file_format": [
            {"name": "parse_file", "description": "Parse specialized file format"},
            {"name": "convert_format", "description": "Convert between file formats"}
        ],
        "cloud": [
            {"name": "upload_to_cloud", "description": "Upload file to cloud storage"},
            {"name": "download_from_cloud", "description": "Download from cloud storage"}
        ],
        "automation": [
            {"name": "create_workflow", "description": "Create automated workflow"},
            {"name": "schedule_task", "description": "Schedule recurring task"}
        ],
        "integration": [
            {"name": "sync_data", "description": "Synchronize data between systems"},
            {"name": "handle_webhook", "description": "Process incoming webhook"}
        ],
        "data_processing": [
            {"name": "transform_data", "description": "Transform data structure"},
            {"name": "aggregate_results", "description": "Aggregate and summarize data"}
        ],
    }
    
    for ptype in plugin_types:
        if ptype in tool_templates:
            suggestions.extend(tool_templates[ptype])
    
    return suggestions


def generate_plugin_code(
    plugin_name: str,
    plugin_type: str,
    tools: List[Dict[str, str]],
    task_description: str
) -> str:
    """Generate Python code for a custom plugin.
    
    Args:
        plugin_name: Name for the plugin
        plugin_type: Type of plugin (api, database, etc.)
        tools: List of tool specifications
        task_description: Original task description for context
        
    Returns:
        Generated Python code as string
    """
    tools_code = []
    register_code = []
    
    for tool in tools:
        tool_name = tool["name"]
        tool_desc = tool["description"]
        
        # Generate function code
        func_code = f'''
def {tool_name}(**kwargs) -> Dict[str, Any]:
    """
    {tool_desc}
    
    Generated to support: {task_description[:100]}
    
    Args:
        **kwargs: Tool-specific arguments
        
    Returns:
        Dictionary with tool execution results
    """
    try:
        # TODO: Implement {tool_name} logic
        # This is a generated stub - Doctor Vibe should implement actual logic
        
        return {{
            "tool": "{tool_name}",
            "status": "success",
            "message": "Tool executed successfully",
            "data": kwargs
        }}
    except Exception as e:
        return {{
            "tool": "{tool_name}",
            "status": "error",
            "error": str(e)
        }}
'''
        tools_code.append(func_code)
        
        # Generate registration
        register_code.append(f'''    registry.register_tool(
        "{tool_name}",
        {tool_name},
        description="{tool_desc}"
    )''')
    
    # Build complete plugin code
    plugin_code = f'''"""
{plugin_name} - Auto-Generated Plugin

Type: {plugin_type}
Purpose: {task_description[:200]}

Generated by Doctor Vibe Extensions to provide specialized capabilities
not available in standard Trinity toolset.
"""

from typing import Dict, Any
from plugins import PluginMeta


PLUGIN_META = PluginMeta(
    name="{plugin_name}",
    version="1.0.0",
    description="Auto-generated plugin for {plugin_type} operations",
    author="Doctor Vibe (Trinity System)",
    dependencies=[]
)

{''.join(tools_code)}

def register(registry) -> None:
    """Register auto-generated tools with MCP registry."""
{chr(10).join(register_code)}


def initialize() -> bool:
    """Initialize plugin."""
    print(f"✅ [{{PLUGIN_META.name}}] Auto-generated plugin initialized")
    return True
'''
    
    return plugin_code


def create_vibe_plugin(
    task_description: str,
    plugin_name: str = None,
    plugin_type: str = "custom",
    auto_implement: bool = False
) -> Dict[str, Any]:
    """Create a custom plugin for Doctor Vibe to accomplish a specific task.
    
    This is the main entry point for automatic plugin generation.
    
    Args:
        task_description: What the plugin needs to accomplish
        plugin_name: Optional custom name (auto-generated if not provided)
        plugin_type: Type of plugin (api, database, custom, etc.)
        auto_implement: If True, attempt to implement tools using LLM
        
    Returns:
        Dictionary with creation status and plugin details
    """
    try:
        from plugins.plugin_creator import create_plugin_structure, sanitize_plugin_name
        
        # Analyze task requirements
        analysis = analyze_task_requirements(task_description)
        
        if not analysis["requires_plugin"]:
            return {
                "status": "not_needed",
                "message": "Standard tools should be sufficient for this task",
                "analysis": analysis
            }
        
        # Generate plugin name if not provided
        if not plugin_name:
            type_prefix = analysis["plugin_type"]
            import time
            plugin_name = f"vibe_{type_prefix}_{int(time.time())}"
        
        # Create basic structure
        result = create_plugin_structure(
            plugin_name=plugin_name,
            description=f"Auto-generated plugin for: {task_description[:100]}"
        )
        
        if result.get("status") != "success":
            return result
        
        # Generate specialized code
        plugin_code = generate_plugin_code(
            plugin_name=plugin_name,
            plugin_type=analysis["plugin_type"],
            tools=analysis["suggested_tools"],
            task_description=task_description
        )
        
        # Write generated code
        plugin_dir = Path(result["path"])
        plugin_file = plugin_dir / "plugin.py"
        plugin_file.write_text(plugin_code)
        
        return {
            "status": "success",
            "plugin_name": plugin_name,
            "plugin_path": result["path"],
            "plugin_type": analysis["plugin_type"],
            "tools_generated": [t["name"] for t in analysis["suggested_tools"]],
            "message": (
                f"✅ Doctor Vibe plugin '{plugin_name}' created successfully. "
                f"Generated {len(analysis['suggested_tools'])} tools for {analysis['plugin_type']} operations. "
                f"Plugin requires implementation - Doctor Vibe should now develop the actual logic."
            ),
            "next_steps": [
                "Doctor Vibe should implement tool functions in plugin.py",
                "Add error handling and validation",
                "Create unit tests",
                "Register plugin with Trinity to use tools"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to create Doctor Vibe plugin: {e}"
        }


def register(registry) -> None:
    """Register Doctor Vibe extension tools with MCP registry."""
    
    registry.register_tool(
        "vibe_analyze_task_requirements",
        analyze_task_requirements,
        description=(
            "Analyze if a task requires a custom plugin. "
            "Args: task_description (str), failed_attempts (list, optional). "
            "Returns analysis with requires_plugin flag and suggestions."
        )
    )
    
    registry.register_tool(
        "vibe_create_plugin",
        create_vibe_plugin,
        description=(
            "Auto-generate a specialized plugin for Doctor Vibe when standard tools are insufficient. "
            "Args: task_description (str), plugin_name (str, optional), plugin_type (str, optional). "
            "Creates plugin structure, generates tool stubs, and guides Doctor Vibe to implement functionality."
        )
    )


def initialize() -> bool:
    """Initialize Doctor Vibe Extensions plugin."""
    print("✅ [Doctor Vibe Extensions] Auto-plugin generation system initialized")
    print("   Doctor Vibe can now create specialized plugins on-demand")
    return True


def cleanup() -> None:
    """Cleanup plugin resources."""
    pass
