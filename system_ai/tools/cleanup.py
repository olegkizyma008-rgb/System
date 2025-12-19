
import os
import subprocess
from typing import Any, Dict

def _get_script_path(script_name: str) -> str:
    # Assume cleanup_scripts is in the project root
    # We can find it relative to this file: system_ai/tools/cleanup.py -> ../../cleanup_scripts
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "cleanup_scripts", script_name)

def _run_cleanup_script(script_name: str, allow: bool = True) -> Dict[str, Any]:
    if not allow:
        return {"tool": script_name, "status": "error", "error": "Confirmation required"}
    
    script_path = _get_script_path(script_name)
    if not os.path.exists(script_path):
        return {"tool": script_name, "status": "error", "error": f"Script not found: {script_path}"}
    
    try:
        # Make executable if needed
        subprocess.run(["chmod", "+x", script_path], check=False)
        
        proc = subprocess.run(
            [script_path],
            capture_output=True,
            text=True
        )
        
        return {
            "tool": script_name,
            "status": "success" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "").strip()[-5000:],
            "stderr": (proc.stderr or "").strip()[-5000:]
        }
    except Exception as e:
        return {"tool": script_name, "status": "error", "error": str(e)}

def system_cleanup_stealth(allow: bool = True) -> Dict[str, Any]:
    """Run stealth cleanup (logs, caches)."""
    return _run_cleanup_script("stealth_cleanup.sh", allow=allow)

def system_cleanup_windsurf(allow: bool = True) -> Dict[str, Any]:
    """Run deep Windsurf cleanup (removes traces)."""
    return _run_cleanup_script("deep_windsurf_cleanup.sh", allow=allow)

def system_spoof_hardware(allow: bool = True) -> Dict[str, Any]:
    """Run hardware spoofing (MAC address, hostname). WARNING: May disconnect network."""
    return _run_cleanup_script("hardware_spoof.sh", allow=allow)

def system_check_identifiers() -> Dict[str, Any]:
    """Check current system identifiers."""
    return _run_cleanup_script("check_identifier_cleanup.sh", allow=True)
