#!/usr/bin/env python3
"""cli.py - Entry point for the System CLI.

The main implementation is located in `tui/cli.py`.
This file serves as a minimal wrapper to ensure proper path configuration and encoding.
"""

from __future__ import annotations

import os
import sys

# Ensure project root is in path
_repo_root = os.path.abspath(os.path.dirname(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Ensure stdin is utf-8 to prevent encoding errors
try:
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass


def main() -> None:
    try:
        # Auto-detect 'run' command for natural language
        if len(sys.argv) > 1:
            first_arg = sys.argv[1]
            known_commands = {
                "tui", "list-editors", "list-modules", "run", "enable", "disable", 
                "install", "smart-plan", "ask", "agent-chat", "agent-reset", 
                "agent-on", "agent-off", "self-healing-status", "self-healing-scan",
                "vibe-status", "vibe-continue", "vibe-cancel", "vibe-help",
                "eternal-engine", "screenshots",
                "-h", "--help"
            }
            if first_arg not in known_commands and not first_arg.startswith("-"):
                # Treat as agent-chat message
                # Reconstruct argv to: cli.py agent-chat --message "all args joined"
                message = " ".join(sys.argv[1:])
                sys.argv = [sys.argv[0], "agent-chat", "--message", message]

        from tui.cli import main as tui_main
        tui_main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
