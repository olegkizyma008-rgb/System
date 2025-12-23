import types
import os

from archive.task_analysis_system import TaskAnalyzer


def test_capture_screenshot_records_error(monkeypatch, tmp_path, caplog):
    ta = TaskAnalyzer()
    ta.start_task_analysis("Test", "desc")

    # Simulate take_screenshot returning an error with traceback
    def fake_take_screenshot(*args, **kwargs):
        return {"tool": "take_screenshot", "status": "error", "error": "simulated", "traceback": "traceback_here"}

    monkeypatch.setattr("system_ai.tools.screenshot.take_screenshot", fake_take_screenshot)

    result = ta.capture_screenshot("testing error")

    assert result["success"] is False
    # Check that the task recorded an error event
    assert len(ta.current_task["errors"]) >= 1
    # Ensure the returned dict includes traceback
    assert "traceback" in result
