import pytest
import os
from langchain_core.messages import AIMessage
from core.trinity import TrinityRuntime

def test_meta_planner_preserves_fail_count(monkeypatch):
    """Verify that current_step_fail_count is incremented and preserved through Meta-Planner -> Atlas dispatch."""
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    rt = TrinityRuntime(verbose=False)
    
    # Mock LLM to avoid real calls
    class DummyLLM:
        def invoke(self, msgs): return AIMessage(content="{}")
    rt.llm = DummyLLM()

    # Initial state with plan and uncertain status
    state = {
        "original_task": "test task",
        "plan": [{"id": 1, "type": "execute", "description": "test step", "agent": "tetyana"}],
        "last_step_status": "uncertain",
        "current_step_fail_count": 0,
        "step_count": 1,
        "messages": [AIMessage(content="Tetyana output")],
        "meta_config": {"strategy": "hybrid"}
    }
    
    # 1. First call to Meta-Planner
    # It should increment fail_count to 1
    out1 = rt._meta_planner_node(state)
    
    # FAILURE EXPECTED HERE BEFORE FIX: out1['current_step_fail_count'] will be 0
    # because _atlas_dispatch reads it from 'state' (which is 0) instead of the local variable.
    assert out1["current_step_fail_count"] == 1, f"Expected fail_count 1, got {out1.get('current_step_fail_count')}"
    assert out1["last_step_status"] == "uncertain"

    # 2. Simulate second loop
    # Update state with previous output
    state.update(out1)
    out2 = rt._meta_planner_node(state)
    assert out2["current_step_fail_count"] == 2
    
    # 3. Verify it eventually escalates to 'failed'
    state.update(out2)
    out3 = rt._meta_planner_node(state) # count 3
    state.update(out3)
    out4 = rt._meta_planner_node(state) # count 4 -> should become 'failed'
    
    assert out4["last_step_status"] == "failed"
    # When failed, it triggers a replan (current_agent='atlas')
    assert out4["current_agent"] == "atlas"

if __name__ == "__main__":
    pytest.main([__file__])
