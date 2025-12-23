#!/usr/bin/env python3
"""
MCP Data Ingestion Script
Downloads and ingests prompts and schemas into ChromaDB.
Optimized for Apple Silicon (MPS).
"""

import os
import json
import logging
import argparse
import requests
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_integration.chroma_utils import create_persistent_client, get_default_chroma_persist_dir
from typing import List, Dict, Any

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CHROMA_PERSIST_DIR = os.path.expanduser("~/.system_cli/chroma/mcp_integration")
PROMPTS_COLLECTION = "mcp_prompts"
SCHEMAS_COLLECTION = "mcp_tool_schemas"

# Github Sources for Prompts
PROMPT_SOURCES = [
    {
        "name": "fabric_patterns",
        "url": "https://api.github.com/repos/danielmiessler/fabric/contents/patterns",
        "type": "github_dir",
        "recursive": True,
        "target_file": "system.md"
    },
    {
        "name": "langgpt_llms",
        "url": "https://api.github.com/repos/langgptai/awesome-system-prompts/contents/LLMs",
        "type": "github_dir",
        "recursive": True,
        "target_extension": ".md"
    },
    {
        "name": "big_prompt_library_sys",
        "url": "https://api.github.com/repos/0xeb/TheBigPromptLibrary/contents/SystemPrompts",
        "type": "github_dir",
        "recursive": True,
        "target_extension": ".md"
    }
]

# Manual Data for specific servers (simulating schema/prompt ingestion)
SERVER_DATA = {
    "filesystem": {
        "prompts": [
            "When using filesystem tools, ALWAYS verify the path exists using `list_directory` or `allowed_directories` check before reading.",
            "If a file is large, read it in chunks or use `read_file` with line limits to avoid memory issues.",
            "For write operations, always create a backup of critical configuration files before overwriting.",
            "Prefer absolute paths over relative paths to avoid ambiguity in file operations."
        ],
        "schemas": [
            {
                "name": "read_file",
                "description": "Read the contents of a file from the filesystem.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The absolute path to the file to read"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file. Overwrites existing content.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The absolute path to the file"},
                        "content": {"type": "string", "description": "The content to write"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The directory path"}
                    },
                    "required": ["path"]
                }
            }
        ]
    },
    "playwright": {
        "prompts": [
            "When automating a browser to watch video, ALWAYS ensure you handle cookie consent popups explicitly before trying to interact with player controls.",
            "To find a movie online, use a search engine (Google/DuckDuckGo) first, then navigate to a specific high-probability streaming site result.",
            "If a video player click fails, try using `evaluate_javascript` to trigger the click event directly on the standard video API.",
            "Wait for the page to fully load (load_state='networkidle') before attempting to find video elements."
        ],
        "schemas": [
            {
                "name": "navigate",
                "description": "Navigate to a URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            },
            {
                "name": "click",
                "description": "Click an element",
                "inputSchema": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}},
                    "required": ["selector"]
                }
            },
            {
                "name": "input_text",
                "description": "Input text into a field",
                "inputSchema": {
                    "type": "object",
                    "properties": {"selector": {"type": "string"}, "text": {"type": "string"}},
                    "required": ["selector", "text"]
                }
            }
        ]
    },
    "desktop_control": {
        "prompts": [
            "To make a video fullscreen, first try the browser's fullscreen button. If that fails, simulate the 'f' key press using `press_key`.",
            "To verify fullscreen mode, use `take_screenshot` and analyze if the window borders are visible or if the content covers the entire resolution.",
            "When watching content, ensure the mouse cursor is moved to a safe corner (e.g., 0,0) to hide controls.",
            "If valid state cannot be confirmed via DOM (e.g. canvas or video), rely on visual verification."
        ],
        "schemas": [
            {
                "name": "press_key",
                "description": "Simulate a key press (PyAutoGUI)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                    "required": ["key"]
                }
            },
            {
                "name": "move_mouse",
                "description": "Move the mouse cursor",
                "inputSchema": {
                    "type": "object",
                    "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                    "required": ["x", "y"]
                }
            },
            {
                "name": "take_screenshot",
                "description": "Capture the screen for analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
    },
    "applescript": {
        "prompts": [
            "Use AppleScript for macOS UI automation when specific low-level control is needed for an application.",
            "Always handle potential permissions blocks (System Events) by checking permissions first if possible.",
            "When clicking UI elements with AppleScript, use `click menu item` pattern for menu bar interactions.",
            "Prefer `run_applescript` for executing raw scripts over shell invocation of `osascript`."
        ],
        "schemas": [
            {
                "name": "run_applescript",
                "description": "Execute AppleScript code",
                "inputSchema": {
                    "type": "object",
                    "properties": {"script": {"type": "string"}},
                    "required": ["script"]
                }
            }
        ]
    },
    "anthropic": {
        "prompts": [
            "Use Anthropic tools for generating creative text, code snippets, or analyzing complex documents.",
            "For sub-tasks requiring reasoning (e.g., 'summarize this text'), use `generate_text` directly instead of asking the main agent to do it internally.",
            "When generating code, use `generate_code` to ensure proper markdown formatting and language specification."
        ],
        "schemas": [
            {
                "name": "generate_text",
                "description": "Generate text using Claude",
                "inputSchema": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                    "required": ["prompt"]
                }
            },
            {
                "name": "generate_code",
                "description": "Generate code using Claude",
                "inputSchema": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}, "language": {"type": "string"}},
                    "required": ["prompt"]
                }
            }
        ]
    },
    "sonarqube": {
        "prompts": [
            "Use SonarQube tools to check project health or finding specific code issues.",
            "To check overall quality, use `get_project_status` and look for the 'quality_gate' status.",
            "To find specific bugs or vulnerabilities, use `get_issues` with filters for severity or type.",
            "If analyzing legacy code, prioritize 'blocker' and 'critical' issues first."
        ],
        "schemas": [
            {
                "name": "get_project_status",
                "description": "Get quality gate status",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project_key": {"type": "string"}},
                    "required": ["project_key"]
                }
            },
            {
                "name": "get_issues",
                "description": "Search for code issues",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project_key": {"type": "string"}, "severity": {"type": "string"}},
                    "required": ["project_key"]
                }
            }
        ]
    },
    "context7": {
        "prompts": [
            "Context7 provides library documentation. Use it when you need to understand how to use a specific package.",
            "First, use `resolve_library_id` to find the canonical ID for a library (e.g., 'react' -> '/npm/react').",
            "Once you have an ID, use `get_library_docs` to fetch the actual API reference or guide.",
            "Do NOT guess library IDs; always resolve them first."
        ],
        "schemas": [
            {
                "name": "resolve_library_id",
                "description": "Find library ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            },
            {
                "name": "get_library_docs",
                "description": "Get documentation",
                "inputSchema": {
                    "type": "object",
                    "properties": {"library_id": {"type": "string"}},
                    "required": ["library_id"]
                }
            }
        ]
    }
}

def get_device():
    """Check for MPS (Apple Silicon) or CUDA, else CPU."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"

def setup_chroma():
    """Setup ChromaDB client with sentence-transformers embedding function."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        
        device = get_device()
        logger.info(f"🚀 Using device: {device} for embeddings")
        
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device=device
        )
        
        persist_dir = get_default_chroma_persist_dir() / "mcp_integration"
        init_res = create_persistent_client(persist_dir=persist_dir, logger=logger)
        
        if not init_res:
            logger.error("❌ Failed to initialize ChromaDB client")
            return None, None
            
        client = init_res.client
        
        prompts_col = client.get_or_create_collection(
            name=PROMPTS_COLLECTION,
            embedding_function=ef,
            metadata={"description": "MCP System Prompts"}
        )
        
        schemas_col = client.get_or_create_collection(
            name=SCHEMAS_COLLECTION,
            embedding_function=ef,
            metadata={"description": "MCP Tool Schemas"}
        )
        
        return prompts_col, schemas_col
    
    except Exception as e:
        logger.error(f"❌ Chroma Setup Failed: {e}")
        return None, None

def ingest_samples(collection):
    """Ingest sample prompts for verification."""
    logger.info("🧪 Ingesting sample prompts...")
    documents = [
        "You are an expert at extracting patterns from text. Analyze the input and output a structured pattern description.",
        "You are a coding assistant optimized for Python. Always use type hints and docstrings.",
        "You are a database administrator. Analyze the logs for slow queries and suggest indexes."
    ]
    metadatas = [
        {"source": "sample", "pattern": "extract_pattern", "type": "system_prompt"},
        {"source": "sample", "pattern": "python_coder", "type": "system_prompt"},
        {"source": "sample", "pattern": "dba_expert", "type": "system_prompt"},
    ]
    ids = ["sample_1", "sample_2", "sample_3"]
    
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    logger.info(f"✅ Upserted {len(documents)} sample prompts")

def ingest_manual_server_data(prompts_col, schemas_col):
    """Ingest manually defined server data (Prompts + Schemas)."""
    logger.info("🛠 Ingesting manual server data...")
    
    for server, data in SERVER_DATA.items():
        # Ingest Prompts
        if "prompts" in data:
            docs = data["prompts"]
            metas = [{"source": f"mcp_server_{server}", "type": "expert_prompt", "server": server} for _ in docs]
            ids = [f"{server}_prompt_{i}" for i in range(len(docs))]
            prompts_col.upsert(documents=docs, metadatas=metas, ids=ids)
            logger.info(f"   - Ingested {len(docs)} prompts for {server}")

        # Ingest Schemas
        if "schemas" in data:
            schemas = data["schemas"]
            # Store schema as JSON string in document, or description as document and full schema in metadata
            # Strategy: Document = Description + Signature. Metadata = Full JSON.
            docs = []
            metas = []
            ids = []
            for i, tool in enumerate(schemas):
                sig = f"{tool['name']}({', '.join(tool['inputSchema'].get('properties', {}).keys())})"
                content = f"Tool: {tool['name']}\nDescription: {tool['description']}\nSignature: {sig}"
                docs.append(content)
                metas.append({
                    "source": f"mcp_server_{server}", 
                    "type": "tool_schema", 
                    "server": server,
                    "tool_name": tool['name'],
                    "full_schema": json.dumps(tool)
                })
                ids.append(f"{server}_schema_{tool['name']}")
            
            schemas_col.upsert(documents=docs, metadatas=metas, ids=ids)
            logger.info(f"   - Ingested {len(docs)} schemas for {server}")

def ingest_github_dir_prompts(source: Dict, collection):
    """Ingest prompts from a GitHub directory (recursive support)."""
    logger.info(f"📥 Ingesting from {source['name']} ({source['url']})...")
    
    def process_directory(url: str, depth=0):
        if depth > 3: return # Safety limit
        
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {resp.status_code}")
                return
                
            items = resp.json()
            if not isinstance(items, list): return

            documents = []
            metadatas = []
            ids = []

            for item in items:
                if item['type'] == 'dir' and source.get('recursive'):
                    # Recurse
                    process_directory(item['url'], depth + 1)
                
                elif item['type'] == 'file':
                    # Check if this is a target file
                    is_target = False
                    if 'target_file' in source and item['name'] == source['target_file']:
                        is_target = True
                    elif 'target_extension' in source and item['name'].endswith(source['target_extension']):
                        is_target = True
                        
                    if is_target:
                        # Construct raw URL
                        raw_url = item['download_url']
                        try:
                            p_resp = requests.get(raw_url)
                            if p_resp.status_code == 200:
                                content = p_resp.text
                                if len(content) > 50: # valid content check
                                    name = item['path'].replace('/', '_').replace('.', '_')
                                    score_val = 1.0 # Base score for high quality repos
                                    
                                    documents.append(content)
                                    metadatas.append({
                                        "source": source['name'], 
                                        "path": item['path'], 
                                        "type": "system_prompt",
                                        "reputation_score": score_val
                                    })
                                    ids.append(f"{source['name']}_{name}")
                                    logger.info(f"   - Loaded {item['path']}")
                        except Exception as ex:
                            logger.warning(f"   Skipped {item['name']}: {ex}")

            if documents:
                collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
                logger.info(f"✅ Upserted {len(documents)} prompts from {url}")

        except Exception as e:
            logger.error(f"Error processing dir {url}: {e}")

    # Start processing
    process_directory(source['url'])

def main():
    parser = argparse.ArgumentParser(description="Ingest MCP Data")
    parser.add_argument("--prompts", action="store_true", help="Ingest prompts")
    parser.add_argument("--schemas", action="store_true", help="Ingest schemas")
    args = parser.parse_args()
    
    prompts_col, schemas_col = setup_chroma()
    if not prompts_col:
        return

    # ALWAYS ingest manual data for verification/demo purposes
    ingest_manual_server_data(prompts_col, schemas_col)

    if args.prompts:
        # Try samples first to guarantee data
        ingest_samples(prompts_col)
        
        for source in PROMPT_SOURCES:
            if source['type'] == 'github_dir':
                ingest_github_dir_prompts(source, prompts_col)

if __name__ == "__main__":
    main()
