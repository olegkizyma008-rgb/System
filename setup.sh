#!/bin/bash
# Trinity System Setup Script

echo "🚀 Starting Trinity System Setup..."

# 1. Python 3.12 Environment
echo "🐍 Checking Python 3.12 environment..."

# Check if python3.12 is installed
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "❌ Python 3.12 is not installed. Please install it: brew install python@3.12"
    exit 1
fi

# Create or verify .venv
if [ ! -d ".venv" ]; then
    echo "� Creating virtual environment with Python 3.12..."
    python3.12 -m venv .venv
else
    # Check if existing .venv is 3.12
    VENV_VERSION=$(.venv/bin/python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [ "$VENV_VERSION" != "3.12" ]; then
        echo "⚠️  Existing .venv is version $VENV_VERSION. Recreating with 3.12..."
        rm -rf .venv
        python3.12 -m venv .venv
    else
        echo "✅ Existing .venv is Python 3.12."
    fi
fi

source .venv/bin/activate
echo "📦 Installing Python dependencies into .venv..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Patching mcp-pyautogui-server
echo "🛠️ Patching mcp-pyautogui-server..."
SERVER_FILE=".venv/lib/python3.12/site-packages/mcp_pyautogui_server/server.py"

if [ -f "$SERVER_FILE" ]; then
    # Fix Image import
    sed -i '' 's/from fastmcp import FastMCP, Image/from fastmcp import FastMCP/g' "$SERVER_FILE"
    
    # Fix FastMCP init
    sed -i '' 's/mcp = FastMCP("MCP Pyautogui Server", dependencies=\["pyautogui", "Pillow"\])/mcp = FastMCP("MCP Pyautogui Server")/g' "$SERVER_FILE"
    
    # Fix screenshot tool types and base64 return
    # This is more complex for sed, but we can do a simple replacement for the common signature and return
    sed -i '' 's/def screenshot() -> Image | Dict\[str, str\]:/def screenshot() -> Dict[str, str]:/g' "$SERVER_FILE"
    # Note: The full base64 return logic is already manually patched, 
    # but this ensures basic functionality if reinstalled.
    echo "✅ Patched $SERVER_FILE"
else
    echo "⚠️  $SERVER_FILE not found, skipping patch."
fi

# 2. Node.js & Playwright setup (for external MCP)
echo "🌐 Checking Node.js for Playwright MCP..."
if ! command -v node >/dev/null 2>&1; then
    echo "❌ Node.js is not installed. Please install it: brew install node"
else
    echo "✅ Node.js found: $(node -v)"
    echo "🎭 Installing Playwright browsers..."
    npx playwright install chromium
fi

# 3. Cleanup Scripts Permissions
if [ -d "cleanup_scripts" ]; then
    echo "🛡️  Setting permissions for cleanup scripts..."
    chmod +x cleanup_scripts/*.sh
    echo "✅ Cleanup scripts are now executable."
fi

# 3. Patching mcp-pyautogui-server if needed
# (This is a workaround for the broken site-package version)
# We can add a more permanent patch logic here if desired.

echo "✅ Setup complete! You can now run the system using ./cli.sh"
