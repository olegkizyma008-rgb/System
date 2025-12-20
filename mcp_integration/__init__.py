#!/usr/bin/env python3

"""
MCP Server Integration - Core Package
"""

import logging
logger = logging.getLogger(__name__)

# Core imports that work
from .core.mcp_manager import MCPManager, Context7Client, SonarQubeClient

# Try to import modes, but handle failures gracefully
try:
    from .modes.atlas_healing_mode import AtlasHealingMode
    ATLAS_HEALING_AVAILABLE = True
except Exception as e:
    logger.warning(f"Atlas Healing Mode not available: {e}")
    ATLAS_HEALING_AVAILABLE = False
    AtlasHealingMode = None

try:
    from .modes.dev_project_mode import DevProjectMode
    DEV_PROJECT_AVAILABLE = True
except Exception as e:
    logger.warning(f"Dev Project Mode not available: {e}")
    DEV_PROJECT_AVAILABLE = False
    DevProjectMode = None

__version__ = "1.0.0"
__author__ = "MCP Integration System"
__license__ = "MIT"


def create_mcp_integration(config_path: str = "config/mcp_config.json"):
    """
    Create a complete MCP integration instance with available modes
    """
    # Initialize MCP Manager
    mcp_manager = MCPManager(config_path)
    
    # Initialize available modes
    integration = {"manager": mcp_manager}
    
    if ATLAS_HEALING_AVAILABLE:
        integration["atlas_healing"] = AtlasHealingMode(mcp_manager)
    
    if DEV_PROJECT_AVAILABLE:
        integration["dev_project"] = DevProjectMode(mcp_manager)
    
    return integration


def get_version() -> str:
    """Get the version of the MCP integration package"""
    return __version__


def get_available_servers() -> list:
    """Get list of available MCP servers"""
    return ["context7", "sonarqube"]
