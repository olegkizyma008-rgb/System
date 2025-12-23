"""Cleanup and editor module management for TUI.

Provides functions for:
- Loading/saving cleanup configuration
- Running cleanup scripts
- Module enable/disable
- Editor installation (DMG/ZIP/URL)
- Scanning editor traces
"""

from __future__ import annotations

import fnmatch
import glob
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from tui.cli_paths import CLEANUP_CONFIG_PATH, SCRIPT_DIR
from tui.cli_defaults import DEFAULT_CLEANUP_CONFIG


@dataclass
class ModuleRef:
    """Reference to a cleanup module."""
    editor: str
    module_id: str


def load_cleanup_config() -> Dict[str, Any]:
    """Load cleanup configuration from file."""
    if not os.path.exists(CLEANUP_CONFIG_PATH):
        return json.loads(json.dumps(DEFAULT_CLEANUP_CONFIG))

    try:
        with open(CLEANUP_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}
    data.setdefault("editors", {})

    for key, val in (DEFAULT_CLEANUP_CONFIG.get("editors", {}) or {}).items():
        if key not in data["editors"]:
            data["editors"][key] = val
            continue

        for field_name in ["label", "install", "modules"]:
            if field_name not in data["editors"][key]:
                data["editors"][key][field_name] = val.get(field_name)

        if not data["editors"][key].get("modules") and val.get("modules"):
            data["editors"][key]["modules"] = val["modules"]

    return data


def save_cleanup_config(cfg: Dict[str, Any]) -> None:
    """Save cleanup configuration to file."""
    with open(CLEANUP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def list_editors(cfg: Dict[str, Any]) -> List[str]:
    """List available editor keys from config."""
    editors = cfg.get("editors", {}) or {}
    result = []
    for key, val in editors.items():
        if isinstance(val, dict):
            result.append(key)
    return result


def pick_fallback_editor(editors: Dict[str, Any]) -> str:
    """Pick a default editor if none specified."""
    if not editors:
        return ""
    if "windsurf" in editors:
        return "windsurf"
    
    for key, meta in editors.items():
        try:
            modules = (meta or {}).get("modules", []) if isinstance(meta, dict) else []
            if any(isinstance(m, dict) and m.get("enabled") for m in (modules or [])):
                return key
        except Exception:
            continue
            
    return sorted([str(k) for k in editors.keys() if str(k)])[0] if editors else ""


def resolve_editor_arg(cfg: Dict[str, Any], editor: Optional[str]) -> Tuple[str, Optional[str]]:
    """Resolve editor argument to a valid editor key."""
    editors = cfg.get("editors", {}) or {}

    if not editor:
        fallback = pick_fallback_editor(editors)
        if not fallback:
            return "", f"Editor not specified. Доступні редактори: {', '.join(editors.keys())}. Вкажіть --editor."
        
        msg = f"Editor not specified. Доступні редактори: {', '.join(editors.keys())}. Вкажіть --editor."
        return fallback, None if len(editors) == 1 else msg

    low = editor.strip().lower()
    aliases = {
        "ws": "windsurf", "windsurfs": "windsurf", "wind": "windsurf",
        "code": "vscode", "vs": "vscode", "vscodium": "vscode",
        "anti": "antigravity", "ag": "antigravity", "google": "antigravity", "gemini": "antigravity",
        "curs": "cursor", "cur": "cursor",
    }
    resolved = aliases.get(low, low)
    if resolved in editors:
        return resolved, None
        
    fallback = pick_fallback_editor(editors)
    if fallback:
        note = f"Editor not specified. Доступні редактори: {', '.join(editors.keys())}. Вкажіть --editor."
        return fallback, note
        
    return resolved, None


def find_module(cfg: Dict[str, Any], editor: str, module_id: str) -> Optional[ModuleRef]:
    """Find a module in configuration."""
    editors = cfg.get("editors", {}) or {}
    if editor not in editors:
        return None
    for m in editors[editor].get("modules", []) or []:
        if isinstance(m, dict) and m.get("id") == module_id:
            return ModuleRef(editor=editor, module_id=module_id)
    return None


def set_module_enabled(cfg: Dict[str, Any], ref: ModuleRef, enabled: bool) -> bool:
    """Enable or disable a cleanup module."""
    editor_cfg = (cfg.get("editors", {}) or {}).get(ref.editor)
    if not isinstance(editor_cfg, dict):
        return False

    for m in editor_cfg.get("modules", []) or []:
        if not isinstance(m, dict):
            continue
        if m.get("id") == ref.module_id:
            m["enabled"] = bool(enabled)
            save_cleanup_config(cfg)
            return True

    return False


def script_env() -> Dict[str, str]:
    """Prepare environment variables for script execution."""
    env = os.environ.copy()
    
    # Ensure required environment variables are set
    env["AUTO_YES"] = os.getenv("AUTO_YES", "1")
    env["UNSAFE_MODE"] = os.getenv("UNSAFE_MODE", "1")
    
    # Pass SUDO_PASSWORD if available
    if "SUDO_PASSWORD" in os.environ:
        env["SUDO_PASSWORD"] = os.environ["SUDO_PASSWORD"]
    
    # Set SUDO_ASKPASS for non-interactive sudo
    sudo_helper = os.path.join(SCRIPT_DIR, "cleanup_scripts", "sudo_helper.sh")
    if os.path.exists(sudo_helper):
        env["SUDO_ASKPASS"] = sudo_helper
    
    return env


def _stream_output(proc: subprocess.Popen, timeout: int, start_time: float, log_callback=None) -> int:
    """Helper to stream output line by line with timeout."""
    import time
    while True:
        if time.time() - start_time > timeout:
            proc.kill()
            return 124
        
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        
        if line:
            line = line.rstrip()
            if log_callback and line:
                log_callback(line)
    return int(proc.returncode or 0)


def run_script(script_path: str, timeout: int = 300, log_callback=None) -> int:
    """Run a cleanup script and return exit code."""
    full = script_path
    if not os.path.isabs(full):
        full = os.path.join(SCRIPT_DIR, script_path)

    if not os.path.exists(full):
        return 1

    try:
        subprocess.run(["chmod", "+x", full], check=False)
        
        proc = subprocess.Popen(
            [full], 
            cwd=SCRIPT_DIR, 
            env=script_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        import time
        return _stream_output(proc, timeout, time.time(), log_callback)
    except Exception:
        return 1


def run_cleanup(cfg: Dict[str, Any], editor: str, dry_run: bool = False, log_callback=None) -> Tuple[bool, str]:
    """Run cleanup for specified editor.
    
    Args:
        cfg: Cleanup configuration
        editor: Editor key to clean
        dry_run: If True, only show what would be done
        log_callback: Optional callback function to log output lines
    """
    editors = cfg.get("editors", {}) or {}
    if editor not in editors:
        return False, f"Невідомий редактор: {editor}"

    meta = editors[editor] or {}
    label = meta.get("label", editor)
    modules: List[Dict[str, Any]] = meta.get("modules", []) or []
    active = [m for m in modules if isinstance(m, dict) and m.get("enabled")]

    if not active:
        return False, f"Для {label} немає увімкнених модулів. Налаштуйте їх у Modules або через smart-plan."

    if dry_run:
        names = ", ".join([str(m.get("id")) for m in active])
        return True, f"[DRY-RUN] {label}: {names}"

    for m in active:
        script = m.get("script")
        if not script:
            continue
        code = run_script(str(script), log_callback=log_callback)
        if code != 0:
            return False, f"Модуль {m.get('id')} завершився з кодом {code}"

    return True, f"Очищення завершено: {label}"


def perform_install(cfg: Dict[str, Any], editor: str) -> Tuple[bool, str]:
    """Perform installation for specified editor."""
    editors = cfg.get("editors", {}) or {}
    if editor not in editors:
        return False, f"Невідомий редактор: {editor}"

    install = (editors[editor] or {}).get("install", {}) or {}
    label = (editors[editor] or {}).get("label", editor)
    itype = install.get("type")

    if itype == "dmg":
        pattern = install.get("pattern", "*.dmg")
        candidates = [f for f in os.listdir(SCRIPT_DIR) if f.endswith(".dmg") and fnmatch.fnmatch(f, pattern)]
        if not candidates:
            return False, f"DMG-файлів за шаблоном '{pattern}' не знайдено в {SCRIPT_DIR}"
        dmg = sorted(candidates)[-1]
        subprocess.run(["open", os.path.join(SCRIPT_DIR, dmg)])
        return True, f"Відкрито DMG для {label}: {dmg}"

    if itype == "zip":
        pattern = install.get("pattern", "*.zip")
        candidates = [f for f in os.listdir(SCRIPT_DIR) if f.endswith(".zip") and fnmatch.fnmatch(f, pattern)]
        if not candidates:
            return False, f"ZIP-файлів за шаблоном '{pattern}' не знайдено в {SCRIPT_DIR}"
        z = sorted(candidates)[-1]
        subprocess.run(["open", os.path.join(SCRIPT_DIR, z)])
        return True, f"Відкрито ZIP для {label}: {z}"

    if itype == "url":
        url = install.get("url")
        if not url:
            return False, f"URL для {label} не налаштовано"
        subprocess.run(["open", str(url)])
        return True, f"Відкрито URL для {label}: {url}"

    return False, f"Install не налаштовано для {label}"


def _scan_directory(p: str) -> Dict[str, Any]:
    """Helper to scan a single directory/file."""
    entry: Dict[str, Any] = {"path": p, "type": "file" if os.path.isfile(p) else "dir"}
    if os.path.isdir(p):
        try:
            items = os.listdir(p)
            entry["items"] = len(items)
            entry["sample"] = items[:20]
        except Exception as e:
            entry["error"] = str(e)
    return entry


def scan_traces(editor: str) -> Dict[str, Any]:
    """Scan for editor traces in system directories."""
    editor_key = editor.strip().lower()

    patterns_map: Dict[str, List[str]] = {
        "windsurf": ["*Windsurf*", "*windsurf*"],
        "vscode": ["*Code*", "*VSCodium*", "*vscode*", "*VSCode*"],
        "antigravity": ["*Antigravity*", "*antigravity*", "*Google/Antigravity*"],
        "cursor": ["*Cursor*", "*cursor*"],
        "continue": ["*Continue*", "*continue*"],
    }

    base_dirs = [
        "~/Library/Application Support",
        "~/Library/Caches",
        "~/Library/Preferences",
        "~/Library/Logs",
        "~/Library/Saved Application State",
    ]

    patterns = patterns_map.get(editor_key) or [f"*{editor_key}*"]
    found: List[Dict[str, Any]] = []

    # System library scan
    for b in base_dirs:
        base = os.path.expanduser(b)
        for pat in patterns:
            for p in sorted(glob.glob(os.path.join(base, pat))):
                found.append(_scan_directory(p))

    # Applications bundles
    for pat in patterns:
        for p in sorted(glob.glob(os.path.join("/Applications", pat))):
            found.append({"path": p, "type": "app" if p.endswith(".app") else "file"})

    # Dot-directories
    dot_candidates = [
        os.path.expanduser(f"~/.{e}") for e in ["vscode", "vscode-oss", "cursor", "windsurf", "continue"]
    ]
    for p in dot_candidates:
        if os.path.exists(p) and editor_key in os.path.basename(p).lower():
            found.append({"path": p, "type": "dir" if os.path.isdir(p) else "file"})

    return {
        "editor": editor_key,
        "count": len(found),
        "found": found[:120],
        "note": "Це швидкий скан типових директорій. Якщо потрібно глибше — скажи, які саме шляхи/патерни шукати.",
    }


def get_editors_list(cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Get list of (key, label) tuples for editors."""
    editors = cfg.get("editors", {}) or {}
    result = []
    for key, val in editors.items():
        if isinstance(val, dict):
            result.append((key, val.get("label", key)))
    return result


# Backward compatibility aliases
_load_cleanup_config = load_cleanup_config
_save_cleanup_config = save_cleanup_config
_list_editors = list_editors
_resolve_editor_arg = resolve_editor_arg
_find_module = find_module
_set_module_enabled = set_module_enabled
_script_env = script_env
_run_script = run_script
_run_cleanup = run_cleanup
_perform_install = perform_install
_scan_traces = scan_traces
_get_editors_list = get_editors_list
