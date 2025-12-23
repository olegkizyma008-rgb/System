"""Test that self-healing module ignores temporary and test files."""

import pytest
import tempfile
import os


def test_self_healing_ignores_pytest_temp_files(tmp_path):
    """Test that pytest temporary files are ignored during error detection."""
    from core.self_healing import CodeSelfHealer
    
    # Create a temporary log with pytest temp file errors
    log_file = tmp_path / "test.log"
    log_content = """
[ERROR] Error in file
  File "/private/var/folders/4w/9xm5jfnj5n59yj02w6rxqs440000gn/T/pytest-of-dev/pytest-144/test_quick_repair_name_error0.py", line 5
NameError: undefined name: context
  
[ERROR] Another error
  File "/Users/dev/Documents/GitHub/System/core/trinity.py", line 100
ImportError: real error in project
"""
    log_file.write_text(log_content)
    
    sh = CodeSelfHealer(
        project_root="/Users/dev/Documents/GitHub/System",
        log_path=str(log_file)
    )
    
    issues = sh.detect_errors()
    
    # Should only detect the error in trinity.py, not pytest temp file
    assert len(issues) == 1
    assert "trinity.py" in issues[0].file_path
    assert "pytest-of-dev" not in issues[0].file_path


def test_self_healing_ignores_tmp_directory():
    """Test that /tmp and /var/folders files are ignored."""
    from core.self_healing import CodeSelfHealer
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        log_path = f.name
        f.write("""
[ERROR] Temp error
  File "/tmp/some_temp_file.py", line 10
RuntimeError: temp error
    
[ERROR] Var folders error  
  File "/var/folders/xyz/abc/test.py", line 20
RuntimeError: var folders error
    
[ERROR] Real error
  File "/Users/dev/Documents/GitHub/System/core/mcp.py", line 30
RuntimeError: real project error
""")
    
    try:
        sh = CodeSelfHealer(
            project_root="/Users/dev/Documents/GitHub/System",
            log_path=log_path
        )
        
        issues = sh.detect_errors()
        
        # Should only detect the real project error
        assert len(issues) == 1
        assert "mcp.py" in issues[0].file_path
        assert "/tmp/" not in issues[0].file_path
        assert "/var/folders/" not in issues[0].file_path
    finally:
        os.unlink(log_path)


def test_self_healing_ignore_patterns():
    """Test that all ignore patterns work correctly."""
    from core.self_healing import CodeSelfHealer
    
    sh = CodeSelfHealer()
    
    # Test ignore patterns
    test_paths = [
        ("/tmp/test.py", True),
        ("/var/folders/abc/test.py", True),
        ("/private/var/folders/xyz/pytest-of-dev/test.py", True),
        ("/home/user/.pytest_cache/test.py", True),
        ("/project/__pycache__/module.pyc", True),
        ("/Users/dev/Documents/GitHub/System/core/trinity.py", False),
        ("/Users/dev/Documents/GitHub/System/tests/test_file.py", False),
    ]
    
    for path, should_ignore in test_paths:
        ignored = any(pattern in path for pattern in sh.IGNORE_PATHS)
        assert ignored == should_ignore, f"Path {path} ignore check failed"


def test_self_healing_ignores_pycache():
    """Test that __pycache__ and .pyc files are ignored."""
    from core.self_healing import CodeSelfHealer
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        log_path = f.name
        f.write("""
[ERROR] Cache error
  File "/Users/dev/project/__pycache__/module.cpython-311.pyc", line 5
RuntimeError: cache error
    
[ERROR] Real error
  File "/Users/dev/Documents/GitHub/System/plugins/plugin_creator.py", line 50
RuntimeError: real error
""")
    
    try:
        sh = CodeSelfHealer(
            project_root="/Users/dev/Documents/GitHub/System",
            log_path=log_path
        )
        
        issues = sh.detect_errors()
        
        # Should only detect the real plugin error
        assert len(issues) == 1
        assert "plugin_creator.py" in issues[0].file_path
        assert "__pycache__" not in issues[0].file_path
    finally:
        os.unlink(log_path)
