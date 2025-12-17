#!/usr/bin/env python3
"""Compatibility wrapper.

The main implementation was moved into `tui/cli.py`.
This file is kept to avoid breaking existing scripts (e.g. `cli.sh`) and imports.
"""

from __future__ import annotations

import importlib
import sys

# Ensure stdin is utf-8 to prevent encoding errors
try:
    sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass

_impl = None


def _load_impl():
    global _impl
    if _impl is None:
        _impl = importlib.import_module("tui.cli")
    return _impl


def main() -> None:
    _load_impl().main()


def __getattr__(name: str):  # pragma: no cover
    return getattr(_load_impl(), name)


def __dir__():  # pragma: no cover
    return sorted(set(globals().keys()) | set(dir(_load_impl())))


if __name__ == "__main__":
    main()
