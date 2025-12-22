"""Learning Memory System

Stores successful task executions and learned patterns when
learning_mode is enabled. Automatically consolidates patterns
from successful executions into long-term semantic memory.

Features:
- Record successful task executions with full context
- Store learned UI patterns and strategies
- Auto-consolidate successful patterns to semantic memory
- Export/import learning data
"""

import os
import json
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class LearningEntry:
    """A single learning entry from successful task execution."""
    id: str
    task: str
    steps: List[Dict[str, Any]]
    tools_used: List[str]
    outcome: str
    duration_ms: int
    timestamp: str
    consolidated: bool = False
    confidence: float = 0.7
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningEntry":
        return cls(**data)


class LearningMemory:
    """
    Dedicated memory storage for learning mode.
    
    Stores successful task executions and learned patterns,
    with ability to consolidate to long-term semantic memory.
    """
    
    def __init__(self, persist_path: str = "./.learning_memory"):
        self.persist_path = Path(persist_path).expanduser().resolve()
        self.persist_path.mkdir(parents=True, exist_ok=True)
        
        self._entries_file = self.persist_path / "learning_entries.json"
        self._lock = threading.Lock()
        
        # Load existing entries
        self._entries: Dict[str, LearningEntry] = {}
        self._load_entries()
        
        # ChromaDB for vector search
        self._chroma_client = None
        self._collection = None
        self._init_chroma()
    
    def _init_chroma(self) -> None:
        """Initialize ChromaDB for semantic search of learning entries."""
        try:
            import chromadb
            chroma_path = self.persist_path / "chroma"
            chroma_path.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=str(chroma_path))
            self._collection = self._chroma_client.get_or_create_collection(
                name="learning_entries",
                metadata={"description": "Learning mode successful executions"}
            )
        except Exception as e:
            print(f"[LearningMemory] ChromaDB init failed: {e}")
            self._chroma_client = None
            self._collection = None
    
    def _load_entries(self) -> None:
        """Load entries from JSON file."""
        if not self._entries_file.exists():
            return
        try:
            with open(self._entries_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._entries = {
                    k: LearningEntry.from_dict(v) 
                    for k, v in data.items()
                }
        except Exception as e:
            print(f"[LearningMemory] Load error: {e}")
            self._entries = {}
    
    def _save_entries(self) -> None:
        """Save entries to JSON file."""
        try:
            with open(self._entries_file, "w", encoding="utf-8") as f:
                data = {k: v.to_dict() for k, v in self._entries.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LearningMemory] Save error: {e}")
    
    def record_successful_execution(
        self,
        task: str,
        steps: List[Dict[str, Any]],
        tools_used: List[str],
        outcome: str = "success",
        duration_ms: int = 0,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Record a successful task execution for learning.
        
        Args:
            task: The original task description
            steps: List of execution steps (action, result, etc.)
            tools_used: List of tool names used
            outcome: Execution outcome (success/partial)
            duration_ms: Execution duration in milliseconds
            metadata: Additional metadata
            tags: Tags for categorization
            
        Returns:
            Status dict with entry ID
        """
        with self._lock:
            entry_id = f"learn_{int(time.time() * 1000)}"
            
            entry = LearningEntry(
                id=entry_id,
                task=task,
                steps=steps or [],
                tools_used=tools_used or [],
                outcome=outcome,
                duration_ms=duration_ms,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {},
                tags=tags or []
            )
            
            self._entries[entry_id] = entry
            self._save_entries()
            
            # Add to ChromaDB for semantic search
            if self._collection is not None:
                try:
                    self._collection.add(
                        documents=[task],
                        metadatas=[{
                            "entry_id": entry_id,
                            "outcome": outcome,
                            "tools": ",".join(tools_used or []),
                            "timestamp": entry.timestamp
                        }],
                        ids=[entry_id]
                    )
                except Exception as e:
                    print(f"[LearningMemory] ChromaDB add error: {e}")
            
            return {"status": "success", "id": entry_id}
    
    def get_learning_history(
        self,
        limit: int = 50,
        filter_type: Optional[str] = None,
        consolidated_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get list of recorded learning entries.
        
        Args:
            limit: Maximum number of entries to return
            filter_type: Filter by outcome type (success/partial)
            consolidated_only: Only return consolidated entries
            
        Returns:
            List of learning entry dicts
        """
        with self._lock:
            entries = list(self._entries.values())
            
            # Apply filters
            if filter_type:
                entries = [e for e in entries if e.outcome == filter_type]
            if consolidated_only:
                entries = [e for e in entries if e.consolidated]
            
            # Sort by timestamp descending (newest first)
            entries.sort(key=lambda x: x.timestamp, reverse=True)
            
            return [e.to_dict() for e in entries[:limit]]
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific learning entry by ID."""
        with self._lock:
            entry = self._entries.get(entry_id)
            return entry.to_dict() if entry else None
    
    def search_similar(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past executions using semantic search.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of similar learning entries
        """
        if self._collection is None:
            return []
        
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            found = []
            if results["ids"] and results["ids"][0]:
                for entry_id in results["ids"][0]:
                    entry = self._entries.get(entry_id)
                    if entry:
                        found.append(entry.to_dict())
            return found
        except Exception as e:
            print(f"[LearningMemory] Search error: {e}")
            return []
    
    def consolidate_to_semantic(
        self,
        entry_id: str,
        confidence_boost: float = 0.1
    ) -> Dict[str, Any]:
        """
        Promote learning entry to long-term semantic memory.
        
        Args:
            entry_id: The learning entry ID to consolidate
            confidence_boost: Additional confidence score
            
        Returns:
            Status dict
        """
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return {"status": "error", "error": f"Entry not found: {entry_id}"}
            
            if entry.consolidated:
                return {"status": "error", "error": "Entry already consolidated"}
            
            try:
                from core.memory import get_hierarchical_memory
                
                mem = get_hierarchical_memory()
                
                # Create semantic content from execution
                content = f"Task: {entry.task}\n"
                content += f"Tools: {', '.join(entry.tools_used)}\n"
                content += f"Outcome: {entry.outcome}\n"
                if entry.steps:
                    content += f"Steps: {len(entry.steps)} actions performed\n"
                
                result = mem.add_semantic_memory(
                    content=content,
                    knowledge_type="learned_pattern",
                    confidence=min(1.0, entry.confidence + confidence_boost),
                    source="learning_memory",
                    metadata={
                        "learning_entry_id": entry_id,
                        "tools": entry.tools_used,
                        "consolidated_at": datetime.now().isoformat()
                    }
                )
                
                # Mark as consolidated
                entry.consolidated = True
                entry.confidence = min(1.0, entry.confidence + confidence_boost)
                self._save_entries()
                
                return {
                    "status": "success", 
                    "semantic_id": result.get("id"),
                    "message": f"Consolidated entry {entry_id} to semantic memory"
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
    
    def delete_entry(self, entry_id: str) -> Dict[str, Any]:
        """
        Delete a learning entry.
        
        Args:
            entry_id: The entry ID to delete
            
        Returns:
            Status dict
        """
        with self._lock:
            if entry_id not in self._entries:
                return {"status": "error", "error": f"Entry not found: {entry_id}"}
            
            del self._entries[entry_id]
            self._save_entries()
            
            # Remove from ChromaDB
            if self._collection is not None:
                try:
                    self._collection.delete(ids=[entry_id])
                except Exception:
                    pass
            
            return {"status": "success", "deleted": entry_id}
    
    def export_learning_data(self, path: str) -> Dict[str, Any]:
        """
        Export learning data to JSON file.
        
        Args:
            path: Export file path
            
        Returns:
            Status dict
        """
        with self._lock:
            try:
                export_path = Path(path).expanduser().resolve()
                data = {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "total_entries": len(self._entries),
                    "entries": {k: v.to_dict() for k, v in self._entries.items()}
                }
                
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return {
                    "status": "success", 
                    "path": str(export_path),
                    "entries_exported": len(self._entries)
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
    
    def import_learning_data(self, path: str, merge: bool = True) -> Dict[str, Any]:
        """
        Import learning data from JSON file.
        
        Args:
            path: Import file path
            merge: If True, merge with existing. If False, replace.
            
        Returns:
            Status dict
        """
        with self._lock:
            try:
                import_path = Path(path).expanduser().resolve()
                
                with open(import_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                entries_data = data.get("entries", {})
                imported_count = 0
                
                if not merge:
                    self._entries.clear()
                
                for k, v in entries_data.items():
                    if k not in self._entries or not merge:
                        self._entries[k] = LearningEntry.from_dict(v)
                        imported_count += 1
                
                self._save_entries()
                
                # Re-index ChromaDB
                self._reindex_chroma()
                
                return {
                    "status": "success",
                    "imported": imported_count,
                    "total": len(self._entries)
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
    
    def _reindex_chroma(self) -> None:
        """Reindex all entries in ChromaDB."""
        if self._collection is None:
            return
        
        try:
            # Clear and re-add all
            for entry_id, entry in self._entries.items():
                try:
                    self._collection.delete(ids=[entry_id])
                except Exception:
                    pass
                
                self._collection.add(
                    documents=[entry.task],
                    metadatas=[{
                        "entry_id": entry_id,
                        "outcome": entry.outcome,
                        "tools": ",".join(entry.tools_used or []),
                        "timestamp": entry.timestamp
                    }],
                    ids=[entry_id]
                )
        except Exception as e:
            print(f"[LearningMemory] Reindex error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning memory statistics."""
        with self._lock:
            total = len(self._entries)
            consolidated = sum(1 for e in self._entries.values() if e.consolidated)
            
            # Group by outcome
            outcomes = {}
            for e in self._entries.values():
                outcomes[e.outcome] = outcomes.get(e.outcome, 0) + 1
            
            return {
                "total_entries": total,
                "consolidated": consolidated,
                "pending": total - consolidated,
                "outcomes": outcomes,
                "chroma_available": self._collection is not None
            }
    
    def clear_all(self) -> Dict[str, Any]:
        """Clear all learning entries."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._save_entries()
            
            # Clear ChromaDB
            if self._collection is not None:
                try:
                    # Delete all
                    ids = list(self._entries.keys()) 
                    if ids:
                        self._collection.delete(ids=ids)
                except Exception:
                    pass
            
            return {"status": "success", "cleared": count}


# Global instance
_learning_memory_instance: Optional[LearningMemory] = None


def get_learning_memory() -> LearningMemory:
    """Get the global learning memory instance."""
    global _learning_memory_instance
    if _learning_memory_instance is None:
        _learning_memory_instance = LearningMemory(
            persist_path=os.path.join(os.getcwd(), ".learning_memory")
        )
    return _learning_memory_instance
