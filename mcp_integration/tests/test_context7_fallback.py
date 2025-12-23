import types
import os

from mcp_integration.core.mcp_manager import Context7Client


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_context7_fallback_on_too_many_args(monkeypatch):
    cfg = {"command": "context7", "args": []}
    client = Context7Client(cfg)

    calls = []

    def fake_run(cmd):
        calls.append(list(cmd))
        # First attempt returns 'too many arguments'
        if len(calls) == 1:
            return FakeResult(returncode=1, stdout="", stderr="too many arguments")
        # Second attempt succeeds
        return FakeResult(returncode=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(client, "_run_command", fake_run)

    res = client.execute_command("store", data="small")

    assert res.get("success") is True
    assert any("context7" in c[0] or c[0] == "context7" for c in calls)
    # Ensure fallback was attempted (2 calls)
    assert len(calls) >= 2


def test_context7_fallback_metric_increment(monkeypatch):
    from mcp_integration.core.mcp_manager import Context7Client, CONTEXT7_FALLBACK_COUNT

    cfg = {"command": "context7", "args": []}
    client = Context7Client(cfg)

    # Ensure metric reset
    try:
        # direct reset (module variable)
        import mcp_integration.core.mcp_manager as mgr
        mgr.CONTEXT7_FALLBACK_COUNT = 0
    except Exception:
        pass

    calls = []

    def fake_run(cmd):
        calls.append(list(cmd))
        if len(calls) == 1:
            return FakeResult(returncode=1, stdout="", stderr="too many arguments")
        return FakeResult(returncode=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(client, "_run_command", fake_run)

    res = client.execute_command("store", data="small")
    import mcp_integration.core.mcp_manager as mgr
    assert mgr.CONTEXT7_FALLBACK_COUNT >= 1


def test_context7_writes_large_data_to_tempfile(monkeypatch):
    cfg = {"command": "context7", "args": []}
    client = Context7Client(cfg)

    recorded = {"cmds": []}

    def fake_run(cmd):
        recorded["cmds"].append(list(cmd))
        return FakeResult(returncode=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(client, "_run_command", fake_run)

    large = "x" * 1000
    res = client.execute_command("store", data=large)

    assert res.get("success") is True
    # Check that one of the calls included --data-file
    assert any("--data-file" in c for c in recorded["cmds"]) or any(any(a.startswith("--data-file") for a in c) for c in recorded["cmds"]) 
    # Ensure temp file was cleaned up
    # find path from commands
    data_file_path = None
    for c in recorded["cmds"]:
        if "--data-file" in c:
            idx = c.index("--data-file")
            if idx + 1 < len(c):
                data_file_path = c[idx + 1]
                break

    if data_file_path:
        assert not os.path.exists(data_file_path)
