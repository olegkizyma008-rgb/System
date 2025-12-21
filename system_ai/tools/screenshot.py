import os
import time
import subprocess
from typing import Any, Dict, Optional, Tuple, Union, List
from PIL import Image, ImageChops
import mss
import mss.tools
from datetime import datetime


def get_frontmost_app() -> Dict[str, Any]:
    """Get information about the currently active (frontmost) application on macOS.
    
    Returns:
        dict with keys: app_name, window_title, bundle_id, or error
    """
    try:
        # Get frontmost app name
        script_app = '''
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            return appName
        end tell
        '''
        proc_app = subprocess.run(["osascript", "-e", script_app], capture_output=True, text=True, timeout=3)
        app_name = proc_app.stdout.strip() if proc_app.returncode == 0 else None
        
        if not app_name:
            return {"status": "error", "error": "Cannot determine frontmost app"}
        
        # Get window title
        script_title = f'''
        tell application "System Events"
            tell process "{app_name}"
                try
                    set winTitle to name of front window
                    return winTitle
                on error
                    return ""
                end try
            end tell
        end tell
        '''
        proc_title = subprocess.run(["osascript", "-e", script_title], capture_output=True, text=True, timeout=3)
        window_title = proc_title.stdout.strip() if proc_title.returncode == 0 else ""
        
        return {
            "status": "success",
            "app_name": app_name,
            "window_title": window_title
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_all_windows() -> Dict[str, Any]:
    """Get list of all visible windows on macOS.
    
    Returns:
        dict with list of windows, each containing: app_name, window_title, position, size
    """
    try:
        script = '''
        set windowList to {}
        tell application "System Events"
            repeat with proc in (every process whose visible is true)
                set procName to name of proc
                try
                    repeat with win in (every window of proc)
                        try
                            set winName to name of win
                            set winPos to position of win
                            set winSize to size of win
                            set end of windowList to procName & "|" & winName & "|" & (item 1 of winPos as text) & "," & (item 2 of winPos as text) & "|" & (item 1 of winSize as text) & "," & (item 2 of winSize as text)
                        end try
                    end repeat
                end try
            end repeat
        end tell
        set AppleScript's text item delimiters to "\\n"
        return windowList as text
        '''
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        
        if proc.returncode != 0:
            return {"status": "error", "error": proc.stderr}
        
        windows = []
        for line in proc.stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    pos_parts = parts[2].split(",")
                    size_parts = parts[3].split(",")
                    windows.append({
                        "app_name": parts[0],
                        "window_title": parts[1],
                        "position": {"x": int(pos_parts[0]), "y": int(pos_parts[1])},
                        "size": {"width": int(size_parts[0]), "height": int(size_parts[1])}
                    })
        
        return {"status": "success", "windows": windows, "count": len(windows)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class VisionDiffManager:
    """Manages screenshot lifecycle and calculates differences between frames."""
    _instance = None
    _last_image: Optional[Image.Image] = None
    _last_focus: Optional[str] = None 
    _session_id: Optional[str] = None

    def __init__(self):
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_session_id(self, sid: str):
        self._session_id = sid

    def _rotate_files(self, directory: str, limit: int):
        """Keep only the N most recent files in a directory."""
        try:
            files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            if len(files) <= limit:
                return
            files.sort(key=os.path.getmtime)
            for f in files[:-limit]:
                try:
                    os.unlink(f)
                except Exception:
                    pass
        except Exception:
            pass

    def _rotate_sessions(self, base_dir: str, limit: int):
        """Keep only the N most recent session directories."""
        try:
            dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
            if len(dirs) <= limit:
                return
            dirs.sort(key=os.path.getmtime)
            for d in dirs[:-limit]:
                try:
                    import shutil
                    shutil.rmtree(d)
                except Exception:
                    pass
        except Exception:
            pass

    def process_screenshot(self, current_img: Image.Image, focus_id: str) -> Dict[str, Any]:
        # Prioritize project data folder if it exists
        project_base_dir = os.path.abspath(".agent/workflows/data/screenshots")
        if not os.path.isdir(os.path.dirname(project_base_dir)):
             # Fallback if .agent/workflows/data doesn't exist
             project_base_dir = os.path.expanduser("~/.antigravity/vision_cache")
        
        os.makedirs(project_base_dir, exist_ok=True)
        
        # Session rotation (max 5)
        self._rotate_sessions(project_base_dir, 5)
        
        # Session folder
        sid = self._session_id or "default"
        session_dir = os.path.join(project_base_dir, sid)
        os.makedirs(session_dir, exist_ok=True)
        
        # File rotation within session (max 20)
        self._rotate_files(session_dir, 20)
        
        timestamp = int(time.time() * 1000)
        path = os.path.join(session_dir, f"snap_{timestamp}.jpg")
        
        # Save current frame
        current_img.convert("RGB").save(path, "JPEG", quality=85)
        
        mode = "initial"
        bbox = None
        
        if self._last_image and self._last_focus == focus_id and self._last_image.size == current_img.size:
            diff = ImageChops.difference(current_img, self._last_image)
            bbox = diff.getbbox()
            if bbox:
                mode = "update"
            else:
                mode = "no_change"
        
        self._last_image = current_img
        self._last_focus = focus_id
        
        return {
            "path": path,
            "mode": mode,
            "bbox": bbox
        }

def take_screenshot(app_name: Optional[str] = None, window_title: Optional[str] = None, activate: bool = False, use_frontmost: bool = False) -> Dict[str, Any]:
    """Takes a smart screenshot of an app or the full screen.
    
    Args:
        app_name: Name of the application (e.g. "Safari")
        window_title: Optional substring to filter specific windows (e.g. "Google")
        activate: If True, brings the application/window to the front before capturing.
        use_frontmost: If True and no app_name provided, capture the frontmost app window.
    """
    try:
        # Auto-detect frontmost app if requested
        if use_frontmost and not app_name:
            frontmost = get_frontmost_app()
            if frontmost.get("status") == "success":
                app_name = frontmost.get("app_name")
                if not window_title:
                    window_title = frontmost.get("window_title")
        
        if activate and app_name:
            # Dynamic Focus: Bring app to front
            # If window_title is specific, we could try to raise just that window, but raising the App is safer/standard.
            # We use ignoring application responses to avoid blocking if the app is hung, though basic activate is usually fine.
            script = f'tell application "{app_name}" to activate'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            time.sleep(0.5) # Wait for animation
            
        manager = VisionDiffManager.get_instance()
        focus_id = "FULL"
        if app_name:
            focus_id = f"APP_{app_name}"
            if window_title:
                focus_id += f"_{window_title}"
        
        with mss.mss() as sct:
            # Multi-monitor support: monitor 0 is the union of all monitors
            monitor = sct.monitors[0]
            
            # If app_name, try to get its window geometry
            region = None
            if app_name:
                region = _get_app_geometry(app_name, window_title)
            
            sct_img = sct.grab(region or monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
        res = manager.process_screenshot(img, focus_id)
        
        return {
            "tool": "take_screenshot",
            "status": "success",
            "path": res["path"],
            "mode": res["mode"],
            "focus": focus_id,
            "diff_bbox": res["bbox"]
        }
    except Exception as e:
        return {"tool": "take_screenshot", "status": "error", "error": str(e)}

def _get_app_geometry(app_name: str, window_title: Optional[str] = None) -> Optional[Dict[str, int]]:
    # If window_title provided, filter by it. otherwise get window 1.
    if window_title:
        # Get first window where name contains title
        script = f'tell application "System Events" to tell process "{app_name}" to get {{position, size}} of first window where name contains "{window_title}"'
    else:
        # Default to first window
        script = f'tell application "System Events" to tell process "{app_name}" to get {{position, size}} of window 1'
        
    try:
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        if proc.returncode == 0:
            # Format: 100, 100, 800, 600
            parts = proc.stdout.strip().replace(" ", "").split(",")
            if len(parts) >= 4:
                return {
                    "left": int(parts[0]),
                    "top": int(parts[1]),
                    "width": int(parts[2]),
                    "height": int(parts[3])
                }
    except Exception:
        pass
    return None

def capture_screen_region(x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    try:
        region = {"left": int(x), "top": int(y), "width": int(width), "height": int(height)}
        with mss.mss() as sct:
            sct_img = sct.grab(region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
        output_dir = os.path.expanduser("~/.antigravity/vision_cache")
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"region_{int(time.time())}.png")
        img.save(path)
        
        return {"tool": "capture_screen_region", "status": "success", "path": path}
    except Exception as e:
        return {"tool": "capture_screen_region", "status": "error", "error": str(e)}

def take_burst_screenshot(app_name: Optional[str] = None, count: int = 3, interval: float = 0.3) -> Dict[str, Any]:
    paths = []
    for _ in range(count):
        res = take_screenshot(app_name)
        if res["status"] == "success":
            paths.append(res["path"])
        time.sleep(interval)
    return {"tool": "take_burst_screenshot", "status": "success", "paths": paths}
