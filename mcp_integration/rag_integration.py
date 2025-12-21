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
            # Load configuration
            config_file = self.base_dir / "config" / "mcp_config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                self.fallback_chain = self.config.get('fallbackChain', ['local_fallback'])
            
            # Initialize ChromaDB with persistent storage
            persist_dir = get_default_chroma_persist_dir() / "mcp_integration"
            
            # Use PersistentClient for data persistence (repair+retry once on Rust panic)
            init_res = create_persistent_client(persist_dir=persist_dir, logger=logger)
            if init_res is not None:
                self.chroma_client = init_res.client
            else:
                # If persistence is not available, fall back to in-memory as last resort
                logger.warning("⚠️ ChromaDB persistence unavailable; using in-memory client")
                try:
                    self.chroma_client = chromadb.Client()
                except BaseException:
                    self.chroma_client = None
                    logger.error("❌ ChromaDB completely unavailable, RAG disabled")
            
            if self.chroma_client:
                try:
                    self.collection = self.chroma_client.get_collection("mcp_tool_schemas")
                    count = self.collection.count()
                    logger.info(f"✅ Connected to existing RAG collection ({count} items)")
                except:
                    try:
                        self.collection = self.chroma_client.create_collection(
                            name="mcp_tool_schemas",
                            metadata={"description": "MCP tool schemas and examples"}
                        )
                        logger.info("📊 Created new RAG collection")
                    except Exception as col_err:
                        self.collection = None
                        logger.warning(f"⚠️ Could not create collection: {col_err}")
            
            # Initialize Redis
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("✅ Connected to Redis cache")
            except:
                self.redis_client = None
                logger.warning("⚠️  Redis not available, using direct search")
                
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
    
    def select_tool(self, task_description: str, n_candidates: int = 5) -> List[Dict[str, Any]]:
        """
        Select the best tools for a given task using semantic search.
        
        Args:
            task_description: Natural language description of the task
            n_candidates: Number of candidate tools to return
            
        Returns:
            List of tool candidates with scores
        """
        try:
            # Check Redis cache first
            cache_key = f"tool_selection:{hash(task_description)}"
            if self.redis_client:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            
            # Perform semantic search
            if self.collection:
                results = self.collection.query(
                    query_texts=[task_description],
                    n_results=n_candidates
                )
                
                candidates = []
                if results and results['documents'] and results['documents'][0]:
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
                            "score": 1.0 - (dist / 2.0),  # Convert distance to similarity
                            "full_schema": json.loads(meta.get("full_schema", "{}")) if meta.get("full_schema") else {}
                        }
                        candidates.append(candidate)
                
                # Cache results
                if self.redis_client and candidates:
                    self.redis_client.setex(cache_key, 300, json.dumps(candidates))
                
                return candidates
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Tool selection error: {e}")
            return []
    
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
            except:
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
