import os
import time
import subprocess
import shlex
from typing import Any, Dict, Optional, Tuple, Union
from PIL import Image, ImageChops
import mss
import mss.tools

class VisionFocusUtils:
    """Helper methods to determine WHAT to capture before we capture it."""
    
    @staticmethod
    def get_app_window_geometry(app_name: str) -> Optional[Dict[str, int]]:
        """
        Uses AppleScript to find the coordinates of the frontmost window of the specified app.
        Returns a dict compatible with MSS: {'top': y, 'left': x, 'width': w, 'height': h}
        """
        script = f"""
        tell application "System Events"
            if exists process "{app_name}" then
                tell process "{app_name}"
                    if (count of windows) > 0 then
                        set win to window 1
                        set pos to position of win
                        set sz to size of win
                        return (item 1 of pos) & "," & (item 2 of pos) & "," & (item 1 of sz) & "," & (item 2 of sz)
                    end if
                end tell
            end if
        end tell
        """
        try:
            # Run applescript
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
            output = result.stdout.strip()
            
            if not output or "," not in output:
                return None
                
            x, y, w, h = map(int, output.split(","))
            
            # MacOS menubar offset correction usually not needed for raw window pos,
            # but check if using MSS. MSS treats (0,0) validly.
            return {"top": y, "left": x, "width": w, "height": h}
        except Exception:
            return None

class VisionDiffManager:
    _instance = None
    _last_image: Optional[Image.Image] = None
    _last_focus: Optional[str] = None # Tracks what we were looking at (App Name or 'FULL')

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_screenshot(self, current_img: Image.Image, focus_context: str) -> Tuple[str, str, Optional[Tuple[int, int, int, int]]]:
        """
        Calculates diff between current and last image.
        focus_context: Identifier of what we are capturing (e.g. 'Calculator' or 'FULL_SCREEN')
        """
        output_dir = os.path.expanduser("~/.antigravity/vision_cache")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        
        full_path = os.path.join(output_dir, f"snap_{timestamp}.jpg")
        diff_path = os.path.join(output_dir, f"diff_{timestamp}.jpg")

        # Logic: If focus context changed (e.g. was Calculator, now Terminal), we MUST reset diff.
        if self._last_image is None or self._last_focus != focus_context:
            current_img.convert("RGB").save(full_path, "JPEG", quality=85)
            self._last_image = current_img
            self._last_focus = focus_context
            return "initial_focus_frame", full_path, None
        
        # Calculate Diff
        try:
            # Ensure same size (window resize handling)
            if current_img.size != self._last_image.size:
                current_img.convert("RGB").save(full_path, "JPEG", quality=85)
                self._last_image = current_img
                return "resize_reset_frame", full_path, None

            diff = ImageChops.difference(current_img, self._last_image)
            bbox = diff.getbbox()
            
            if not bbox:
                return "no_change", full_path, None
            
            # Simple heuristic: ignore negligible changes
            width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if width < 5 and height < 5:
                 return "negligible_change", full_path, bbox

            # Crop the changed area (with padding)
            padding = 50
            crop_box = (
                max(0, bbox[0] - padding),
                max(0, bbox[1] - padding),
                min(current_img.width, bbox[2] + padding),
                min(current_img.height, bbox[3] + padding)
            )
            
            diff_crop = current_img.crop(crop_box)
            diff_crop.convert("RGB").save(diff_path, "JPEG", quality=90)
            
            self._last_image = current_img
            return "diff_update", diff_path, crop_box
            
        except Exception as e:
            print(f"[VisionDiff] Error: {e}")
            current_img.convert("RGB").save(full_path)
            self._last_image = current_img
            return "error_fallback_full", full_path, None


def take_screenshot(app_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Takes a smart screenshot.
    
    STRATEGY:
    1. If app_name is provided: Try to find that specific window -> Capture ONLY that region.
    2. If no app_name or window not found: Capture Primary Monitor.
    
    This ensures we don't 'spread attention' to the whole desktop when focusing on one app.
    """
    try:
        manager = VisionDiffManager.get_instance()
        region: Union[Dict[str, int], Any] = None
        focus_id = "FULL_SCREEN"

        # 1. Try Surgical Window Capture
        if app_name:
            region = VisionFocusUtils.get_app_window_geometry(app_name)
            if region:
                focus_id = f"APP_{app_name}"
        
        # 2. Capture using MSS
        with mss.mss() as sct:
            if region:
                # Surgical capture
                sct_img = sct.grab(region)
            else:
                # Fallback to Primary Monitor (monitor 1)
                sct_img = sct.grab(sct.monitors[1])

            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        status, path, bbox = manager.process_screenshot(img, focus_context=focus_id)
        
        return {
            "tool": "take_screenshot",
            "status": "success",
            "path": path,
            "vision_mode": status,
            "focus_context": focus_id, # Tells LLM what it's looking at (Window or Desktop)
            "diff_bbox": bbox,
        }

    except Exception as e:
        err_str = str(e).lower()
        if "screen recording" in err_str or "access" in err_str:
             return {
                "tool": "take_screenshot",
                "status": "error",
                "error_type": "permission_required",
                "permission": "screen_recording",
                "error": "Permission denied. Please allow Screen Recording in System Settings."
            }
        
        # Fallback to legacy
        return _legacy_screencapture_full()


def capture_screen_region(x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    try:
        x_i = int(x)
        y_i = int(y)
        w_i = int(width)
        h_i = int(height)
        if w_i <= 0 or h_i <= 0:
            return {"tool": "capture_screen_region", "status": "error", "error": "Invalid region size"}

        region = {"top": y_i, "left": x_i, "width": w_i, "height": h_i}
        output_dir = os.path.expanduser("~/.antigravity/vision_cache")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        path = os.path.join(output_dir, f"region_{timestamp}.png")

        with mss.mss() as sct:
            sct_img = sct.grab(region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(path, format="PNG")

        return {
            "tool": "capture_screen_region",
            "status": "success",
            "path": path,
            "region": {"x": x_i, "y": y_i, "width": w_i, "height": h_i},
        }
    except Exception as e:
        err_str = str(e).lower()
        if "screen recording" in err_str or "access" in err_str:
            return {
                "tool": "capture_screen_region",
                "status": "error",
                "error_type": "permission_required",
                "permission": "screen_recording",
                "error": "Permission denied. Please allow Screen Recording in System Settings.",
            }
        return {"tool": "capture_screen_region", "status": "error", "error": str(e)}

def _legacy_screencapture_full():
    output_path = os.path.expanduser(f"~/Desktop/fallback_{int(time.time())}.jpg")
    try:
        subprocess.run(["screencapture", "-x", "-t", "jpg", output_path], check=True)
        return {"tool": "take_screenshot", "status": "success", "path": output_path, "vision_mode": "legacy_cli"}
    except Exception as e:
        return {"tool": "take_screenshot", "status": "error", "error": str(e)}

def take_burst_screenshot(app_name: Optional[str] = None, count: int = 3, interval: float = 0.3) -> Dict[str, Any]:
    """Takes multiple screenshots in a burst to capture blinking cursors/animations.
    
    Args:
        app_name: Optional application name to focus on
        count: Number of shots (default 3)
        interval: Seconds between shots (default 0.3)
    """
    try:
        paths = []
        for i in range(count):
            res = take_screenshot(app_name=app_name)
            if res.get("status") == "success":
                paths.append(res.get("path"))
            if i < count - 1:
                time.sleep(interval)
        
        return {
            "tool": "take_burst_screenshot",
            "status": "success",
            "paths": paths,
            "message": f"Captured {len(paths)} frames to detect changes (like blinking cursors)"
        }
    except Exception as e:
        return {"tool": "take_burst_screenshot", "status": "error", "error": str(e)}
