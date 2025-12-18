import pytest
from langchain_core.messages import AIMessage

from core.trinity import TrinityRuntime


class _DummyLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, _messages):
        return AIMessage(content=self._content)

    def invoke_with_stream(self, _messages, on_delta=None):
        if on_delta:
            on_delta(self._content)
        return AIMessage(content=self._content)


class _DummyLLMWithToolCalls:
    class _Resp:
        def __init__(self):
            self.content = "I'll verify using tools."
            self.tool_calls = [{"name": "capture_screen", "args": {}}]

    def invoke(self, _messages):
        return self._Resp()

    def invoke_with_stream(self, _messages, on_delta=None):
        return self._Resp()


@pytest.mark.parametrize(
    "grisha_message",
    [
        "План виглядає безпечним і чітким. Проте перед початком перевірки я маю уточнити кілька моментів:\n\n1. Чи впевнені ви, що папка `System_Report_2025` доступна для читання?\n\n2. Якщо все готово, я можу розпочати з перевірки вмісту папки.",
        "Якщо все готово, можу починати?",
    ],
)
def test_grisha_question_like_message_does_not_end(monkeypatch: pytest.MonkeyPatch, grisha_message: str):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    rt = TrinityRuntime(verbose=False)
    rt.llm = _DummyLLM(grisha_message)
    monkeypatch.setattr(rt, "_get_repo_changes", lambda: {"ok": True, "changed_files": []})

    state = {"messages": [AIMessage(content="previous")], "gui_mode": "off", "execution_mode": "native"}
    out = rt._grisha_node(state)

    assert out["current_agent"] == "atlas"


@pytest.mark.parametrize(
    "grisha_message",
    [
        "Все перевірено. [VERIFIED]",
        "Verification passed. [VERIFIED]",
        "верифікація пройдена\n[VERIFIED]",
    ],
)
def test_grisha_explicit_verified_marker_ends(monkeypatch: pytest.MonkeyPatch, grisha_message: str):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    rt = TrinityRuntime(verbose=False)
    rt.llm = _DummyLLM(grisha_message)
    monkeypatch.setattr(rt, "_get_repo_changes", lambda: {"ok": True, "changed_files": []})

    state = {"messages": [AIMessage(content="previous")], "gui_mode": "off", "execution_mode": "native"}
    out = rt._grisha_node(state)

    assert out["current_agent"] == "atlas"
    assert out["last_step_status"] == "success"


def test_grisha_tool_calls_branch_does_not_crash(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    rt = TrinityRuntime(verbose=False)
    rt.llm = _DummyLLMWithToolCalls()
    monkeypatch.setattr(rt, "_get_repo_changes", lambda: {"ok": True, "changed_files": []})

    # Avoid calling real MCP tools.
    rt.registry.execute = lambda _name, _args: "{}"

    state = {"messages": [AIMessage(content="previous")], "gui_mode": "off", "execution_mode": "native"}
    out = rt._grisha_node(state)

    assert out["current_agent"] == "atlas"
    assert out["last_step_status"] in {"uncertain", "failed", "success"}
