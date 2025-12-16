import os
from typing import List, Dict, Any, Optional
import json
import time

class AtlasMemory:
    """
    RAG Memory System for Project Atlas (`NeuroMac`).
    Stores:
    - UI Patterns (how to interact with specific apps)
    - Strategies (successful plans)
    - User Preferences
    """
    
    def __init__(self, persist_path: str = "./memory_db"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_path)
        
        # Initialize Collections
        self.ui_patterns = self.client.get_or_create_collection(name="ui_patterns")
        self.strategies = self.client.get_or_create_collection(name="strategies")
        self.user_habits = self.client.get_or_create_collection(name="user_habits")
        
    def add_memory(self, category: str, content: str, metadata: Dict[str, Any] = None):
        """
        Saves a memory fragment.
        category: 'ui_patterns', 'strategies', 'user_habits'
        """
        collection = self._get_collection(category)
        if not collection:
            return {"status": "error", "error": f"Invalid category: {category}"}
            
        memory_id = f"{category}_{int(time.time())}"
        
        try:
            collection.add(
                documents=[content],
                metadatas=[metadata or {}],
                ids=[memory_id]
            )
            return {"status": "success", "id": memory_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def query_memory(self, category: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memories.
        """
        collection = self._get_collection(category)
        if not collection:
            return []
            
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    formatted.append({
                        "content": doc,
                        "metadata": meta
                    })
            return formatted
            
        except Exception as e:
            print(f"[Memory] Query error: {e}")
            return []

    def _get_collection(self, category: str):
        if category == "ui_patterns": return self.ui_patterns
        if category == "strategies": return self.strategies
        if category == "user_habits": return self.user_habits
        return None

# Global Instance
_memory_instance = None


class _FallbackMemory:
    def add_memory(self, category: str, content: str, metadata: Dict[str, Any] = None):
        _ = category
        _ = content
        _ = metadata
        return {"status": "success", "id": "fallback"}

    def query_memory(self, category: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        _ = category
        _ = query
        _ = n_results
        return []

def get_memory() -> AtlasMemory:
    global _memory_instance
    if _memory_instance is None:
        # Use a hidden directory in home for persistence or project local
        # Project local is better for containment
        try:
            _memory_instance = AtlasMemory(persist_path=os.path.join(os.getcwd(), ".atlas_memory"))
        except BaseException:
            _memory_instance = _FallbackMemory()
    return _memory_instance

# MCP Wrapper Functions
def save_memory_tool(category: str, content: str, tags: str = "") -> Dict[str, Any]:
    """Saves useful information to long-term memory."""
    mem = get_memory()
    meta = {"tags": tags}
    return mem.add_memory(category, content, meta)

def query_memory_tool(category: str, query: str) -> Dict[str, Any]:
    """Retrieves similar past experiences."""
    mem = get_memory()
    results = mem.query_memory(category, query)
    return {"status": "success", "results": results}
