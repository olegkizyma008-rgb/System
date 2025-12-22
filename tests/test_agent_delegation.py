"""Tests for Agent Delegation System."""

import pytest
import os
from core.agent_delegation import (
    DelegationManager,
    DelegationReason,
    AgentRole,
    should_delegate_to_tetyana,
    create_tetyana_delegation
)


def test_delegation_manager_init():
    """Test DelegationManager initialization."""
    manager = DelegationManager()
    
    assert manager.delegation_history == []
    assert isinstance(manager.vibe_enabled, bool)


def test_permission_denied_detection(monkeypatch):
    """Test detection of permission denied errors."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "Permission denied: cannot write to file"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "write_file",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.PERMISSION_DENIED


def test_access_denied_detection(monkeypatch):
    """Test detection of access denied errors."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "Access denied to /private/var/system/"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "read_file",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.ACCESS_DENIED


def test_operation_not_permitted(monkeypatch):
    """Test detection of operation not permitted errors."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "Operation not permitted: kill process 1234"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "kill_process",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.OPERATION_NOT_PERMITTED


def test_requires_sudo_detection(monkeypatch):
    """Test detection of sudo requirement."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "This operation requires sudo privileges"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "run_shell",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.REQUIRES_SUDO


def test_file_locked_detection(monkeypatch):
    """Test detection of file locked errors."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "File is locked by another process"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "write_file",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.FILE_LOCKED


def test_resource_busy_detection(monkeypatch):
    """Test detection of resource busy errors."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "Resource busy: cannot unmount"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "run_shell",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.RESOURCE_BUSY


def test_ukrainian_permission_denied(monkeypatch):
    """Test Ukrainian permission denied detection."""
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "Доступ заборонено до файлу"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "read_file",
        error_result
    )
    
    assert should_delegate is True
    assert reason == DelegationReason.PERMISSION_DENIED


def test_no_delegation_on_success():
    """Test that successful operations don't trigger delegation."""
    manager = DelegationManager()
    
    success_result = {
        "status": "success",
        "data": "file written"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "write_file",
        success_result
    )
    
    assert should_delegate is False
    assert reason is None


def test_no_delegation_on_non_permission_error():
    """Test that non-permission errors don't trigger delegation."""
    manager = DelegationManager()
    
    error_result = {
        "status": "error",
        "error": "File not found: /path/to/file"
    }
    
    should_delegate, reason = manager.should_delegate_to_tetyana(
        "read_file",
        error_result
    )
    
    assert should_delegate is False
    assert reason is None


def test_create_delegation_request():
    """Test creation of delegation request."""
    manager = DelegationManager()
    
    request = manager.create_delegation_request(
        tool_name="write_file",
        tool_args={"path": "/etc/test.conf", "content": "test"},
        reason=DelegationReason.PERMISSION_DENIED,
        error_message="Permission denied",
        task_description="Write config file"
    )
    
    assert request.from_agent == AgentRole.DOCTOR_VIBE
    assert request.to_agent == AgentRole.TETYANA
    assert request.reason == DelegationReason.PERMISSION_DENIED
    assert request.tool_name == "write_file"
    assert request.error_message == "Permission denied"
    assert request.task_description == "Write config file"
    
    # Check it was added to history
    assert len(manager.delegation_history) == 1
    assert manager.delegation_history[0] == request


def test_delegation_message_format():
    """Test formatting of delegation message."""
    manager = DelegationManager()
    
    request = manager.create_delegation_request(
        tool_name="run_shell",
        tool_args={"command": "sudo rm /var/log/test.log"},
        reason=DelegationReason.REQUIRES_SUDO,
        error_message="This operation requires sudo",
        task_description="Remove system log file"
    )
    
    message = manager.format_delegation_message(request)
    
    assert "[DELEGATION FROM DOCTOR VIBE]" in message
    assert "потрібні права адміністратора" in message
    assert "Remove system log file" in message
    assert "run_shell" in message
    assert "This operation requires sudo" in message
    assert "Tetyana" in message


def test_delegation_stats_empty():
    """Test delegation stats when no delegations."""
    manager = DelegationManager()
    
    stats = manager.get_delegation_stats()
    
    assert stats["total_delegations"] == 0
    assert stats["by_reason"] == {}
    assert stats["by_tool"] == {}


def test_delegation_stats_with_history():
    """Test delegation stats with multiple delegations."""
    manager = DelegationManager()
    
    # Create several delegations
    manager.create_delegation_request(
        "write_file", {}, DelegationReason.PERMISSION_DENIED,
        task_description="Write file 1"
    )
    manager.create_delegation_request(
        "write_file", {}, DelegationReason.PERMISSION_DENIED,
        task_description="Write file 2"
    )
    manager.create_delegation_request(
        "run_shell", {}, DelegationReason.REQUIRES_SUDO,
        task_description="Run command"
    )
    
    stats = manager.get_delegation_stats()
    
    assert stats["total_delegations"] == 3
    assert stats["by_reason"]["permission_denied"] == 2
    assert stats["by_reason"]["requires_sudo"] == 1
    assert stats["by_tool"]["write_file"] == 2
    assert stats["by_tool"]["run_shell"] == 1


def test_convenience_function_should_delegate():
    """Test convenience function should_delegate_to_tetyana."""
    error_result = {
        "status": "error",
        "error": "Permission denied"
    }
    
    should_delegate, reason = should_delegate_to_tetyana(
        "write_file",
        error_result
    )
    
    # Result depends on TRINITY_DEV_BY_VIBE env var
    assert isinstance(should_delegate, bool)
    if should_delegate:
        assert reason is not None


def test_convenience_function_create_delegation():
    """Test convenience function create_tetyana_delegation."""
    message = create_tetyana_delegation(
        tool_name="write_file",
        tool_args={"path": "/test", "content": "test"},
        reason=DelegationReason.PERMISSION_DENIED,
        error_message="Permission denied",
        task_description="Write test file"
    )
    
    assert isinstance(message, str)
    assert "[DELEGATION FROM DOCTOR VIBE]" in message
    assert "Permission denied" in message or "недостатньо прав" in message


def test_vibe_enabled_detection(monkeypatch):
    """Test Doctor Vibe enabled detection."""
    # Test when enabled
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    manager = DelegationManager()
    assert manager._is_vibe_enabled() is True
    
    # Test when disabled
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "0")
    manager = DelegationManager()
    assert manager._is_vibe_enabled() is False
    
    # Test when not set
    monkeypatch.delenv("TRINITY_DEV_BY_VIBE", raising=False)
    manager = DelegationManager()
    assert manager._is_vibe_enabled() is False


def test_tetyana_preferred_tools():
    """Test that certain tools are marked as Tetyana-preferred."""
    manager = DelegationManager()
    
    # These tools should be in TETYANA_PREFERRED_TOOLS
    system_tools = [
        "run_shell",
        "run_applescript",
        "kill_process",
        "system_cleanup_stealth"
    ]
    
    for tool in system_tools:
        assert tool in manager.TETYANA_PREFERRED_TOOLS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
