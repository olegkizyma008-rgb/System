"""Agent tool handlers for TUI.

Provides all _tool_* handler functions for agent tools:
- File operations (list_dir, read_file, grep)
- Desktop organization
- Browser/app control (chrome_open_url, open_app, open_url)
- Shell execution (run_shell, run_shortcut, run_automator, run_applescript)
- Screenshots
- Module creation
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from system_cli.state import state
from tui.cli_paths import SCRIPT_DIR, UI_SETTINGS_PATH, LLM_SETTINGS_PATH
from tui.themes import THEME_NAMES


def _safe_abspath(path: str) -> str:
    """Safely expand and resolve absolute path."""
    expanded = os.path.expanduser(str(path or "")).strip()
    if not expanded:
        return ""
    if os.path.isabs(expanded):
        return expanded
    try:
        return os.path.abspath(expanded)
    except Exception:
        return ""


# Permission tracking
class _ToolPermissions:
    """Track granted permissions for tool execution."""
    allow_run: bool = False
    allow_shell: bool = False
    allow_applescript: bool = False
    allow_gui: bool = False


_agent_last_permissions = _ToolPermissions()


def tool_scan_traces(args: Dict[str, Any]) -> Dict[str, Any]:
    """Scan for editor traces in typical macOS paths."""
    from tui.cleanup import scan_traces
    
    editor = str(args.get("editor", "")).strip()
    if not editor:
        return {"ok": False, "error": "Missing editor"}
    return {"ok": True, "result": scan_traces(editor)}


def tool_list_dir(args: Dict[str, Any]) -> Dict[str, Any]:
    """List directory contents."""
    path = _safe_abspath(str(args.get("path", "")))
    if not path or not os.path.exists(path):
        return {"ok": False, "error": f"Path not found: {path}"}
    if not os.path.isdir(path):
        return {"ok": False, "error": f"Not a directory: {path}"}
    try:
        items = sorted(os.listdir(path))
        return {"ok": True, "path": path, "count": len(items), "items": items[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Screenshot management helpers ---
def _task_screenshots_dir() -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(base, "task_screenshots")


def tool_list_screenshots(args: Dict[str, Any]) -> Dict[str, Any]:
    """List recent screenshots in task_screenshots directory."""
    try:
        root = _task_screenshots_dir()
        count = int(args.get("count", 10) or 10)
        if not os.path.isdir(root):
            return {"ok": True, "root": root, "count": 0, "items": []}
        # Collect files
        files = [os.path.join(root, f) for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        items = []
        for p in files[:count]:
            try:
                items.append({
                    "name": os.path.basename(p),
                    "path": p,
                    "size": os.path.getsize(p),
                    "mtime": int(os.path.getmtime(p))
                })
            except Exception:
                continue
        return {"ok": True, "root": root, "count": len(items), "items": items}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_open_screenshots(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open the task_screenshots directory in Finder (macOS)."""
    try:
        root = _task_screenshots_dir()
        os.makedirs(root, exist_ok=True)
        # Use macOS 'open' to reveal directory
        subprocess.run(["open", root], capture_output=True)
        return {"ok": True, "root": root}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_organize_desktop(args: Dict[str, Any], allow_shell: bool) -> Dict[str, Any]:
    """Organize desktop by moving files into categorized folders."""
    if not allow_shell:
        return {"ok": False, "error": "File operations require unsafe mode or CONFIRM_SHELL"}

    desktop_path = str(args.get("desktop_path") or "~/Desktop")
    target_folder_name = str(args.get("target_folder_name") or "Organized_Files")

    desktop = _safe_abspath(desktop_path)
    if not desktop or not os.path.exists(desktop):
        return {"ok": False, "error": f"Path not found: {desktop}"}
    if not os.path.isdir(desktop):
        return {"ok": False, "error": f"Not a directory: {desktop}"}

    target_dir = os.path.join(desktop, target_folder_name)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        return {"ok": False, "error": f"Failed to create target dir: {target_dir}. {e}"}

    screenshot_prefixes = (
        "screenshot",
        "screen shot",
        "знімок екрана",
        "знімок екрану",
        "снимок экрана",
    )
    screenshot_exts = {".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff", ".bmp", ".gif"}

    def _is_screenshot_file(filename: str) -> bool:
        name = str(filename or "").strip()
        if not name:
            return False
        base, ext = os.path.splitext(name)
        if ext.lower() not in screenshot_exts:
            return False
        low = base.strip().lower()
        return any(low.startswith(p) for p in screenshot_prefixes)

    def _unique_dest_path(dest: str) -> str:
        if not os.path.exists(dest):
            return dest
        root, ext = os.path.splitext(dest)
        i = 2
        while True:
            cand = f"{root} ({i}){ext}"
            if not os.path.exists(cand):
                return cand
            i += 1

    deleted = 0
    moved = 0
    skipped_dirs = 0
    errors: List[str] = []

    try:
        items = sorted(os.listdir(desktop))
    except Exception as e:
        return {"ok": False, "error": str(e)}

    for name in items:
        if name in {".", "..", target_folder_name, ".DS_Store"}:
            continue
        src = os.path.join(desktop, name)
        try:
            if os.path.isdir(src):
                skipped_dirs += 1
                continue
            if not os.path.isfile(src):
                continue

            if _is_screenshot_file(name):
                os.remove(src)
                deleted += 1
                continue

            _base, ext = os.path.splitext(name)
            ext_key = (ext.lower().lstrip(".") or "no_extension")
            dest_dir = os.path.join(target_dir, ext_key)
            os.makedirs(dest_dir, exist_ok=True)
            dest = _unique_dest_path(os.path.join(dest_dir, name))
            shutil.move(src, dest)
            moved += 1
        except Exception as e:
            errors.append(f"{name}: {e}")

    ok = len(errors) == 0
    return {
        "ok": ok,
        "desktop": desktop,
        "target_dir": target_dir,
        "deleted_screenshots": deleted,
        "moved_files": moved,
        "skipped_directories": skipped_dirs,
        "errors": errors[:50],
    }


def tool_organize_desktop_wrapper(args: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Wrapper for organize_desktop that checks permissions."""
    allow_shell = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_shell", False)
    )
    return tool_organize_desktop(args, allow_shell)


def tool_chrome_open_url(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open URL specifically in Google Chrome."""
    url = str(args.get("url", "")).strip()
    if not url:
        return {"ok": False, "error": "Missing url"}
    allow_applescript = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_applescript", False)
    )
    if not allow_applescript:
        return {"ok": False, "error": "AppleScript requires unsafe mode or CONFIRM_APPLESCRIPT"}
    try:
        from tui.cli import log
        log(f"[BROWSER] Opening Chrome URL: {url}", "info")
        script = f'tell application "Google Chrome" to open location "{url}"'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
        log(f"[BROWSER] Chrome URL opened: {url}", "success")
        return {"ok": True, "url": url}
    except Exception as e:
        from tui.cli import log
        log(f"[BROWSER] Failed to open Chrome URL: {e}", "error")
        return {"ok": False, "error": str(e)}


def tool_chrome_active_tab(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get Google Chrome active tab information."""
    allow_applescript = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_applescript", False)
    )
    if not allow_applescript:
        return {"ok": False, "error": "AppleScript requires unsafe mode or CONFIRM_APPLESCRIPT"}
    try:
        script = '''
        tell application "Google Chrome"
            set tabTitle to title of active tab of front window
            set tabURL to URL of active tab of front window
            return tabTitle & "|||" & tabURL
        end tell
        '''
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            output = result.stdout.strip()
            parts = output.split("|||")
            if len(parts) >= 2:
                return {"ok": True, "title": parts[0], "url": parts[1]}
            return {"ok": True, "raw": output}
        return {"ok": False, "error": result.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_open_url(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open URL using macOS open command."""
    url = str(args.get("url", "")).strip()
    if not url:
        return {"ok": False, "error": "Missing url"}
    try:
        from tui.cli import log
        log(f"[App] Opening URL: {url}", "info")
        subprocess.run(["open", url], check=True, capture_output=True, timeout=10)
        return {"ok": True, "url": url}
    except Exception as e:
        from tui.cli import log
        log(f"[App] Failed to open URL: {e}", "error")
        return {"ok": False, "error": str(e)}


def tool_open_app(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open a macOS application by name."""
    name = str(args.get("name", "")).strip()
    if not name:
        return {"ok": False, "error": "Missing name"}
    try:
        from tui.cli import log
        log(f"[App] Opening app: {name}", "info")
        subprocess.run(["open", "-a", name], check=True, capture_output=True, timeout=10)
        return {"ok": True, "app": name}
    except Exception as e:
        from tui.cli import log
        log(f"[App] Failed to open app {name}: {e}", "error")
        return {"ok": False, "error": str(e)}


def tool_run_shell(args: Dict[str, Any], allow_shell: bool) -> Dict[str, Any]:
    """Run a shell command."""
    command = str(args.get("command", "")).strip()
    if not command:
        return {"ok": False, "error": "Missing command"}
    if not allow_shell:
        return {"ok": False, "error": "Shell commands require unsafe mode or CONFIRM_SHELL"}
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return {
            "ok": result.returncode == 0,
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_run_shell_wrapper(args: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Wrapper for run_shell that checks permissions."""
    allow_shell = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_shell", False)
    )
    return tool_run_shell(args, allow_shell)


def tool_run_shortcut(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run a macOS Shortcut by name."""
    name = str(args.get("name", "")).strip()
    if not name:
        return {"ok": False, "error": "Missing name"}
    allow_shell = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_shell", False)
    )
    if not allow_shell:
        return {"ok": False, "error": "Shortcuts require unsafe mode or CONFIRM_SHELL"}
    try:
        result = subprocess.run(["shortcuts", "run", name], capture_output=True, text=True, timeout=60)
        return {"ok": result.returncode == 0, "name": name, "output": result.stdout[:2000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_run_automator(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run an Automator workflow."""
    workflow_path = str(args.get("workflow_path", "")).strip()
    if not workflow_path:
        return {"ok": False, "error": "Missing workflow_path"}
    allow_shell = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_shell", False)
    )
    if not allow_shell:
        return {"ok": False, "error": "Automator requires unsafe mode or CONFIRM_SHELL"}
    try:
        result = subprocess.run(["automator", workflow_path], capture_output=True, text=True, timeout=120)
        return {"ok": result.returncode == 0, "workflow": workflow_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_run_applescript(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run an AppleScript."""
    script = str(args.get("script", "")).strip()
    if not script:
        return {"ok": False, "error": "Missing script"}
    allow_applescript = bool(getattr(state, "ui_unsafe_mode", False)) or bool(
        getattr(_agent_last_permissions, "allow_applescript", False)
    )
    if not allow_applescript:
        return {"ok": False, "error": "AppleScript requires unsafe mode or CONFIRM_APPLESCRIPT"}
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)
        return {
            "ok": result.returncode == 0,
            "output": result.stdout[:2000],
            "error": result.stderr[:1000] if result.returncode != 0 else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read file contents."""
    path = _safe_abspath(str(args.get("path", "")))
    limit = args.get("limit")
    if not path or not os.path.exists(path):
        return {"ok": False, "error": f"Path not found: {path}"}
    if not os.path.isfile(path):
        return {"ok": False, "error": f"Not a file: {path}"}
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            if limit is not None:
                lines = []
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    lines.append(line.rstrip('\n'))
                content = '\n'.join(lines)
            else:
                content = f.read()
        return {"ok": True, "path": path, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_grep(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search for pattern in files under root directory."""
    import re
    
    root = _safe_abspath(str(args.get("root", "")))
    query = str(args.get("query", "")).strip()
    max_files = args.get("max_files", 50)
    max_hits = args.get("max_hits", 100)
    
    if not root or not os.path.exists(root):
        return {"ok": False, "error": f"Root path not found: {root}"}
    if not query:
        return {"ok": False, "error": "Missing query"}
    
    try:
        pattern = re.compile(query, re.IGNORECASE)
        matches = []
        files_searched = 0
        
        for dirpath, dirnames, filenames in os.walk(root):
            if files_searched >= max_files:
                break
            for filename in filenames:
                if files_searched >= max_files:
                    break
                filepath = os.path.join(dirpath, filename)
                files_searched += 1
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                matches.append({
                                    "file": filepath,
                                    "line": line_num,
                                    "content": line.rstrip('\n')
                                })
                                if len(matches) >= max_hits:
                                    break
                except Exception:
                    continue  # Skip unreadable files
                    
                if len(matches) >= max_hits:
                    break
                    
        return {"ok": True, "root": root, "query": query, "matches": matches, "files_searched": files_searched}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_take_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    """Take a screenshot of focused window or target app."""
    app_name = args.get("app_name")
    try:
        # Create temporary file for screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        
        if app_name:
            # Try to focus app first, then take screenshot
            try:
                subprocess.run(["osascript", "-e", f'tell application "{app_name}" to activate'], 
                             capture_output=True, timeout=5)
            except Exception:
                pass  # Continue even if app activation fails
        
        # Take screenshot of focused window
        result = subprocess.run(["screencapture", "-w", filename], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(filename):
            return {"ok": True, "file": os.path.abspath(filename)}
        err = str(result.stderr or "").strip()
        low = err.lower()
        if "screen recording" in low or "not permitted" in low:
            return {
                "ok": False,
                "error": f"Screenshot failed: {err}",
                "error_type": "permission_required",
                "permission": "screen_recording",
                "settings_url": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
            }
        return {"ok": False, "error": f"Screenshot failed: {err}"}
            
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_create_module(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a cleanup module."""
    try:
        # This would create a cleanup module based on the args
        # For now, return a placeholder response
        return {"ok": True, "result": "Module creation not yet implemented"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_ui_streaming_status(args: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get UI streaming status."""
    return {"ok": True, "streaming": getattr(state, 'ui_streaming', True)}


def tool_ui_streaming_set(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set UI streaming status."""
    streaming = args.get("streaming")
    if streaming is not None:
        if isinstance(streaming, str):
            streaming = streaming.lower() in {"true", "1", "on", "yes"}
        state.ui_streaming = bool(streaming)
    return {"ok": True, "streaming": state.ui_streaming}


def tool_llm_status(args: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get LLM configuration status."""
    from tui.agents import load_llm_settings
    load_llm_settings()
    
    section = str((args or {}).get("section") or "").strip().lower()
    
    # Global defaults
    result = {
        "ok": True,
        "provider": str(os.getenv("LLM_PROVIDER") or "copilot"),
        "main_model": str(os.getenv("COPILOT_MODEL") or ""),
        "vision_model": str(os.getenv("COPILOT_VISION_MODEL") or ""),
        "settings_path": LLM_SETTINGS_PATH,
    }
    
    if section:
        # Override with section specific env vars if known
        if section == "atlas":
            result["provider"] = os.getenv("ATLAS_PROVIDER") or result["provider"]
            result["model"] = os.getenv("ATLAS_MODEL") or "gpt-4.1"
        elif section == "tetyana":
            result["provider"] = os.getenv("TETYANA_PROVIDER") or result["provider"]
            result["model"] = os.getenv("TETYANA_MODEL") or "gpt-4o"
        elif section == "grisha":
            result["provider"] = os.getenv("GRISHA_PROVIDER") or result["provider"]
            result["model"] = os.getenv("GRISHA_MODEL") or "gpt-4.1"
        elif section == "vision":
            result["provider"] = os.getenv("VISION_TOOL_PROVIDER") or result["provider"]
            result["model"] = os.getenv("VISION_TOOL_MODEL") or "gpt-4.1"
            
    return result


def tool_llm_set(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set LLM configuration."""
    from tui.agents import save_llm_settings, reset_agent_llm
    
    section = str(args.get("section") or "").strip().lower()
    
    if section in {"atlas", "tetyana", "grisha", "vision"}:
        # Section update
        provider = args.get("provider")
        model = args.get("model")
        ok = save_llm_settings(section=section, provider=provider, model=model)
        if ok:
            reset_agent_llm()
        return {"ok": ok, "section": section, "provider": provider, "model": model}
        
    # Default global update
    provider = str(args.get("provider") or os.getenv("LLM_PROVIDER") or "copilot").strip().lower() or "copilot"
    main_model = str(args.get("main_model") or os.getenv("COPILOT_MODEL") or "gpt-4o").strip() or "gpt-4o"
    vision_model = str(args.get("vision_model") or os.getenv("COPILOT_VISION_MODEL") or "gpt-4.1").strip() or "gpt-4.1"
    ok = save_llm_settings(provider=provider, main_model=main_model, vision_model=vision_model)
    if ok:
        reset_agent_llm()
    return {"ok": ok, "provider": provider, "main_model": main_model, "vision_model": vision_model}


def tool_ui_theme_status(args: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get UI theme status."""
    return {"ok": True, "theme": state.ui_theme, "settings_path": UI_SETTINGS_PATH}


def tool_ui_theme_set(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set UI theme."""
    theme = str(args.get("theme") or "").strip().lower()
    if theme not in set(THEME_NAMES):
        return {"ok": False, "error": f"Unknown theme: {theme}"}
    state.ui_theme = theme
    from tui.cli import _save_ui_settings
    ok = _save_ui_settings()
    return {"ok": ok, "theme": state.ui_theme}


# Backward compatibility aliases
_tool_scan_traces = tool_scan_traces
_tool_list_dir = tool_list_dir
_tool_organize_desktop = tool_organize_desktop
_tool_organize_desktop_wrapper = tool_organize_desktop_wrapper
_tool_chrome_open_url = tool_chrome_open_url
_tool_chrome_active_tab = tool_chrome_active_tab
_tool_open_url = tool_open_url
_tool_open_app = tool_open_app
_tool_run_shell = tool_run_shell
_tool_run_shell_wrapper = tool_run_shell_wrapper
_tool_run_shortcut = tool_run_shortcut
_tool_run_automator = tool_run_automator
_tool_run_applescript = tool_run_applescript
_tool_read_file = tool_read_file
_tool_grep = tool_grep
_tool_take_screenshot = tool_take_screenshot
_tool_create_module = tool_create_module
_tool_ui_streaming_status = tool_ui_streaming_status
_tool_ui_streaming_set = tool_ui_streaming_set
_tool_llm_status = tool_llm_status
_tool_llm_set = tool_llm_set
_tool_ui_theme_status = tool_ui_theme_status
_tool_ui_theme_set = tool_ui_theme_set
