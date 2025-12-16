import os
import shutil
from typing import Any, Dict, Optional, List

def read_file(path: str) -> Dict[str, Any]:
    """Reads the content of a file."""
    try:
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        
        if not os.path.exists(path):
            return {"tool": "read_file", "status": "error", "error": f"File not found: {path}"}
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {
            "tool": "read_file", 
            "status": "success", 
            "path": path, 
            "content": content
        }
    except Exception as e:
        return {"tool": "read_file", "status": "error", "path": path, "error": str(e)}

def write_file(path: str, content: str, mode: str = "w") -> Dict[str, Any]:
    """Writes content to a file. Mode can be 'w' (overwrite) or 'a' (append)."""
    try:
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
            
        return {
            "tool": "write_file", 
            "status": "success", 
            "path": path, 
            "mode": mode,
            "bytes_written": len(content)
        }
    except Exception as e:
        return {"tool": "write_file", "status": "error", "path": path, "error": str(e)}

def list_files(path: str) -> Dict[str, Any]:
    """Lists files in a directory."""
    try:
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
        if not os.path.exists(path):
             return {"tool": "list_files", "status": "error", "error": f"Path not found: {path}"}
             
        items = os.listdir(path)
        details = []
        for item in items[:50]: # Limit for safety
            full = os.path.join(path, item)
            is_dir = os.path.isdir(full)
            details.append({"name": item, "is_dir": is_dir})
            
        return {
            "tool": "list_files", 
            "status": "success", 
            "path": path, 
            "items": details,
            "total_count": len(items)
        }
    except Exception as e:
        return {"tool": "list_files", "status": "error", "path": path, "error": str(e)}


def copy_file(src: str, dst: str, overwrite: bool = True) -> Dict[str, Any]:
    """Copy a file from src to dst (binary-safe)."""
    try:
        src_p = os.path.abspath(os.path.expanduser(str(src or "").strip()))
        dst_p = os.path.abspath(os.path.expanduser(str(dst or "").strip()))
        if not src_p or not dst_p:
            return {"tool": "copy_file", "status": "error", "error": "Missing src or dst"}
        if not os.path.exists(src_p):
            return {"tool": "copy_file", "status": "error", "error": f"Source not found: {src_p}", "src": src_p, "dst": dst_p}
        if os.path.isdir(src_p):
            return {"tool": "copy_file", "status": "error", "error": "Source is a directory", "src": src_p, "dst": dst_p}
        if (not overwrite) and os.path.exists(dst_p):
            return {"tool": "copy_file", "status": "error", "error": f"Destination exists: {dst_p}", "src": src_p, "dst": dst_p}

        dst_dir = os.path.dirname(dst_p)
        if dst_dir and not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)

        shutil.copy2(src_p, dst_p)
        try:
            size = os.path.getsize(dst_p)
        except Exception:
            size = None

        return {
            "tool": "copy_file",
            "status": "success",
            "src": src_p,
            "dst": dst_p,
            "bytes_copied": size,
        }
    except Exception as e:
        return {"tool": "copy_file", "status": "error", "src": str(src or ""), "dst": str(dst or ""), "error": str(e)}
