import os
import json
import types
import pytest

from core.trinity import TrinityRuntime


class DummyResp:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


def _mock_requests_get(url, params=None, auth=None, timeout=None):
    # Simple URL routing for tests
    if "/api/issues/search" in url:
        return DummyResp(200, {"total": 2, "issues": [
            {"key": "i1", "message": "Leak", "severity": "CRITICAL", "component": "a.py", "textRange": {"startLine": 10}, "rule": "py:leak"},
            {"key": "i2", "message": "Raw types", "severity": "MAJOR", "component": "b.py", "textRange": {"startLine": 20}, "rule": "py:raw"}
        ]})
    if "/api/qualitygates/project_status" in url:
        return DummyResp(200, {"projectStatus": {"status": "OK", "conditions": []}})
    return DummyResp(404, {})


def test_fetch_sonar_issues_no_api_key(monkeypatch):
    monkeypatch.delenv("SONAR_API_KEY", raising=False)
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    rt = TrinityRuntime(verbose=False)
    assert rt._fetch_sonar_issues() is None


def test_fetch_sonar_issues_success(monkeypatch):
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_URL", "https://sonarcloud.io")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    monkeypatch.setattr("requests.get", _mock_requests_get)

    rt = TrinityRuntime(verbose=False)
    res = rt._fetch_sonar_issues()
    assert res is not None
    assert res.get("project_key") == "test_proj"
    assert res.get("issues_count") == 2
    assert isinstance(res.get("issues"), list)


def test_pause_includes_sonar(monkeypatch):
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_URL", "https://sonarcloud.io")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setattr("requests.get", _mock_requests_get)

    rt = TrinityRuntime(verbose=False)

    state = {
        "original_task": "Make a dev change",
        "plan": [{"description": "edit file", "tools": [{"name": "write_file", "args": {"path": "x"}}]}]
    }

    new_state = rt._create_vibe_assistant_pause_state(state, "doctor_vibe_dev", "Doctor Vibe: Manual dev intervention required for this step")
    assert new_state.get("vibe_assistant_pause") is not None
    diags = new_state["vibe_assistant_pause"].get("diagnostics") or {}
    assert "sonar" in diags
    assert diags["sonar"]["issues_count"] == 2


def test_proactive_sonar_enrichment(monkeypatch):
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_URL", "https://sonarcloud.io")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setattr("requests.get", _mock_requests_get)

    rt = TrinityRuntime(verbose=False)
    state = {"is_dev": True, "retrieved_context": "", "original_task": "Make dev change"}
    new_state = rt._enrich_context_with_sonar(state)
    assert "SonarQube summary" in new_state.get("retrieved_context", "")
    assert "test_proj" in new_state.get("retrieved_context", "")


def test_index_to_context7_via_mcp(monkeypatch):
    # Setup env and mocked requests
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_URL", "https://sonarcloud.io")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    monkeypatch.setattr("requests.get", _mock_requests_get)

    # Mock MCP manager with context7-docs client
    class MockDocsClient:
        def __init__(self):
            self.stored = None

        def store_context(self, data):
            self.stored = data
            return {"success": True, "id": "mcp_doc_1"}

    class MockMCPManager:
        def __init__(self):
            self._docs = MockDocsClient()

        def get_client(self, name):
            if name == "context7-docs":
                return self._docs
            return None

    # Monkeypatch create_mcp_integration to return our manager
    manager_inst = MockMCPManager()

    def _fake_create_mcp_integration(config=None):
        return {"manager": manager_inst}

    monkeypatch.setattr("mcp_integration.create_mcp_integration", _fake_create_mcp_integration)
    # Also monkeypatch the helper to ensure indexing is performed and visible to our mock
    def _fake_create_helper(mgr):
        def _index(analysis):
            # Store into the manager's docs client for test visibility
            try:
                mgr.get_client("context7-docs").store_context({"test": "ok"})
            except Exception:
                pass
            return {"stored_in": "context7-docs", "result": {"id": "mcp_doc_1"}, "doc": {"title": "t"}}

        return types.SimpleNamespace(index_analysis_to_context7=_index)

    monkeypatch.setattr("mcp_integration.utils.sonarqube_context7_helper.create_sonarqube_context7_helper", _fake_create_helper)

    rt = TrinityRuntime(verbose=False)
    state = {"is_dev": True, "retrieved_context": "", "original_task": "Make dev change"}
    new_state = rt._enrich_context_with_sonar(state)

    # Ensure MCP client actually stored the document (indexing happened)
    assert manager_inst._docs.stored is not None
    # And a short summary was attached to state
    assert "SonarQube summary" in new_state.get("retrieved_context", "")


def test_index_structured_doc_content(monkeypatch):
    # Test that the stored doc contains structured metadata and markdown content
    monkeypatch.setenv("SONAR_API_KEY", "dummy")
    monkeypatch.setenv("SONAR_URL", "https://sonarcloud.io")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "test_proj")
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")

    # Create a mock context7-docs client that captures stored doc
    class MockDocsClient2:
        def __init__(self):
            self.stored = None

        def store_context(self, data):
            self.stored = data
            return {"success": True, "id": "mcp_doc_2"}

    class MockMCPManager2:
        def __init__(self):
            self._docs = MockDocsClient2()

        def get_client(self, name):
            if name == "context7-docs":
                return self._docs
            return None

    mgr = MockMCPManager2()
    helper = __import__("mcp_integration.utils.sonarqube_context7_helper", fromlist=["SonarQubeContext7Helper"]).SonarQubeContext7Helper(mgr)

    sample = {"project_key": "test_proj", "issues_count": 2, "issues": [{"key": "i1", "message": "Leak", "severity": "CRITICAL", "component": "a.py", "line": 10, "rule": "py:leak"}]}
    res = helper.index_analysis_to_context7(sample, title="Test Sonar Doc")
    assert res.get("stored_in") == "context7-docs"
    doc = res.get("doc")
    assert doc["type"] == "sonarqube.analysis"
    assert "SonarQube Analysis" in doc["content"]
    assert doc["metadata"]["issues_count"] == 2
    assert isinstance(doc["metadata"]["issues"], list)
