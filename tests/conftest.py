import os
import sys


def pytest_configure(config):
    _ = config
    # Keep tests deterministic and avoid accidental use of interactive TUI.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root and repo_root not in sys.path:
        sys.path.insert(0, repo_root)
