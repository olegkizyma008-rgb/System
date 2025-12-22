import os

from system_ai.tools import windsurf


def test_windsurf_tools_blocked_when_vibe(monkeypatch):
    monkeypatch.setenv("TRINITY_DEV_BY_VIBE", "1")

    # open_project_in_windsurf should not attempt to open when vibe mode set
    res = windsurf.open_project_in_windsurf("/tmp")
    assert isinstance(res, dict)
    # Expect it to be blocked by Doctor Vibe preference
    assert res.get("status") in {"error", "blocked", "blocked_by_doctor_vibe"} or "blocked" in str(res.get("error", "")).lower()

    res2 = windsurf.open_file_in_windsurf("/tmp/file.py")
    assert isinstance(res2, dict)
    assert res2.get("status") in {"error", "blocked", "blocked_by_doctor_vibe"} or "blocked" in str(res2.get("error", "")).lower()

    res3 = windsurf.send_to_windsurf("hello")
    assert isinstance(res3, dict)
    assert res3.get("status") in {"error", "blocked", "blocked_by_doctor_vibe"} or "blocked" in str(res3.get("error", "")).lower()
