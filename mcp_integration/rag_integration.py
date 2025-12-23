#!/usr/bin/env python3
"""
MCP RAG Integration Module
Provides intelligent tool selection using RAG-powered semantic search.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
import redis

from mcp_integration.chroma_utils import create_persistent_client, get_default_chroma_persist_dir

logger = logging.getLogger(__name__)


class MCPToolSelector:
    """Intelligent tool selector using RAG and semantic search."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.base_dir = Path(__file__).parent
        self.chroma_client = None
        self.collection = None
        self.redis_client = None
        self.config = {}
        self.fallback_chain = []
        
        self._initialize()
        self._initialized = True
    
    def _initialize(self):
        """Initialize the tool selector with graceful fallback for ChromaDB issues."""
        try:
            self._load_config()
            self._init_chroma()
            self._init_redis()
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")

    def _load_config(self):
        config_file = self.base_dir / "config" / "mcp_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.fallback_chain = self.config.get('fallbackChain', ['local_fallback'])

    def _init_chroma(self):
        persist_dir = get_default_chroma_persist_dir() / "mcp_integration"
        try:
            init_res = create_persistent_client(persist_dir=persist_dir, logger=logger)
        except BaseException as e:
            # Catch pyo3_runtime.PanicException and other fatal errors from chromadb
            logger.error(f"❌ Chroma PersistentClient init failed (panic or error): {e}")
            init_res = None
        
        if init_res is not None:
            self.chroma_client = init_res.client
        else:
            logger.warning("⚠️ ChromaDB persistence unavailable; using in-memory client")
            try:
                self.chroma_client = chromadb.Client()
            except Exception as disc_err:
                self.chroma_client = None
                logger.error(f"❌ ChromaDB completely unavailable, RAG disabled: {disc_err}")
        
        if self.chroma_client:
            self._setup_collection()

    def _setup_collection(self):
        try:
            self.collection = self.chroma_client.get_collection("mcp_tool_schemas")
            logger.info(f"✅ Connected to existing RAG collection ({self.collection.count()} items)")
        except Exception:
            try:
                self.collection = self.chroma_client.create_collection(
                    name="mcp_tool_schemas",
                    metadata={"description": "MCP tool schemas and examples"}
                )
                logger.info("📊 Created new RAG collection")
            except Exception as col_err:
                self.collection = None
                logger.warning(f"⚠️ Could not create collection: {col_err}")

    def _init_redis(self):
        try:
            self.redis_client = redis.Redis(
                host='localhost', port=6379, db=0, decode_responses=True
            )
            self.redis_client.ping()
            logger.info("✅ Connected to Redis cache")
        except Exception as redis_err:
            self.redis_client = None
            logger.warning(f"⚠️  Redis not available, using direct search: {redis_err}")
    
    def select_tool(self, task_description: str, n_candidates: int = 5) -> List[Dict[str, Any]]:
        """Select the best tools for a given task using semantic search."""
        try:
            cached = self._check_cache(task_description)
            if cached:
                return cached
            
            if not self.collection:
                return []

            results = self.collection.query(
                query_texts=[task_description],
                n_results=n_candidates
            )
            
            candidates = self._process_query_results(results)
            
            if candidates:
                self._update_cache(task_description, candidates)
            
            return self._prioritize_mcp_tools(candidates)
            
        except Exception as e:
            logger.error(f"❌ Tool selection error: {e}")
            return []

    def _check_cache(self, task_description: str) -> Optional[List[Dict[str, Any]]]:
        if not self.redis_client:
            return None
        cache_key = f"tool_selection:{hash(task_description)}"
        cached = self.redis_client.get(cache_key)
        return json.loads(cached) if cached else None

    def _update_cache(self, task_description: str, candidates: List[Dict[str, Any]]):
        if not self.redis_client:
            return
        cache_key = f"tool_selection:{hash(task_description)}"
        self.redis_client.setex(cache_key, 300, json.dumps(candidates))

    def _process_query_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates = []
        if not (results and results.get('documents') and results['documents'][0]):
            return candidates

        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            candidate = {
                "rank": i + 1,
                "tool": meta.get("tool", "unknown"),
                "server": meta.get("server", "local"),
                "category": meta.get("category", "general"),
                "description": doc,
                "score": 1.0 - (dist / 2.0),
                "full_schema": json.loads(meta.get("full_schema", "{}")) if meta.get("full_schema") else {}
            }
            candidates.append(candidate)
        return candidates

    def _prioritize_mcp_tools(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Boost scores of MCP server tools to ensure they are prioritized/
        """
        for candidate in candidates:
            server = candidate.get("server", "local")
            # Boost score if not a fallback/local server
            if server not in ["local", "local_fallback", "unknown"]:
                candidate["score"] = min(1.0, candidate["score"] * 1.2)  # 20% boost
        
        # Re-sort based on new scores
        return sorted(candidates, key=lambda x: x["score"], reverse=True)

    def select_tool_sequence(self, task_steps: List[str]) -> List[Dict[str, Any]]:
        """
        Select the best tool for each step in a sequence of tasks.
        
        Args:
            task_steps: List of task descriptions (e.g. ["open browser", "search google"])
            
        Returns:
            List of best tool for each step, maintaining order.
        """
        sequence_tools = []
        for step in task_steps:
            best_tool = self.get_best_tool(step)
            if best_tool:
                sequence_tools.append(best_tool)
            else:
                sequence_tools.append({"tool": "unknown", "description": "No suitable tool found for step"})
        return sequence_tools
    
    def get_best_tool(self, task_description: str) -> Optional[Dict[str, Any]]:
        """Get the single best tool for a task."""
        candidates = self.select_tool(task_description, n_candidates=1)
        return candidates[0] if candidates else None
    
    def get_server_for_tool(self, tool_name: str) -> str:
        """Get the MCP server that provides a specific tool."""
        servers = self.config.get('mcpServers', {})
        
        # Check Redis cache
        if self.redis_client:
            for server_name in servers:
                tool_key = f"mcp:tool:{server_name}:{tool_name}"
                if self.redis_client.exists(tool_key):
                    return server_name
        
        # Fallback to config-based lookup
        tool_to_server = {
            "browser_": "playwright",
            "gui_": "pyautogui", 
            "ai_": "anthropic",
            "file_": "filesystem",
            "dir_": "filesystem",
            "run_shell": "local_fallback",
            "run_applescript": "applescript",
            "code_": "sonarqube"
        }
        
        for prefix, server in tool_to_server.items():
            if tool_name.startswith(prefix):
                return server
        
        return self.fallback_chain[0] if self.fallback_chain else "local_fallback"
    
    def get_fallback_server(self, primary_server: str) -> Optional[str]:
        """Get the fallback server for a given primary server."""
        try:
            idx = self.fallback_chain.index(primary_server)
            if idx + 1 < len(self.fallback_chain):
                return self.fallback_chain[idx + 1]
        except ValueError:
            pass
        
        return self.fallback_chain[0] if self.fallback_chain else None
    
    def classify_task(self, task_description: str) -> Tuple[str, float]:
        """
        Classify a task into a category.
        
        Returns:
            Tuple of (category, confidence)
        """
        candidates = self.select_tool(task_description, n_candidates=3)
        
        if not candidates:
            return ("general", 0.0)
        
        # Vote by category
        category_scores = {}
        for c in candidates:
            cat = c.get("category", "general")
            category_scores[cat] = category_scores.get(cat, 0) + c.get("score", 0)
        
        best_category = max(category_scores, key=category_scores.get)
        confidence = category_scores[best_category] / sum(category_scores.values())
        
        return (best_category, confidence)
    
    def get_tool_examples(self, tool_name: str, n_examples: int = 5) -> List[str]:
        """Get example usages for a tool."""
        if self.collection:
            results = self.collection.query(
                query_texts=[f"example of using {tool_name}"],
                n_results=n_examples,
                where={"tool": tool_name}
            )
            
            if results and results['documents']:
                return results['documents'][0]
        
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG database."""
        stats = {
            "total_tools": 0,
            "categories": [],
            "servers": [],
            "chroma_enabled": self.collection is not None,
            "redis_enabled": self.redis_client is not None
        }
        
        if self.collection:
            try:
                stats["total_tools"] = self.collection.count()
            except Exception:
                pass
        
        return stats


# Singleton instance
tool_selector = MCPToolSelector()


def select_tool_for_task(task: str, n_candidates: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for tool selection."""
    return tool_selector.select_tool(task, n_candidates)


def get_best_tool_for_task(task: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get the best tool."""
    return tool_selector.get_best_tool(task)


def classify_task(task: str) -> Tuple[str, float]:
    """Convenience function for task classification."""
    return tool_selector.classify_task(task)
