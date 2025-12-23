import os
import pathlib
import logging

from core.task_analyzer import TaskAnalyzer


def test_task_analyzer_handler_cleanup(tmp_path):
    ta = TaskAnalyzer(log_dir=str(tmp_path / "task_logs"))
    res = ta.start_task_analysis("Test Task", "Testing handler cleanup")
    assert res.get("success") is True
    log_file = ta.current_task["log_file"]

    # Emit a log entry
    ta.log_task_event("info", {"message": "hello"})
    assert os.path.exists(log_file)

    # Finalize
    out = ta.analyze_task_execution()
    assert out.get("success") is True

    # Ensure file handler was removed/closed from ta.logger
    base = str(log_file)
    for h in ta.logger.handlers:
        if isinstance(h, logging.FileHandler):
            assert getattr(h, "baseFilename", None) != base


def test_task_analyzer_status_failed(tmp_path):
    ta = TaskAnalyzer(log_dir=str(tmp_path / "task_logs"))
    ta.start_task_analysis("Error Task", "Expect failed status")
    ta.log_task_event("error", {"message": "boom"})
    out = ta.analyze_task_execution()
    assert out.get("status") == "failed"
