#!/usr/bin/env python3
"""
Open-MCP Client - CopilotKit/open-mcp-client integration

Based on https://github.com/CopilotKit/open-mcp-client
Uses LangGraph agents for MCP server communication.
"""

import json
import logging
import os
import subprocess
import threading
from typing import Any, Dict, List, Optional

from .mcp_client_manager import BaseMCPClient

logger = logging.getLogger(__name__)


class OpenMCPClient(BaseMCPClient):
    """
    CopilotKit Open-MCP Client integration.
    
    This client wraps the open-mcp-client architecture which uses:
    - LangGraph for agent orchestration
    - Poetry for dependency management
    - OpenAI API for LLM operations
    """
    
    DEFAULT_AGENT_DIR = "mcp_integration/agents/open_mcp"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._agent_dir = config.get("agent_dir", self.DEFAULT_AGENT_DIR) if config else self.DEFAULT_AGENT_DIR
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        
        # MCP server connections managed internally
        self._mcp_servers: Dict[str, Dict[str, Any]] = {}
        
    def _get_base_dir(self) -> str:
        """Get the base directory for the project."""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def _ensure_dependencies(self) -> bool:
        """Ensure Poetry and dependencies are available."""
        try:
            # Check if poetry is installed
            result = subprocess.run(
                ["poetry", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.warning("Poetry not installed. Run: pip install poetry")
                return False
            return True
        except FileNotFoundError:
            logger.warning("Poetry not found in PATH. Run: pip install poetry")
            return False
        except Exception as e:
            logger.error(f"Error checking Poetry: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Establish connection to Open-MCP client.
        
        This initializes the LangGraph agent and connects to configured MCP servers.
        """
        if self._connected:
            return True
        
        with self._lock:
            try:
                # Load available tools from MCP config
                self._load_mcp_servers()
                
                # Mark as connected (lazy initialization for actual LLM calls)
                self._connected = True
                logger.info("Open-MCP Client connected successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect Open-MCP Client: {e}")
                return False
    
    def disconnect(self) -> None:
        """Disconnect from Open-MCP client."""
        with self._lock:
            if self._process:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except Exception:
                    pass
                finally:
                    self._process = None
            
            self._connected = False
            self._mcp_servers.clear()
            logger.info("Open-MCP Client disconnected")
    
    def _load_mcp_servers(self) -> None:
        """Load MCP server configurations."""
        try:
            config_path = os.path.join(
                self._get_base_dir(),
                "mcp_integration", "config", "mcp_config.json"
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._mcp_servers = config.get("mcpServers", {})
                    
            # Add tool descriptions to internal registry
            # Skip persistent servers that are handled by ExternalMCPProvider in MCPToolRegistry
            persistent_servers = ["playwright", "pyautogui", "applescript"]
            
            for server_name, server_config in self._mcp_servers.items():
                if server_name in persistent_servers:
                    continue
                    
                self._tools[server_name] = {
                    "name": server_name,
                    "description": server_config.get("description", f"MCP Server: {server_name}"),
                    "category": server_config.get("category", "general")
                }
                
        except Exception as e:
            logger.warning(f"Failed to load MCP servers: {e}")
    
    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool via the Open-MCP client.
        
        This uses subprocess to call MCP servers via their configured commands.
        """
        if not self._connected:
            return {
                "success": False,
                "error": "Client not connected"
            }
        
        try:
            # Parse tool name for potential server prefix
            parts = name.split(".", 1)
            if len(parts) == 2:
                server_name, tool_name = parts
            else:
                server_name = None
                tool_name = name
            
            # Find matching MCP server
            server_config = None
            if server_name and server_name in self._mcp_servers:
                server_config = self._mcp_servers[server_name]
            else:
                # Try to find a server that might handle this tool
                for sname, sconfig in self._mcp_servers.items():
                    if sconfig.get("category") in self._infer_category(tool_name):
                        server_config = sconfig
                        server_name = sname
                        break
            
            if not server_config:
                return {
                    "success": False,
                    "error": f"No MCP server found for tool: {name}"
                }
            
            # Build and execute command
            cmd = [server_config["command"]] + server_config.get("args", [])
            
            # For stdio-based MCP, we send JSON via stdin
            input_data = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                },
                "id": 1
            })
            
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=server_config.get("timeout", 30000) / 1000,
                env={**os.environ, **server_config.get("env", {})}
            )
            
            if result.returncode == 0:
                if not result.stdout.strip():
                    provider_info = f"command='{server_config['command']}'"
                    return {
                        "success": False,
                        "tool": name,
                        "error": f"MCP server {server_name} returned empty stdout. This common for stdio-based servers executed as one-off CLI if they initialization fails or they are not installed correctly ({provider_info}).",
                        "raw_stderr": result.stderr
                    }

                    
                try:
                    response = json.loads(result.stdout)
                    # Standard MCP tool response should have result or content
                    if "result" not in response and "error" not in response:
                        # Best effort for non-standard responses
                        return {
                            "success": True,
                            "tool": name,
                            "data": response,
                            "raw_output": result.stdout
                        }
                        
                    return {
                        "success": True if "error" not in response else False,
                        "tool": name,
                        "data": response.get("result", response.get("error")),
                        "raw_output": result.stdout
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "tool": name,
                        "error": f"Failed to parse JSON response: {result.stdout[:200]}...",
                        "raw_output": result.stdout
                    }
            else:
                return {
                    "success": False,
                    "tool": name,
                    "error": result.stderr or f"MCP command failed with exit code {result.returncode}",
                    "returncode": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "tool": name,
                "error": "Tool execution timed out"
            }
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {
                "success": False,
                "tool": name,
                "error": str(e)
            }
    
    def _infer_category(self, tool_name: str) -> List[str]:
        """Infer potential categories from tool name."""
        tool_lower = tool_name.lower()
        categories = []
        
        if any(k in tool_lower for k in ["browser", "playwright", "web", "navigate"]):
            categories.append("browser")
        if any(k in tool_lower for k in ["file", "read", "write", "copy"]):
            categories.append("system")
        if any(k in tool_lower for k in ["applescript", "macos", "native"]):
            categories.append("system")
        if any(k in tool_lower for k in ["gui", "click", "mouse", "keyboard"]):
            categories.append("gui")
        if any(k in tool_lower for k in ["ai", "analyze", "copilot"]):
            categories.append("ai")
        if any(k in tool_lower for k in ["sonar", "quality", "code"]):
            categories.append("code_analysis")
        
        return categories or ["general"]
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List available tools from the Open-MCP client."""
        if not self._connected:
            self.connect()
        
        result = []
        for name, tool_info in self._tools.items():
            result.append({
                "name": name,
                "description": tool_info.get("description", ""),
                "category": tool_info.get("category", "general")
            })
        return result
    
    def execute_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Execute a natural language prompt using LangGraph agent.
        
        This creates an agent that can use available MCP tools to complete the task.
        """
        if not self._connected:
            if not self.connect():
                return {
                    "success": False,
                    "error": "Failed to connect"
                }
        
        try:
            # Try to use LangChain/LangGraph for agent execution
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                
                # Check for provider
                provider_path = os.path.join(self._get_base_dir(), "providers", "copilot.py")
                if os.path.exists(provider_path):
                    import sys
                    if self._get_base_dir() not in sys.path:
                        sys.path.insert(0, self._get_base_dir())
                    from providers.copilot import CopilotLLM
                    
                    llm = CopilotLLM()
                    
                    # Create messages
                    messages = [
                        SystemMessage(content="You are an AI assistant with access to MCP tools. Execute the user's request."),
                        HumanMessage(content=prompt)
                    ]
                    
                    response = llm.invoke(messages)
                    content = response.content if hasattr(response, 'content') else str(response)
                    
                    return {
                        "success": True,
                        "data": content,
                        "provider": "copilot"
                    }
                    
            except ImportError:
                pass
            
            # Fallback: return instruction for manual execution
            return {
                "success": True,
                "data": f"[Open-MCP] Prompt received: {prompt}\n\nAvailable tools: {', '.join(self._tools.keys())}",
                "note": "LangGraph agent not configured. Using basic response."
            }
            
        except Exception as e:
            logger.error(f"Error executing prompt: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get Open-MCP client status."""
        return {
            "client": "open_mcp",
            "name": "Open-MCP (CopilotKit)",
            "connected": self._connected,
            "mcp_servers": len(self._mcp_servers),
            "tools_count": len(self._tools),
            "has_poetry": self._ensure_dependencies() if self._connected else None
        }
