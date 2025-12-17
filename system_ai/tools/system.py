"""System Tools Module

Provides tools for system process management and monitoring using psutil.
"""

import psutil
import time
from typing import Dict, Any, List, Optional

def list_processes(limit: int = 50, sort_by: str = "cpu") -> List[Dict[str, Any]]:
    """List running processes
    
    Args:
        limit: Max number of processes to return
        sort_by: Sort key ("cpu", "memory", "name")
        
    Returns:
        List of process dictionaries
    """
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort
    if sort_by == "cpu":
        procs.sort(key=lambda x: float(x.get('cpu_percent') or 0.0), reverse=True)
    elif sort_by == "memory":
        procs.sort(key=lambda x: float(x.get('memory_percent') or 0.0), reverse=True)
    elif sort_by == "name":
        procs.sort(key=lambda x: str(x.get('name', '')).lower())

    return procs[:limit]

def kill_process(pid: int) -> Dict[str, Any]:
    """Terminate a process by PID
    
    Args:
        pid: Process ID
        
    Returns:
        Dict with status
    """
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            p.kill()
            
        return {
            "tool": "kill_process",
            "status": "success",
            "message": f"Process {name} ({pid}) terminated"
        }
    except psutil.NoSuchProcess:
        return {
            "tool": "kill_process",
            "status": "error",
            "error": f"Process {pid} not found"
        }
    except psutil.AccessDenied:
        return {
            "tool": "kill_process",
            "status": "error",
            "error": f"Access denied to process {pid}"
        }
    except Exception as e:
        return {
            "tool": "kill_process",
            "status": "error",
            "error": str(e)
        }

def get_system_stats() -> Dict[str, Any]:
    """Get global system statistics
    
    Returns:
        Dict with CPU, memory, and disk info
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "tool": "get_system_stats",
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": mem.percent,
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "memory_available_gb": round(mem.available / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2)
    }
