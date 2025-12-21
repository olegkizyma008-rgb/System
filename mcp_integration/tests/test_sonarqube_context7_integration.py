#!/usr/bin/env python3

"""
Test SonarQube Context7 Integration
Verify that SonarQube is properly integrated with Context7
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_integration import create_mcp_integration
from utils.sonarqube_context7_helper import create_sonarqube_context7_helper


def test_configuration():
    """Test that SonarQube and Context7 are configured"""
    print("\n" + "="*60)
    print("Testing SonarQube Context7 Integration Configuration")
    print("="*60)
    
    try:
        # Create MCP integration
        mcp = create_mcp_integration()
        manager = mcp["manager"]
        
        # Check configuration
        config = manager.config
        servers = config.get("mcpServers", {})
        
        # Check SonarQube configuration
        print("\n1. Checking SonarQube Configuration...")
        if "sonarqube" in servers:
            sq_config = servers["sonarqube"]
            print("   ✓ SonarQube server configured")
            print(f"   - Command: {sq_config.get('command')}")
            print(f"   - Description: {sq_config.get('description')}")
            
            # Check if 'stdio' is incorrectly in args
            args = sq_config.get('args', [])
            if 'stdio' in args:
                print("   ⚠ WARNING: 'stdio' found in args - this may cause issues!")
                print("   ⚠ Should be removed from Docker command")
            else:
                print("   ✓ Args configured correctly (no 'stdio')")
        else:
            print("   ✗ SonarQube server NOT configured")
            return False
        
        # Check Context7 configuration
        print("\n2. Checking Context7 Configuration...")
        if "context7" in servers:
            c7_config = servers["context7"]
            print("   ✓ Context7 server configured")
            print(f"   - Command: {c7_config.get('command')}")
            print(f"   - Description: {c7_config.get('description')}")
        else:
            print("   ✗ Context7 server NOT configured")
            return False
        
        # Check Context7-docs configuration
        print("\n3. Checking Context7-docs Configuration...")
        if "context7-docs" in servers:
            c7d_config = servers["context7-docs"]
            print("   ✓ Context7-docs server configured")
            print(f"   - Command: {c7d_config.get('command')}")
            print(f"   - Description: {c7d_config.get('description')}")
            
            metadata = c7d_config.get('metadata', {})
            if metadata:
                print(f"   - Purpose: {metadata.get('purpose')}")
                print(f"   - Library: {metadata.get('library')}")
        else:
            print("   ⚠ Context7-docs server NOT configured")
            print("   ⚠ This is optional but recommended for SonarQube API docs")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        return False


def test_client_initialization():
    """Test that clients are properly initialized"""
    print("\n" + "="*60)
    print("Testing Client Initialization")
    print("="*60)
    
    try:
        # Create MCP integration
        mcp = create_mcp_integration()
        manager = mcp["manager"]
        
        # Check SonarQube client
        print("\n1. Checking SonarQube Client...")
        sq_client = manager.get_client("sonarqube")
        if sq_client:
            print(f"   ✓ SonarQube client initialized: {type(sq_client).__name__}")
            print(f"   - Server type: {sq_client.server_type}")
        else:
            print("   ✗ SonarQube client NOT initialized")
            return False
        
        # Check Context7 client
        print("\n2. Checking Context7 Client...")
        c7_client = manager.get_client("context7")
        if c7_client:
            print(f"   ✓ Context7 client initialized: {type(c7_client).__name__}")
            print(f"   - Server type: {c7_client.server_type}")
        else:
            print("   ✗ Context7 client NOT initialized")
            return False
        
        # Check Context7-docs client
        print("\n3. Checking Context7-docs Client...")
        c7d_client = manager.get_client("context7-docs")
        if c7d_client:
            print(f"   ✓ Context7-docs client initialized: {type(c7d_client).__name__}")
            print(f"   - Server type: {c7d_client.server_type}")
        else:
            print("   ⚠ Context7-docs client NOT initialized (optional)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Client initialization test failed: {e}")
        return False


def test_integration_helper():
    """Test the SonarQube Context7 helper"""
    print("\n" + "="*60)
    print("Testing SonarQube Context7 Helper")
    print("="*60)
    
    try:
        # Create MCP integration
        mcp = create_mcp_integration()
        manager = mcp["manager"]
        
        # Create helper
        print("\n1. Creating Helper...")
        helper = create_sonarqube_context7_helper(manager)
        print(f"   ✓ Helper created: {type(helper).__name__}")
        
        # Verify integration
        print("\n2. Verifying Integration...")
        verification = helper.verify_integration()
        
        if verification.get("success"):
            print("   ✓ Integration verification PASSED")
            print(f"   - Status: {verification.get('status')}")
        else:
            print("   ⚠ Integration verification FAILED")
            print(f"   - Status: {verification.get('status')}")
        
        print("\n   Integration Checks:")
        for check, status in verification.get("checks", {}).items():
            status_icon = "✓" if status else "✗"
            print(f"   {status_icon} {check}: {status}")
        
        # Show recommendations
        recommendations = verification.get("recommendations", [])
        if recommendations:
            print("\n   Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Test library resolution
        print("\n3. Testing Library Resolution...")
        lib_result = helper.resolve_sonarqube_library()
        if lib_result.get("success"):
            print("   ✓ Library resolution successful")
            print(f"   - Library ID: {lib_result.get('library_id')}")
            print(f"   - Library Name: {lib_result.get('library_name')}")
        else:
            print(f"   ✗ Library resolution failed: {lib_result.get('error')}")
        
        # Test documentation retrieval
        print("\n4. Testing Documentation Retrieval...")
        docs_result = helper.get_sonarqube_api_docs(topic="webhooks")
        if docs_result.get("success"):
            print("   ✓ Documentation retrieval configured")
            print(f"   - Topic: {docs_result.get('topic')}")
            print(f"   - Mode: {docs_result.get('mode')}")
            print(f"   - Library: {docs_result.get('library_id')}")
        else:
            print(f"   ✗ Documentation retrieval failed: {docs_result.get('error')}")
        
        return verification.get("success", False)
        
    except Exception as e:
        print(f"\n✗ Helper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_project_integration():
    """Test SonarQube integration with a project"""
    print("\n" + "="*60)
    print("Testing Project Integration")
    print("="*60)
    
    try:
        # Create MCP integration
        mcp = create_mcp_integration()
        manager = mcp["manager"]
        helper = create_sonarqube_context7_helper(manager)
        
        # Test project configuration
        print("\n1. Testing Project Configuration Storage...")
        test_project_id = "test_project_123"
        test_config = {
            "project_key": "test_project",
            "project_name": "Test Project",
            "sources": "src",
            "tests": "tests",
            "language": "py"
        }
        
        result = helper.integrate_with_project(test_project_id, test_config)
        
        if result.get("success"):
            print("   ✓ Project integration successful")
            print(f"   - Project ID: {result.get('project_id')}")
            print(f"   - Context stored: {result.get('context_stored')}")
        else:
            print(f"   ✗ Project integration failed: {result.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Project integration test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("  SONARQUBE CONTEXT7 INTEGRATION VERIFICATION")
    print("="*70)
    
    tests = [
        ("Configuration", test_configuration),
        ("Client Initialization", test_client_initialization),
        ("Integration Helper", test_integration_helper),
        ("Project Integration", test_project_integration)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} | {name}")
    
    total_passed = sum(1 for _, r in results if r)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n✓ All tests PASSED - SonarQube is properly integrated with Context7!")
        return True
    else:
        print("\n⚠ Some tests FAILED - Check recommendations above")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
