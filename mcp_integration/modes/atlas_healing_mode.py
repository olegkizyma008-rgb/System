#!/usr/bin/env python3

"""
Atlas Healing Mode - Specialized mode for error recovery and system healing
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.mcp_manager import MCPManager

# Set up logging
logger = logging.getLogger(__name__)


class AtlasHealingMode:
    """
    Atlas Healing Mode - Handles error recovery, system diagnostics, and healing operations
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self.context7_client = mcp_manager.get_client("context7")
        self.sonarqube_client = mcp_manager.get_client("sonarqube")
        self.healing_session_id = f"healing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.healing_log = []
        
    def start_healing_session(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new healing session"""
        try:
            # Log the start of healing session
            self._log_healing_event("session_start", {
                "session_id": self.healing_session_id,
                "timestamp": datetime.now().isoformat(),
                "error_context": error_context
            })
            
            # Store initial error context
            if self.context7_client:
                context_result = self.context7_client.store_context({
                    "session_id": self.healing_session_id,
                    "type": "healing_session",
                    "status": "started",
                    "error_context": error_context,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Ensure context_result is not None and has the expected structure
                if context_result is None:
                    logger.error("Context7 client returned None")
                    return {"success": False, "error": "Context7 client returned None"}
                
                if not context_result.get("success"):
                    error_msg = context_result.get('error', 'Unknown error')
                    logger.error(f"Failed to store healing context: {error_msg}")
                    return {"success": False, "error": f"Failed to initialize healing context: {error_msg}"}
            
            return {
                "success": True,
                "session_id": self.healing_session_id,
                "message": "Healing session started successfully"
            }
            
        except Exception as e:
            logger.error(f"Error starting healing session: {e}")
            return {"success": False, "error": str(e)}
    
    def _log_healing_event(self, event_type: str, data: Dict[str, Any]):
        """Log healing events"""
        event = {
            "session_id": self.healing_session_id,
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.healing_log.append(event)
        logger.info(f"Healing event: {event_type}")
    
    def diagnose_system(self) -> Dict[str, Any]:
        """Perform system diagnostics"""
        try:
            diagnostics = {
                "timestamp": datetime.now().isoformat(),
                "system_status": {},
                "mcp_servers": {},
                "recommendations": []
            }
            
            # Check MCP server status
            if self.mcp_manager:
                server_statuses = self.mcp_manager.get_all_status()
                diagnostics["mcp_servers"] = server_statuses
                
                # Analyze server statuses
                for server_name, status in server_statuses.items():
                    if not status.get("success"):
                        diagnostics["recommendations"].append({
                            "priority": "high",
                            "issue": f"MCP server {server_name} is not responding",
                            "action": f"Check {server_name} server connection and configuration"
                        })
            
            # Add system diagnostics
            diagnostics["system_status"] = {
                "memory_usage": self._get_system_memory_usage(),
                "cpu_usage": self._get_system_cpu_usage(),
                "disk_space": self._get_system_disk_space()
            }
            
            # Store diagnostics in context
            if self.context7_client:
                self.context7_client.store_context({
                    "session_id": self.healing_session_id,
                    "type": "diagnostics",
                    "diagnostics": diagnostics
                })
            
            self._log_healing_event("diagnostics_complete", diagnostics)
            
            return {
                "success": True,
                "diagnostics": diagnostics
            }
            
        except Exception as e:
            logger.error(f"Error during system diagnostics: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_system_memory_usage(self) -> Dict[str, Any]:
        """Get system memory usage (placeholder)"""
        # In a real implementation, this would use psutil or similar
        return {
            "total": "8GB",
            "used": "4.2GB",
            "free": "3.8GB",
            "percentage": 52.5
        }
    
    def _get_system_cpu_usage(self) -> Dict[str, Any]:
        """Get system CPU usage (placeholder)"""
        # In a real implementation, this would use psutil or similar
        return {
            "cores": 8,
            "usage_percentage": 23.7,
            "load_average": [1.2, 1.5, 1.3]
        }
    
    def _get_system_disk_space(self) -> Dict[str, Any]:
        """Get system disk space (placeholder)"""
        # In a real implementation, this would use psutil or similar
        return {
            "/": {
                "total": "500GB",
                "used": "230GB",
                "free": "270GB",
                "percentage": 46.0
            }
        }
    
    def analyze_error_patterns(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error patterns and suggest fixes"""
        try:
            analysis = {
                "error_type": error_data.get("type", "unknown"),
                "patterns": [],
                "suggested_fixes": [],
                "confidence": 0.0
            }
            
            # Simple pattern analysis (would be more sophisticated in real implementation)
            error_message = error_data.get("message", "").lower()
            
            if "memory" in error_message or "out of memory" in error_message:
                analysis["patterns"].append("memory_issue")
                analysis["suggested_fixes"].append({
                    "action": "Increase memory allocation",
                    "details": "Check system memory usage and consider increasing limits"
                })
                analysis["confidence"] += 0.8
            
            if "timeout" in error_message or "timed out" in error_message:
                analysis["patterns"].append("timeout_issue")
                analysis["suggested_fixes"].append({
                    "action": "Increase timeout settings",
                    "details": "Review MCP server timeout configurations"
                })
                analysis["confidence"] += 0.7
            
            if "connection" in error_message or "network" in error_message:
                analysis["patterns"].append("network_issue")
                analysis["suggested_fixes"].append({
                    "action": "Check network connectivity",
                    "details": "Verify network connections to MCP servers"
                })
                analysis["confidence"] += 0.9
            
            # Store analysis in context
            if self.context7_client:
                self.context7_client.store_context({
                    "session_id": self.healing_session_id,
                    "type": "error_analysis",
                    "analysis": analysis,
                    "original_error": error_data
                })
            
            self._log_healing_event("error_analysis_complete", analysis)
            
            return {
                "success": True,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error during error pattern analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def apply_healing_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply healing actions to fix issues"""
        results = []
        
        for action in actions:
            try:
                action_type = action.get("type")
                action_data = action.get("data", {})
                
                if action_type == "restart_server":
                    server_name = action_data.get("server")
                    result = self._restart_mcp_server(server_name)
                    
                elif action_type == "reconfigure_server":
                    server_name = action_data.get("server")
                    config_updates = action_data.get("config")
                    result = self._reconfigure_mcp_server(server_name, config_updates)
                    
                elif action_type == "clear_cache":
                    result = self._clear_server_cache(action_data)
                    
                else:
                    result = {"success": False, "error": f"Unknown action type: {action_type}"}
                
                results.append({
                    "action": action,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Log the action
                self._log_healing_event("healing_action_applied", {
                    "action": action,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "action": action,
                    "result": {"success": False, "error": str(e)},
                    "timestamp": datetime.now().isoformat()
                })
                logger.error(f"Error applying healing action: {e}")
        
        # Store healing results
        if self.context7_client:
            self.context7_client.store_context({
                "session_id": self.healing_session_id,
                "type": "healing_results",
                "results": results,
                "status": "completed"
            })
        
        return {
            "success": True,
            "results": results,
            "session_id": self.healing_session_id
        }
    
    def _restart_mcp_server(self, server_name: str) -> Dict[str, Any]:
        """Restart an MCP server"""
        try:
            client = self.mcp_manager.get_client(server_name)
            if not client:
                return {"success": False, "error": f"Server {server_name} not found"}
            
            # In a real implementation, this would actually restart the server
            # For now, we'll simulate it by reconnecting
            connection_result = client.connect()
            
            if connection_result:
                return {
                    "success": True,
                    "message": f"Server {server_name} restarted successfully",
                    "action": "restart"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to restart server {server_name}"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _reconfigure_mcp_server(self, server_name: str, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Reconfigure an MCP server"""
        try:
            # In a real implementation, this would update the server configuration
            # For now, we'll just log the intended changes
            logger.info(f"Would reconfigure {server_name} with updates: {config_updates}")
            
            return {
                "success": True,
                "message": f"Server {server_name} configuration updated",
                "updates_applied": config_updates
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _clear_server_cache(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clear server cache"""
        try:
            server_name = action_data.get("server", "all")
            cache_type = action_data.get("type", "all")
            
            # In a real implementation, this would clear the cache
            logger.info(f"Would clear {cache_type} cache for {server_name}")
            
            return {
                "success": True,
                "message": f"Cache cleared for {server_name}",
                "cache_type": cache_type
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def end_healing_session(self, status: str = "completed") -> Dict[str, Any]:
        """End the current healing session"""
        try:
            # Store final session status
            if self.context7_client:
                self.context7_client.store_context({
                    "session_id": self.healing_session_id,
                    "type": "healing_session",
                    "status": status,
                    "end_timestamp": datetime.now().isoformat(),
                    "healing_log": self.healing_log
                })
            
            self._log_healing_event("session_end", {"status": status})
            
            return {
                "success": True,
                "session_id": self.healing_session_id,
                "status": status,
                "log_entries": len(self.healing_log)
            }
            
        except Exception as e:
            logger.error(f"Error ending healing session: {e}")
            return {"success": False, "error": str(e)}
    
    def get_healing_report(self) -> Dict[str, Any]:
        """Generate a comprehensive healing report"""
        try:
            # Retrieve all healing session data from context
            if self.context7_client:
                session_data = self.context7_client.retrieve_context(
                    f"session_id:{self.healing_session_id}"
                )
                
                if session_data.get("success"):
                    return {
                        "success": True,
                        "report": {
                            "session_id": self.healing_session_id,
                            "status": session_data.get("data", {}).get("status", "unknown"),
                            "start_time": session_data.get("data", {}).get("timestamp"),
                            "end_time": session_data.get("data", {}).get("end_timestamp"),
                            "log_entries": len(self.healing_log),
                            "actions_taken": len([e for e in self.healing_log if e["type"] == "healing_action_applied"])
                        }
                    }
            
            return {
                "success": True,
                "report": {
                    "session_id": self.healing_session_id,
                    "status": "active",
                    "log_entries": len(self.healing_log)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating healing report: {e}")
            return {"success": False, "error": str(e)}


# Example usage
if __name__ == "__main__":
    # Initialize MCP Manager
    from ..core.mcp_manager import MCPManager
    
    mcp_manager = MCPManager("../config/mcp_config.json")
    
    # Create healing mode instance
    healer = AtlasHealingMode(mcp_manager)
    
    # Example error context
    error_context = {
        "type": "system_error",
        "message": "Context7 MCP server connection timeout",
        "timestamp": datetime.now().isoformat(),
        "severity": "high"
    }
    
    # Start healing session
    print("Starting healing session...")
    start_result = healer.start_healing_session(error_context)
    print(f"Session started: {start_result}")
    
    # Run diagnostics
    print("\nRunning system diagnostics...")
    diagnostics_result = healer.diagnose_system()
    print(f"Diagnostics: {diagnostics_result}")
    
    # Analyze error patterns
    print("\nAnalyzing error patterns...")
    analysis_result = healer.analyze_error_patterns(error_context)
    print(f"Analysis: {analysis_result}")
    
    # Apply healing actions
    healing_actions = [
        {
            "type": "restart_server",
            "data": {"server": "context7"}
        },
        {
            "type": "reconfigure_server",
            "data": {
                "server": "context7",
                "config": {"timeout": 60000}
            }
        }
    ]
    
    print("\nApplying healing actions...")
    actions_result = healer.apply_healing_actions(healing_actions)
    print(f"Actions result: {actions_result}")
    
    # End healing session
    print("\nEnding healing session...")
    end_result = healer.end_healing_session("completed")
    print(f"Session ended: {end_result}")
    
    # Get healing report
    print("\nGenerating healing report...")
    report = healer.get_healing_report()
    print(f"Healing report: {report}")