#!/usr/bin/env python3
"""
MCP Prompt Engine
Handles retrieval of dynamic prompts and official documentation for MCP servers/tasks.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings

from mcp_integration.chroma_utils import create_persistent_client, get_default_chroma_persist_dir

logger = logging.getLogger(__name__)

class MCPPromptEngine:
    """
    Engine for retrieving task-specific prompts and official documentation 
    using semantic search (RAG).
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.chroma_client = None
        self.prompts_collection = None
        self.docs_collection = None
        
        self._initialize()
        self._initialized = True
    
    def _initialize(self):
        """Initialize ChromaDB connection and collections."""
        persist_dir = get_default_chroma_persist_dir() / "mcp_integration"
        try:
            init_res = create_persistent_client(persist_dir=persist_dir, logger=logger)
            if init_res:
                self.chroma_client = init_res.client
                self._setup_collections()
            else:
                logger.warning("⚠️ ChromaDB unavailable for Prompt Engine")
        except Exception as e:
            logger.error(f"❌ Prompt Engine Init Error: {e}")

    def _setup_collections(self):
        """Get or create necessary collections."""
        if not self.chroma_client:
            return

        try:
            # Collection for "Expert Prompts" (Community/Optimized)
            self.prompts_collection = self.chroma_client.get_or_create_collection(
                name="mcp_prompts",
                metadata={"description": "Optimized system prompts for specific tasks/servers"}
            )
            
            # Collection for "Official Docs" (Fallback)
            self.docs_collection = self.chroma_client.get_or_create_collection(
                name="mcp_docs",
                metadata={"description": "Official documentation for MCP servers and tools"}
            )
            logger.info("✅ Prompt Engine collections ready")
        except Exception as e:
            logger.error(f"❌ Failed to setup prompt collections: {e}")

    def get_relevant_prompts(self, task: str, n_results: int = 3, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant system prompts for the task.
        
        Args:
            task: The user's task description or query.
            n_results: Number of prompts to retrieve.
            threshold: Minimum similarity score (0.0 to 1.0) to consider valid.
            
        Returns:
            List of prompt dicts {content, source, score, metadata}
        """
        if not self.prompts_collection:
            return []
            
        try:
            results = self.prompts_collection.query(
                query_texts=[task],
                n_results=n_results
            )
            
            return self._process_results(results, threshold)
        except Exception as e:
            logger.error(f"Error retrieving prompts: {e}")
            return []

    def get_relevant_docs(self, query: str, n_results: int = 3) -> List[str]:
        """
        Retrieve relevant official documentation chunks.
        Used as fallback or context augmentation.
        """
        if not self.docs_collection:
            return []
            
        try:
            results = self.docs_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Simply return the text content for docs
            docs = []
            if results['documents']:
                for doc in results['documents'][0]:
                    docs.append(doc)
            return docs
        except Exception as e:
            logger.error(f"Error retrieving docs: {e}")
            return []

    def _process_results(self, results: Dict[str, Any], threshold: float) -> List[Dict[str, Any]]:
        """Process ChromaDB query results into standardized format."""
        processed = []
        if not (results and results.get('documents') and results['documents'][0]):
            return processed

        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            # Convert cosine distance to similarity score approx
            score = 1.0 - (dist / 2.0)
            
            if score < threshold:
                continue
                
            item = {
                "content": doc,
                "metadata": meta,
                "score": score,
                "source": meta.get("source", "unknown")
            }
            processed.append(item)
            
        return sorted(processed, key=lambda x: x['score'], reverse=True)

    def construct_context(self, task: str) -> str:
        """
        Construct a context block for the LLM based on RAG results.
        Combines optimized prompts and fallback docs if needed.
        """
        prompts = self.get_relevant_prompts(task)
        context_parts = []
        
        if prompts:
            context_parts.append("### Recommended Strategies")
            for p in prompts:
                context_parts.append(f"- {p['content']} (Source: {p['source']})")
        else:
            # Fallback to docs if no specific prompts found
            docs = self.get_relevant_docs(task, n_results=2)
            if docs:
                context_parts.append("### Reference Documentation")
                context_parts.extend(docs)
                
        return "\n\n".join(context_parts)

# Singleton
prompt_engine = MCPPromptEngine()
