import subprocess

from tui import monitoring
from tui.state import state


def test_monitor_auto_select_populates_targets(monkeypatch, tmp_path):
    sample = "Google Chrome\nCode\nTerminal\npython\n"

    class _CP:
        def __init__(self):
            self.stdout = sample

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: _CP())

    monitoring.monitor_auto_select_targets()
    # Should pick up at least a browser and editor-like target and network:all
    assert any(t.startswith("browser:") for t in state.monitor_targets)
    assert any(t.startswith("editor:") for t in state.monitor_targets)
    assert "network:all" in state.monitor_targets


def test_monitor_set_mode_tool_auto(monkeypatch):
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")
    out = monitoring.tool_monitor_set_mode({"mode": "auto"})
    assert out.get("status") == "success"
    assert state.monitor_mode == "auto"
