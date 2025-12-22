"""Memory Manager TUI

Provides TUI interface for managing all memory systems:
- View memory statistics
- Browse and manage learning history
- Import examples from GitHub
- Load data into RAG/ChromaDB vector databases
- Trigger GPU processing for embeddings
"""

import os
import json
import subprocess
import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime


def handle_memory_action(
    action: str,
    memory: Any,
    log: Optional[Callable[[str, str], None]] = None
) -> Dict[str, Any]:
    """
    Handle memory manager actions.
    
    Args:
        action: Action name (stats, learning_history, etc.)
        memory: HierarchicalMemory instance
        log: Optional log function
        
    Returns:
        Status dict with result/message
    """
    handlers = {
        "stats": _action_stats,
        "learning_history": _action_learning_history,
        "semantic": _action_semantic_browser,
        "episodic": _action_episodic_browser,
        "import": _action_import,
        "export": _action_export,
        "vector_db": _action_vector_db,
    }
    
    handler = handlers.get(action)
    if not handler:
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    try:
        return handler(memory, log)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _action_stats(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Show memory statistics."""
    try:
        stats = memory.get_stats()
        
        # Format stats for display
        lines = [
            "═══ Memory Statistics ═══",
            "",
            f"Session: {stats.get('session_id', 'N/A')}",
            "",
            "Working Memory:",
            f"  Active items: {stats.get('working_memory', {}).get('active_items', 0)}",
            f"  Expired items: {stats.get('working_memory', {}).get('expired_items', 0)}",
            "",
            "Episodic Memory:",
            f"  Total items: {stats.get('episodic_memory', {}).get('total_items', 0)}",
            "",
            "Semantic Memory:",
            f"  Total items: {stats.get('semantic_memory', {}).get('total_items', 0)}",
            "",
            "Legacy Collections:",
        ]
        
        legacy = stats.get("legacy_collections", {})
        for name, count in legacy.items():
            lines.append(f"  {name}: {count}")
        
        # Add learning memory stats
        try:
            from core.learning_memory import get_learning_memory
            learn_stats = get_learning_memory().get_stats()
            lines.extend([
                "",
                "Learning Memory:",
                f"  Total entries: {learn_stats.get('total_entries', 0)}",
                f"  Consolidated: {learn_stats.get('consolidated', 0)}",
                f"  Pending: {learn_stats.get('pending', 0)}",
            ])
        except ImportError:
            pass
        
        message = "\n".join(lines)
        
        if log:
            log(message, "info")
        
        return {"status": "success", "message": message, "stats": stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _action_learning_history(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Show learning history."""
    try:
        from core.learning_memory import get_learning_memory
        
        learn_mem = get_learning_memory()
        history = learn_mem.get_learning_history(limit=20)
        
        if not history:
            message = "No learning history found. Enable learning mode and complete tasks to record entries."
            if log:
                log(message, "info")
            return {"status": "success", "message": message, "entries": []}
        
        lines = [
            "═══ Learning History ═══",
            "",
        ]
        
        for entry in history:
            timestamp = entry.get("timestamp", "")[:19].replace("T", " ")
            task = entry.get("task", "")[:50] + ("..." if len(entry.get("task", "")) > 50 else "")
            outcome = entry.get("outcome", "")
            consolidated = "✓" if entry.get("consolidated") else " "
            
            lines.append(f"[{consolidated}] {timestamp} | {outcome}")
            lines.append(f"    {task}")
            lines.append(f"    Tools: {', '.join(entry.get('tools_used', [])[:3])}")
            lines.append("")
        
        message = "\n".join(lines)
        
        if log:
            log(message, "info")
        
        return {"status": "success", "message": message, "entries": history}
    except ImportError:
        return {"status": "error", "error": "Learning memory module not available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _action_semantic_browser(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Browse semantic memory."""
    try:
        # Query semantic memory for recent entries
        results = memory.query_semantic_memory(
            query="recent patterns",
            n_results=20
        )
        
        if not results:
            message = "Semantic memory is empty."
            if log:
                log(message, "info")
            return {"status": "success", "message": message, "entries": []}
        
        lines = [
            "═══ Semantic Memory ═══",
            f"Total entries found: {len(results)}",
            "",
        ]
        
        for i, entry in enumerate(results, 1):
            content = entry.get("content", "")[:80] + ("..." if len(entry.get("content", "")) > 80 else "")
            meta = entry.get("metadata", {})
            ktype = meta.get("knowledge_type", "unknown")
            confidence = meta.get("confidence", 0)
            
            lines.append(f"{i}. [{ktype}] (conf: {confidence:.2f})")
            lines.append(f"   {content}")
            lines.append("")
        
        message = "\n".join(lines)
        
        if log:
            log(message, "info")
        
        return {"status": "success", "message": message, "entries": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _action_episodic_browser(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Browse episodic memory."""
    try:
        # Query episodic memory for recent entries
        results = memory.query_episodic_memory(
            query="recent actions",
            n_results=20,
            session_only=False
        )
        
        if not results:
            message = "Episodic memory is empty."
            if log:
                log(message, "info")
            return {"status": "success", "message": message, "entries": []}
        
        lines = [
            "═══ Episodic Memory ═══",
            f"Total entries found: {len(results)}",
            "",
        ]
        
        for i, entry in enumerate(results, 1):
            content = entry.get("content", "")[:80] + ("..." if len(entry.get("content", "")) > 80 else "")
            meta = entry.get("metadata", {})
            action_type = meta.get("action_type", "unknown")
            outcome = meta.get("outcome", "unknown")
            timestamp = meta.get("timestamp", "")[:19]
            
            lines.append(f"{i}. [{action_type}] {outcome} | {timestamp}")
            lines.append(f"   {content}")
            lines.append("")
        
        message = "\n".join(lines)
        
        if log:
            log(message, "info")
        
        return {"status": "success", "message": message, "entries": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _action_import(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Show import options."""
    lines = [
        "═══ Import Options ═══",
        "",
        "Available import sources:",
        "",
        "1. Import from GitHub:",
        "   /memory import github <repo_url>",
        "",
        "2. Import JSON examples:",
        "   /memory import json <file_path>",
        "",
        "3. Import learning data:",
        "   /memory import learning <file_path>",
        "",
        "4. Load schema examples:",
        "   /memory load-schema <collection> <json_path>",
        "",
        "Example commands:",
        "   /memory import github https://github.com/user/patterns",
        "   /memory import json ./examples/patterns.json",
    ]
    
    message = "\n".join(lines)
    
    if log:
        log(message, "info")
    
    return {"status": "success", "message": message}


def _action_export(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Show export options and perform default export."""
    try:
        from core.learning_memory import get_learning_memory
        
        export_dir = Path.cwd() / "exports"
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export learning data
        learn_path = export_dir / f"learning_export_{timestamp}.json"
        learn_result = get_learning_memory().export_learning_data(str(learn_path))
        
        lines = [
            "═══ Export Data ═══",
            "",
            "Export completed:",
            f"  Learning data: {learn_path}",
            f"    Entries: {learn_result.get('entries_exported', 0)}",
            "",
            "For more export options, use:",
            "   /memory export learning <path>",
            "   /memory export semantic <path>",
            "   /memory export all <directory>",
        ]
        
        message = "\n".join(lines)
        
        if log:
            log(message, "info")
        
        return {"status": "success", "message": message, "exported_to": str(learn_path)}
    except ImportError:
        lines = [
            "═══ Export Data ═══",
            "",
            "Learning memory module not available.",
            "",
            "For export options, use:",
            "   /memory export semantic <path>",
            "   /memory export episodic <path>",
        ]
        message = "\n".join(lines)
        if log:
            log(message, "info")
        return {"status": "success", "message": message}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _action_vector_db(memory: Any, log: Optional[Callable] = None) -> Dict[str, Any]:
    """Show vector DB management options."""
    try:
        # Get collection stats
        stats = memory.get_stats()
        
        lines = [
            "═══ Vector DB Management ═══",
            "",
            "ChromaDB Collections:",
        ]
        
        # Show legacy collections
        legacy = stats.get("legacy_collections", {})
        for name, count in legacy.items():
            lines.append(f"  • {name}: {count} entries")
        
        # Episodic and Semantic
        lines.append(f"  • episodic_memory: {stats.get('episodic_memory', {}).get('total_items', 0)} entries")
        lines.append(f"  • semantic_memory: {stats.get('semantic_memory', {}).get('total_items', 0)} entries")
        
        lines.extend([
            "",
            "Management commands:",
            "   /memory clear <collection>",
            "   /memory reindex <collection>",
            "   /memory vacuum",
            "",
            "GPU Processing:",
            "   /memory gpu-embed <collection>",
            "   /memory gpu-status",
        ])
        
        message = "\n".join(lines)
        
        if log:
            log(message, "info")
        
        return {"status": "success", "message": message, "stats": stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============ Import Functions ============

def import_from_github(
    repo_url: str,
    branch: str = "main",
    patterns_dir: str = "patterns"
) -> Dict[str, Any]:
    """
    Import example patterns from GitHub repository.
    
    Args:
        repo_url: GitHub repository URL
        branch: Branch name
        patterns_dir: Directory containing pattern files
        
    Returns:
        Status dict
    """
    try:
        import tempfile
        import shutil
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Clone repository (shallow)
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, repo_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {"status": "error", "error": f"Git clone failed: {result.stderr}"}
            
            # Find pattern files
            patterns_path = Path(tmpdir) / patterns_dir
            if not patterns_path.exists():
                patterns_path = Path(tmpdir)  # Use root if patterns_dir not found
            
            json_files = list(patterns_path.glob("**/*.json"))
            
            imported = 0
            from core.memory import get_hierarchical_memory
            mem = get_hierarchical_memory()
            
            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Handle different formats
                    if isinstance(data, list):
                        for item in data:
                            _import_pattern_item(mem, item)
                            imported += 1
                    elif isinstance(data, dict):
                        _import_pattern_item(mem, data)
                        imported += 1
                except Exception:
                    continue
            
            return {
                "status": "success",
                "imported": imported,
                "source": repo_url,
                "message": f"Imported {imported} patterns from {repo_url}"
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _import_pattern_item(memory: Any, item: Dict[str, Any]) -> None:
    """Import a single pattern item into memory."""
    content = item.get("content") or item.get("pattern") or item.get("text") or json.dumps(item)
    knowledge_type = item.get("type") or item.get("knowledge_type") or "pattern"
    confidence = float(item.get("confidence", 0.7))
    
    memory.add_semantic_memory(
        content=content,
        knowledge_type=knowledge_type,
        confidence=confidence,
        source="github_import",
        metadata=item.get("metadata", {})
    )


def import_json_to_vector_db(
    json_path: str,
    collection: str = "knowledge_base"
) -> Dict[str, Any]:
    """
    Load JSON data into ChromaDB vector database.
    
    Args:
        json_path: Path to JSON file
        collection: Target collection name
        
    Returns:
        Status dict
    """
    try:
        path = Path(json_path).expanduser().resolve()
        
        if not path.exists():
            return {"status": "error", "error": f"File not found: {path}"}
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        from core.memory import get_memory
        mem = get_memory()
        
        imported = 0
        
        if isinstance(data, list):
            for item in data:
                content = item.get("content") or item.get("text") or json.dumps(item)
                metadata = {k: v for k, v in item.items() if k != "content" and isinstance(v, (str, int, float, bool))}
                mem.add_memory(collection, content, metadata)
                imported += 1
        elif isinstance(data, dict):
            if "entries" in data:
                for item in data["entries"]:
                    content = item.get("content") or item.get("text") or json.dumps(item)
                    metadata = {k: v for k, v in item.items() if k != "content" and isinstance(v, (str, int, float, bool))}
                    mem.add_memory(collection, content, metadata)
                    imported += 1
            else:
                content = json.dumps(data)
                mem.add_memory(collection, content, {})
                imported += 1
        
        return {
            "status": "success",
            "imported": imported,
            "collection": collection,
            "source": str(path),
            "message": f"Loaded {imported} entries into {collection}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============ Chat Command Handler ============

def handle_memory_chat_command(args: List[str]) -> Dict[str, Any]:
    """
    Handle /memory chat commands.
    
    Args:
        args: Command arguments
        
    Returns:
        Status dict
    """
    if not args:
        return _show_memory_help()
    
    cmd = args[0].lower()
    
    if cmd == "stats":
        from core.memory import get_hierarchical_memory
        return _action_stats(get_hierarchical_memory())
    
    elif cmd == "history":
        from core.memory import get_hierarchical_memory
        return _action_learning_history(get_hierarchical_memory())
    
    elif cmd == "import":
        if len(args) < 3:
            return {"status": "error", "error": "Usage: /memory import <type> <source>"}
        import_type = args[1].lower()
        source = args[2]
        
        if import_type == "github":
            return import_from_github(source)
        elif import_type == "json":
            collection = args[3] if len(args) > 3 else "knowledge_base"
            return import_json_to_vector_db(source, collection)
        elif import_type == "learning":
            from core.learning_memory import get_learning_memory
            return get_learning_memory().import_learning_data(source)
        else:
            return {"status": "error", "error": f"Unknown import type: {import_type}"}
    
    elif cmd == "export":
        if len(args) < 2:
            from core.memory import get_hierarchical_memory
            return _action_export(get_hierarchical_memory())
        export_type = args[1].lower()
        path = args[2] if len(args) > 2 else None
        
        if export_type == "learning":
            from core.learning_memory import get_learning_memory
            if path:
                return get_learning_memory().export_learning_data(path)
            else:
                return {"status": "error", "error": "Usage: /memory export learning <path>"}
        else:
            return {"status": "error", "error": f"Unknown export type: {export_type}"}
    
    elif cmd == "clear":
        if len(args) < 2:
            return {"status": "error", "error": "Usage: /memory clear <target>"}
        target = args[1].lower()
        from core.memory import get_hierarchical_memory
        return clear_memory_layer(get_hierarchical_memory(), target)
    
    elif cmd == "consolidate":
        if len(args) < 2:
            return {"status": "error", "error": "Usage: /memory consolidate <entry_id>"}
        entry_id = args[1]
        from core.learning_memory import get_learning_memory
        return get_learning_memory().consolidate_to_semantic(entry_id)
    
    elif cmd == "help":
        return _show_memory_help()
    
    else:
        return {"status": "error", "error": f"Unknown command: {cmd}\nRun /memory help for options."}


def clear_memory_layer(memory: Any, target: str) -> Dict[str, Any]:
    """Clear a specific memory layer."""
    try:
        if target == "working":
            memory.clear_working_memory()
            return {"status": "success", "message": "Working memory cleared"}
        elif target == "episodic":
            result = memory.clear_episodic_memory()
            return {"status": "success", "message": "Episodic memory cleared", "result": result}
        elif target == "learning":
            from core.learning_memory import get_learning_memory
            result = get_learning_memory().clear_all()
            return {"status": "success", "message": "Learning memory cleared", "result": result}
        else:
            return {"status": "error", "error": f"Unknown target: {target}. Use: working, episodic, learning"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _show_memory_help() -> Dict[str, Any]:
    """Show memory command help."""
    help_text = """
═══ Memory Manager Commands ═══

/memory stats          - Show memory statistics
/memory history        - Show learning history

Import:
  /memory import github <url>     - Import from GitHub repo
  /memory import json <path>      - Import JSON to vector DB
  /memory import learning <path>  - Import learning data

Export:
  /memory export                  - Quick export all
  /memory export learning <path>  - Export learning data

Management:
  /memory clear <target>          - Clear memory (working/episodic/learning)
  /memory consolidate <id>        - Consolidate learning entry

/memory help           - Show this help
"""
    return {"status": "success", "message": help_text.strip()}
