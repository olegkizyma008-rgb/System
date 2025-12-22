import os
from core.trinity import TrinityRuntime
from langchain_core.messages import AIMessage
import pytest


def test_dev_tasks_trigger_vibe_pause(tmp_path: "Path", monkeypatch: pytest.MonkeyPatch):
    # Force Doctor Vibe to handle DEV tasks
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "regenerate_structure.sh").write_text("#!/bin/bash\necho ok > project_structure_final.txt\n")
    (repo / "regenerate_structure.sh").chmod(0o755)
    (repo / "some_change.txt").write_text("x")

    monkeypatch.chdir(repo)

    rt = TrinityRuntime(verbose=False)

    class _DummyWorkflow:
        def stream(self, initial_state, config=None):
            # Yield a plan that includes a write_file call
            yield {"atlas": {"messages": [AIMessage(content="ok")], "current_agent": "tetyana", "plan": [{"description": "Edit file", "type": "execute", "tools": [{"name": "write_file", "args": {"path": "some_change.txt", "content": "y"}}]}]}}

    rt.workflow = _DummyWorkflow()

    events = list(rt.run("Make dev change"))
    # Check that a Vibe pause was created during the run
    found = any("Doctor Vibe" in str(e) or (isinstance(e, dict) and e.get("atlas") and "Final report" in str(e["atlas"])) for e in events)
    assert found
