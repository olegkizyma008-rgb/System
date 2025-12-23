#!/usr/bin/env python3

"""
MCP Integration Tool for System AI

This tool integrates MCP (Microservice Communication Protocol) servers with the main system,
providing enhanced capabilities for Atlas healing and development project management.
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Add MCP integration to path
mcp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'mcp_integration')
if mcp_path not in sys.path:
    sys.path.insert(0, mcp_path)

try:
    from mcp_integration import create_mcp_integration
    from mcp_integration.core.mcp_manager import MCPManager
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"MCP Integration not available: {e}")
    MCP_AVAILABLE = False


class MCPIntegrationTool:
    """
    MCP Integration Tool for System AI
    
    This tool provides:
    1. MCP Server Management (Context7 and SonarQube)
    2. Atlas Healing Mode integration
    3. Development Project Mode integration
    4. Global operation planning and execution
    """
    
    def __init__(self):
        self.mcp_integration = None
        self.atlas_healing = None
        self.dev_project = None
        self.initialized = False
        
        # NOTE: Do NOT auto-initialize on construction.
        # This module is imported during Trinity startup; initializing MCP servers here can
        # trigger slow/heavy dependencies (e.g., OCR model checks) and block unrelated tasks.
    
    def _initialize_mcp_integration(self):
        """Initialize MCP integration"""
        try:
            # Get the correct config path
            config_path = os.path.join(mcp_path, 'config', 'mcp_config.json')
            
            # Create MCP integration
            self.mcp_integration = create_mcp_integration(config_path)
            
            # Extract components
            if 'manager' in self.mcp_integration:
                self.manager = self.mcp_integration['manager']
            
            if 'atlas_healing' in self.mcp_integration:
                self.atlas_healing = self.mcp_integration['atlas_healing']
            
            if 'dev_project' in self.mcp_integration:
                self.dev_project = self.mcp_integration['dev_project']
            
            self.initialized = True
            print("✓ MCP Integration Tool initialized successfully")
            
        except Exception as e:
            print(f"✗ Failed to initialize MCP integration: {e}")
            self.initialized = False

    def ensure_initialized(self) -> bool:
        """Initialize MCP integration on-demand."""
        if not MCP_AVAILABLE:
            return False
        if self.initialized:
            return True
        # Allow disabling heavy MCP init entirely via env var.
        disable = str(os.environ.get("TRINITY_DISABLE_MCP_INTEGRATION", "")).strip().lower()
        if disable in {"1", "true", "yes", "on"}:
            return False
        self._initialize_mcp_integration()
        return bool(self.initialized)
    
    def is_available(self) -> bool:
        """Check if MCP integration is available"""
        return self.ensure_initialized() and MCP_AVAILABLE
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers"""
        if not self.is_available():
            return {"success": False, "error": "MCP integration not available"}
        
        try:
            statuses = self.manager.get_all_status()
            return {
                "success": True,
                "servers": list(statuses.keys()),
                "statuses": statuses
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_atlas_healing_session(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Start an Atlas healing session"""
        if not self.is_available() or not self.atlas_healing:
            return {"success": False, "error": "Atlas Healing Mode not available"}
        
        try:
            result = self.atlas_healing.start_healing_session(error_context)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def diagnose_system(self) -> Dict[str, Any]:
        """Run system diagnostics using Atlas Healing Mode"""
        if not self.is_available() or not self.atlas_healing:
            return {"success": False, "error": "Atlas Healing Mode not available"}
        
        try:
            result = self.atlas_healing.diagnose_system()
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_error_patterns(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error patterns using Atlas Healing Mode"""
        if not self.is_available() or not self.atlas_healing:
            return {"success": False, "error": "Atlas Healing Mode not available"}
        
        try:
            result = self.atlas_healing.analyze_error_patterns(error_data)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def apply_healing_actions(self, actions: list) -> Dict[str, Any]:
        """Apply healing actions using Atlas Healing Mode"""
        if not self.is_available() or not self.atlas_healing:
            return {"success": False, "error": "Atlas Healing Mode not available"}
        
        try:
            result = self.atlas_healing.apply_healing_actions(actions)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_development_project(self, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a development project using Dev Project Mode"""
        if not self.is_available() or not self.dev_project:
            return {"success": False, "error": "Dev Project Mode not available"}
        
        try:
            result = self.dev_project.create_project(project_config)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def setup_sonarqube_analysis(self, project_id: str) -> Dict[str, Any]:
        """Set up SonarQube analysis for a project"""
        if not self.is_available() or not self.dev_project:
            return {"success": False, "error": "Dev Project Mode not available"}
        
        try:
            result = self.dev_project.setup_sonarqube_analysis(project_id)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_sonarqube_analysis(self, project_id: str) -> Dict[str, Any]:
        """Run SonarQube analysis on a project"""
        try:
            if not self.is_available() or not self.dev_project:
                return {"success": False, "error": "Dev Project Mode not available"}
            
            result = self.dev_project.run_sonarqube_analysis(project_id)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_global_operation(self, operation_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute global operations using MCP integration"""
        if not self.is_available():
            return {"success": False, "error": "MCP integration not available"}
        
        try:
            # Global operation planning
            if operation_type == "create_website":
                return self._execute_create_website(parameters)
            
            elif operation_type == "enhance_ecommerce":
                return self._execute_enhance_ecommerce(parameters)
            
            elif operation_type == "improve_design":
                return self._execute_improve_design(parameters)
            
            elif operation_type == "system_diagnostics":
                return self._execute_system_diagnostics(parameters)
            
            else:
                return {"success": False, "error": f"Unknown operation type: {operation_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_create_website(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute 'create website' global operation"""
        try:
            # Use Context7 for global planning
            context_result = self.manager.execute_on_server(
                "context7",
                "store",
                data=json.dumps({
                    "operation": "create_website",
                    "parameters": parameters,
                    "status": "planning"
                })
            )
            
            if not context_result.get("success"):
                return context_result
            
            # Create project structure
            project_config = {
                "name": parameters.get("name", "New Website"),
                "type": "web",
                "description": parameters.get("description", "Website project"),
                "features": parameters.get("features", [])
            }
            
            if self.dev_project:
                project_result = self.dev_project.create_project(project_config)
                if not project_result.get("success"):
                    return project_result
                
                project_id = project_result["project_id"]
                
                # Set up quality analysis
                sonarqube_result = self.dev_project.setup_sonarqube_analysis(project_id)
                
                return {
                    "success": True,
                    "operation": "create_website",
                    "project_id": project_id,
                    "project_result": project_result,
                    "sonarqube_result": sonarqube_result,
                    "message": "Website creation initiated successfully"
                }
            else:
                return {
                    "success": True,
                    "operation": "create_website",
                    "message": "Website creation planned (Dev Project Mode not available for full execution)",
                    "planning_data": project_config
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_enhance_ecommerce(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute 'enhance ecommerce' global operation"""
        try:
            # Store ecommerce enhancement plan
            context_result = self.manager.execute_on_server(
                "context7",
                "store",
                data=json.dumps({
                    "operation": "enhance_ecommerce",
                    "parameters": parameters,
                    "status": "planning"
                })
            )
            
            if not context_result.get("success"):
                return context_result
            
            # Analyze current system for ecommerce capabilities
            if self.atlas_healing:
                diagnostics = self.atlas_healing.diagnose_system()
                
                # Plan enhancement actions
                enhancement_plan = [
                    {
                        "type": "add_feature",
                        "data": {
                            "feature": "shopping_cart",
                            "priority": "high"
                        }
                    },
                    {
                        "type": "add_feature",
                        "data": {
                            "feature": "payment_gateway",
                            "priority": "high"
                        }
                    },
                    {
                        "type": "add_feature",
                        "data": {
                            "feature": "product_catalog",
                            "priority": "medium"
                        }
                    }
                ]
                
                return {
                    "success": True,
                    "operation": "enhance_ecommerce",
                    "diagnostics": diagnostics.get("diagnostics", {}),
                    "enhancement_plan": enhancement_plan,
                    "message": "Ecommerce enhancement planned successfully"
                }
            else:
                return {
                    "success": True,
                    "operation": "enhance_ecommerce",
                    "message": "Ecommerce enhancement planned",
                    "parameters": parameters
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_improve_design(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute 'improve design' global operation"""
        try:
            # Store design improvement plan
            context_result = self.manager.execute_on_server(
                "context7",
                "store",
                data=json.dumps({
                    "operation": "improve_design",
                    "parameters": parameters,
                    "status": "planning"
                })
            )
            
            if not context_result.get("success"):
                return context_result
            
            # Design improvement plan
            design_plan = {
                "improvements": [
                    {
                        "area": "user_interface",
                        "changes": parameters.get("ui_changes", []),
                        "priority": "high"
                    },
                    {
                        "area": "user_experience",
                        "changes": parameters.get("ux_changes", []),
                        "priority": "high"
                    },
                    {
                        "area": "accessibility",
                        "changes": parameters.get("accessibility_changes", []),
                        "priority": "medium"
                    }
                ],
                "timeline": parameters.get("timeline", "2 weeks"),
                "resources_required": parameters.get("resources", [])
            }
            
            return {
                "success": True,
                "operation": "improve_design",
                "design_plan": design_plan,
                "message": "Design improvement planned successfully"
            }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_system_diagnostics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute system diagnostics global operation"""
        try:
            # Run comprehensive system diagnostics
            if self.atlas_healing:
                diagnostics = self.atlas_healing.diagnose_system()
                analysis = self.atlas_healing.analyze_error_patterns(
                    parameters.get("error_context", {})
                )
                
                return {
                    "success": True,
                    "operation": "system_diagnostics",
                    "diagnostics": diagnostics.get("diagnostics", {}),
                    "analysis": analysis.get("analysis", {}),
                    "message": "System diagnostics completed successfully"
                }
            else:
                # Basic diagnostics without Atlas Healing
                mcp_status = self.get_mcp_status()
                
                return {
                    "success": True,
                    "operation": "system_diagnostics",
                    "mcp_status": mcp_status,
                    "message": "Basic system diagnostics completed"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def integrate_with_atlas(self, atlas_instance):
        """Integrate with Atlas system"""
        if not self.is_available():
            return False
        
        try:
            # Store integration context
            context_result = self.manager.execute_on_server(
                "context7",
                "store",
                data=json.dumps({
                    "integration": "atlas_mcp",
                    "status": "connected",
                    "timestamp": datetime.now().isoformat()
                })
            )
            
            return context_result.get("success", False)
            
        except Exception as e:
            print(f"Failed to integrate with Atlas: {e}")
            return False
    
    def get_global_operation_capabilities(self) -> Dict[str, Any]:
        """Get available global operation capabilities"""
        capabilities = {
            "available_operations": [
                "create_website",
                "enhance_ecommerce",
                "improve_design",
                "system_diagnostics"
            ],
            "mcp_servers": [
                "context7",
                "sonarqube"
            ],
            "modes_available": {
                "atlas_healing": self.atlas_healing is not None,
                "dev_project": self.dev_project is not None
            }
        }
        
        return capabilities


_mcp_tool: Optional[MCPIntegrationTool] = None


def get_mcp_tool() -> MCPIntegrationTool:
    """Get the global MCP integration tool instance"""
    global _mcp_tool
    if _mcp_tool is None:
        _mcp_tool = MCPIntegrationTool()
    return _mcp_tool


# Integration with Trinity's MCPToolRegistry
def register_mcp_tools_with_trinity(registry):
    """
    Register MCP integration tools with Trinity's MCPToolRegistry
    
    Args:
        registry: The MCPToolRegistry instance from core.mcp
    """
    try:
        mcp_tool = get_mcp_tool()

        # Register MCP system diagnostics tool
        def mcp_system_diagnostics(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Run MCP system diagnostics"""
            if not mcp_tool.is_available():
                return {"success": False, "error": "MCP integration not available"}
            
            return mcp_tool.execute_global_operation('system_diagnostics', 
                task_data.get('error_context', {}))
        
        registry.register_tool(
            "mcp_system_diagnostics",
            mcp_system_diagnostics,
            "Run comprehensive system diagnostics using MCP integration"
        )
        
        # Register MCP project creation tool
        def mcp_create_project(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Create a development project using MCP"""
            if not mcp_tool.is_available():
                return {"success": False, "error": "MCP integration not available"}
            
            project_config = {
                "name": task_data.get("project_name", "New Project"),
                "type": task_data.get("project_type", "web"),
                "description": task_data.get("description", ""),
                "features": task_data.get("features", [])
            }
            
            return mcp_tool.create_development_project(project_config)
        
        registry.register_tool(
            "mcp_create_project",
            mcp_create_project,
            "Create a new development project with MCP integration"
        )
        
        # Register MCP healing tool
        def mcp_start_healing(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Start Atlas healing session using MCP"""
            if not mcp_tool.is_available():
                return {"success": False, "error": "MCP integration not available"}
            
            error_context = {
                "type": task_data.get("error_type", "system_error"),
                "message": task_data.get("error_message", "Unknown error"),
                "severity": task_data.get("severity", "medium")
            }
            
            return mcp_tool.start_atlas_healing_session(error_context)
        
        registry.register_tool(
            "mcp_start_healing",
            mcp_start_healing,
            "Start Atlas healing session using MCP integration"
        )
        
        print("✓ MCP tools registered with Trinity's MCPToolRegistry")
        return True
        
    except Exception as e:
        print(f"✗ Failed to register MCP tools with Trinity: {e}")
        return False


# Auto-register with Trinity if available
try:
    from core.mcp_registry import MCPToolRegistry
    
    # This will be called when Trinity initializes
    def _auto_register_with_trinity():
        """Automatically register MCP tools when Trinity starts"""
        try:
            # We'll register when Trinity creates its registry
            # This is a placeholder for the actual integration
            pass
        except Exception as e:
            print(f"MCP auto-registration deferred: {e}")
    
    # Call auto-registration
    _auto_register_with_trinity()
    
except ImportError:
    # Trinity's MCP module not available yet, that's fine
    pass


if __name__ == "__main__":
    # Test the MCP integration tool
    print("Testing MCP Integration Tool...")
    
    if mcp_tool.is_available():
        print("✓ MCP Integration Tool is available")
        
        # Test status
        status = mcp_tool.get_mcp_status()
        print(f"✓ MCP Status: {status.get('success')}")
        
        # Test capabilities
        capabilities = mcp_tool.get_global_operation_capabilities()
        print(f"✓ Available operations: {len(capabilities['available_operations'])}")
        
        print("🎉 MCP Integration Tool is ready!")
    else:
        print("✗ MCP Integration Tool is not available")