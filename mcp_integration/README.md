# MCP Server Integration

A comprehensive integration system for Context7 MCP and SonarQube MCP servers with specialized modes for Atlas healing and development project management.

## Overview

This package provides a robust framework for interacting with MCP (Microservice Communication Protocol) servers, specifically:

1. **Context7 MCP** - Memory and context management server
2. **SonarQube MCP** - Code quality analysis server

The system includes two specialized operation modes:

- **Atlas Healing Mode** - For system diagnostics, error recovery, and healing operations
- **Dev Project Mode** - For project creation, scaffolding, and management

## Installation

### Prerequisites

- Python 3.8+
- **Node.js/npm** (for Context7 MCP) - https://nodejs.org/
- **Docker** (for SonarQube MCP) - https://www.docker.com/products/docker-desktop
- pip

### Setup Instructions

#### 1. Install System Dependencies

**Node.js (for Context7 MCP):**
```bash
# macOS with Homebrew
brew install node

# Or download from: https://nodejs.org/

# Verify installation
node --version
npm --version
```

**Docker (for SonarQube MCP):**
```bash
# Download Docker Desktop from: https://www.docker.com/products/docker-desktop
# Or install with Homebrew:
brew install --cask docker

# Start Docker daemon
open -a Docker

# Verify installation
docker --version
docker ps  # Should not error
```

#### 2. Python Setup

```bash
# Clone the repository or copy the mcp_integration directory
# Install required Python packages
pip install -r requirements.txt
```

#### 3. Configure MCP Servers

**Context7 MCP** will be automatically discovered via npx when needed.

**SonarQube MCP** requires environment configuration:

```bash
# Set SonarQube credentials in your environment
export SONARQUBE_TOKEN="your_sonarqube_token_here"
export SONARQUBE_URL="https://sonarqube.example.com"
export SONARQUBE_ORG="your_org_name"

# Or edit mcp_integration/config/mcp_config.json directly
```

#### 4. Test MCP Availability (Optional)

```bash
# Test Context7 MCP
npx @upstash/context7-mcp --version

# Test SonarQube MCP (requires Docker running)
docker run --rm mcp/sonarqube --version
```

### Automatic Setup

The `setup.sh` script in the project root will automatically:
1. ✅ Check for Node.js and npm
2. ✅ Check for Docker and verify daemon is running
3. ✅ Test MCP server accessibility
4. ⚠️  Warn if any dependencies are missing
5. ✅ Configure Python virtual environment with all dependencies

## Configuration

The system uses a JSON configuration file located at `mcp_integration/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "description": "Context7 MCP Server",
      "timeout": 30000,
      "retryAttempts": 3
    },
    "sonarqube": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "SONARQUBE_TOKEN", "-e", "SONARQUBE_ORG", "-e", "SONARQUBE_URL", "mcp/sonarqube", "stdio"],
      "env": {
        "SONARQUBE_TOKEN": "your_token_here",
        "SONARQUBE_URL": "your_url_here",
        "SONARQUBE_ORG": "your_org_here"
      },
      "description": "SonarQube MCP Server",
      "timeout": 60000,
      "retryAttempts": 2
    }
  },
  "defaultServer": "context7",
  "logging": {
    "level": "info",
    "file": "mcp_integration.log",
    "maxSize": "10MB",
    "maxFiles": 5
  }
}
```

## Usage

### Basic Usage

```python
from mcp_integration import create_mcp_integration

# Initialize the integration
mcp = create_mcp_integration()

# Access components
manager = mcp["manager"]
atlas_healing = mcp["atlas_healing"]
dev_project = mcp["dev_project"]

# Connect to all MCP servers
connections = manager.connect_all()
print("Connection results:", connections)

# Get server statuses
statuses = manager.get_all_status()
print("Server statuses:", statuses)
```

### Atlas Healing Mode

```python
# Start a healing session
error_context = {
    "type": "system_error",
    "message": "Context7 MCP server connection timeout",
    "severity": "high"
}

healing_result = atlas_healing.start_healing_session(error_context)
print("Healing session started:", healing_result)

# Run system diagnostics
diagnostics = atlas_healing.diagnose_system()
print("System diagnostics:", diagnostics)

# Analyze error patterns
analysis = atlas_healing.analyze_error_patterns(error_context)
print("Error analysis:", analysis)

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

actions_result = atlas_healing.apply_healing_actions(healing_actions)
print("Healing actions applied:", actions_result)

# End healing session
end_result = atlas_healing.end_healing_session("completed")
print("Healing session ended:", end_result)
```

### Dev Project Mode

```python
# Create a new project
project_config = {
    "name": "My Web Application",
    "type": "web",
    "description": "A sample web application",
    "version": "1.0.0",
    "author": "Developer"
}

project_result = dev_project.create_project(project_config)
print("Project created:", project_result)

# Set up SonarQube analysis
if project_result.get("success"):
    project_id = project_result["project_id"]
    sonarqube_result = dev_project.setup_sonarqube_analysis(project_id)
    print("SonarQube setup:", sonarqube_result)
    
    # Run SonarQube analysis
    analysis_result = dev_project.run_sonarqube_analysis(project_id)
    print("SonarQube analysis:", analysis_result)
    
    # Get quality gate status
    qg_result = dev_project.get_quality_gate_status(project_id)
    print("Quality gate status:", qg_result)

# Get project history
history = dev_project.get_project_history()
print("Project history:", history)
```

## Architecture

```
mcp_integration/
├── config/
│   ├── mcp_config.json          # Main configuration
│   └── server_specific/         # Server-specific configs
├── core/
│   ├── mcp_manager.py           # Main MCP manager
│   ├── context7_client.py       # Context7 client
│   ├── sonarqube_client.py      # SonarQube client
│   └── server_factory.py        # Client factory
├── modes/
│   ├── atlas_healing_mode.py    # Atlas healing mode
│   └── dev_project_mode.py      # Dev project mode
├── utils/
│   ├── config_loader.py         # Config utilities
│   ├── error_handler.py         # Error handling
│   └── logging_setup.py         # Logging config
├── tests/
│   ├── test_context7.py         # Context7 tests
│   ├── test_sonarqube.py        # SonarQube tests
│   └── test_integration.py      # Integration tests
├── __init__.py                  # Package initialization
└── README.md                    # Documentation
```

## Key Features

### MCP Manager
- **Multi-server support**: Manage multiple MCP servers simultaneously
- **Connection management**: Automatic connection handling and retries
- **Command execution**: Unified interface for executing commands
- **Status monitoring**: Health checks and status reporting

### Context7 Client
- **Context storage**: Store and retrieve contextual information
- **Memory management**: Efficient memory operations
- **Query capabilities**: Advanced context querying

### SonarQube Client
- **Code analysis**: Run comprehensive code quality analysis
- **Quality gates**: Monitor project quality status
- **Configuration management**: Project-specific analysis setup

### Atlas Healing Mode
- **System diagnostics**: Comprehensive system health checks
- **Error analysis**: Pattern recognition and root cause analysis
- **Automated healing**: Apply corrective actions
- **Session management**: Track healing sessions and outcomes

### Dev Project Mode
- **Project scaffolding**: Automatic project structure creation
- **Template system**: Project-type-specific templates
- **SonarQube integration**: Built-in code quality setup
- **Project management**: History tracking and metadata storage

## Error Handling

The system includes comprehensive error handling:

- **Connection errors**: Automatic retries and fallback mechanisms
- **Command failures**: Detailed error reporting and logging
- **Validation errors**: Input validation and configuration checks
- **Resource management**: Proper cleanup and resource handling

## Logging

All operations are logged with detailed information:

- **Timestamps**: Precise operation timing
- **Context**: Operation context and parameters
- **Results**: Success/failure outcomes
- **Errors**: Detailed error information

## Testing

The package includes comprehensive testing:

```bash
# Run all tests
python -m pytest mcp_integration/tests/

# Run specific tests
python -m pytest mcp_integration/tests/test_context7.py
python -m pytest mcp_integration/tests/test_sonarqube.py
```

## Best Practices

1. **Configuration Management**: Store sensitive data in environment variables
2. **Error Handling**: Always check operation results and handle errors
3. **Resource Cleanup**: Properly close connections and release resources
4. **Logging**: Maintain comprehensive logs for debugging
5. **Testing**: Test thoroughly before production deployment

## Troubleshooting

### Common Issues

1. **Connection failures**: Check server availability and network connectivity
2. **Authentication errors**: Verify API tokens and credentials
3. **Timeout issues**: Adjust timeout settings in configuration
4. **Permission problems**: Ensure proper file system permissions

### Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run operations with detailed logging
```

## Future Enhancements

- **Additional MCP servers**: Support for more MCP server types
- **Advanced analytics**: Machine learning-based error analysis
- **CI/CD integration**: Built-in continuous integration support
- **Monitoring dashboard**: Visual monitoring and management interface

## License

This project is licensed under the MIT License.

## Support

For issues, questions, or contributions, please contact the development team.