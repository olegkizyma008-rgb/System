"""Text selection tracking and auto-copy for TUI.

Provides mouse selection detection and automatic clipboard operations
similar to vibe CLI behavior.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime, timedelta

_selection_lock = threading.Lock()
_last_selection_time: Optional[datetime] = None
_current_selection: Optional[str] = None
_selection_history: list[str] = []

# Configuration
SELECTION_AUTO_COPY_ENABLED = True
SELECTION_DEBOUNCE_MS = 100  # Minimum time between consecutive copy operations
SELECTION_HISTORY_MAX = 50


@dataclass
class SelectionState:
    """Represents current text selection state."""
    start_pos: int = 0
    end_pos: int = 0
    selected_text: str = ""
    timestamp: datetime = None
    window_name: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def has_content(self) -> bool:
        """Check if selection has content."""
        return bool(self.selected_text and len(self.selected_text) > 0)
    
    def is_valid(self) -> bool:
        """Check if selection is valid."""
        return self.start_pos < self.end_pos and self.has_content()


def extract_selection_from_content(
    content: list[Tuple[str, str]],
    start_pos: int,
    end_pos: int
) -> str:
    """Extract selected text from formatted content.
    
    Args:
        content: List of (style, text) tuples
        start_pos: Start position in the combined text
        end_pos: End position in the combined text
        
    Returns:
        Selected text without formatting
    """
    if not content or start_pos >= end_pos:
        return ""
    
    try:
        # Flatten content to get plain text
        plain_text = "".join(str(t or "") for _, t in content)
        
        # Extract selection
        selected = plain_text[start_pos:end_pos]
        return selected.strip()
    except Exception:
        return ""


def on_text_selection(
    selection_state: SelectionState,
    auto_copy_callback=None
) -> bool:
    """Handle text selection event.
    
    Args:
        selection_state: The current selection state
        auto_copy_callback: Optional callback to copy text (receives text content)
        
    Returns:
        True if selection was processed and copied
    """
    global _last_selection_time, _current_selection, _selection_history
    
    if not SELECTION_AUTO_COPY_ENABLED or not selection_state.is_valid():
        return False
    
    with _selection_lock:
        now = datetime.now()
        
        # Check debounce
        if _last_selection_time is not None:
            elapsed_ms = (now - _last_selection_time).total_seconds() * 1000
            if elapsed_ms < SELECTION_DEBOUNCE_MS:
                return False
        
        # Skip if same text was just copied
        if _current_selection == selection_state.selected_text:
            return False
        
        # Update state
        _last_selection_time = now
        _current_selection = selection_state.selected_text
        
        # Add to history
        if selection_state.selected_text not in _selection_history:
            _selection_history.append(selection_state.selected_text)
            if len(_selection_history) > SELECTION_HISTORY_MAX:
                _selection_history.pop(0)
        
        # Auto-copy if callback provided
        if auto_copy_callback and selection_state.has_content():
            try:
                auto_copy_callback(selection_state.selected_text)
                return True
            except Exception:
                return False
    
    return False


def clear_selection() -> None:
    """Clear current selection state."""
    global _current_selection
    with _selection_lock:
        _current_selection = None


def get_selection_history() -> list[str]:
    """Get list of recently selected texts."""
    with _selection_lock:
        return _selection_history.copy()


def set_auto_copy_enabled(enabled: bool) -> None:
    """Enable or disable auto-copy on selection."""
    global SELECTION_AUTO_COPY_ENABLED
    SELECTION_AUTO_COPY_ENABLED = enabled


def get_selection_stats() -> dict:
    """Get selection tracking statistics."""
    with _selection_lock:
        return {
            "auto_copy_enabled": SELECTION_AUTO_COPY_ENABLED,
            "current_selection_length": len(_current_selection) if _current_selection else 0,
            "history_count": len(_selection_history),
            "last_selection_time": _last_selection_time.isoformat() if _last_selection_time else None,
        }
