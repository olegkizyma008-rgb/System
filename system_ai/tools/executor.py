import os
import subprocess
import time
from typing import Any, Dict, Optional


_DEFAULT_FORBIDDEN_TOKENS = [
    "rm -rf",
    " shutdown",
    "reboot",
    "halt",
    "diskutil erase",
    "mkfs",
    ":(){ :|:& };:",
]


_PRIVACY_URLS: Dict[str, str] = {
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "automation": "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation",
    "full_disk_access": "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
    "screen_recording": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
    "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "files_and_folders": "x-apple.systempreferences:com.apple.preference.security?Privacy_FilesAndFolders",
}


def _detect_applescript_permission_issue(stderr: str) -> Optional[Dict[str, Any]]:
    s = (stderr or "").strip()
    if not s:
        return None
    lower = s.lower()

    if "assistive access" in lower or "not allowed assistive" in lower or "not permitted" in lower:
        return {
            "error_type": "permission_required",
            "permission": "accessibility",
            "settings_url": _PRIVACY_URLS["accessibility"],
        }

    if "not authorized to send apple events" in lower or "not authorised to send apple events" in lower:
        return {
            "error_type": "permission_required",
            "permission": "automation",
            "settings_url": _PRIVACY_URLS["automation"],
        }

    return None


def _detect_shell_permission_issue(command: str, stderr: str) -> Optional[Dict[str, Any]]:
    s = (stderr or "").strip()
    if not s:
        return None
    lower = s.lower()

    if "operation not permitted" in lower:
        return {
            "error_type": "permission_required",
            "permission": "full_disk_access",
            "settings_url": _PRIVACY_URLS["full_disk_access"],
        }

    if "permission denied" in lower:
        return {
            "error_type": "permission_required",
            "permission": "files_and_folders",
            "settings_url": _PRIVACY_URLS["files_and_folders"],
        }

    if "screen recording" in lower:
        return {
            "error_type": "permission_required",
            "permission": "screen_recording",
            "settings_url": _PRIVACY_URLS["screen_recording"],
        }

    if "microphone" in lower and "not" in lower and "permit" in lower:
        return {
            "error_type": "permission_required",
            "permission": "microphone",
            "settings_url": _PRIVACY_URLS["microphone"],
        }

    _ = command
    return None


def open_system_settings_privacy(permission: str) -> Dict[str, Any]:
    perm = str(permission or "").strip() or "accessibility"
    url = _PRIVACY_URLS.get(perm) or _PRIVACY_URLS["accessibility"]
    try:
        proc = subprocess.run(["open", url], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                "tool": "open_system_settings_privacy",
                "status": "error",
                "permission": perm,
                "error": (proc.stderr or "").strip() or "Failed to open System Settings",
                "url": url,
            }
        return {"tool": "open_system_settings_privacy", "status": "success", "permission": perm, "url": url}
    except Exception as e:
        return {"tool": "open_system_settings_privacy", "status": "error", "permission": perm, "error": str(e), "url": url}


def open_app(name: str) -> Dict[str, Any]:
    try:
        raw = str(name or "").strip()
        n = raw
        key = " ".join(raw.lower().replace("_", " ").split())
        app_aliases = {
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "гугл хром": "Google Chrome",
            "гуглхром": "Google Chrome",
            "хром": "Google Chrome",
            "chrom": "Google Chrome",
            "сафари": "Safari",
            "сафарі": "Safari",
            "safari": "Safari",
            "finder": "Finder",
            "файндер": "Finder",
            "фіндер": "Finder",
            "термінал": "Terminal",
            "терминал": "Terminal",
            "terminal": "Terminal",
            "shortcuts": "Shortcuts",
            "ярлики": "Shortcuts",
            "шорткати": "Shortcuts",
            "команди": "Shortcuts",
            "settings": "System Settings",
            "system settings": "System Settings",
            "налаштування": "System Settings",
            "настройки": "System Settings",
        }
        n = app_aliases.get(key, n)

        proc = subprocess.run(
            ["open", "-a", n],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return {"tool": "open_app", "status": "error", "error": (proc.stderr or "").strip(), "app": n, "input": raw}
        time.sleep(1.5)
        return {"tool": "open_app", "status": "success", "app": n, "input": raw}
    except Exception as e:
        return {"tool": "open_app", "status": "error", "error": str(e)}


def open_url(url: str) -> Dict[str, Any]:
    u = str(url or "").strip()
    if not u:
        return {"tool": "open_url", "status": "error", "error": "Missing url"}
    try:
        proc = subprocess.run(
            ["open", u],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return {"tool": "open_url", "status": "error", "error": (proc.stderr or "").strip(), "url": u}
        time.sleep(0.8)
        return {"tool": "open_url", "status": "success", "url": u}
    except Exception as e:
        return {"tool": "open_url", "status": "error", "error": str(e), "url": u}


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
            perm_issue = _detect_shell_permission_issue(command, proc.stderr or "")
            if perm_issue:
                return {
                    "tool": "run_shell",
                    "status": "error",
                    "command": command,
                    "returncode": proc.returncode,
                    "stdout": (proc.stdout or "")[-8000:],
                    "stderr": (proc.stderr or "")[-8000:],
                    **perm_issue,
                }
        return {
            "tool": "run_shell",
            "status": "success" if proc.returncode == 0 else "error",
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

    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            perm_issue = _detect_applescript_permission_issue(proc.stderr or "")
            if perm_issue:
                return {
                    "tool": "run_applescript",
                    "status": "error",
                    "error": (proc.stderr or "").strip(),
                    "script_preview": (script[:120] + "...") if len(script) > 120 else script,
                    **perm_issue,
                }
            return {
                "tool": "run_applescript",
                "status": "error",
                "error": (proc.stderr or "").strip(),
                "script_preview": (script[:120] + "...") if len(script) > 120 else script,
            }
        return {"tool": "run_applescript", "status": "success", "output": (proc.stdout or "").strip()}
    except Exception as e:
        return {"tool": "run_applescript", "status": "error", "error": str(e)}


def run_shortcut(name: str, *, allow: bool) -> Dict[str, Any]:
    if not allow:
        return {"tool": "run_shortcut", "status": "error", "error": "Confirmation required"}

    n = str(name or "").strip()
    if not n:
        return {"tool": "run_shortcut", "status": "error", "error": "Missing name"}

    try:
        proc = subprocess.run(
            ["shortcuts", "run", n],
            capture_output=True,
            text=True,
        )
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


def run_automator(workflow_path: str, *, allow: bool) -> Dict[str, Any]:
    if not allow:
        return {"tool": "run_automator", "status": "error", "error": "Confirmation required"}

    w = str(workflow_path or "").strip()
    if not w:
        return {"tool": "run_automator", "status": "error", "error": "Missing workflow path"}

    try:
        proc = subprocess.run(
            ["automator", "-i", "", w],
            capture_output=True,
            text=True,
        )
        return {
            "tool": "run_automator",
            "status": "success" if proc.returncode == 0 else "error",
            "workflow": w,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-8000:],
            "stderr": (proc.stderr or "")[-8000:],
        }
    except Exception as e:
        return {"tool": "run_automator", "status": "error", "workflow": w, "error": str(e)}
