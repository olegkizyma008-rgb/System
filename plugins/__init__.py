"""Trinity System Plugins

This package contains custom plugins developed by Trinity.
Plugins are automatically discovered and registered with the MCP tool registry.
"""

from typing import Dict, Any, List, Optional
import os
import importlib.util
from pathlib import Path


class PluginMeta:
    """Plugin metadata descriptor."""
    
    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        description: str = "",
        author: str = "Trinity System",
        dependencies: Optional[List[str]] = None
    ):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies
        }


def discover_plugins(plugins_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Discover all plugins in the plugins directory.
    
    Returns:
        List of plugin metadata dictionaries
    """
    if plugins_dir is None:
        plugins_dir = Path(__file__).parent
    
    discovered = []
    
    for item in plugins_dir.iterdir():
        if not item.is_dir() or item.name.startswith("_") or item.name.startswith("."):
            continue
        
        plugin_file = item / "plugin.py"
        if not plugin_file.exists():
            continue
        
        try:
            # Import plugin module
            spec = importlib.util.spec_from_file_location(f"plugins.{item.name}.plugin", plugin_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get plugin metadata
                if hasattr(module, "PLUGIN_META"):
                    meta = module.PLUGIN_META
                    if isinstance(meta, PluginMeta):
                        discovered.append(meta.to_dict())
        except Exception as e:
            # Log error but continue discovery
            import logging
            logging.getLogger(__name__).warning(f"Failed to load plugin {item.name}: {e}")
    
    return discovered


def load_plugin(plugin_name: str, registry: Any) -> bool:
    """Load and register a specific plugin.
    
    Args:
        plugin_name: Name of the plugin directory
        registry: MCPToolRegistry instance to register tools with
        
    Returns:
        True if plugin loaded successfully, False otherwise
    """
    plugins_dir = Path(__file__).parent
    plugin_dir = plugins_dir / plugin_name
    plugin_file = plugin_dir / "plugin.py"
    
    if not plugin_file.exists():
        return False
    
    try:
        # Import plugin module
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}.plugin", plugin_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Call register function if it exists
            if hasattr(module, "register"):
                module.register(registry)
                return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to load plugin {plugin_name}: {e}")
    
    return False


def load_all_plugins(registry: Any) -> Dict[str, bool]:
    """Load all discovered plugins.
    
    Args:
        registry: MCPToolRegistry instance to register tools with
        
    Returns:
        Dictionary mapping plugin names to load status (True/False)
    """
    plugins_dir = Path(__file__).parent
    results = {}
    
    for item in plugins_dir.iterdir():
        if not item.is_dir() or item.name.startswith("_") or item.name.startswith("."):
            continue
        
        results[item.name] = load_plugin(item.name, registry)
    
    return results
