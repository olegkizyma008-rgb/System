import os

from langchain_core.messages import AIMessage

from core.trinity import TrinityRuntime, TrinityPermissions


class _DummyToolLLM:
    def __init__(self, content, tool_calls=None):
        self._content = content
        self._tool_calls = tool_calls or []

    def invoke(self, _messages):
        class _Resp:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls

        return _Resp(self._content, self._tool_calls)

    def invoke_with_stream(self, _messages, on_delta=None):
        return self.invoke(_messages)


def test_tetyana_pauses_on_windsurf_in_content(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")

    rt = TrinityRuntime(verbose=False, permissions=TrinityPermissions(allow_file_write=True))
    class _DummyRegistry:
        def __init__(self):
            self.executed = []
        def execute(self, name, args):
            self.executed.append((name, args))
            return {"status":"success"}
        def list_tools(self):
            return ""
        def get_all_tool_definitions(self):
            return []

    rt.registry = _DummyRegistry()

    # LLM content mentions Windsurf but provides no tool_calls
    rt.llm = _DummyToolLLM("I will open the project in Windsurf to edit the cleanup module.")

    state = {
        "messages": [AIMessage(content="change code")],
        "gui_mode": "off",
        "execution_mode": "native",
        "task_type": "DEV",
        "requires_windsurf": True,
        # dev_edit_mode intentionally omitted to let env override apply
    }

    out = rt._tetyana_node(state)
    # The UI logging should sanitize 'Windsurf' mentions when TRINITY_DEV_BY_VIBE is enabled.
    from tui.render import log
    from tui.render import state as tui_state
    log("I will open the project in Windsurf to edit the cleanup module.")
    last_log = tui_state.logs[-1][1]
    assert "windsurf" not in last_log.lower()
    assert "Doctor Vibe (paused)" in last_log
