import pytest
from langchain_core.messages import AIMessage
from core.trinity import TrinityRuntime


def test_router_preemptive_vibe_pause(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    # Ensure auto-apply is disabled for this test so pause is created
    monkeypatch.setenv("TRINITY_VIBE_AUTO_APPLY", "0")

    rt = TrinityRuntime(verbose=True)

    state = {
        "current_agent": "meta_planner",
        "plan": [{"description": "Edit file", "type": "execute", "tools": [{"name": "write_file", "args": {"path": "x"}}]}],
        "dev_edit_mode": "vibe",
        "task_type": "DEV",
        "original_task": "Modify cleanup module",
    }

    res = rt._router(state)
    # Router should leave current agent unchanged but create a Vibe pause
    assert state.get("vibe_assistant_pause") is not None
    assert "doctor_vibe_dev" in state.get("vibe_assistant_pause").get("reason")
