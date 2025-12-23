#!/bin/bash

echo "🚀 Setting up MCP Servers..."

# Install Playwright MCP Server (PRIORITY 1)
echo "📦 Installing Playwright MCP Server..."
npm install -g @executeautomation/playwright-mcp-server
if [ $? -eq 0 ]; then
    echo "✅ Playwright MCP Server installed"
else
    echo "❌ Playwright MCP Server failed"
fi

# Install AppleScript MCP Server (PRIORITY 2)
echo "📦 Installing AppleScript MCP Server..."
npm install -g @iflow-mcp/applescript-mcp
if [ $? -eq 0 ]; then
    echo "✅ AppleScript MCP Server installed"
else
    echo "❌ AppleScript MCP Server failed"
fi

# Install PyAutoGUI MCP Server (PRIORITY 3)
echo "📦 Installing PyAutoGUI MCP Server..."
pip install mcp-pyautogui-server
if [ $? -eq 0 ]; then
    echo "✅ PyAutoGUI MCP Server installed"
else
    echo "❌ PyAutoGUI MCP Server failed"
fi

echo "🎉 MCP Server setup complete!"
echo "Run: python mcp_integration/check_servers.py to verify"
