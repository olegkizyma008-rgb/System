#!/usr/bin/env python3

"""
MCP Server Manager - Main integration class for Context7 and SonarQube MCP servers
"""

import json
import subprocess
import os
import logging
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPServerClient(ABC):
    """Abstract base class for MCP server clients"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.command = config.get('command', '')
        self.args = config.get('args', [])
        self.env = config.get('env', {})
        self.timeout = config.get('timeout', 30000)
        self.retry_attempts = config.get('retryAttempts', 3)
        
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to MCP server"""
        pass
    
    @abstractmethod
    def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute command on MCP server"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        pass
    
    def _run_command(self, cmd: list) -> subprocess.CompletedProcess:
        """Internal method to run shell commands"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, **self.env}
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Error running command: {e}")
            raise


class Context7Client(MCPServerClient):
    """Context7 MCP Server Client"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_type = "context7"
        
    def connect(self) -> bool:
        """Connect to Context7 MCP server"""
        try:
            # Test connection by getting server info
            test_cmd = [self.command] + self.args + ["--version"]
            result = self._run_command(test_cmd)
            
            if result.returncode == 0:
                logger.info(f"Successfully connected to Context7 MCP server")
                return True
            else:
                logger.error(f"Failed to connect to Context7: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Context7 connection error: {e}")
            return False
    
    def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute command on Context7 MCP server"""
        try:
            # Build the full command
            full_cmd = [self.command] + self.args + [command]
            
            # Add any additional arguments from kwargs
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float)):
                    full_cmd.extend([f"--{key}", str(value)])
                elif isinstance(value, bool):
                    if value:
                        full_cmd.append(f"--{key}")
            
            result = self._run_command(full_cmd)
            
            if result.returncode == 0:
                try:
                    # Try to parse JSON output
                    return {
                        "success": True,
                        "data": json.loads(result.stdout),
                        "raw_output": result.stdout
                    }
                except json.JSONDecodeError:
                    # Return raw output if not JSON
                    return {
                        "success": True,
                        "data": result.stdout,
                        "raw_output": result.stdout
                    }
            else:
                # Handle Context7 specific errors more gracefully
                error_msg = result.stderr if result.stderr else "Unknown error"
                
                # Check for common Context7 errors
                if "too many arguments" in error_msg:
                    logger.warning("Context7 argument error - trying simplified command")
                    # Try with just the basic command
                    simple_cmd = [self.command] + self.args + [command]
                    simple_result = self._run_command(simple_cmd)
                    
                    if simple_result.returncode == 0:
                        try:
                            return {
                                "success": True,
                                "data": json.loads(simple_result.stdout),
                                "raw_output": simple_result.stdout,
                                "fallback": "used_simple_command"
                            }
                        except json.JSONDecodeError:
                            return {
                                "success": True,
                                "data": simple_result.stdout,
                                "raw_output": simple_result.stdout,
                                "fallback": "used_simple_command"
                            }
                    else:
                        return {
                            "success": False,
                            "error": f"Context7 command failed: {error_msg}",
                            "returncode": result.returncode,
                            "fallback_attempted": True
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Context7 error: {error_msg}",
                        "returncode": result.returncode
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": type(e).__name__
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get Context7 server status"""
        return self.execute_command("status")
    
    def store_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store context data in Context7"""
        return self.execute_command("store", data=json.dumps(context_data))
    
    def retrieve_context(self, query: str) -> Dict[str, Any]:
        """Retrieve context data from Context7"""
        return self.execute_command("retrieve", query=query)


class SonarQubeClient(MCPServerClient):
    """SonarQube MCP Server Client"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_type = "sonarqube"
        
    def connect(self) -> bool:
        """Connect to SonarQube MCP server"""
        try:
            # Test connection by running a simple command
            test_cmd = [self.command] + self.args + ["--test-connection"]
            result = self._run_command(test_cmd)
            
            if result.returncode == 0:
                logger.info(f"Successfully connected to SonarQube MCP server")
                return True
            else:
                logger.error(f"Failed to connect to SonarQube: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"SonarQube connection error: {e}")
            return False
    
    def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute command on SonarQube MCP server"""
        try:
            # Build the full command
            full_cmd = [self.command] + self.args + [command]
            
            # Add any additional arguments from kwargs
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float)):
                    full_cmd.extend([f"--{key}", str(value)])
                elif isinstance(value, bool):
                    if value:
                        full_cmd.append(f"--{key}")
            
            result = self._run_command(full_cmd)
            
            if result.returncode == 0:
                try:
                    # Try to parse JSON output
                    return {
                        "success": True,
                        "data": json.loads(result.stdout),
                        "raw_output": result.stdout
                    }
                except json.JSONDecodeError:
                    # Return raw output if not JSON
                    return {
                        "success": True,
                        "data": result.stdout,
                        "raw_output": result.stdout
                    }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "returncode": result.returncode
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": type(e).__name__
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get SonarQube server status"""
        return self.execute_command("status")
    
    def analyze_project(self, project_key: str, **kwargs) -> Dict[str, Any]:
        """Analyze a project with SonarQube"""
        return self.execute_command("analyze", project=project_key, **kwargs)
    
    def get_quality_gate(self, project_key: str) -> Dict[str, Any]:
        """Get quality gate status for a project"""
        return self.execute_command("quality-gate", project=project_key)


class MCPManager:
    """Main MCP Server Manager"""
    
    def __init__(self, config_path: str = "config/mcp_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.clients = {}
        self._initialize_clients()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded MCP configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def _initialize_clients(self):
        """Initialize MCP server clients"""
        servers_config = self.config.get('mcpServers', {})
        
        for server_name, server_config in servers_config.items():
            if server_name == "context7":
                self.clients[server_name] = Context7Client(server_config)
            elif server_name == "sonarqube":
                self.clients[server_name] = SonarQubeClient(server_config)
            else:
                logger.warning(f"Unknown server type: {server_name}")
        
        logger.info(f"Initialized {len(self.clients)} MCP server clients")
    
    def get_client(self, server_name: str) -> Optional[MCPServerClient]:
        """Get MCP client by name"""
        return self.clients.get(server_name)
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect to all MCP servers"""
        results = {}
        for name, client in self.clients.items():
            results[name] = client.connect()
        return results
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status from all MCP servers"""
        results = {}
        for name, client in self.clients.items():
            results[name] = client.get_status()
        return results
    
    def execute_on_server(self, server_name: str, command: str, **kwargs) -> Dict[str, Any]:
        """Execute command on specific server"""
        client = self.get_client(server_name)
        if client:
            return client.execute_command(command, **kwargs)
        else:
            return {
                "success": False,
                "error": f"Server {server_name} not found"
            }


if __name__ == "__main__":
    # Example usage
    manager = MCPManager()
    
    # Connect to all servers
    connections = manager.connect_all()
    print("Connection results:", connections)
    
    # Get status from all servers
    statuses = manager.get_all_status()
    print("Server statuses:", statuses)
    
    # Example: Store context in Context7
    if "context7" in manager.clients:
        context_result = manager.execute_on_server(
            "context7", 
            "store",
            data=json.dumps({"test": "context", "value": "hello world"})
        )
        print("Context7 store result:", context_result)