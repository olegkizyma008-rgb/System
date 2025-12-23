import pytest
from core.trinity import TrinityRuntime, TrinityPermissions
from tui.state import state
from tui.commands import set_agent_pause, clear_agent_pause_state, get_input_prompt

def test_permission_metadata_generation(monkeypatch):
    # Clear env vars that might override permissions
    for env in ["TRINITY_ALLOW_APPLESCRIPT", "TRINITY_ALLOW_GUI", "TRINITY_ALLOW_SHELL", "TRINITY_HYPER_MODE"]:
        monkeypatch.delenv(env, raising=False)
        
    perms = TrinityPermissions(allow_applescript=False, allow_gui=False, allow_shell=False)
    rt = TrinityRuntime(verbose=False, permissions=perms)
    
    # Check applescript tool
    pause_info = rt._check_tool_permissions({}, "run_applescript", {})
    assert pause_info is not None
    assert pause_info["permission"] == "applescript"
    assert pause_info["mac_pane"] == "automation"
    
    # Check gui tool
    pause_info = rt._check_tool_permissions({}, "click", {})
    assert pause_info is not None
    assert pause_info["permission"] == "gui"
    assert pause_info["mac_pane"] == "accessibility"
    
    # Check shell tool
    pause_info = rt._check_tool_permissions({}, "run_shell", {})
    assert pause_info is not None
    assert pause_info["permission"] == "shell"
    assert pause_info["mac_pane"] == "automation"

def test_tui_prompt_with_privacy_hint():
    clear_agent_pause_state()
    
    # Simulate a pause with a mac_pane
    set_agent_pause(
        pending_text="test task",
        permission="applescript",
        message="Need applescript",
        mac_pane="automation"
    )
    
    prompt = get_input_prompt()
    assert "privacy" in prompt
    assert "automation" in prompt
    
    clear_agent_pause_state()
    prompt = get_input_prompt()
    assert "privacy" not in prompt

def test_open_privacy_command(monkeypatch):
    clear_agent_pause_state()
    state.agent_pause_mac_pane = "accessibility"
    
    opened_pane = None
    def mock_open_pane(pane):
        nonlocal opened_pane
        opened_pane = pane
        
    monkeypatch.setattr("tui.permissions.macos_open_privacy_pane", mock_open_pane)
    
    from tui.commands import _cmd_open_privacy
    _cmd_open_privacy("/privacy", [], False)
    
    assert opened_pane == "accessibility"
