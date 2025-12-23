#!/usr/bin/env python3
"""
Continue MCP Client - Integration with @continuedev/cli
"""

import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

from .mcp_client_manager import BaseMCPClient

logger = logging.getLogger(__name__)


class ContinueMCPClient(BaseMCPClient):
    """
    Continue CLI MCP Client integration.
    
    This client leverages the Continue configuration (~/.continue/config.json)
    to discover and execute MCP tools, and uses the 'cn' CLI for prompt execution.
    """
    
    CLI_COMMAND = "cn"
    DEFAULT_CONFIG_PATH = os.path.expanduser("~/.continue/config.json")
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._config_path = config.get("config_path", self.DEFAULT_CONFIG_PATH) if config else self.DEFAULT_CONFIG_PATH
        self._mcp_servers: List[Dict[str, Any]] = []
    
    def connect(self) -> bool:
        """
        Connect to Continue Client.
        
        Checks if 'cn' is available and loads configuration.
        """
        try:
            # Check CLI availability
            result = subprocess.run(
                [self.CLI_COMMAND, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error("Continue CLI (cn) check failed")
                return False
            
            # Load configuration
            self._load_config()
            
            self._connected = True
            logger.info("Continue MCP Client connected")
            return True
            
        except FileNotFoundError:
            logger.error(f"Continue CLI '{self.CLI_COMMAND}' not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Failed to connect Continue MCP Client: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect."""
        self._connected = False
        self._mcp_servers = []

    def _load_config(self) -> None:
        """Load MCP servers from Continue config."""
        try:
            if not os.path.exists(self._config_path):
                logger.warning(f"Continue config not found at {self._config_path}")
                return
                
            with open(self._config_path, 'r', encoding='utf-8') as f:
                # Handle potential comments in JSON if any (simple load for now)
                data = json.load(f)
                
            # mcpServers in Continue config is typically an array of objects
            # [{ "name": "...", "command": "...", "args": [...] }]
            self._mcp_servers = data.get("experimental", {}).get("modelContextProtocolServers", [])
            # Also check newer config location if schema changed
            if not self._mcp_servers:
                self._mcp_servers = data.get("mcpServers", [])

            # Index tools (simulated for now, as we don't query servers on load)
            self._tools = {}
            for server in self._mcp_servers:
                name = server.get("name", "unknown")
                self._tools[name] = {
                    "name": name,
                    "description": f"MCP Server: {name}",
                    "command": server.get("command"),
                    "args": server.get("args", [])
                }
                
        except Exception as e:
            logger.error(f"Error loading Continue config: {e}")

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool.
        
        Since 'cn' doesn't support direct tool execution, we manually invoke
        the server binary defined in continue config, similar to OpenMCPClient.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            # Find server for tool
            # Assuming tool name format: "server_name.tool_name" or just "tool_name"
            # Since we don't have a full map of tools->servers without querying them,
            # this is a best-effort match or we need to query servers.
            
            # Strategy: Query all servers or fallback to prompt if tool identification fails?
            # Better strategy: For this implementation, we will iterate servers
            # and try to execute. But this is inefficient.
            
            # Alternative: Assume user provides "server.tool" or we use 'OpenMCPClient' approach
            # of trying to guess.
            
            # For now, let's look for a server matching the prefix if present.
            parts = name.split(".")
            target_server = None
            tool_name = name
            
            if len(parts) > 1:
                potential_server = parts[0]
                for s in self._mcp_servers:
                    if s.get("name") == potential_server:
                        target_server = s
                        tool_name = parts[1]
                        break
            
            if not target_server and len(self._mcp_servers) == 1:
                # Ambiguous but only one server, let's try it
                target_server = self._mcp_servers[0]
            
            if not target_server:
                 # Try execution via prompt if we can't find manual server?
                 # No, execute_tool expects structured output.
                 return {
                     "success": False, 
                     "error": f"Could not map tool '{name}' to a configured MCP server in Continue config"
                 }

            # Execute manually
            cmd = [target_server["command"]] + target_server.get("args", [])
            
            input_data = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                },
                "id": 1
            })
            
            env = os.environ.copy()
            env.update(target_server.get("env", {}))
            
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    return {
                        "success": True,
                        "data": response.get("result", response)
                    }
                except:
                    return {"success": True, "data": result.stdout}
            else:
                 return {"success": False, "error": result.stderr}

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"success": False, "error": str(e)}

    def execute_prompt(self, prompt: str) -> Dict[str, Any]:
        """Execute prompt via 'cn' CLI."""
        if not self._connected:
            self.connect()
            
        try:
            # Use 'cn session prompt' or similar if available, or just pipe to 'cn'
            # Based on help: `cn [options] [prompt]`
            
            result = subprocess.run(
                [self.CLI_COMMAND, "-p", "--format", "json", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "data": result.stdout.strip(),
                    "source": "continue_cli"
                }
            else:
                return {
                    "success": False, 
                    "error": result.stderr
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tools(self) -> List[Dict[str, str]]:
        """List tools (summary of servers)."""
        return [
            {"name": s.get("name", "unknown"), "description": f"Server: {s.get('command')}"}
            for s in self._mcp_servers
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "client": "continue",
            "connected": self._connected,
            "servers_count": len(self._mcp_servers)
        }
