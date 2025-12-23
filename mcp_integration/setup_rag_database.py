#!/usr/bin/env python3
"""
Setup RAG database with tool examples for MCP servers.
Loads examples from repository and creates vector database.
"""

import glob
import json
import os
from chromadb import Client
from chromadb.utils import embedding_functions


def setup_rag_database():
    """Setup Chroma vector database with tool examples."""
    
    # Initialize Chroma client
    client = Client()
    
    # Use sentence-transformers for embeddings
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Create collection
    collection = client.create_collection(
        name="mcp_tool_examples",
        embedding_function=sentence_transformer_ef
    )
    
    # Load examples from repository
    examples = []
    example_dirs = [
        "repository/tool_examples",
        "mcp_examples",
        "examples/tool_examples"
    ]
    
    for dir_path in example_dirs:
        if os.path.exists(dir_path):
            for file_path in glob.glob(f"{dir_path}/*.json"):
                with open(file_path, 'r') as f:
                    examples.extend(json.load(f))
    
    if not examples:
        print("⚠️  No tool examples found")
        return
    
    # Add examples to collection
    collection.add(
        documents=[e["description"] for e in examples],
        metadatas=[
            {
                "tool": e.get("tool", "unknown"),
                "category": e.get("category", "general"),
                "server": e.get("server", "playwright")
            }
            for e in examples
        ],
        ids=[f"example_{i}" for i in range(len(examples))]
    )
    
    print(f"✅ Added {len(examples)} tool examples to RAG database")
    print(f"📊 Database ready for semantic search")
    
    return collection


def query_rag_database(collection, query: str, top_k: int = 5):
    """Query RAG database for similar examples."""
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    return [
        {
            "tool": r["metadatas"][0]["tool"],
            "description": r["documents"][0],
            "category": r["metadatas"][0]["category"],
            "server": r["metadatas"][0]["server"],
            "similarity": r["distances"][0]
        }
        for r in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


if __name__ == "__main__":
    print("🚀 Setting up RAG database...")
    
    # Create example directory if needed
    os.makedirs("repository/tool_examples", exist_ok=True)
    
    # Create sample examples if none exist
    if not glob.glob("repository/tool_examples/*.json"):
        print("📦 Creating sample tool examples...")
        samples = [
            {
                "tool": "browser_navigate",
                "description": "Navigate to URL using browser_navigate",
                "category": "browser",
                "server": "playwright"
            },
            {
                "tool": "browser_click_element",
                "description": "Click element using browser_click_element",
                "category": "browser",
                "server": "playwright"
            },
            {
                "tool": "run_shell",
                "description": "Execute shell command using run_shell",
                "category": "system",
                "server": "local"
            }
        ]
        
        for i, sample in enumerate(samples):
            with open(f"repository/tool_examples/sample_{i}.json", 'w') as f:
                json.dump([sample], f)
    
    # Setup database
    collection = setup_rag_database()
    
    # Test query
    if collection:
        results = query_rag_database(collection, "search for AI news")
        print(f"✅ Test query results: {len(results)} examples found")
        for r in results:
            print(f"  - {r['tool']}: {r['description']}")
    
    print("🎉 RAG database setup complete!")
