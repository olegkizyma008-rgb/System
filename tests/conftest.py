import os


def pytest_configure(config):
    _ = config
    # Keep tests deterministic and avoid accidental use of interactive TUI.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
