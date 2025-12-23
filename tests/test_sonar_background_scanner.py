import os
import types
import time

import pytest

from core.trinity import TrinityRuntime


class DummyResp:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


def _mock_requests_get(url, params=None, auth=None, timeout=None):
    if "/api/issues/search" in url:
        return DummyResp(200, {"total": 1, "issues": [{"key": "i1", "message": "Leak", "severity": "CRITICAL", "component": "a.py", "textRange": {"startLine": 10}}]})
    return DummyResp(404, {})


def test_scanner_run_once(monkeypatch):
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setattr("requests.get", _mock_requests_get)

    rt = TrinityRuntime(verbose=False)
    # ensure context7 local store is available
    rt.context_layer.clear_metrics_history()

    # run scanner once via direct class
    from core.sonar_scanner import SonarBackgroundScanner
    scanner = SonarBackgroundScanner(rt, interval_minutes=1)
    new_state = scanner.run_once()

    # after run_once, either local Context7 doc was created or returned state has a Sonar summary/pointer
    docs = getattr(rt, 'context_layer')._documents
    if docs:
        assert any("SonarQube" in (d.get('content') or '') or "SonarQube" in (d.get('title') or '') for d in docs)
    else:
        # fallback: check returned state contains summary or pointer
        assert new_state is not None
        assert "SonarQube" in new_state.get('retrieved_context', "") or "SonarDoc" in new_state.get('retrieved_context', "")


def test_trinity_starts_scanner_when_enabled(monkeypatch):
    monkeypatch.setenv("TRINITY_SONAR_BACKGROUND", "1")
    monkeypatch.setenv("TRINITY_SONAR_SCAN_INTERVAL", "1")
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setattr("requests.get", _mock_requests_get)

    rt = TrinityRuntime(verbose=False)
    assert hasattr(rt, "_sonar_scanner")
    # Stop the scanner to avoid background thread after test
    try:
        rt._sonar_scanner.stop()
    except Exception:
        pass
