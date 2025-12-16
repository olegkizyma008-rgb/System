import json
import logging
import os
import shutil
import subprocess
import urllib.parse
from typing import Dict, Any

from system_ai.tools.executor import run_applescript

logger = logging.getLogger(__name__)


def is_windsurf_running() -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            ["pgrep", "-x", "Windsurf"],
            capture_output=True,
            text=True,
        )
        running = proc.returncode == 0 and bool((proc.stdout or "").strip())
        return {"tool": "is_windsurf_running", "status": "success", "running": running}
    except Exception as e:
        return {"tool": "is_windsurf_running", "status": "error", "error": str(e)}


def _file_uri_to_path(uri: str) -> str:
    u = str(uri or "").strip()
    if not u:
        return ""
    if u.startswith("file://"):
        parsed = urllib.parse.urlparse(u)
        return urllib.parse.unquote(parsed.path)
    return u


def get_windsurf_current_project_path() -> Dict[str, Any]:
    storage_path = os.path.expanduser("~/Library/Application Support/Windsurf/User/globalStorage/storage.json")
    running_res = is_windsurf_running()
    running = bool(running_res.get("running"))

    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {
            "tool": "get_windsurf_current_project_path",
            "status": "error",
            "running": running,
            "error": f"Storage file not found: {storage_path}",
        }
    except Exception as e:
        return {
            "tool": "get_windsurf_current_project_path",
            "status": "error",
            "running": running,
            "error": str(e),
        }

    folder_uri = ""
    try:
        windows_state = data.get("windowsState") or {}
        last_active = windows_state.get("lastActiveWindow") or {}
        folder_uri = str(last_active.get("folder") or last_active.get("workspace") or "").strip()
    except Exception:
        folder_uri = ""

    if not folder_uri:
        try:
            bw = data.get("backupWorkspaces") or {}
            folders = bw.get("folders") or []
            if isinstance(folders, list) and folders:
                folder_uri = str((folders[0] or {}).get("folderUri") or "").strip()
        except Exception:
            folder_uri = ""

    path = _file_uri_to_path(folder_uri)
    if path:
        return {
            "tool": "get_windsurf_current_project_path",
            "status": "success",
            "running": running,
            "path": path,
            "uri": folder_uri,
        }

    return {
        "tool": "get_windsurf_current_project_path",
        "status": "error",
        "running": running,
        "error": "Could not determine current project path",
    }


def open_project_in_windsurf(path: str, new_window: bool = True) -> Dict[str, Any]:
    p = str(path or "").strip()
    if not p:
        return {"tool": "open_project_in_windsurf", "status": "error", "error": "Missing path"}

    p = os.path.abspath(os.path.expanduser(p))
    tool_path = shutil.which("windsurf")

    try:
        if tool_path:
            cmd = [tool_path]
            if new_window:
                cmd.append("--new-window")
            cmd.append(p)

            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return {
                    "tool": "open_project_in_windsurf",
                    "status": "error",
                    "error": (proc.stderr or "").strip() or "Failed to open project in Windsurf",
                    "path": p,
                }
            return {
                "tool": "open_project_in_windsurf",
                "status": "success",
                "path": p,
                "new_window": bool(new_window),
            }

        proc = subprocess.run(["open", "-a", "Windsurf", p], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                "tool": "open_project_in_windsurf",
                "status": "error",
                "error": (proc.stderr or "").strip() or "Failed to open project in Windsurf",
                "path": p,
            }
        return {
            "tool": "open_project_in_windsurf",
            "status": "success",
            "path": p,
            "new_window": bool(new_window),
        }
    except Exception as e:
        return {"tool": "open_project_in_windsurf", "status": "error", "error": str(e), "path": p}

def send_to_windsurf(message: str) -> Dict[str, Any]:
    """
    Focuses Windsurf and types the message into the active window/chat.
    Uses AppleScript to simulate keystrokes.
    WARNING: Requires Accessibility permissions.
    """
    # AppleScript to focus Windsurf and paste content
    # We use clipboard to avoid slow typing of long messages
    script = f"""
    set msg to {repr(message)}
    tell application "System Events"
        set frontmost of application process "Windsurf" to true
        delay 0.5
        keystroke "l" using {{command down}} -- Focus chat/composer usually Cmd+L
        delay 0.2
        set the clipboard to msg
        delay 0.1
        keystroke "v" using {{command down}} -- Paste
        delay 0.5
        keystroke return -- Send
    end tell
    """
    
    # We sanitize the script execution
    try:
        result = run_applescript(script, allow=True)
        if result.get("status") == "success":
             return {"tool": "send_to_windsurf", "status": "success", "message_sent": True}
        return {"tool": "send_to_windsurf", "status": "error", "error": result.get("error")}
    except Exception as e:
        return {"tool": "send_to_windsurf", "status": "error", "error": str(e)}

def open_file_in_windsurf(path: str, line: int = 0) -> Dict[str, Any]:
    """Opens a specific file in Windsurf via 'code' CLI alias or 'open' command."""
    import subprocess
    import shutil
    
    # Try using 'windsurf' command if in path, or just 'open -a Windsurf'
    tool_path = shutil.which("windsurf")
    
    try:
        if tool_path:
            cmd = [tool_path, path]
            if line > 0:
                cmd.extend(["--goto", f"{path}:{line}"])
            subprocess.run(cmd, check=True)
        else:
            # Fallback to generic open
            subprocess.run(["open", "-a", "Windsurf", path], check=True)
            
        return {"tool": "open_file_in_windsurf", "status": "success", "path": path}
    except Exception as e:
         return {"tool": "open_file_in_windsurf", "status": "error", "error": str(e)}
