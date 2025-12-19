import pytest
from langchain_core.messages import AIMessage
from core.trinity import TrinityRuntime
from core.self_healing import CodeIssue, IssueType, IssueSeverity

class DummySelfHealer:
    def __init__(self):
        self.repair_called = False
        self.detected_issues = []
    
    def quick_repair(self, **kwargs):
        self.repair_called = True
        return True

    def quick_repair_from_message(self, message):
        self.repair_called = True
        return True

    def set_trinity_runtime(self, rt):
        pass

    def integrate_with_trinity(self, rt):
        pass
    
    def start_background_monitoring(self, interval=60.0):
        return None

def test_router_auto_repair_flow(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    
    rt = TrinityRuntime(verbose=True)
    dummy_healer = DummySelfHealer()
    rt.self_healer = dummy_healer
    rt.vibe_assistant.set_self_healer(dummy_healer)
    rt.vibe_assistant.auto_repair_enabled = True
    
    # Create a state with a pause
    pause_info = {
        "reason": "runtime_error",
        "message": "NameError: name 'context' is not defined",
        "auto_resume_available": True
    }
    
    state = {
        "current_agent": "atlas",
        "messages": [AIMessage(content="Error occurred")],
        "vibe_assistant_pause": pause_info
    }
    
    # Run router
    next_agent = rt._router(state)
    
    # Verify
    assert dummy_healer.repair_called is True
    assert next_agent == "meta_planner"
    assert state.get("vibe_assistant_pause") is None
    assert "AUTO-REPAIRED" in state.get("vibe_assistant_context", "")

def test_router_stay_paused_if_repair_fails(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    
    rt = TrinityRuntime(verbose=True)
    
    class FailingHealer:
        def quick_repair(self, **kwargs): return False
        def quick_repair_from_message(self, msg): return False
        def set_self_healer(self, h): pass
        def set_trinity_runtime(self, rt): pass
        def integrate_with_trinity(self, rt): pass
        def start_background_monitoring(self, interval=60.0): return None
        def quick_repair_from_message(self, message): return False

    dummy_healer = FailingHealer()
    rt.self_healer = dummy_healer
    rt.vibe_assistant.set_self_healer(dummy_healer)
    
    pause_info = {
        "reason": "critical_issues_detected",
        "message": "Unfixable error",
        "auto_resume_available": True
    }
    
    state = {
        "current_agent": "tetyana",
        "vibe_assistant_pause": pause_info
    }
    
    next_agent = rt._router(state)
    
    assert next_agent == "tetyana"
    assert state.get("vibe_assistant_pause") == pause_info
