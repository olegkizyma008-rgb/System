import os
from core.trinity import TrinityRuntime


def test_vibe_auto_resume_permissions(monkeypatch):
    # Enable per-permission auto-resume
    monkeypatch.setenv("TRINITY_VIBE_AUTO_RESUME_PERMISSIONS", "1")
    rt = TrinityRuntime(verbose=False)

    # Simulate an active permission pause
    state = {
        "vibe_assistant_pause": {
            "permission": "shortcuts",
            "message": "Permission required for shortcuts",
            "timestamp": "now"
        }
    }

    # Mock Vibe assistant continue command to indicate resume
    rt.vibe_assistant.handle_user_command = lambda cmd: {"action": "resume"}

    res = rt._handle_existing_pause(state, "meta_planner")
    assert res == "meta_planner"
    assert state.get("vibe_assistant_pause") is None
