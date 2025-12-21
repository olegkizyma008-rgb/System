#!/usr/bin/env python3
"""
Comprehensive MCP Server Registration System
Registers all MCP servers, downloads tool schemas, and vectorizes them.
"""

import json
import os
import sys
import subprocess
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
import redis

from mcp_integration.chroma_utils import create_persistent_client, get_default_chroma_persist_dir

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_registration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ServerRegistry:
    """Registry for all MCP servers"""
    
    def __init__(self, config_path: str = "config/mcp_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.registered_servers = {}
        self.tool_schemas = {}
        
        # Vector storage
        self.chroma_client = None
        self.collection = None
        
        # Redis connection
        self.redis_client = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration"""
        try:
            config_file = Path(__file__).parent / self.config_path
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"✅ Loaded config from {config_file}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return {"mcpServers": {}}
    
    def initialize_storage(self):
        """Initialize ChromaDB and Redis"""
        try:
            # Initialize ChromaDB with persistent storage
            persist_directory = get_default_chroma_persist_dir() / "mcp_integration"
            
            # Use PersistentClient for data persistence (repair+retry once on Rust panic)
            init_res = create_persistent_client(persist_dir=persist_directory, logger=logger)
            if init_res is None:
                raise RuntimeError("ChromaDB persistence unavailable")
            self.chroma_client = init_res.client
            
            # Delete existing collection to start fresh
            try:
                self.chroma_client.delete_collection("mcp_tool_schemas")
                logger.info("🗑️  Deleted existing ChromaDB collection")
            except:
                pass
            
            # Create new collection
            self.collection = self.chroma_client.create_collection(
                name="mcp_tool_schemas",
                metadata={"description": "MCP tool schemas and examples"}
            )
            logger.info("📊 Created new ChromaDB collection")
            
            # Initialize Redis connection
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("✅ Connected to Redis")
            except Exception as e:
                logger.warning(f"⚠️  Redis not available: {e}")
                self.redis_client = None
                
        except Exception as e:
            logger.error(f"❌ Storage initialization error: {e}")
            raise
    
    def register_server(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Register a single MCP server"""
        try:
            logger.info(f"🔧 Registering server: {server_name}")
            
            # Store server configuration
            self.registered_servers[server_name] = {
                "name": server_name,
                "config": server_config,
                "status": "registered",
                "tools": []
            }
            
            # Cache in Redis if available
            if self.redis_client:
                self.redis_client.hset(
                    f"mcp:server:{server_name}",
                    mapping={
                        "config": json.dumps(server_config),
                        "status": "registered"
                    }
                )
            
            logger.info(f"✅ Server registered: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register {server_name}: {e}")
            return False
    
    def discover_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools for a specific server"""
        try:
            logger.info(f"🔍 Discovering tools for: {server_name}")
            
            server_config = self.config.get('mcpServers', {}).get(server_name, {})
            server_category = server_config.get('category', 'general')
            
            # Load tool examples from existing JSON files
            tools = []
            tool_examples_dir = Path(__file__).parent / "core" / "tool_examples"
            
            # Mapping of server names to categories
            server_to_categories = {
                "context7": ["ai", "system"],
                "playwright": ["browser"],
                "pyautogui": ["gui"],
                "applescript": ["system"],
                "anthropic": ["ai"],
                "filesystem": ["filesystem"],
                "sonarqube": ["code_analysis"],
                "local_fallback": ["system", "gui", "browser"]
            }
            
            categories = server_to_categories.get(server_name, [server_category])
            
            # Try to load combined dataset first
            combined_file = tool_examples_dir / "all_examples_combined.json"
            if combined_file.exists():
                with open(combined_file, 'r') as f:
                    all_examples = json.load(f)
                    # Filter by server or category
                    tools = [ex for ex in all_examples 
                            if ex.get('server') == server_name or ex.get('category') in categories]
            else:
                # Fallback to individual files
                for category in categories:
                    file_path = tool_examples_dir / f"{category}_examples.json"
                    if file_path.exists():
                        with open(file_path, 'r') as f:
                            try:
                                examples = json.load(f)
                                if isinstance(examples, dict):
                                    examples = examples.get('examples', [])
                                tools.extend(examples)
                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️  Error parsing {category}_examples.json: {e}")
            
            logger.info(f"✅ Discovered {len(tools)} tools for {server_name}")
            return tools
            
        except Exception as e:
            logger.error(f"❌ Tool discovery failed for {server_name}: {e}")
            return []
    
    def download_schemas(self, server_name: str) -> Dict[str, Any]:
        """Download tool schemas for a server"""
        try:
            logger.info(f"📥 Downloading schemas for: {server_name}")
            
            # Get tools for this server
            tools = self.discover_tools(server_name)
            
            # Create schema structure
            schema = {
                "server": server_name,
                "version": "1.0.0",
                "tools": tools,
                "metadata": {
                    "total_tools": len(tools),
                    "categories": list(set(t.get('category', 'general') for t in tools))
                }
            }
            
            # Store schema
            self.tool_schemas[server_name] = schema
            
            # Save to file
            schema_dir = Path(__file__).parent / "data" / "schemas"
            schema_dir.mkdir(parents=True, exist_ok=True)
            
            schema_file = schema_dir / f"{server_name}_schema.json"
            with open(schema_file, 'w') as f:
                json.dump(schema, f, indent=2)
            
            logger.info(f"✅ Downloaded schema: {len(tools)} tools")
            return schema
            
        except Exception as e:
            logger.error(f"❌ Schema download failed for {server_name}: {e}")
            return {}
    
    def vectorize_schemas(self, server_name: str, schema: Dict[str, Any]):
        """Vectorize tool schemas and store in ChromaDB"""
        try:
            logger.info(f"🧮 Vectorizing schemas for: {server_name}")
            
            tools = schema.get('tools', [])
            if not tools:
                logger.warning(f"⚠️  No tools to vectorize for {server_name}")
                return
            
            # Prepare documents for vectorization
            documents = []
            metadatas = []
            ids = []
            
            for idx, tool in enumerate(tools):
                # Create rich document text for better embeddings
                doc_text = f"{tool.get('tool', 'unknown')}: {tool.get('description', '')}"
                if 'example' in tool:
                    doc_text += f"\nExample: {tool['example']}"
                
                documents.append(doc_text)
                metadatas.append({
                    "server": server_name,
                    "tool": tool.get('tool', 'unknown'),
                    "category": tool.get('category', 'general'),
                    "full_schema": json.dumps(tool)
                })
                ids.append(f"{server_name}_{idx}")
            
            # Add to ChromaDB collection in batches (max 5000 per batch)
            BATCH_SIZE = 5000
            if documents:
                for i in range(0, len(documents), BATCH_SIZE):
                    batch_docs = documents[i:i + BATCH_SIZE]
                    batch_metas = metadatas[i:i + BATCH_SIZE]
                    batch_ids = ids[i:i + BATCH_SIZE]
                    
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    logger.info(f"  📦 Added batch {i//BATCH_SIZE + 1}: {len(batch_docs)} items")
                    
                logger.info(f"✅ Vectorized {len(documents)} tool schemas")
            
            # Store in Redis for quick access
            if self.redis_client:
                for tool in tools:
                    tool_key = f"mcp:tool:{server_name}:{tool.get('tool', 'unknown')}"
                    self.redis_client.hset(
                        tool_key,
                        mapping={
                            "schema": json.dumps(tool),
                            "server": server_name,
                            "category": tool.get('category', 'general')
                        }
                    )
                logger.info(f"✅ Cached {len(tools)} tools in Redis")
                
        except Exception as e:
            logger.error(f"❌ Vectorization failed for {server_name}: {e}")
    
    def query_tools(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Query vectorized tools using semantic search"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            return [
                {
                    "tool": meta.get("tool"),
                    "server": meta.get("server"),
                    "category": meta.get("category"),
                    "description": doc,
                    "full_schema": json.loads(meta.get("full_schema", "{}"))
                }
                for doc, meta in zip(results['documents'][0], results['metadatas'][0])
            ]
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return []
    
    def register_all_servers(self):
        """Register all configured MCP servers"""
        logger.info("🚀 Starting server registration process...")
        
        # Initialize storage
        self.initialize_storage()
        
        servers = self.config.get('mcpServers', {})
        total = len(servers)
        
        logger.info(f"📋 Found {total} servers to register")
        
        for idx, (server_name, server_config) in enumerate(servers.items(), 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {idx}/{total}: {server_name}")
            logger.info(f"{'='*60}")
            
            # Register server
            if self.register_server(server_name, server_config):
                
                # Download schemas
                schema = self.download_schemas(server_name)
                
                # Vectorize schemas
                if schema:
                    self.vectorize_schemas(server_name, schema)
        
        # Generate summary report
        self.generate_report()
        
        logger.info("\n✅ All servers registered and vectorized!")
    
    def generate_report(self):
        """Generate registration report"""
        try:
            report = {
                "total_servers": len(self.registered_servers),
                "servers": list(self.registered_servers.keys()),
                "total_tools": sum(
                    len(schema.get('tools', [])) 
                    for schema in self.tool_schemas.values()
                ),
                "schemas_by_server": {
                    name: {
                        "tools_count": len(schema.get('tools', [])),
                        "categories": schema.get('metadata', {}).get('categories', [])
                    }
                    for name, schema in self.tool_schemas.items()
                },
                "storage": {
                    "chromadb": "enabled" if self.collection else "disabled",
                    "redis": "enabled" if self.redis_client else "disabled"
                }
            }
            
            # Save report
            report_file = Path(__file__).parent / "data" / "registration_report.json"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Print summary
            logger.info("\n" + "="*60)
            logger.info("REGISTRATION SUMMARY")
            logger.info("="*60)
            logger.info(f"Total Servers: {report['total_servers']}")
            logger.info(f"Total Tools: {report['total_tools']}")
            logger.info(f"ChromaDB: {report['storage']['chromadb']}")
            logger.info(f"Redis: {report['storage']['redis']}")
            logger.info("\nServers:")
            for server in report['servers']:
                info = report['schemas_by_server'].get(server, {})
                logger.info(f"  - {server}: {info.get('tools_count', 0)} tools")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")


def main():
    """Main entry point"""
    try:
        # Start Redis if not running
        logger.info("🔧 Checking Redis status...")
        try:
            subprocess.run(['redis-server', '--daemonize', 'yes'], 
                         capture_output=True, timeout=5)
            logger.info("✅ Redis server started")
        except:
            logger.warning("⚠️  Could not start Redis, will continue without it")
        
        # Create registry and register all servers
        registry = ServerRegistry()
        registry.register_all_servers()
        
        # Test query
        logger.info("\n🔍 Testing semantic search...")
        results = registry.query_tools("browser automation and navigation", n_results=3)
        logger.info(f"Found {len(results)} relevant tools:")
        for r in results:
            logger.info(f"  - {r['server']}.{r['tool']}: {r.get('category', 'N/A')}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Registration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
