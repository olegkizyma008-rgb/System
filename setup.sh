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

# 4. Git Hook Installation
echo "🪝 Installing git hooks..."
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOK_SRC="$REPO_ROOT/templates/bootstrap/post-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/post-commit"

if [ -f "$HOOK_SRC" ]; then
    cp "$HOOK_SRC" "$HOOK_DST"
    chmod +x "$HOOK_DST"
    echo "✅ Installed post-commit hook."
else
    echo "⚠️  Post-commit template not found at $HOOK_SRC"
fi

# 3. Patching mcp-pyautogui-server if needed
# (This is a workaround for the broken site-package version)
# We can add a more permanent patch logic here if desired.

# 5. Continue CLI Installation (npm)
echo "📦 Installing Continue CLI..."
if command -v npm >/dev/null 2>&1; then
    npm i -g @continuedev/cli cn 2>/dev/null && echo "✅ Continue CLI installed" || echo "⚠️ Continue CLI installation failed (non-critical)"
else
    echo "⚠️ npm not found, skipping Continue CLI"
fi

# 6. Mistral Vibe CLI Installation (pip)
echo "🎵 Installing Mistral Vibe CLI..."
# Install in the activated venv
pip install mistral-vibe 2>/dev/null && echo "✅ Vibe CLI installed" || echo "⚠️ Vibe CLI installation failed (non-critical)"

# 7. Vibe CLI Configuration
VIBE_HOME="${HOME}/.vibe"
if [ ! -d "$VIBE_HOME" ]; then
    mkdir -p "$VIBE_HOME"
    echo "✅ Created Vibe config directory: $VIBE_HOME"
fi

# 8. API Key Validation
echo "🔑 Checking API keys..."
if [ -f ".env" ]; then
    if grep -q "^MISTRAL_API_KEY=" .env; then
        # Check if key is not empty
        MISTRAL_KEY=$(grep "^MISTRAL_API_KEY=" .env | cut -d'=' -f2)
        if [ -n "$MISTRAL_KEY" ] && [ "$MISTRAL_KEY" != "your_key_here" ]; then
            echo "✅ MISTRAL_API_KEY found in .env"
            # Copy to Vibe config if not exists
            if [ ! -f "$VIBE_HOME/.env" ]; then
                echo "MISTRAL_API_KEY=$MISTRAL_KEY" > "$VIBE_HOME/.env"
                echo "✅ Copied MISTRAL_API_KEY to $VIBE_HOME/.env"
            fi
        else
            echo "⚠️ MISTRAL_API_KEY is empty or placeholder in .env - Vibe CLI requires this"
        fi
    else
        echo "⚠️ MISTRAL_API_KEY not found in .env - Vibe CLI requires this"
    fi
else
    echo "⚠️ .env file not found - Create it and add MISTRAL_API_KEY for Vibe CLI"
fi

echo "✅ Setup complete! You can now run the system using ./cli.sh"

