"""Desktop Tools Module

Provides tools for inspecting windows, monitors, and managing clipboard state using Quartz and AppKit.
"""

import Quartz
import AppKit
from typing import Dict, Any, List, Optional

def get_monitors_info() -> List[Dict[str, Any]]:
    """Get information about connected displays
    
    Returns:
        List of monitor dictionaries with ID, resolution, and position.
    """
    monitors = []
    # Get active display list
    (err, ids, count) = Quartz.CGGetActiveDisplayList(32, None, None)
    if err != 0:
        return [{"error": f"CGGetActiveDisplayList failed with error {err}"}]
        
    ids = list(ids) # tuple to list
    
    for display_id in ids:
        bounds = Quartz.CGDisplayBounds(display_id)
        is_main = Quartz.CGDisplayIsMain(display_id)
        
        monitors.append({
            "id": display_id,
            "is_main": bool(is_main),
            "width": int(bounds.size.width),
            "height": int(bounds.size.height),
            "x": int(bounds.origin.x),
            "y": int(bounds.origin.y),
        })
        
    return monitors

def get_open_windows(on_screen_only: bool = True) -> List[Dict[str, Any]]:
    """Get list of open windows
    
    Args:
        on_screen_only: If True, only returns windows that are currently on screen
        
    Returns:
        List of window info dictionaries
    """
    options = Quartz.kCGWindowListOptionOnScreenOnly if on_screen_only else Quartz.kCGWindowListOptionAll
    options |= Quartz.kCGWindowListExcludeDesktopElements
    
    window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
    
    results = []
    for w in window_list:
        # Filter out system windows or tiny overlays if needed, keeping it raw for now but cleaner
        layer = w.get('kCGWindowLayer', 0)
        if layer != 0: # Usually layer 0 is normal apps
            continue
            
        owner_name = w.get('kCGWindowOwnerName', '')
        name = w.get('kCGWindowName', '')
        bounds = w.get('kCGWindowBounds', {})
        pid = w.get('kCGWindowOwnerPID', 0)
        
        results.append({
            "app": owner_name,
            "title": name,
            "pid": pid,
            "x": int(bounds.get('X', 0)),
            "y": int(bounds.get('Y', 0)),
            "width": int(bounds.get('Width', 0)),
            "height": int(bounds.get('Height', 0)),
            "id": w.get('kCGWindowNumber', 0)
        })
        
    return results

def get_clipboard() -> Dict[str, Any]:
    """Get text content from clipboard
    
    Returns:
        Dict with status and content
    """
    try:
        pb = AppKit.NSPasteboard.generalPasteboard()
        content = pb.stringForType_(AppKit.NSPasteboardTypeString)
        return {
            "tool": "get_clipboard",
            "status": "success",
            "content": str(content) if content else ""
        }
    except Exception as e:
        return {
            "tool": "get_clipboard",
            "status": "error",
            "error": str(e)
        }

def set_clipboard(text: str) -> Dict[str, Any]:
    """Set text content to clipboard
    
    Args:
        text: Content to copy
        
    Returns:
        Dict with status
    """
    try:
        pb = AppKit.NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, AppKit.NSPasteboardTypeString)
        return {
            "tool": "set_clipboard",
            "status": "success",
            "length": len(text)
        }
    except Exception as e:
        return {
            "tool": "set_clipboard",
            "status": "error",
            "error": str(e)
        }
