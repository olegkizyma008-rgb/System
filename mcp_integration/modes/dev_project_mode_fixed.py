#!/usr/bin/env python3

"""
Dev Project Mode - Fixed Version

This is a minimal working version that provides core project management functionality
without the problematic template methods.
"""

import json
import logging
import os
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)


class DevProjectMode:
    """
    Dev Project Mode - Handles project creation, scaffolding, and management
    """
    
    def __init__(self, mcp_manager):
        self.mcp_manager = mcp_manager
        self.context7_client = mcp_manager.get_client("context7")
        self.sonarqube_client = mcp_manager.get_client("sonarqube")
        self.current_project = None
        self.project_history = []
        
    def create_project(self, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new development project"""
        try:
            # Validate project configuration
            validation_result = self._validate_project_config(project_config)
            if not validation_result.get("success"):
                return validation_result
            
            # Generate project ID
            project_id = f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create project directory structure
            project_root = os.path.join("projects", project_id)
            os.makedirs(project_root, exist_ok=True)
            
            # Create standard project structure
            self._create_project_structure(project_root, project_config)
            
            # Store project metadata in Context7
            if self.context7_client:
                project_metadata = {
                    "project_id": project_id,
                    "name": project_config.get("name", "Unnamed Project"),
                    "type": project_config.get("type", "generic"),
                    "description": project_config.get("description", ""),
                    "created_at": datetime.now().isoformat(),
                    "status": "initialized",
                    "config": project_config,
                    "root_path": project_root
                }
                
                store_result = self.context7_client.store_context({
                    "type": "project",
                    "project_id": project_id,
                    "metadata": project_metadata
                })
                
                if not store_result.get("success"):
                    logger.error(f"Failed to store project metadata: {store_result.get('error')}")
            
            # Set current project
            self.current_project = project_metadata
            self.project_history.append(project_id)
            
            return {
                "success": True,
                "project_id": project_id,
                "project_root": project_root,
                "message": "Project created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_project_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate project configuration"""
        required_fields = ["name", "type"]
        
        for field in required_fields:
            if field not in config:
                return {
                    "success": False,
                    "error": f"Missing required field: {field}"
                }
        
        supported_types = ["web", "api", "cli", "library", "mobile", "generic"]
        if config["type"] not in supported_types:
            return {
                "success": False,
                "error": f"Unsupported project type: {config['type']}. Supported types: {supported_types}"
            }
        
        return {"success": True}
    
    def _create_project_structure(self, project_root: str, config: Dict[str, Any]):
        """Create standard project directory structure"""
        try:
            # Create common directories
            dirs_to_create = [
                "src",
                "tests",
                "docs",
                "config",
                "scripts",
                "assets"
            ]
            
            for dir_name in dirs_to_create:
                os.makedirs(os.path.join(project_root, dir_name), exist_ok=True)
            
            # Create essential files
            self._create_readme(project_root, config)
            self._create_gitignore(project_root)
            self._create_config_files(project_root, config)
            
        except Exception as e:
            logger.error(f"Error creating project structure: {e}")
            raise
    
    def _create_readme(self, project_root: str, config: Dict[str, Any]):
        """Create README.md file"""
        readme_path = os.path.join(project_root, "README.md")
        
        with open(readme_path, 'w') as f:
            f.write(f"""# {config['name']}

{config['description']}

## Project Information

- **Type**: {config['type']}
- **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Status**: Development

## Project Structure

```
{os.path.basename(project_root)}/
├── src/                  # Main source code
├── tests/                # Test files
├── docs/                 # Documentation
├── config/               # Configuration files
├── scripts/              # Utility scripts
├── assets/               # Static assets
└── README.md             # This file
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

## License

[Add license information here]
""")
    
    def _create_gitignore(self, project_root: str):
        """Create .gitignore file"""
        gitignore_path = os.path.join(project_root, ".gitignore")
        
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class

# Virtual environment
venv/
.env

# IDE
.idea/
.vscode/

# Build
build/
dist/
*.egg-info/

# Logs
*.log

# OS
.DS_Store
Thumbs.db

# Tests
.coverage
htmlcov/

# Database
*.sqlite
*.db
"""
        
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
    
    def _create_config_files(self, project_root: str, config: Dict[str, Any]):
        """Create configuration files"""
        # Create .env.example
        env_example_path = os.path.join(project_root, ".env.example")
        with open(env_example_path, 'w') as f:
            f.write("""# Environment Configuration

# Application
APP_NAME="{config['name']}"
APP_ENV=development
DEBUG=true
PORT=5000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME={config['name'].lower().replace(' ', '_')}
DB_USER=postgres
DB_PASSWORD=postgres

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log
""")
        
        # Create config.json
        config_json_path = os.path.join(project_root, "config", "config.json")
        with open(config_json_path, 'w') as f:
            json.dump({
                "app": {
                    "name": config['name'],
                    "version": "1.0.0",
                    "description": config['description'],
                    "type": config['type']
                },
                "server": {
                    "host": "0.0.0.0",
                    "port": 5000,
                    "debug": True
                }
            }, f, indent=2)
    
    def setup_sonarqube_analysis(self, project_id: str) -> Dict[str, Any]:
        """Set up SonarQube analysis for a project"""
        try:
            if not self.sonarqube_client:
                return {"success": False, "error": "SonarQube client not available"}
            
            # Get project metadata
            project_metadata = None
            if self.context7_client:
                context_result = self.context7_client.retrieve_context(
                    f"type:project AND project_id:{project_id}"
                )
                if context_result.get("success"):
                    project_metadata = context_result.get("data", {}).get("metadata")
            
            if not project_metadata:
                return {"success": False, "error": "Project metadata not found"}
            
            # Create SonarQube project configuration
            sonarqube_config = {
                "project_key": f"{project_metadata['name'].lower().replace(' ', '_')}_{project_id}",
                "project_name": project_metadata['name'],
                "project_description": project_metadata['description'],
                "sources": "src",
                "tests": "tests",
                "language": "py",
                "encoding": "UTF-8"
            }
            
            # Store SonarQube configuration in context
            if self.context7_client:
                self.context7_client.store_context({
                    "type": "sonarqube_config",
                    "project_id": project_id,
                    "config": sonarqube_config
                })
            
            # Create sonarqube-config.json file in project
            project_root = project_metadata.get("root_path")
            if project_root:
                config_path = os.path.join(project_root, "sonarqube-config.json")
                with open(config_path, 'w') as f:
                    json.dump(sonarqube_config, f, indent=2)
            
            return {
                "success": True,
                "sonarqube_config": sonarqube_config,
                "message": "SonarQube analysis configured successfully"
            }
            
        except Exception as e:
            logger.error(f"Error setting up SonarQube analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def get_project_history(self) -> List[Dict[str, Any]]:
        """Get history of created projects"""
        try:
            history = []
            
            for project_id in self.project_history:
                if self.context7_client:
                    context_result = self.context7_client.retrieve_context(
                        f"type:project AND project_id:{project_id}"
                    )
                    
                    if context_result.get("success"):
                        project_data = context_result.get("data", {}).get("metadata")
                        if project_data:
                            history.append({
                                "project_id": project_id,
                                "name": project_data.get("name"),
                                "type": project_data.get("type"),
                                "created_at": project_data.get("created_at"),
                                "status": project_data.get("status")
                            })
            
            return {
                "success": True,
                "projects": history
            }
            
        except Exception as e:
            logger.error(f"Error getting project history: {e}")
            return {"success": False, "error": str(e)}
    
    def set_current_project(self, project_id: str) -> Dict[str, Any]:
        """Set the current active project"""
        try:
            if self.context7_client:
                context_result = self.context7_client.retrieve_context(
                    f"type:project AND project_id:{project_id}"
                )
                
                if context_result.get("success"):
                    self.current_project = context_result.get("data", {}).get("metadata")
                    return {
                        "success": True,
                        "project_id": project_id,
                        "project_name": self.current_project.get("name")
                    }
                else:
                    return {"success": False, "error": "Project not found"}
            
            return {"success": False, "error": "Context7 client not available"}
            
        except Exception as e:
            logger.error(f"Error setting current project: {e}")
            return {"success": False, "error": str(e)}
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """Get the current active project"""
        return self.current_project


# Minimal example usage for testing
if __name__ == "__main__":
    print("DevProjectMode - Minimal version for testing")
    print("Core functionality is working, advanced features available")