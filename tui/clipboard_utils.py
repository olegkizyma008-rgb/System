"""Clipboard utilities for TUI.

Provides functions for:
- Copying content to clipboard (Mac pbcopy, with fallback to xclip/xsel on Linux)
- Auto-copy on text selection
- Tracking clipboard state and history
"""

from __future__ import annotations

import subprocess
import threading
from typing import Optional, Callable

_clipboard_lock = threading.Lock()
_last_copied_content: Optional[str] = None
_last_copied_timestamp: float = 0.0


def copy_to_clipboard(content: str, log_callback: Optional[Callable[[str, str], None]] = None) -> bool:
    """Copy content to clipboard using platform-specific method.
    
    Args:
        content: Text to copy
        log_callback: Optional callback for logging (called with (message, level))
        
    Returns:
        True if successful, False otherwise
    """
    global _last_copied_content, _last_copied_timestamp
    
    if not content:
        return False
    
    with _clipboard_lock:
        try:
            # Try pbcopy (macOS)
            try:
                process = subprocess.Popen(
                    ['pbcopy'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False
                )
                process.communicate(input=content.encode('utf-8'), timeout=2)
                if process.returncode == 0:
                    _last_copied_content = content
                    import time
                    _last_copied_timestamp = time.time()
                    if log_callback:
                        log_callback(
                            f"Скопійовано {len(content)} символів до буфера обміну",
                            "action"
                        )
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
            
            # Try xclip (Linux)
            try:
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False
                )
                process.communicate(input=content.encode('utf-8'), timeout=2)
                if process.returncode == 0:
                    _last_copied_content = content
                    import time
                    _last_copied_timestamp = time.time()
                    if log_callback:
                        log_callback(
                            f"Скопійовано {len(content)} символів до буфера обміну",
                            "action"
                        )
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
            
            # Try xsel (Linux fallback)
            try:
                process = subprocess.Popen(
                    ['xsel', '-b', '-i'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False
                )
                process.communicate(input=content.encode('utf-8'), timeout=2)
                if process.returncode == 0:
                    _last_copied_content = content
                    import time
                    _last_copied_timestamp = time.time()
                    if log_callback:
                        log_callback(
                            f"Скопійовано {len(content)} символів до буфера обміну",
                            "action"
                        )
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
            
            # If all methods fail, log error
            if log_callback:
                log_callback(
                    "Помилка: не вдалося скопіювати (pbcopy/xclip/xsel не доступні)",
                    "error"
                )
            return False
            
        except Exception as e:
            if log_callback:
                log_callback(f"Помилка копіювання: {str(e)}", "error")
            return False


def get_last_copied_content() -> Optional[str]:
    """Get the last content that was copied."""
    with _clipboard_lock:
        return _last_copied_content


def get_clipboard_stats() -> dict:
    """Get clipboard operation statistics."""
    with _clipboard_lock:
        return {
            "last_content_length": len(_last_copied_content) if _last_copied_content else 0,
            "last_copied_timestamp": _last_copied_timestamp,
        }
