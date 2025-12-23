#!/usr/bin/env python3
"""
Sync MCP Configuration to Continue
==================================

Reads the master MCP configuration from `mcp_integration/config/mcp_config.json`
and updates `~/.continue/config.json` to include these servers.

This ensures that the Continue CLI client has access to the same tools as the Open-MCP client.
"""

import json
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_CONFIG_PATH = os.path.join(BASE_DIR, "mcp_integration", "config", "mcp_config.json")
CONTINUE_CONFIG_PATH = os.path.expanduser("~/.continue/config.json")

def load_json(path):
    if not os.path.exists(path):
        logger.error(f"File not found: {path}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return None

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing {path}: {e}")
        return False

def sync_configs():
    logger.info("Starting MCP Configuration Sync...")
    
    # 1. Load Master Config
    mcp_config = load_json(MCP_CONFIG_PATH)
    if not mcp_config:
        sys.exit(1)
        
    master_servers = mcp_config.get("mcpServers", {})
    logger.info(f"Found {len(master_servers)} servers in master config.")

    # 2. Load Continue Config
    continue_config = load_json(CONTINUE_CONFIG_PATH)
    if not continue_config:
        logger.warning(f"Continue config not found at {CONTINUE_CONFIG_PATH}. Creating new...")
        continue_config = {}

    # 3. Prepare Target Structure
    # Continue uses an array of objects for mcpServers
    # Structure: [{"name": "...", "command": "...", "args": [...]}]
    
    # Check where to put it. Recent versions use "mcpServers" at root or under "experimental"
    # We will put it in "mcpServers" at root as it's becoming standard, 
    # but also check if "experimental.modelContextProtocolServers" exists and warn/update?
    # Let's stick to root "mcpServers" list for simplicity unless existing config dictates otherwise.
    
    current_servers = continue_config.get("mcpServers", [])
    if not isinstance(current_servers, list):
         # If it's a dict (older format?), warn but try to handle
         logger.warning("Existing mcpServers is not a list. overwriting/resetting.")
         current_servers = []

    # Map existing by name to avoid duplicates/overwrite
    server_map = {s.get("name"): s for s in current_servers if "name" in s}
    
    updates_count = 0
    adds_count = 0
    
    for name, config in master_servers.items():
        # Skip internal/special servers if needed
        if name in ["local_fallback"]:
            continue
            
        # Transform to Continue format
        new_entry = {
            "name": name,
            "command": config.get("command"),
            "args": config.get("args", []),
            "env": config.get("env", {})
        }
        
        if name in server_map:
            # Update existing?
            # For now, yes, let's treat master config as source of truth for these specific keys
            server_map[name].update(new_entry)
            updates_count += 1
        else:
            server_map[name] = new_entry
            adds_count += 1
    
    # Reconstruct list
    continue_config["mcpServers"] = list(server_map.values())
    
    # 4. Save
    if save_json(CONTINUE_CONFIG_PATH, continue_config):
        logger.info(f"Sync complete. Added: {adds_count}, Updated: {updates_count}")
        logger.info(f"Updated config saved to {CONTINUE_CONFIG_PATH}")
    else:
        logger.error("Failed to save Continue config.")
        sys.exit(1)

if __name__ == "__main__":
    sync_configs()
