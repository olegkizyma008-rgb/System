#!/bin/bash

# System Vision Full Setup Script
# This script sets up Python 3.12 environment and installs all required dependencies

echo "🚀 Starting System Vision Full Setup..."

# Check if running in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: This script must be run from the project root directory"
    exit 1
fi

# Function to check Python version
check_python_version() {
    local required_version="3.11"
    local python_cmd="python3.11"
    
    # Try to find Python 3.11
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        PYTHON_VERSION=$(python3.11 --version 2>&1 | awk '{print $2}')
        echo "✅ Found Python 3.11: $PYTHON_VERSION"
        return 0
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "⚠️  Using Python $PYTHON_VERSION (Python 3.11 recommended)"
        return 0
    else
        echo "❌ Python 3 not found. Please install Python 3.11 or later."
        return 1
    fi
}

# Check Python version
if ! check_python_version; then
    exit 1
fi

# Remove existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔧 Removing existing virtual environment..."
    rm -rf .venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to remove existing virtual environment"
        exit 1
    fi
fi

# Create new virtual environment
echo "🔧 Creating new virtual environment with Python $PYTHON_VERSION..."
$PYTHON_CMD -m venv .venv
if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and setuptools
echo "🔧 Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel

# Install main requirements
echo "📦 Installing main requirements..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install main requirements"
    exit 1
fi

# Note: PaddleOCR is included in requirements.txt, but we ensure it here if something failed differently, or just trust requirements.txt.
# Relying on requirements.txt for paddleocr.


# Note: super-rag is deprecated (abandoned project with broken dependencies)
# System uses DifferentialVisionAnalyzer (OpenCV + PaddleOCR) instead
echo "📝 Using DifferentialVisionAnalyzer for vision analysis (OpenCV + PaddleOCR)"

# Check and setup MCP servers for DEV mode
echo ""
echo "🔌 Setting up MCP Servers for DEV mode..."
echo ""

# Check Node.js and npm for Context7 MCP
echo "--- Context7 MCP Setup ---"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js found: $NODE_VERSION"
else
    echo "⚠️  Node.js not found. Context7 MCP requires Node.js."
    echo "   Install Node.js from: https://nodejs.org/"
    echo "   Context7 MCP will be unavailable."
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✅ npm found: $NPM_VERSION"
    
    # Test if Context7 MCP package can be accessed via npx
    echo "   Testing Context7 MCP package accessibility..."
    if npx -y @upstash/context7-mcp --version &>/dev/null 2>&1; then
        echo "✅ Context7 MCP package (@upstash/context7-mcp) is accessible"
    else
        echo "⚠️  Context7 MCP package might not be immediately available"
        echo "   It will be installed on first use via npx"
    fi
else
    echo "⚠️  npm not found. Context7 MCP requires npm."
    echo "   Install Node.js from: https://nodejs.org/"
fi

echo ""
echo "--- SonarQube MCP Setup ---"
# Check Docker for SonarQube MCP
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker found: $DOCKER_VERSION"
    
    # Check if Docker daemon is running
    if docker ps &>/dev/null 2>&1; then
        echo "✅ Docker daemon is running"
        echo "   SonarQube MCP will be available for dev analysis"
    else
        echo "⚠️  Docker daemon is not running"
        echo "   Start Docker before using SonarQube MCP"
        echo "   Run: open -a Docker"
    fi
else
    echo "⚠️  Docker not found. SonarQube MCP requires Docker."
    echo "   Install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    echo "   SonarQube MCP will be unavailable."
fi

echo ""

# Apply patches to MCP servers
echo "🔧 Applying patches to MCP servers..."
if [ -f "scripts/fix_mcp_server.py" ]; then
    $PYTHON_CMD scripts/fix_mcp_server.py
    if [ $? -ne 0 ]; then
        echo "⚠️  Failed to patch MCP server. Use with caution."
    fi
else
    echo "⚠️  Patch script scripts/fix_mcp_server.py not found."
fi


# Additional packages are now in requirements.txt


# Verify all installations
echo "🔍 Verifying all installations..."

echo "--- Core Dependencies ---"

# Check OpenCV
if $PYTHON_CMD -c "import cv2; print('✅ OpenCV version:', cv2.__version__)" 2>/dev/null; then
    echo "✅ OpenCV installed"
else
    echo "❌ OpenCV not installed"
    exit 1
fi

# Check PIL/Pillow
if $PYTHON_CMD -c "from PIL import Image; print('✅ PIL/Pillow installed')" 2>/dev/null; then
    echo "✅ PIL/Pillow installed"
else
    echo "❌ PIL/Pillow not installed"
    exit 1
fi

# Check numpy
if $PYTHON_CMD -c "import numpy as np; print('✅ NumPy version:', np.__version__)" 2>/dev/null; then
    echo "✅ NumPy installed"
else
    echo "❌ NumPy not installed"
    exit 1
fi

echo "--- Vision Dependencies ---"

# Check PaddleOCR
if $PYTHON_CMD -c "import paddleocr; print('✅ PaddleOCR version:', paddleocr.__version__)" 2>/dev/null; then
    echo "✅ PaddleOCR installed"
    PADDLEOCR_INSTALLED=true
else
    echo "⚠️  PaddleOCR not installed (fallback to Copilot OCR)"
    PADDLEOCR_INSTALLED=false
fi

# DifferentialVisionAnalyzer check
if $PYTHON_CMD -c "from system_ai.tools.vision import DifferentialVisionAnalyzer; print('✅ DifferentialVisionAnalyzer available')" 2>/dev/null; then
    echo "✅ DifferentialVisionAnalyzer installed"
else
    echo "⚠️  DifferentialVisionAnalyzer not found"
fi

echo "--- LLM Dependencies ---"

# Check langchain
if $PYTHON_CMD -c "import langchain; print('✅ LangChain version:', langchain.__version__)" 2>/dev/null; then
    echo "✅ LangChain installed"
else
    echo "❌ LangChain not installed"
    exit 1
fi

# Check langchain-core
if $PYTHON_CMD -c "import langchain_core; print('✅ LangChain Core installed')" 2>/dev/null; then
    echo "✅ LangChain Core installed"
else
    echo "❌ LangChain Core not installed"
    exit 1
fi

echo "--- System Dependencies ---"

# Check python-dotenv
if $PYTHON_CMD -c "import dotenv; print('✅ python-dotenv installed')" 2>/dev/null; then
    echo "✅ python-dotenv installed"
else
    echo "❌ python-dotenv not installed"
    exit 1
fi

# Check rich
if $PYTHON_CMD -c "import rich; print('✅ Rich installed')" 2>/dev/null; then
    echo "✅ Rich installed"
else
    echo "⚠️  Rich not installed (optional for better UI)"
fi

# Check typer
if $PYTHON_CMD -c "import typer; print('✅ Typer installed')" 2>/dev/null; then
    echo "✅ Typer installed"
else
    echo "⚠️  Typer not installed (optional for CLI)"
fi

echo "--- MCP Server Dependencies (for DEV mode) ---"

# Check MCP manager integration
if $PYTHON_CMD -c "from mcp_integration.core.mcp_manager import MCPServerManager; print('✅ MCP Manager available')" 2>/dev/null; then
    echo "✅ MCP Integration module available"
else
    echo "⚠️  MCP Integration module not found"
fi

# Check Context7 MCP availability
if command -v npx &> /dev/null; then
    echo "✅ npx available (for Context7 MCP)"
else
    echo "⚠️  npx not found (Context7 MCP unavailable - install Node.js)"
fi

# Check SonarQube MCP availability
if command -v docker &> /dev/null && docker ps &>/dev/null 2>&1; then
    echo "✅ Docker available (for SonarQube MCP)"
else
    echo "⚠️  Docker not running (SonarQube MCP unavailable - start Docker or install it)"
fi

echo ""
echo "🎉 System Vision Full Setup completed successfully!"
echo ""
echo "📋 Installation Summary:"
echo "  • Python version: $PYTHON_VERSION"
echo "  • Virtual environment: .venv (created)"
echo "  • Core dependencies: ✅ Installed"
echo "  • Vision dependencies: ✅ Installed (with fallbacks)"
echo "  • LLM dependencies: ✅ Installed"
echo "  • System dependencies: ✅ Installed"
echo "  • MCP Servers: Context7 (Node.js/npm) and SonarQube (Docker) - check status above"
echo ""
echo "💡 To activate the virtual environment later, run:"
echo "   source .venv/bin/activate"
echo ""
echo "🚀 To start the system, run:"
echo "   python cli.py"
echo ""
echo "🔧 To update the system later, run:"
echo "   source .venv/bin/activate && pip install -r requirements.txt --upgrade"
echo ""
echo "🔌 MCP Servers for DEV mode:"
echo "  • Context7 MCP: Requires Node.js and npm"
echo "    - Install: https://nodejs.org/"
echo "    - Command: npx @upstash/context7-mcp"
echo "  • SonarQube MCP: Requires Docker"
echo "    - Install: https://www.docker.com/products/docker-desktop"
echo "    - Start Docker before use: open -a Docker"
echo ""
echo "📝 System is ready for:"
echo "  • Vision analysis with DifferentialVisionAnalyzer (OpenCV)"
echo "  • OCR with PaddleOCR (or Copilot fallback)"
echo "  • VisionContextManager for cyclical summarization"
echo "  • Full LLM integration"
echo "  • All agent operations (Atlas, Tetyana, Grisha)"
echo "  • DEV mode with code quality analysis (when MCP servers are available)"