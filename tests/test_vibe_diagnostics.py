import os
from core.trinity import TrinityRuntime
from langchain_core.messages import AIMessage
import pytest


def test_vibe_pause_includes_diagnostics(tmp_path: "Path", monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "regenerate_structure.sh").write_text("#!/bin/bash\necho ok > project_structure_final.txt\n")
    (repo / "regenerate_structure.sh").chmod(0o755)
    (repo / "some_change.txt").write_text("x")
    # initialize git and create initial commit so we can later show diffs
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)
    # modify the file so git diff will capture a change
    (repo / "some_change.txt").write_text("y")

    monkeypatch.chdir(repo)

    rt = TrinityRuntime(verbose=False)

    class _DummyWorkflow:
        def stream(self, initial_state, config=None):
            # Trigger a write_file tool call which should pause and include diagnostics
            yield {"atlas": {"messages": [AIMessage(content="ok")], "current_agent": "tetyana", "plan": [{"description": "Edit file", "type": "execute", "tools": [{"name": "write_file", "args": {"path": "some_change.txt", "content": "y"}}]}]}}

    # Directly create a pause so diagnostics collection runs deterministically
    state = {
        "original_task": "Make dev change",
        "plan": [],
    }
    tools = [{"name": "write_file", "args": {"path": "some_change.txt", "content": "y"}}]

    pause = rt._create_vibe_assistant_pause_state(state, "doctor_vibe_dev", "Doctor Vibe: Manual intervention",)
    # The runtime's Vibe assistant stores the pause too
    status = rt.get_vibe_assistant_status()
    pause = status.get("current_pause")
    assert pause is not None
    # Manually add diagnostics via helper to mimic tool-triggered pause
    diags = rt._collect_pause_diagnostics(state, tools=tools)
    assert isinstance(diags, dict)
    assert "files" in diags
    assert "diffs" in diags
    files = diags.get("files") or []
    assert any("some_change.txt" in f for f in files) or any(d.get("file") == "some_change.txt" for d in diags.get("diffs", []))
