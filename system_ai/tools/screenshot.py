import os
import time
import subprocess
from typing import Any, Dict, Optional, Tuple, Union, List
from PIL import Image, ImageChops
import mss
import mss.tools

class VisionDiffManager:
    """Manages screenshot lifecycle and calculates differences between frames."""
    _instance = None
    _last_image: Optional[Image.Image] = None
    _last_focus: Optional[str] = None 

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_screenshot(self, current_img: Image.Image, focus_id: str) -> Dict[str, Any]:
        output_dir = os.path.expanduser("~/.antigravity/vision_cache")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        path = os.path.join(output_dir, f"snap_{timestamp}.jpg")
        
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

def take_screenshot(app_name: Optional[str] = None) -> Dict[str, Any]:
    """Takes a smart screenshot of an app or the full screen."""
    try:
        manager = VisionDiffManager.get_instance()
        focus_id = "FULL" if not app_name else f"APP_{app_name}"
        
        with mss.mss() as sct:
            # Multi-monitor support: monitor 0 is the union of all monitors
            monitor = sct.monitors[0]
            
            # If app_name, try to get its window geometry
            region = None
            if app_name:
                region = _get_app_geometry(app_name)
            
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

def _get_app_geometry(app_name: str) -> Optional[Dict[str, int]]:
    script = f'tell application "System Events" to tell process "{app_name}" to get {{position, size}} of window 1'
    try:
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        if proc.returncode == 0:
            # Format: 100, 100, 800, 600
            parts = proc.stdout.strip().replace(" ", "").split(",")
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
