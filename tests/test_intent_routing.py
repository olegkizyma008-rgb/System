import json

import pytest
from langchain_core.messages import AIMessage

from core.trinity import TrinityRuntime, TrinityPermissions


class _DummyToolLLM:
    def __init__(self, tool_calls):
        self._tool_calls = tool_calls

    def bind_tools(self, _tools):
        return self

    def invoke(self, _messages):
        class _Resp:
            def __init__(self, tool_calls):
                self.content = ""
                self.tool_calls = tool_calls

        return _Resp(self._tool_calls)

    def invoke_with_stream(self, _messages, on_delta=None):
        return self.invoke(_messages)


class _DummyRegistry:
    def __init__(self):
        self.executed = []
        self._tools = {}
        self._descriptions = {}

    def list_tools(self):
        return ""

    def get_all_tool_definitions(self):
        """Return empty list of tool definitions for testing."""
        return []

    def execute(self, name, args):
        self.executed.append((name, args))
        return json.dumps({"tool": name, "status": "success"}, ensure_ascii=False)


def test_general_task_blocks_windsurf_tools(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    rt = TrinityRuntime(verbose=False, permissions=TrinityPermissions(allow_applescript=True))
    rt.registry = _DummyRegistry()
    rt.llm = _DummyToolLLM([{"name": "send_to_windsurf", "args": {"message": "hi"}}])

    state = {
        "messages": [AIMessage(content="do something")],
        "gui_mode": "off",
        "execution_mode": "native",
        "task_type": "GENERAL",
        "requires_windsurf": False,
        "dev_edit_mode": "cli",
    }
    out = rt._tetyana_node(state)

    assert rt.registry.executed == []
    msg = out["messages"][-1].content
    assert "GENERAL task must not use Windsurf dev subsystem" in msg


def test_dev_windsurf_mode_blocks_direct_file_writes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    rt = TrinityRuntime(verbose=False, permissions=TrinityPermissions(allow_file_write=True))
    rt.registry = _DummyRegistry()
    rt.llm = _DummyToolLLM(
        [{"name": "write_file", "args": {"path": "x.txt", "content": "x"}}]
    )

    state = {
        "messages": [AIMessage(content="change code")],
        "gui_mode": "off",
        "execution_mode": "native",
        "task_type": "DEV",
        "requires_windsurf": True,
        "dev_edit_mode": "windsurf",
    }
    out = rt._tetyana_node(state)

    assert rt.registry.executed == []
    msg = out["messages"][-1].content
    assert "DEV task requires Windsurf-first" in msg


def test_dev_cli_fallback_allows_file_writes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    rt = TrinityRuntime(verbose=False, permissions=TrinityPermissions(allow_file_write=True))
    rt.registry = _DummyRegistry()
    rt.llm = _DummyToolLLM(
        [{"name": "write_file", "args": {"path": "x.txt", "content": "x"}}]
    )

    state = {
        "messages": [AIMessage(content="change code")],
        "gui_mode": "off",
        "execution_mode": "native",
        "task_type": "DEV",
        "requires_windsurf": True,
        "dev_edit_mode": "cli",
    }
    out = rt._tetyana_node(state)

    assert rt.registry.executed and rt.registry.executed[0][0] == "write_file"
    msg = out["messages"][-1].content
    assert "Tool Results" in msg
