#!/bin/bash

echo "🚀 Setting up all MCP servers and tools..."

# Install Node.js packages
echo "📦 Installing Node.js packages..."
npm install -g @executeautomation/playwright-mcp-server
npm install -g @iflow-mcp/applescript-mcp
npm install -g mcp-pyautogui-server

# Install Python packages
pip install chromadb sentence-transformers

# Create tool examples directory
mkdir -p mcp_integration/core/tool_examples

# Create sample tool examples
cat > mcp_integration/core/tool_examples/browser_examples.json << 'EOF'
[
  {"tool": "browser_navigate", "description": "Navigate to URL", "category": "browser", "server": "playwright"},
  {"tool": "browser_click", "description": "Click element", "category": "browser", "server": "playwright"},
  {"tool": "browser_type", "description": "Type text", "category": "browser", "server": "playwright"},
  {"tool": "browser_screenshot", "description": "Take screenshot", "category": "browser", "server": "playwright"}
]
EOF

cat > mcp_integration/core/tool_examples/system_examples.json << 'EOF'
[
  {"tool": "run_shell", "description": "Execute shell command", "category": "system", "server": "local"},
  {"tool": "open_app", "description": "Open application", "category": "system", "server": "local"},
  {"tool": "run_applescript", "description": "Execute AppleScript", "category": "system", "server": "applescript"}
]
EOF

cat > mcp_integration/core/tool_examples/gui_examples.json << 'EOF'
[
  {"tool": "gui_click", "description": "Click GUI element", "category": "gui", "server": "pyautogui"},
  {"tool": "gui_type", "description": "Type text in GUI", "category": "gui", "server": "pyautogui"},
  {"tool": "gui_screenshot", "description": "Take GUI screenshot", "category": "gui", "server": "pyautogui"}
]
EOF

cat > mcp_integration/core/tool_examples/ai_examples.json << 'EOF'
[
  {"tool": "anthropic_analyze", "description": "Analyze with AI", "category": "ai", "server": "anthropic"},
  {"tool": "anthropic_decide", "description": "Make decision", "category": "ai", "server": "anthropic"},
  {"tool": "anthropic_generate", "description": "Generate content", "category": "ai", "server": "anthropic"}
]
EOF

echo "✅ All MCP servers and tool examples are ready!"
