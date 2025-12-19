import asyncio
import json
import os
from core.mcp import MCPToolRegistry

async def test_playwright_mcp():
    print("Connecting to MCP Registry...")
    reg = MCPToolRegistry()
    
    # Try to list tools which triggers connection
    print("Listing tools...")
    tools = reg.list_tools()
    print(f"Total tools registered: {len(tools.splitlines())}")
    
    if "playwright.browser_navigate" not in tools:
        print("FAIL: playwright.browser_navigate not found in tools list")
        return

    print("Executing playwright.browser_navigate...")
    # Using external playwright provider
    res = reg.execute("playwright.browser_navigate", {"url": "https://www.google.com"})
    print(f"Result: {res[:500]}...")
    
    if "success" in res.lower():
        print("SUCCESS: Playwright MCP server is working correctly.")
    else:
        print("FAIL: Playwright MCP server returned an error.")

if __name__ == "__main__":
    asyncio.run(test_playwright_mcp())
