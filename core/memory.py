"""Atlas Memory System with Hierarchical Layers

RAG Memory System for Project Atlas with enhanced hierarchical architecture:
- Semantic Memory: Long-term knowledge, patterns (persisted)
- Episodic Memory: Session-specific experiences (persisted)
- Working Memory: Current task context (in-memory, volatile)

Original collections preserved for backward compatibility:
- ui_patterns, strategies, user_habits, knowledge_base
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import time
import threading


@dataclass
class WorkingMemoryItem:
    """Item stored in volatile working memory."""
    content: str
    context: str
    priority: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 3600  # 1 hour default TTL
    
    def is_expired(self) -> bool:
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds


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
        self.knowledge_base = self.client.get_or_create_collection(name="knowledge_base")
        
    def add_memory(self, category: str, content: str, metadata: Dict[str, Any] = None):
        """
        Saves a memory fragment with metadata tagging.
        category: 'ui_patterns', 'strategies', 'user_habits', 'knowledge_base'
        """
        collection = self._get_collection(category)
        if not collection:
            return {"status": "error", "error": f"Invalid category: {category}"}
            
        memory_id = f"{category}_{int(time.time())}"
        
        # Ensure metadata is clean
        clean_meta = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
        
        try:
            collection.add(
                documents=[content],
                metadatas=[clean_meta],
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

    def delete_memory(self, category: str, where_filter: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Deletes memories matching the filter.
        
        Args:
            category: Collection name
            where_filter: Metadata filter (e.g. {"session_id": "..."})
        """
        collection = self._get_collection(category)
        if not collection:
            return {"status": "error", "error": f"Invalid category: {category}"}
            
        try:
            # ChromaDB delete requires ids or where filter
            if not where_filter:
                return {"status": "error", "error": "Delete requires a filter (use empty dict for all)"}
                
            collection.delete(where=where_filter)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_collection(self, category: str):
        if category == "ui_patterns": return self.ui_patterns
        if category == "strategies": return self.strategies
        if category == "user_habits": return self.user_habits
        if category == "knowledge_base": return self.knowledge_base
        return None


class HierarchicalMemory(AtlasMemory):
    """
    Extended memory system with hierarchical layers.
    
    Memory Hierarchy:
    1. Working Memory (volatile, in-session)
    2. Episodic Memory (session experiences, persisted)
    3. Semantic Memory (long-term knowledge, persisted)
    
    Original AtlasMemory collections are inherited for backward compatibility.
    """
    
    def __init__(self, persist_path: str = "./memory_db"):
        super().__init__(persist_path)
        
        # New hierarchical collections
        self.semantic_memory = self.client.get_or_create_collection(
            name="semantic_memory",
            metadata={"layer": "semantic", "description": "Long-term consolidated knowledge"}
        )
        self.episodic_memory = self.client.get_or_create_collection(
            name="episodic_memory", 
            metadata={"layer": "episodic", "description": "Session-specific experiences"}
        )
        
        # Working memory is volatile (in-memory only)
        self._working_memory: Dict[str, WorkingMemoryItem] = {}
        self._working_memory_lock = threading.Lock()
        
        # Session tracking
        self._session_id = f"session_{int(time.time())}"
    
    def add_to_working_memory(
        self, 
        key: str, 
        content: str, 
        context: str = "",
        priority: int = 0,
        ttl_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Add item to volatile working memory (current task context).
        
        Args:
            key: Unique identifier for this memory
            content: Memory content
            context: Additional context
            priority: Higher priority = more important (0-10)
            ttl_seconds: Time to live in seconds
        """
        with self._working_memory_lock:
            self._working_memory[key] = WorkingMemoryItem(
                content=content,
                context=context,
                priority=priority,
                ttl_seconds=ttl_seconds
            )
        return {"status": "success", "layer": "working", "key": key}
    
    def get_from_working_memory(self, key: str) -> Optional[WorkingMemoryItem]:
        """Get item from working memory by key."""
        with self._working_memory_lock:
            item = self._working_memory.get(key)
            if item and not item.is_expired():
                return item
            elif item:
                # Clean up expired
                del self._working_memory[key]
        return None
    
    def query_working_memory(self, query: str = "", min_priority: int = 0) -> List[Dict[str, Any]]:
        """
        Query working memory. Returns all non-expired items matching criteria.
        """
        with self._working_memory_lock:
            results = []
            expired_keys = []
            
            for key, item in self._working_memory.items():
                if item.is_expired():
                    expired_keys.append(key)
                    continue
                    
                if item.priority >= min_priority:
                    # Simple substring match for query
                    if not query or query.lower() in item.content.lower():
                        results.append({
                            "key": key,
                            "content": item.content,
                            "context": item.context,
                            "priority": item.priority,
                            "layer": "working"
                        })
            
            # Clean up expired
            for key in expired_keys:
                del self._working_memory[key]
            
            # Sort by priority
            return sorted(results, key=lambda x: x["priority"], reverse=True)
    
    def clear_working_memory(self) -> None:
        """Clear all working memory."""
        with self._working_memory_lock:
            self._working_memory.clear()
    
    def add_episodic_memory(
        self,
        content: str,
        action_type: str,
        outcome: str = "success",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Add experience to episodic memory (session-specific).
        
        Args:
            content: What happened
            action_type: Type of action (e.g., "tool_execution", "user_interaction")
            outcome: "success", "failed", "partial"
            metadata: Additional metadata
        """
        memory_id = f"episodic_{self._session_id}_{int(time.time() * 1000)}"
        
        clean_meta = {
            "session_id": self._session_id,
            "action_type": action_type,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "layer": "episodic"
        }
        
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
        
        try:
            self.episodic_memory.add(
                documents=[content],
                metadatas=[clean_meta],
                ids=[memory_id]
            )
            return {"status": "success", "layer": "episodic", "id": memory_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def query_episodic_memory(
        self, 
        query: str, 
        n_results: int = 5,
        session_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Query episodic memory.
        
        Args:
            query: Search query
            n_results: Max results
            session_only: If True, only return memories from current session
        """
        try:
            where_filter = None
            if session_only:
                where_filter = {"session_id": self._session_id}
            
            results = self.episodic_memory.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            formatted = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    meta["layer"] = "episodic"
                    formatted.append({
                        "content": doc,
                        "metadata": meta
                    })
            return formatted
        except Exception as e:
            print(f"[Memory] Episodic query error: {e}")
            return []
    
    def clear_episodic_memory(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear episodic memory.
        
        Args:
            session_id: If provided, only clear for this session. Otherwise clear all.
        """
        try:
            where_filter = {"session_id": session_id} if session_id else {}
            # If where_filter is empty, we must ensure the library supports it.
            # ChromaDB usually requires a filter for delete.
            self.episodic_memory.delete(where=where_filter)
            return {"status": "success", "layer": "episodic"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def add_semantic_memory(
        self,
        content: str,
        knowledge_type: str,
        confidence: float = 0.8,
        source: str = "trinity_runtime",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Add consolidated knowledge to semantic memory (long-term).
        
        Args:
            content: Knowledge content
            knowledge_type: Type (e.g., "pattern", "rule", "fact")
            confidence: Confidence score 0.0-1.0
            source: Where this knowledge came from
            metadata: Additional metadata
        """
        memory_id = f"semantic_{knowledge_type}_{int(time.time() * 1000)}"
        
        clean_meta = {
            "knowledge_type": knowledge_type,
            "confidence": confidence,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "layer": "semantic"
        }
        
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
        
        try:
            self.semantic_memory.add(
                documents=[content],
                metadatas=[clean_meta],
                ids=[memory_id]
            )
            return {"status": "success", "layer": "semantic", "id": memory_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def query_semantic_memory(
        self,
        query: str,
        n_results: int = 5,
        min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Query semantic memory for long-term knowledge.
        
        Args:
            query: Search query
            n_results: Max results
            min_confidence: Minimum confidence threshold
        """
        try:
            where_filter = None
            if min_confidence > 0:
                where_filter = {"confidence": {"$gte": min_confidence}}
            
            results = self.semantic_memory.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            formatted = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    meta["layer"] = "semantic"
                    formatted.append({
                        "content": doc,
                        "metadata": meta
                    })
            return formatted
        except Exception as e:
            print(f"[Memory] Semantic query error: {e}")
            return []
    
    def consolidate_to_semantic(
        self,
        episodic_content: str,
        knowledge_type: str = "pattern",
        confidence_boost: float = 0.0
    ) -> Dict[str, Any]:
        """
        Consolidate an episodic experience into semantic memory.
        Used to promote successful patterns to long-term knowledge.
        
        Args:
            episodic_content: Content to consolidate
            knowledge_type: Type of knowledge
            confidence_boost: Additional confidence (base is 0.7)
        """
        return self.add_semantic_memory(
            content=episodic_content,
            knowledge_type=knowledge_type,
            confidence=min(1.0, 0.7 + confidence_boost),
            source="consolidation",
            metadata={"consolidated_at": datetime.now().isoformat()}
        )
    
    def get_relevant_context(
        self,
        query: str,
        include_working: bool = True,
        include_episodic: bool = True,
        include_semantic: bool = True,
        max_results_per_layer: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query all memory layers for relevant context.
        
        Returns organized results from each layer, sorted by relevance.
        """
        results = {
            "working": [],
            "episodic": [],
            "semantic": [],
            "legacy": []  # Original AtlasMemory collections
        }
        
        if include_working:
            results["working"] = self.query_working_memory(query)[:max_results_per_layer]
        
        if include_episodic:
            results["episodic"] = self.query_episodic_memory(query, n_results=max_results_per_layer)
        
        if include_semantic:
            results["semantic"] = self.query_semantic_memory(query, n_results=max_results_per_layer)
        
        # Also query legacy knowledge_base for backward compatibility
        results["legacy"] = self.query_memory("knowledge_base", query, n_results=max_results_per_layer)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about memory usage."""
        with self._working_memory_lock:
            working_count = len(self._working_memory)
            expired_count = sum(1 for item in self._working_memory.values() if item.is_expired())
        
        return {
            "session_id": self._session_id,
            "working_memory": {
                "total_items": working_count,
                "expired_items": expired_count,
                "active_items": working_count - expired_count
            },
            "episodic_memory": {
                "total_items": self.episodic_memory.count()
            },
            "semantic_memory": {
                "total_items": self.semantic_memory.count()
            },
            "legacy_collections": {
                "ui_patterns": self.ui_patterns.count(),
                "strategies": self.strategies.count(),
                "user_habits": self.user_habits.count(),
                "knowledge_base": self.knowledge_base.count()
            }
        }


# Global Instance
_memory_instance = None


class _FallbackMemory:
    """Fallback when ChromaDB is not available."""
    def __init__(self):
        self._working_memory = {}

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
    
    # Hierarchical memory fallbacks
    def add_to_working_memory(self, key: str, content: str, *args, **kwargs):
        from datetime import datetime
        self._working_memory[key] = type('obj', (object,), {
            "content": content,
            "is_expired": lambda: False
        })
        return {"status": "success", "layer": "working", "key": key}
    
    def query_working_memory(self, query: str = "", *args, **kwargs):
        return [{"key": k, "content": v.content} for k, v in self._working_memory.items()]

    def get_from_working_memory(self, key: str, *args, **kwargs):
        return self._working_memory.get(key)

    def clear_working_memory(self, *args, **kwargs):
        self._working_memory.clear()
    
    def add_episodic_memory(self, *args, **kwargs):
        return {"status": "success", "layer": "episodic", "id": "fallback"}
    
    def query_episodic_memory(self, *args, **kwargs):
        return []
    
    def add_semantic_memory(self, *args, **kwargs):
        return {"status": "success", "layer": "semantic", "id": "fallback"}
    
    def query_semantic_memory(self, *args, **kwargs):
        return []
    
    def get_relevant_context(self, *args, **kwargs):
        return {"working": [], "episodic": [], "semantic": [], "legacy": []}
    
    def get_stats(self):
        return {"fallback_mode": True}

    def delete_memory(self, *args, **kwargs):
        return {"status": "success", "deleted": 0}
        
    def clear_episodic_memory(self, *args, **kwargs):
        return {"status": "success", "layer": "episodic"}


def get_memory() -> AtlasMemory:
    """Get the global memory instance (backward compatible)."""
    global _memory_instance
    if _memory_instance is None:
        try:
            _memory_instance = HierarchicalMemory(persist_path=os.path.join(os.getcwd(), ".atlas_memory"))
        except BaseException:
            _memory_instance = _FallbackMemory()
    return _memory_instance


def get_hierarchical_memory() -> HierarchicalMemory:
    """Get the global memory instance with hierarchical features."""
    memory = get_memory()
    if isinstance(memory, HierarchicalMemory):
        return memory
    # Return fallback that implements hierarchical interface
    return _FallbackMemory()


# MCP Wrapper Functions (backward compatible)
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


# New hierarchical memory tools
def save_episodic_memory_tool(
    content: str,
    action_type: str = "general",
    outcome: str = "success"
) -> Dict[str, Any]:
    """Save an experience to episodic memory."""
    mem = get_hierarchical_memory()
    return mem.add_episodic_memory(content, action_type, outcome)


def save_semantic_memory_tool(
    content: str,
    knowledge_type: str = "pattern",
    confidence: float = 0.8
) -> Dict[str, Any]:
    """Save knowledge to long-term semantic memory."""
    mem = get_hierarchical_memory()
    return mem.add_semantic_memory(content, knowledge_type, confidence)


def query_all_memory_tool(query: str) -> Dict[str, Any]:
    """Query all memory layers for relevant context."""
    mem = get_hierarchical_memory()
    results = mem.get_relevant_context(query)
    return {"status": "success", "results": results}


def clear_memory_tool(target: str = "working") -> Dict[str, Any]:
    """
    Clear memory layers.
    target: 'working', 'episodic', 'all'
    """
    mem = get_hierarchical_memory()
    if target == "working":
        mem.clear_working_memory()
        return {"status": "success", "target": "working"}
    elif target == "episodic":
        return mem.clear_episodic_memory() # Clear all episodic
    elif target == "all":
        mem.clear_working_memory()
        res = mem.clear_episodic_memory()
        return {"status": "success", "target": "all", "episodic_result": res}
    return {"status": "error", "error": "Invalid target"}
