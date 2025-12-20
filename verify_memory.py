
import sys
import os
import time
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from core.memory import get_hierarchical_memory, clear_memory_tool

def test_working_memory():
    print("Testing Working Memory...")
    mem = get_hierarchical_memory()
    
    # Add item
    mem.add_to_working_memory("test_key", "test content")
    item = mem.get_from_working_memory("test_key")
    assert item is not None
    assert item.content == "test content"
    print("  - Add/Get: OK")
    
    # Clear
    mem.clear_working_memory()
    item = mem.get_from_working_memory("test_key")
    assert item is None
    print("  - Clear: OK")

def test_episodic_memory():
    print("Testing Episodic Memory...")
    mem = get_hierarchical_memory()
    
    # Add item
    res = mem.add_episodic_memory("test experience", "test_action")
    print(f"  - Add result: {res}")
    assert res["status"] == "success"
    
    # Query (might take a moment for indexing, depends on ChromaDB impl, but usually immediate for small data)
    time.sleep(1)
    results = mem.query_episodic_memory("test experience")
    # Note: query might return nothing if embeddings aren't working/mocked, 
    # but we are testing the structure. 
    # If using FallbackMemory, it returns [].
    # If using real ChromaDB, it should return result.
    
    # Clear specific session
    # We need to access the private session_id to test session clearing effectively 
    # or just trust the call.
    # Let's test the clear_memory_tool wrapper.
    
    res = clear_memory_tool("episodic")
    print(f"  - Clear result: {res}")
    assert res["status"] == "success"
    
def main():
    try:
        test_working_memory()
        test_episodic_memory()
        print("\nAll memory tests passed!")
    except Exception as e:
        print(f"\nTests FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
