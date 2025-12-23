import pytest
from langchain_core.messages import AIMessage
from core.trinity import TrinityRuntime


def test_vibe_auto_apply_executes_write(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    monkeypatch.setenv("TRINITY_VIBE_AUTO_APPLY", "1")

    rt = TrinityRuntime(verbose=True)

    # allow file writes in permissions for the test
    rt.permissions.allow_file_write = True

    # Mock registry to capture execute calls
    calls = []
    class DummyRegistry:
        def execute(self, name, args):
            calls.append((name, args))
            return '{"status":"ok"}'

    rt.registry = DummyRegistry()

    state = {
        "current_agent": "tetyana",
        "dev_edit_mode": "vibe",
        "vibe_auto_apply": True,
    }

    tools = [{"name": "write_file", "args": {"path": "test.txt", "content": "hello"}}]

    results, pause, failed = rt._execute_tetyana_tools(state, tools)
    assert calls and calls[0][0] == "write_file"
    assert 'test.txt' in calls[0][1].get('path')
