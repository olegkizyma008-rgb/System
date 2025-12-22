import os

from core.trinity import TrinityRuntime


def test_is_env_true_truthy_falsy(monkeypatch):
    monkeypatch.setenv("COPILOT_API_KEY", "dummy")
    rt = TrinityRuntime(verbose=False)

    for val in ["1", "true", "True", "yes", "on"]:
        monkeypatch.setenv("SOME_FLAG", val)
        assert rt._is_env_true("SOME_FLAG") is True

    for val in ["0", "false", "no", "", "random"]:
        monkeypatch.setenv("SOME_FLAG", val)
        assert rt._is_env_true("SOME_FLAG") is False

    # unset
    monkeypatch.delenv("SOME_FLAG", raising=False)
    assert rt._is_env_true("SOME_FLAG") is False
