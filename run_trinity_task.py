#!/usr/bin/env python3
"""Run a Trinity task directly from the command line."""

import os
import sys

# Add project root to path
_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(_repo_root, ".env"))

os.environ["TRINITY_ALLOW_GENERAL"] = "1"
os.environ["TRINITY_ROUTING_MODE"] = "all"

# Speed-up: avoid long model host connectivity checks (PaddleX/PaddleOCR)
os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "True")

from core.trinity import TrinityRuntime, TrinityPermissions

def main():
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    if not task:
        print("Usage: python run_trinity_task.py <task description>")
        sys.exit(1)
    
    print(f"🚀 Starting Trinity runtime with task: {task}")
    print("-" * 60)
    
    permissions = TrinityPermissions(
        allow_shell=True,
        allow_applescript=True,
        allow_file_write=True,
        allow_gui=True,
        allow_shortcuts=True,
        hyper_mode=True,
    )
    
    runtime = TrinityRuntime(
        verbose=True,
        permissions=permissions,
        preferred_language="uk"
    )
    
    event_count = 0
    try:
        for event in runtime.run(task, gui_mode="auto", execution_mode="native", recursion_limit=200):
            event_count += 1
            for node_name, state_update in event.items():
                tag = node_name.upper()
                messages = state_update.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    content = ""
                    if hasattr(last_msg, "content"):
                        content = str(last_msg.content or "")[:500]
                    elif isinstance(last_msg, dict):
                        content = str(last_msg.get("content", ""))[:500]
                    if content:
                        print(f"[{tag}] {content}")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("-" * 60)
    print(f"✅ Trinity completed. Total events: {event_count}")

if __name__ == "__main__":
    main()
