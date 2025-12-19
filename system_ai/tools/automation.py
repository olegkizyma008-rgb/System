"""Unified Automation Module

Consolidates shell, AppleScript, shortcuts, and input automation tools across the system.
Uses `MacOSNativeAutomation` as the primary driver for AppleScript/Input recording.
"""

import os
import time
import subprocess
from typing import Dict, Any, Optional, List

from system_ai.tools.macos_native_automation import create_automation_executor, MacOSNativeAutomation

# Initialize default automation driver with recording if available
def _get_driver() -> MacOSNativeAutomation:
    # Try to hook into the global recorder if available via standard location
    try:
        from tui.cli import _get_recorder_service
        return create_automation_executor(recorder_service=_get_recorder_service())
    except ImportError:
        return create_automation_executor(recorder_service=None)

# --- Shell & System Tools ---

_DEFAULT_FORBIDDEN_TOKENS = [
    "rm -rf",
    " shutdown",
    "reboot",
    "halt",
    "diskutil erase",
    "mkfs",
    ":(){ :|:& };:",
]

def run_shell(command: str, *, allow: bool, cwd: Optional[str] = None) -> Dict[str, Any]:
    if not allow:
        return {"tool": "run_shell", "status": "error", "error": "Confirmation required"}

    lower_cmd = command.lower()
    for token in _DEFAULT_FORBIDDEN_TOKENS:
        if token in lower_cmd:
            return {"tool": "run_shell", "status": "error", "error": "Command blocked by safety filter", "command": command}

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
        )
        
        if proc.returncode != 0:
            # We can reuse the detection logic or inline it. For now let's keep it simple or recreate it if executor is gone.
            # Inline detection for robustness since we are deleting executor.py
            perm_issue = None
            err_lower = (proc.stderr or "").lower()
            if "operation not permitted" in err_lower:
                perm_issue = {"error_type": "permission_required", "permission": "full_disk_access"}
            elif "permission denied" in err_lower:
                perm_issue = {"error_type": "permission_required", "permission": "files_and_folders"}
            
            res = {
                "tool": "run_shell",
                "status": "error",
                "command": command,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-8000:],
                "stderr": (proc.stderr or "")[-8000:],
            }
            if perm_issue:
                res.update(perm_issue)
            return res
            
        return {
            "tool": "run_shell",
            "status": "success",
            "command": command,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-8000:],
            "stderr": (proc.stderr or "")[-8000:],
        }
    except Exception as e:
        return {"tool": "run_shell", "status": "error", "command": command, "error": str(e)}

def run_applescript(script: str, *, allow: bool) -> Dict[str, Any]:
    if not allow:
        return {"tool": "run_applescript", "status": "error", "error": "Confirmation required"}
    
    # Use native driver for recording support
    driver = _get_driver()
    return driver.execute_applescript(script, record=True)

def run_shortcut(name: str, *, allow: bool) -> Dict[str, Any]:
    if not allow:
        return {"tool": "run_shortcut", "status": "error", "error": "Confirmation required"}
    
    n = str(name or "").strip()
    try:
        proc = subprocess.run(["shortcuts", "run", n], capture_output=True, text=True)
        return {
            "tool": "run_shortcut",
            "status": "success" if proc.returncode == 0 else "error",
            "name": n,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-8000:],
            "stderr": (proc.stderr or "")[-8000:],
        }
    except Exception as e:
        return {"tool": "run_shortcut", "status": "error", "name": n, "error": str(e)}


def open_app(name: str) -> Dict[str, Any]:
    try:
        driver = _get_driver()
        # Use simple 'open' via driver or subprocess? 
        # Executor used 'open -a', MacOSCommands used 'open -a' via AppleScript.
        # Let's stick to subprocess for speed and simplicity for just opening, but record if possible.
        
        proc = subprocess.run(["open", "-a", name], capture_output=True, text=True)
        if proc.returncode != 0:
             return {"tool": "open_app", "status": "error", "error": (proc.stderr or "").strip(), "app": name}
        time.sleep(1.0)
        return {"tool": "open_app", "status": "success", "app": name}
    except Exception as e:
        return {"tool": "open_app", "status": "error", "error": str(e)}

def activate_app(name: str) -> Dict[str, Any]:
    driver = _get_driver()
    script = f'tell application "{name}" to activate'
    return driver.execute_applescript(script, record=True)

# --- Input & UI Tools ---

def move_mouse(x: int, y: int) -> Dict[str, Any]:
    driver = _get_driver()
    # Try PyAutoGUI first if available for smoothness, else AppleScript
    try:
        import pyautogui
        pyautogui.moveTo(x, y)
        return {"tool": "move_mouse", "status": "success", "x": x, "y": y}
    except (ImportError, Exception):
        # Fallback to AppleScript driver
        script = f'tell application "System Events" to set mouse location to {{{x}, {y}}}'
        return driver.execute_applescript(script, record=True)

def click_mouse(button: str = "left", x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    driver = _get_driver()
    try:
        import pyautogui
        if x is not None and y is not None:
            pyautogui.moveTo(x, y)
        
        btn = button.lower()
        if btn == "double":
            pyautogui.click(clicks=2)
        else:
            pyautogui.click(button=btn)
            
        return {"tool": "click_mouse", "status": "success", "button": button}
    except (ImportError, Exception):
        if x is not None and y is not None:
            move_mouse(x, y) # AppleScript move
        
        # Native click via AppleScript
        btn_code = 1
        if button == "right": btn_code = 2
        
        script = f'tell application "System Events" to click mouse button {btn_code}'
        return driver.execute_applescript(script, record=True)

def click(x: int, y: int) -> Dict[str, Any]:
    return click_mouse("left", x, y)

def type_text(text: str) -> Dict[str, Any]:
    driver = _get_driver()
    # Prefer AppleScript for typing as PyAutoGUI can be flaky with layouts on macOS
    return driver.type_text(text, record=True)

def press_key(key: str, command: bool = False, shift: bool = False, option: bool = False, control: bool = False) -> Dict[str, Any]:
    driver = _get_driver()
    modifiers = []
    if command: modifiers.append("command down")
    if shift: modifiers.append("shift down")
    if option: modifiers.append("option down")
    if control: modifiers.append("control down")
    
    return driver.press_key(key, modifiers, record=True)

# --- High Level UI Tools (from macos_commands) ---

def find_and_click_menu(app_name: str, menu_path: List[str]) -> Dict[str, Any]:
    driver = _get_driver()
    if not menu_path:
        return {"status": "error", "error": "Empty menu path"}
    
    menu_str = " of ".join([f'menu item "{item}"' for item in reversed(menu_path)])
    script = f'''
        tell application "{app_name}"
            activate
            tell application "System Events"
                click {menu_str}
            end tell
        end tell
    '''
    return driver.execute_applescript(script, record=True)

