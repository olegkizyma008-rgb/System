"""macOS Permissions Manager

Handles permission checks and requests for automation, recording, and accessibility.
Provides clear feedback and guidance for users.
"""

import subprocess
import ctypes
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class PermissionStatus:
    """Status of a single permission"""
    name: str
    granted: bool
    required: bool = False
    error_message: Optional[str] = None
    settings_url: Optional[str] = None


class PermissionsManager:
    """Manages macOS permissions for automation and recording"""
    
    PRIVACY_URLS = {
        "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        "automation": "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation",
        "full_disk_access": "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
        "screen_recording": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
        "files_and_folders": "x-apple.systempreferences:com.apple.preference.security?Privacy_FilesAndFolders",
    }
    
    def __init__(self):
        self.statuses: Dict[str, PermissionStatus] = {}
    
    def check_accessibility(self) -> PermissionStatus:
        """Check Accessibility permission status"""
        if sys.platform != "darwin":
            return PermissionStatus("accessibility", True, settings_url=None)
        
        try:
            app = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
            fn = getattr(app, "AXIsProcessTrusted", None)
            if fn is None:
                return PermissionStatus(
                    "accessibility",
                    False,
                    error_message="Cannot check accessibility permission",
                    settings_url=self.PRIVACY_URLS["accessibility"]
                )
            
            fn.restype = ctypes.c_bool
            fn.argtypes = []
            granted = bool(fn())
            
            self.statuses["accessibility"] = PermissionStatus(
                "accessibility",
                granted,
                settings_url=self.PRIVACY_URLS["accessibility"] if not granted else None
            )
            return self.statuses["accessibility"]
        except Exception as e:
            status = PermissionStatus(
                "accessibility",
                False,
                error_message=str(e),
                settings_url=self.PRIVACY_URLS["accessibility"]
            )
            self.statuses["accessibility"] = status
            return status
    
    def check_screen_recording(self) -> PermissionStatus:
        """Check Screen Recording permission status"""
        if sys.platform != "darwin":
            return PermissionStatus("screen_recording", True, settings_url=None)
        
        try:
            cg = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
            )
            fn = getattr(cg, "CGPreflightScreenCaptureAccess", None)
            if fn is None:
                return PermissionStatus(
                    "screen_recording",
                    False,
                    error_message="Cannot check screen recording permission",
                    settings_url=self.PRIVACY_URLS["screen_recording"]
                )
            
            fn.restype = ctypes.c_bool
            fn.argtypes = []
            granted = bool(fn())
            
            self.statuses["screen_recording"] = PermissionStatus(
                "screen_recording",
                granted,
                settings_url=self.PRIVACY_URLS["screen_recording"] if not granted else None
            )
            return self.statuses["screen_recording"]
        except Exception as e:
            status = PermissionStatus(
                "screen_recording",
                False,
                error_message=str(e),
                settings_url=self.PRIVACY_URLS["screen_recording"]
            )
            self.statuses["screen_recording"] = status
            return status
    
    def check_automation(self) -> PermissionStatus:
        """Check Automation permission status"""
        if sys.platform != "darwin":
            return PermissionStatus("automation", True, settings_url=None)
        
        script = 'tell application "System Events" to count of processes'
        try:
            proc = subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=2.5,
            )
            
            if proc.returncode == 0:
                self.statuses["automation"] = PermissionStatus("automation", True)
                return self.statuses["automation"]
            
            err = (proc.stderr or "") + "\n" + (proc.stdout or "")
            low = err.lower()
            
            if any(phrase in low for phrase in ["not authorised", "not authorized", "not allowed", "permission"]):
                status = PermissionStatus(
                    "automation",
                    False,
                    error_message="Automation permission denied",
                    settings_url=self.PRIVACY_URLS["automation"]
                )
                self.statuses["automation"] = status
                return status
            
            status = PermissionStatus(
                "automation",
                False,
                error_message=err[:200],
                settings_url=self.PRIVACY_URLS["automation"]
            )
            self.statuses["automation"] = status
            return status
        except subprocess.TimeoutExpired:
            status = PermissionStatus(
                "automation",
                False,
                error_message="Automation check timeout",
                settings_url=self.PRIVACY_URLS["automation"]
            )
            self.statuses["automation"] = status
            return status
        except Exception as e:
            status = PermissionStatus(
                "automation",
                False,
                error_message=str(e),
                settings_url=self.PRIVACY_URLS["automation"]
            )
            self.statuses["automation"] = status
            return status
    
    def request_permission(self, permission: str) -> bool:
        """Request a permission from the user
        
        Args:
            permission: Permission name (accessibility, screen_recording, automation)
            
        Returns:
            True if permission was granted
        """
        if sys.platform != "darwin":
            return True
        
        if permission == "accessibility":
            return self._request_accessibility()
        elif permission == "screen_recording":
            return self._request_screen_recording()
        elif permission == "automation":
            return self._request_automation()
        
        return False
    
    def _request_accessibility(self) -> bool:
        """Request accessibility permission"""
        try:
            app = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
            cf = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
            )
            
            fn = getattr(app, "AXIsProcessTrustedWithOptions", None)
            if fn is None:
                return False
            
            key = ctypes.c_void_p.in_dll(app, "kAXTrustedCheckOptionPrompt")
            val = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")
            
            cf.CFDictionaryCreate.restype = ctypes.c_void_p
            cf.CFDictionaryCreate.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(ctypes.c_void_p), ctypes.c_long,
                ctypes.c_void_p, ctypes.c_void_p,
            ]
            cf.CFRelease.restype = None
            cf.CFRelease.argtypes = [ctypes.c_void_p]
            
            keys = (ctypes.c_void_p * 1)(key)
            vals = (ctypes.c_void_p * 1)(val)
            d = cf.CFDictionaryCreate(None, keys, vals, 1, None, None)
            
            try:
                fn.restype = ctypes.c_bool
                fn.argtypes = [ctypes.c_void_p]
                return bool(fn(ctypes.c_void_p(d)))
            finally:
                try:
                    if d:
                        cf.CFRelease(ctypes.c_void_p(d))
                except Exception:
                    pass
        except Exception:
            return False
    
    def _request_screen_recording(self) -> bool:
        """Request screen recording permission"""
        try:
            cg = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
            )
            fn = getattr(cg, "CGRequestScreenCaptureAccess", None)
            if fn is None:
                return False
            
            fn.restype = ctypes.c_bool
            fn.argtypes = []
            return bool(fn())
        except Exception:
            return False
    
    def _request_automation(self) -> bool:
        """Request automation permission"""
        script = 'tell application "System Events" to count of processes'
        try:
            subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=2.5,
            )
            return True
        except Exception:
            return False
    
    def open_settings(self, permission: str) -> bool:
        """Open System Settings to the permission pane
        
        Args:
            permission: Permission name
            
        Returns:
            True if settings were opened
        """
        url = self.PRIVACY_URLS.get(permission)
        if not url:
            return False
        
        try:
            subprocess.run(["/usr/bin/open", url], capture_output=True, text=True)
            return True
        except Exception:
            return False
    
    def check_all(self) -> Dict[str, PermissionStatus]:
        """Check all permissions
        
        Returns:
            Dictionary of permission statuses
        """
        self.check_accessibility()
        self.check_screen_recording()
        self.check_automation()
        return self.statuses
    
    def get_missing_permissions(self, required: List[str]) -> List[str]:
        """Get list of missing required permissions
        
        Args:
            required: List of required permission names
            
        Returns:
            List of missing permission names
        """
        missing = []
        for perm in required:
            if perm == "accessibility":
                status = self.check_accessibility()
            elif perm == "screen_recording":
                status = self.check_screen_recording()
            elif perm == "automation":
                status = self.check_automation()
            else:
                continue
            
            if not status.granted:
                missing.append(perm)
        
        return missing
    
    def get_permission_help_text(self, lang: str = "en") -> str:
        """Get help text for permissions
        
        Args:
            lang: Language code (en, uk)
            
        Returns:
            Help text
        """
        if lang == "uk":
            return """Дозволи macOS для Recorder + Automation:

1) Accessibility (Доступність):
   System Settings → Privacy & Security → Accessibility
   Увімкни для застосунку, з якого запускаєш SYSTEM CLI
   (Terminal / iTerm / VS Code / Windsurf)

2) Screen Recording (Запис екрана):
   System Settings → Privacy & Security → Screen Recording
   Увімкни для того ж застосунку (для скріншотів у записі)

3) Automation (Автоматизація):
   System Settings → Privacy & Security → Automation
   Дозволь застосунку керувати: "System Events"
   (і за потреби іншими застосунками)

4) Якщо GUI-автоматизація не працює:
   • Перезапусти застосунок-джерело після видачі дозволів
   • Переконайся, що дозволи видані саме для твого терміналу/IDE
   • Перевір, чи не заблокований застосунок у Gatekeeper
"""
        else:
            return """macOS permissions for Recorder + Automation:

1) Accessibility:
   System Settings → Privacy & Security → Accessibility
   Enable for the app running SYSTEM CLI
   (Terminal / iTerm / VS Code / Windsurf)

2) Screen Recording:
   System Settings → Privacy & Security → Screen Recording
   Enable for the same app (for screenshots during recording)

3) Automation:
   System Settings → Privacy & Security → Automation
   Allow the app to control: "System Events"
   (and other apps if needed)

4) If GUI automation doesn't work:
   • Restart the source app after granting permissions
   • Make sure permissions are granted for your specific terminal/IDE
   • Check if the app is blocked by Gatekeeper
"""


def open_system_settings_privacy(permission: str) -> Dict[str, Any]:
    """Open System Settings to the privacy pane for a specific permission
    
    Args:
        permission: Permission name (accessibility, screen_recording, etc.)
        
    Returns:
        Dict with status and url
    """
    perm = str(permission or "").strip().lower() or "accessibility"
    pm = PermissionsManager()
    url = pm.PRIVACY_URLS.get(perm) or pm.PRIVACY_URLS["accessibility"]
    
    try:
        proc = subprocess.run(["open", url], capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                "tool": "open_system_settings_privacy", 
                "status": "error", 
                "permission": perm, 
                "error": (proc.stderr or "").strip() or "Failed to open System Settings",
                "url": url
            }
        return {"tool": "open_system_settings_privacy", "status": "success", "permission": perm, "url": url}
    except Exception as e:
        return {"tool": "open_system_settings_privacy", "status": "error", "permission": perm, "error": str(e), "url": url}

def create_permissions_manager() -> PermissionsManager:
    """Factory function to create a permissions manager
    
    Returns:
        PermissionsManager instance
    """
    return PermissionsManager()
