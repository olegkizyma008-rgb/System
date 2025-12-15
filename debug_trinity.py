#!/usr/bin/env python3
"""Debug script for TrinityRuntime.

Run: python3 debug_trinity.py "Відкрий Калькулятор"
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
from dotenv import load_dotenv
load_dotenv()

from core.trinity import TrinityRuntime

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_trinity.py '<task>'")
        sys.exit(1)
    
    task = sys.argv[1]
    print(f"[DEBUG] Starting TrinityRuntime with task: {task}")
    print("-" * 60)
    
    try:
        runtime = TrinityRuntime(verbose=True)  # Enable verbose mode
        
        for i, event in enumerate(runtime.run(task)):
            print(f"\n[EVENT {i+1}]")
            for node_name, state_update in event.items():
                print(f"  Node: {node_name}")
                messages = state_update.get("messages", [])
                for msg in messages:
                    content = getattr(msg, "content", "")[:500]
                    print(f"  Content: {content}")
                current = state_update.get("current_agent", "?")
                print(f"  Next Agent: {current}")
                
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*60)
    print("[DEBUG] Task completed.")

if __name__ == "__main__":
    main()
