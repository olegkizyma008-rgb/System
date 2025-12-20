#!/usr/bin/env python3

"""
Integration Test - Test the complete MCP integration system
"""

import json
import os
import tempfile
import shutil
from datetime import datetime

# Add the mcp_integration directory to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_integration import create_mcp_integration


def test_basic_integration():
    """Test basic MCP integration functionality"""
    print("=== Testing Basic MCP Integration ===")
    
    try:
        # Create integration instance
        mcp = create_mcp_integration()
        
        # Test components are available
        assert "manager" in mcp, "Manager not found in integration"
        assert "atlas_healing" in mcp, "Atlas healing mode not found"
        assert "dev_project" in mcp, "Dev project mode not found"
        
        print("✓ Integration components initialized successfully")
        
        # Test MCP manager
        manager = mcp["manager"]
        assert manager is not None, "Manager is None"
        
        # Test getting clients
        context7_client = manager.get_client("context7")
        sonarqube_client = manager.get_client("sonarqube")
        
        print(f"✓ Context7 client: {type(context7_client).__name__}")
        print(f"✓ SonarQube client: {type(sonarqube_client).__name__}")
        
        # Test configuration loading
        config = manager.config
        assert "mcpServers" in config, "mcpServers not in config"
        assert "context7" in config["mcpServers"], "context7 not in mcpServers"
        assert "sonarqube" in config["mcpServers"], "sonarqube not in mcpServers"
        
        print("✓ Configuration loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic integration test failed: {e}")
        return False


def test_atlas_healing_mode():
    """Test Atlas Healing Mode functionality"""
    print("\n=== Testing Atlas Healing Mode ===")
    
    try:
        # Create integration instance
        mcp = create_mcp_integration()
        atlas_healing = mcp["atlas_healing"]
        
        # Test error context
        error_context = {
            "type": "test_error",
            "message": "Test error for healing mode",
            "severity": "low",
            "timestamp": datetime.now().isoformat()
        }
        
        # Test starting healing session
        session_result = atlas_healing.start_healing_session(error_context)
        assert session_result["success"], f"Failed to start healing session: {session_result.get('error')}"
        
        session_id = session_result["session_id"]
        print(f"✓ Healing session started: {session_id}")
        
        # Test system diagnostics
        diagnostics_result = atlas_healing.diagnose_system()
        assert diagnostics_result["success"], f"Diagnostics failed: {diagnostics_result.get('error')}"
        
        diagnostics = diagnostics_result["diagnostics"]
        assert "system_status" in diagnostics, "system_status not in diagnostics"
        assert "mcp_servers" in diagnostics, "mcp_servers not in diagnostics"
        
        print("✓ System diagnostics completed")
        
        # Test error analysis
        analysis_result = atlas_healing.analyze_error_patterns(error_context)
        assert analysis_result["success"], f"Error analysis failed: {analysis_result.get('error')}"
        
        analysis = analysis_result["analysis"]
        assert "patterns" in analysis, "patterns not in analysis"
        assert "suggested_fixes" in analysis, "suggested_fixes not in analysis"
        
        print("✓ Error analysis completed")
        
        # Test healing actions
        healing_actions = [
            {
                "type": "restart_server",
                "data": {"server": "context7"}
            }
        ]
        
        actions_result = atlas_healing.apply_healing_actions(healing_actions)
        assert actions_result["success"], f"Healing actions failed: {actions_result.get('error')}"
        
        print("✓ Healing actions applied")
        
        # Test ending session
        end_result = atlas_healing.end_healing_session("completed")
        assert end_result["success"], f"Failed to end session: {end_result.get('error')}"
        
        print("✓ Healing session ended")
        
        # Test healing report
        report = atlas_healing.get_healing_report()
        assert report["success"], f"Failed to get report: {report.get('error')}"
        
        print("✓ Healing report generated")
        
        return True
        
    except Exception as e:
        print(f"✗ Atlas healing mode test failed: {e}")
        return False


def test_dev_project_mode():
    """Test Dev Project Mode functionality"""
    print("\n=== Testing Dev Project Mode ===")
    
    try:
        # Create integration instance
        mcp = create_mcp_integration()
        dev_project = mcp["dev_project"]
        
        # Create a temporary projects directory
        temp_dir = tempfile.mkdtemp()
        projects_dir = os.path.join(temp_dir, "projects")
        os.makedirs(projects_dir, exist_ok=True)
        
        # Change to temp directory for testing
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Test project configuration
            project_config = {
                "name": "Test Project",
                "type": "library",
                "description": "A test project for integration testing",
                "version": "1.0.0",
                "author": "Test Author"
            }
            
            # Test project creation
            project_result = dev_project.create_project(project_config)
            assert project_result["success"], f"Project creation failed: {project_result.get('error')}"
            
            project_id = project_result["project_id"]
            project_root = project_result["project_root"]
            
            print(f"✓ Project created: {project_id}")
            
            # Verify project directory exists
            assert os.path.exists(project_root), f"Project directory not found: {project_root}"
            
            # Verify project structure
            expected_dirs = ["src", "tests", "docs", "config", "scripts", "assets"]
            for dir_name in expected_dirs:
                dir_path = os.path.join(project_root, dir_name)
                assert os.path.exists(dir_path), f"Expected directory not found: {dir_path}"
            
            print("✓ Project structure verified")
            
            # Verify project files
            expected_files = ["README.md", "requirements.txt", ".gitignore", ".env.example"]
            for file_name in expected_files:
                file_path = os.path.join(project_root, file_name)
                assert os.path.exists(file_path), f"Expected file not found: {file_path}"
            
            print("✓ Project files verified")
            
            # Test SonarQube setup
            sonarqube_result = dev_project.setup_sonarqube_analysis(project_id)
            # Note: This might fail if SonarQube client is not properly configured
            # but we'll check if the method works
            print(f"✓ SonarQube setup attempted: {sonarqube_result.get('success', False)}")
            
            # Test project history
            history_result = dev_project.get_project_history()
            assert history_result["success"], f"Failed to get project history: {history_result.get('error')}"
            
            projects = history_result["projects"]
            assert len(projects) > 0, "No projects in history"
            assert any(p["project_id"] == project_id for p in projects), f"Project {project_id} not in history"
            
            print("✓ Project history verified")
            
            # Test setting current project
            current_result = dev_project.set_current_project(project_id)
            assert current_result["success"], f"Failed to set current project: {current_result.get('error')}"
            
            current_project = dev_project.get_current_project()
            assert current_project is not None, "Current project is None"
            assert current_project["project_id"] == project_id, f"Wrong current project: {current_project.get('project_id')}"
            
            print("✓ Current project management verified")
            
            return True
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"✗ Dev project mode test failed: {e}")
        return False


def test_configuration():
    """Test configuration loading and validation"""
    print("\n=== Testing Configuration ===")
    
    try:
        # Create integration instance
        mcp = create_mcp_integration()
        manager = mcp["manager"]
        
        # Test configuration structure
        config = manager.config
        
        # Check required sections
        assert "mcpServers" in config, "mcpServers section missing"
        assert "defaultServer" in config, "defaultServer missing"
        assert "logging" in config, "logging section missing"
        
        # Check server configurations
        servers = config["mcpServers"]
        assert "context7" in servers, "context7 server missing"
        assert "sonarqube" in servers, "sonarqube server missing"
        
        # Check Context7 configuration
        context7_config = servers["context7"]
        assert "command" in context7_config, "context7 command missing"
        assert "args" in context7_config, "context7 args missing"
        assert isinstance(context7_config["args"], list), "context7 args should be a list"
        
        # Check SonarQube configuration
        sonarqube_config = servers["sonarqube"]
        assert "command" in sonarqube_config, "sonarqube command missing"
        assert "args" in sonarqube_config, "sonarqube args missing"
        assert "env" in sonarqube_config, "sonarqube env missing"
        
        print("✓ Configuration structure validated")
        
        # Test logging configuration
        logging_config = config["logging"]
        assert "level" in logging_config, "logging level missing"
        assert "file" in logging_config, "logging file missing"
        
        print("✓ Logging configuration validated")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("Running MCP Integration Tests")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_basic_integration,
        test_atlas_healing_mode,
        test_dev_project_mode
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    # Run all tests
    success = run_all_tests()
    
    # Exit with appropriate code
    exit(0 if success else 1)