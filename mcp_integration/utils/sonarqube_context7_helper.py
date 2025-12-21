#!/usr/bin/env python3

"""
SonarQube Context7 Integration Helper
Helper functions for integrating SonarQube with Context7 documentation
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SonarQubeContext7Helper:
    """Helper class for SonarQube and Context7 integration"""
    
    def __init__(self, mcp_manager):
        """
        Initialize helper with MCP manager
        
        Args:
            mcp_manager: MCPManager instance with both SonarQube and Context7 clients
        """
        self.mcp_manager = mcp_manager
        self.sonarqube_client = mcp_manager.get_client("sonarqube")
        self.context7_client = mcp_manager.get_client("context7")
        self.context7_docs_client = mcp_manager.get_client("context7-docs")
        
    def resolve_sonarqube_library(self) -> Dict[str, Any]:
        """
        Resolve SonarQube library ID for Context7 documentation
        Uses the mcp_io_github_ups_resolve-library-id tool
        
        Returns:
            Dict with library information including Context7-compatible ID
        """
        try:
            # This would call: mcp_io_github_ups_resolve-library-id
            # with libraryName: "sonarqube"
            
            return {
                "success": True,
                "library_id": "/SonarSource/sonarqube",
                "library_name": "SonarQube",
                "description": "Continuous Code Quality and Security Analysis",
                "note": "Use this ID with mcp_io_github_ups_get-library-docs"
            }
        except Exception as e:
            logger.error(f"Failed to resolve SonarQube library: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_sonarqube_api_docs(self, topic: str = None, mode: str = "code", page: int = 1) -> Dict[str, Any]:
        """
        Get SonarQube API documentation from Context7
        Uses the mcp_io_github_ups_get-library-docs tool
        
        Args:
            topic: Specific API topic (e.g., 'webhooks', 'issues', 'quality-gates')
            mode: 'code' for API references, 'info' for conceptual guides
            page: Page number for pagination (default: 1)
        
        Returns:
            Dict with documentation content
        """
        try:
            # This would call: mcp_io_github_ups_get-library-docs
            # with context7CompatibleLibraryID: "/SonarSource/sonarqube"
            # mode: code or info
            # topic: specific topic
            # page: page number
            
            return {
                "success": True,
                "library_id": "/SonarSource/sonarqube",
                "topic": topic or "general",
                "mode": mode,
                "page": page,
                "documentation": "Use mcp_io_github_ups_get-library-docs tool to retrieve actual documentation",
                "note": "This is a helper method - actual implementation requires calling the MCP tool"
            }
        except Exception as e:
            logger.error(f"Failed to get SonarQube docs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_sonarqube_webhook_docs(self) -> Dict[str, Any]:
        """Get SonarQube webhook documentation"""
        return self.get_sonarqube_api_docs(topic="webhooks", mode="code")
    
    def get_sonarqube_issues_docs(self) -> Dict[str, Any]:
        """Get SonarQube issues API documentation"""
        return self.get_sonarqube_api_docs(topic="issues", mode="code")
    
    def get_sonarqube_quality_gates_docs(self) -> Dict[str, Any]:
        """Get SonarQube quality gates documentation"""
        return self.get_sonarqube_api_docs(topic="quality-gates", mode="code")
    
    def get_sonarqube_projects_docs(self) -> Dict[str, Any]:
        """Get SonarQube projects API documentation"""
        return self.get_sonarqube_api_docs(topic="projects", mode="code")
    
    def integrate_with_project(self, project_id: str, sonarqube_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate SonarQube with a project and store configuration in Context7
        
        Args:
            project_id: Project identifier
            sonarqube_config: SonarQube configuration dict
        
        Returns:
            Dict with integration result
        """
        try:
            if not self.context7_client:
                return {
                    "success": False,
                    "error": "Context7 client not available"
                }
            
            # Store SonarQube configuration in Context7
            context_data = {
                "type": "sonarqube_integration",
                "project_id": project_id,
                "config": sonarqube_config,
                "documentation_library": "/SonarSource/sonarqube",
                "integration_status": "active"
            }
            
            result = self.context7_client.store_context(context_data)
            
            return {
                "success": result.get("success", False),
                "project_id": project_id,
                "message": "SonarQube configuration integrated with Context7",
                "context_stored": result.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to integrate SonarQube with project: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_analysis_with_docs(self, project_key: str, include_docs: bool = True) -> Dict[str, Any]:
        """
        Run SonarQube analysis and optionally include relevant documentation
        
        Args:
            project_key: SonarQube project key
            include_docs: Whether to include relevant documentation links
        
        Returns:
            Dict with analysis results and documentation
        """
        try:
            if not self.sonarqube_client:
                return {
                    "success": False,
                    "error": "SonarQube client not available"
                }
            
            # Get analysis results
            analysis_result = self.sonarqube_client.execute_command(
                "analyze",
                project=project_key
            )
            
            result = {
                "success": analysis_result.get("success", False),
                "analysis": analysis_result.get("data"),
                "project_key": project_key
            }
            
            # Add documentation links if requested
            if include_docs:
                result["documentation"] = {
                    "api_reference": "/SonarSource/sonarqube",
                    "topics": {
                        "issues": "Use get_sonarqube_issues_docs()",
                        "quality_gates": "Use get_sonarqube_quality_gates_docs()",
                        "webhooks": "Use get_sonarqube_webhook_docs()"
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get analysis with docs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_integration(self) -> Dict[str, Any]:
        """
        Verify that SonarQube is properly integrated with Context7
        
        Returns:
            Dict with verification results
        """
        try:
            checks = {
                "sonarqube_client": self.sonarqube_client is not None,
                "context7_client": self.context7_client is not None,
                "context7_docs_client": self.context7_docs_client is not None
            }
            
            all_passed = all(checks.values())
            
            return {
                "success": all_passed,
                "checks": checks,
                "status": "fully_integrated" if all_passed else "partial_integration",
                "missing_components": [k for k, v in checks.items() if not v],
                "recommendations": self._get_recommendations(checks)
            }
            
        except Exception as e:
            logger.error(f"Failed to verify integration: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_recommendations(self, checks: Dict[str, bool]) -> list:
        """Get recommendations based on integration checks"""
        recommendations = []
        
        if not checks.get("sonarqube_client"):
            recommendations.append(
                "Configure SonarQube MCP server in mcp_config.json with proper credentials"
            )
        
        if not checks.get("context7_client"):
            recommendations.append(
                "Ensure Context7 MCP server is configured for context management"
            )
        
        if not checks.get("context7_docs_client"):
            recommendations.append(
                "Add 'context7-docs' client for SonarQube API documentation access"
            )
        
        if not recommendations:
            recommendations.append("Integration is properly configured!")
        
        return recommendations


def create_sonarqube_context7_helper(mcp_manager):
    """
    Factory function to create SonarQubeContext7Helper instance
    
    Args:
        mcp_manager: MCPManager instance
    
    Returns:
        SonarQubeContext7Helper instance
    """
    return SonarQubeContext7Helper(mcp_manager)
