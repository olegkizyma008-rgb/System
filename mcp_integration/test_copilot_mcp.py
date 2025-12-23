#!/usr/bin/env python3

"""
Test Copilot MCP Client
Demonstrates how to use Copilot as an alternative to Anthropic for AI analysis tasks
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_integration.core.mcp_manager import MCPManager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_copilot_mcp():
    """Test Copilot MCP client with various AI commands"""
    
    print("=" * 80)
    print("Testing Copilot MCP Client")
    print("=" * 80)
    
    try:
        # Initialize MCP Manager
        config_path = os.path.join(
            os.path.dirname(__file__), 
            "mcp_integration/config/mcp_config.json"
        )
        manager = MCPManager(config_path=config_path)
        
        # Get Copilot client
        copilot_client = manager.get_client("copilot")
        if not copilot_client:
            print("❌ Copilot MCP client not found in configuration")
            return False
        
        print("\n1. Testing connection...")
        if copilot_client.connect():
            print("✅ Connection successful")
        else:
            print("❌ Connection failed")
            return False
        
        # Test status
        print("\n2. Getting status...")
        status = copilot_client.get_status()
        print(f"✅ Status: {status}")
        
        # Test various AI commands
        test_cases = [
            {
                "name": "Summarize",
                "command": "ai_summarize",
                "kwargs": {
                    "content": "GitHub Copilot is an AI-powered code completion tool that helps developers write code faster. It uses machine learning models trained on billions of lines of code to suggest completions."
                }
            },
            {
                "name": "Translate",
                "command": "ai_translate",
                "kwargs": {
                    "text": "Hello, how are you?",
                    "language": "Ukrainian"
                }
            },
            {
                "name": "Analyze Sentiment",
                "command": "ai_sentiment",
                "kwargs": {
                    "text": "I absolutely love this new feature! It's amazing and works perfectly."
                }
            },
            {
                "name": "Extract Keywords",
                "command": "ai_keywords",
                "kwargs": {
                    "text": "Artificial intelligence and machine learning are revolutionizing the software development industry."
                }
            },
            {
                "name": "Code Review",
                "command": "ai_code_review",
                "kwargs": {
                    "code": "def add(a, b):\n    return a + b\n\nresult = add(5, '10')"
                }
            }
        ]
        
        print("\n3. Testing AI commands...")
        for i, test in enumerate(test_cases, 3):
            print(f"\n{i}. {test['name']}:")
            print(f"   Command: {test['command']}")
            print(f"   Parameters: {test['kwargs']}")
            
            result = copilot_client.execute_command(test['command'], **test['kwargs'])
            
            if result.get("success"):
                print(f"   ✅ Success")
                print(f"   Response: {result.get('data', '')[:200]}...")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_with_anthropic():
    """Compare Copilot MCP with Anthropic MCP (if available)"""
    
    print("\n" + "=" * 80)
    print("Comparing Copilot MCP vs Anthropic MCP")
    print("=" * 80)
    
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), 
            "mcp_integration/config/mcp_config.json"
        )
        manager = MCPManager(config_path=config_path)
        
        test_prompt = {
            "command": "ai_analyze",
            "kwargs": {
                "data": "Python 3.12 introduces several new features including improved error messages",
                "purpose": "extracting key information"
            }
        }
        
        # Test Copilot
        print("\n1. Testing with Copilot MCP...")
        copilot_client = manager.get_client("copilot")
        if copilot_client:
            copilot_result = copilot_client.execute_command(**test_prompt)
            print(f"   Copilot Response: {copilot_result.get('data', 'N/A')[:200]}...")
        else:
            print("   ❌ Copilot client not available")
        
        # Test Anthropic (if available)
        print("\n2. Testing with Anthropic MCP...")
        anthropic_client = manager.get_client("anthropic")
        if anthropic_client:
            try:
                anthropic_result = anthropic_client.execute_command(**test_prompt)
                print(f"   Anthropic Response: {anthropic_result.get('data', 'N/A')[:200]}...")
            except Exception as e:
                print(f"   ℹ️  Anthropic not available (expected): {e}")
        else:
            print("   ℹ️  Anthropic client not configured")
        
        print("\n✅ Comparison complete!")
        print("   Copilot MCP is a viable alternative to Anthropic MCP")
        print("   No API key required - uses GitHub token instead")
        
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")


if __name__ == "__main__":
    # Run tests
    success = test_copilot_mcp()
    
    if success:
        # Run comparison
        compare_with_anthropic()
    
    sys.exit(0 if success else 1)
