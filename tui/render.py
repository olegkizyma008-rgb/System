"""Rendering and log management for TUI.

Provides functions for:
- Log snapshot rendering with caching
- Agent messages snapshot rendering
- Log manipulation (reserve, replace, trim)
- Header, context, and status bar rendering
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from prompt_toolkit.data_structures import Point

from system_cli.state import state
from tui.messages import MessageBuffer, AgentType


# Locks and buffers
_logs_lock = threading.RLock()
_logs_need_trim: bool = False
_thread_log_override = threading.local()

_agent_messages_buffer = MessageBuffer(max_messages=1000)
_agent_messages_lock = threading.RLock()

# Render caches
_render_log_cache: Dict[str, Any] = {"ts": 0.0, "logs": [], "cursor": Point(x=0, y=0)}
_render_log_cache_ttl_s: float = 0.05

_render_agents_cache: Dict[str, Any] = {"ts": 0.0, "messages": [], "cursor": Point(x=0, y=0)}
_render_agents_cache_ttl_s: float = 0.05

# Style mapping
STYLE_MAP = {
    "info": "class:log.info",
    "user": "class:log.user",
    "action": "class:log.action",
    "error": "class:log.error",
    "tool_success": "class:log.tool.success",
    "tool_fail": "class:log.tool.fail",
    "tool_run": "class:log.tool.run",
}


def get_render_log_snapshot() -> Tuple[List[Tuple[str, str]], Point]:
    """Get cached log snapshot with cursor position."""
    global _logs_need_trim
    
    with _logs_lock:
        now = time.monotonic()
        try:
            ts = float(_render_log_cache.get("ts", 0.0))
            if (now - ts) < _render_log_cache_ttl_s:
                cached = _render_log_cache.get("logs") or []
                cached_cursor = _render_log_cache.get("cursor") or Point(x=0, y=0)
                try:
                    combined = "".join(str(text or "") for _, text in cached)
                    if combined:
                        parts = combined.split("\n")
                        actual_line_count = max(1, len(parts))
                        if combined.endswith("\n"):
                            actual_line_count = max(1, actual_line_count - 1)
                        valid_cursor_y = max(0, min(cached_cursor.y, actual_line_count - 1))
                        return (
                            list(cached),
                            Point(x=0, y=valid_cursor_y),
                        )
                    else:
                        return (list(cached), Point(x=0, y=0))
                except Exception:
                    pass
        except Exception:
            pass

        try:
            logs_snapshot: List[Tuple[str, str]] = list(state.logs)
        except Exception:
            logs_snapshot = []

    try:
        combined = "".join(str(text or "") for _, text in logs_snapshot)
    except Exception:
        combined = ""

    if not combined:
        line_count = 1
        last_line_y = 0
    else:
        parts = combined.split("\n")
        line_count = max(1, len(parts))
        last_line_y = max(0, line_count - 1)
        if combined.endswith("\n"):
            last_line_y = max(0, last_line_y - 1)

    try:
        state.ui_log_line_count = int(line_count)
    except Exception:
        state.ui_log_line_count = 1

    try:
        if getattr(state, "ui_log_follow", True):
            state.ui_log_cursor_y = int(last_line_y)
        else:
            state.ui_log_cursor_y = max(
                0,
                min(
                    int(getattr(state, "ui_log_cursor_y", 0)),
                    max(0, int(getattr(state, "ui_log_line_count", 1)) - 1),
                ),
            )
            if state.ui_log_cursor_y >= max(0, int(getattr(state, "ui_log_line_count", 1)) - 1):
                state.ui_log_follow = True
    except Exception:
        state.ui_log_follow = True
        state.ui_log_cursor_y = int(last_line_y)

    cursor = Point(x=0, y=max(0, min(int(getattr(state, "ui_log_cursor_y", 0)), max(0, int(getattr(state, "ui_log_line_count", 1)) - 1))))

    with _logs_lock:
        _render_log_cache["ts"] = now
        _render_log_cache["logs"] = logs_snapshot
        _render_log_cache["cursor"] = cursor
        return logs_snapshot, cursor


def get_render_agents_snapshot() -> Tuple[List[Tuple[str, str]], Point]:
    """Get cached agent messages snapshot with cursor position."""
    with _agent_messages_lock:
        now = time.monotonic()
        try:
            ts = float(_render_agents_cache.get("ts", 0.0))
            if (now - ts) < _render_agents_cache_ttl_s:
                cached = _render_agents_cache.get("messages") or []
                cached_cursor = _render_agents_cache.get("cursor") or Point(x=0, y=0)
                try:
                    combined = "".join(str(text or "") for _, text in cached)
                    if combined:
                        parts = combined.split("\n")
                        actual_line_count = max(1, len(parts))
                        if combined.endswith("\n"):
                            actual_line_count = max(1, actual_line_count - 1)
                        valid_cursor_y = max(0, min(cached_cursor.y, actual_line_count - 1))
                        return (
                            list(cached),
                            Point(x=0, y=valid_cursor_y),
                        )
                    else:
                        return (list(cached), Point(x=0, y=0))
                except Exception:
                    pass
        except Exception:
            pass

        try:
            formatted: List[Tuple[str, str]] = list(_agent_messages_buffer.get_formatted() or [])
        except Exception:
            formatted = []

        try:
            combined = "".join(str(text or "") for _, text in formatted)
        except Exception:
            combined = ""

        if not combined:
            line_count = 1
            last_line_y = 0
        else:
            parts = combined.split("\n")
            line_count = max(1, len(parts))
            last_line_y = max(0, line_count - 1)
            if combined.endswith("\n"):
                last_line_y = max(0, last_line_y - 1)

        try:
            state.ui_agents_line_count = int(line_count)
        except Exception:
            state.ui_agents_line_count = 1

        try:
            if getattr(state, "ui_agents_follow", True):
                state.ui_agents_cursor_y = int(last_line_y)
            else:
                state.ui_agents_cursor_y = max(
                    0,
                    min(
                        int(getattr(state, "ui_agents_cursor_y", 0)),
                        max(0, int(getattr(state, "ui_agents_line_count", 1)) - 1),
                    ),
                )
                if state.ui_agents_cursor_y >= max(0, int(getattr(state, "ui_agents_line_count", 1)) - 1):
                    state.ui_agents_follow = True
        except Exception:
            state.ui_agents_follow = True
            state.ui_agents_cursor_y = int(last_line_y)

        cursor = Point(
            x=0,
            y=max(0, min(int(getattr(state, "ui_agents_cursor_y", 0)), max(0, int(getattr(state, "ui_agents_line_count", 1)) - 1))),
        )

        _render_agents_cache["ts"] = now
        _render_agents_cache["messages"] = formatted
        _render_agents_cache["cursor"] = cursor
        return formatted, cursor


def trim_logs_if_needed() -> None:
    """Trim logs if buffer exceeds limit and agent is not processing."""
    global _logs_need_trim
    with _logs_lock:
        if not _logs_need_trim:
            return
        if getattr(state, "agent_processing", False):
            return
        if len(state.logs) > 2000:
            state.logs = state.logs[-1500:]
        _logs_need_trim = False


def log_replace_last(text: str, category: str = "info") -> None:
    """Replace last log entry."""
    with _logs_lock:
        if not state.logs:
            state.logs.append((STYLE_MAP.get(category, "class:log.info"), f"{text}\n"))
            return
        state.logs[-1] = (STYLE_MAP.get(category, "class:log.info"), f"{text}\n")


def log_reserve_line(category: str = "info") -> int:
    """Reserve a new log line and return its index."""
    global _logs_need_trim
    with _logs_lock:
        state.logs.append((STYLE_MAP.get(category, "class:log.info"), "\n"))
        if len(state.logs) > 2000:
            if getattr(state, "agent_processing", False):
                _logs_need_trim = True
            else:
                state.logs = state.logs[-1500:]
        return max(0, len(state.logs) - 1)


def log_replace_at(index: int, text: str, category: str = "info") -> None:
    """Replace log entry at specific index."""
    with _logs_lock:
        if index < 0 or index >= len(state.logs):
            state.logs.append((STYLE_MAP.get(category, "class:log.info"), f"{text}\n"))
        else:
            state.logs[index] = (STYLE_MAP.get(category, "class:log.info"), f"{text}\n")


def log(text: str, category: str = "info") -> None:
    """Main log function - appends to log buffer."""
    global _logs_need_trim
    
    # Log to root file (Left Screen)
    try:
        import logging
        logging.getLogger("system_cli.left").info(f"[{category.upper()}] {text}")
    except Exception:
        pass

    override = getattr(_thread_log_override, "handler", None)
    if callable(override):
        try:
            override(text, category)
        except Exception:
            pass
        return
    with _logs_lock:
        state.logs.append((STYLE_MAP.get(category, "class:log.info"), f"{text}\n"))
        if len(state.logs) > 2000:
            if getattr(state, "agent_processing", False):
                _logs_need_trim = True
            else:
                state.logs = state.logs[-1500:]


def log_agent_message(agent: AgentType, text: str) -> None:
    """Log agent message to clean display panel."""
    # Log to root file (Right Screen)
    try:
        import logging
        logging.getLogger("system_cli.right").info(f"[{agent.value}] {text}")
    except Exception:
        pass

    with _agent_messages_lock:
        try:
            _agent_messages_buffer.upsert_stream(agent, text, is_technical=False)
        except Exception:
            _agent_messages_buffer.add(agent, text, is_technical=False)
    
    # Update UI
    try:
        from tui.layout import force_ui_update
        force_ui_update()
    except Exception:
        pass


def get_logs() -> List[Tuple[str, str]]:
    """Get formatted logs for display."""
    try:
        logs_snapshot, _ = get_render_log_snapshot()
        return logs_snapshot if logs_snapshot else []
    except Exception:
        return []


def get_agent_messages() -> List[Tuple[str, str]]:
    """Get formatted agent messages for clean display panel."""
    try:
        formatted, _ = get_render_agents_snapshot()
        return formatted if formatted else []
    except Exception:
        return []


def get_agent_cursor_position() -> Point:
    """Get cursor position for agent messages panel."""
    try:
        _, cursor = get_render_agents_snapshot()
        return cursor
    except Exception:
        return Point(x=0, y=0)


def get_log_cursor_position() -> Point:
    """Get cursor position for log panel."""
    try:
        _, cursor = get_render_log_snapshot()
        return cursor
    except Exception:
        return Point(x=0, y=0)


def set_thread_log_override(handler: Optional[Callable[[str, str], None]]) -> None:
    """Set thread-local log override handler."""
    _thread_log_override.handler = handler


def clear_thread_log_override() -> None:
    """Clear thread-local log override handler."""
    _thread_log_override.handler = None


def get_agent_messages_buffer() -> MessageBuffer:
    """Get agent messages buffer (for external access)."""
    return _agent_messages_buffer


def get_agent_messages_lock() -> threading.RLock:
    """Get agent messages lock (for external access)."""
    return _agent_messages_lock


def get_logs_lock() -> threading.RLock:
    """Get logs lock (for external access)."""
    return _logs_lock



def get_header() -> List[Tuple[str, str]]:
    """Generate header content for TUI."""
    from i18n import localization
    primary = localization.primary
    active_locales = " ".join(localization.selected)
    selected_editor = state.selected_editor or "-"
    ui_lang = str(getattr(state, "ui_lang", "") or "").strip() or "-"
    chat_lang = str(getattr(state, "chat_lang", "") or "").strip() or "-"
    scroll_target = str(getattr(state, "ui_scroll_target", "log") or "log").strip().lower() or "log"

    return [
        ("class:header", " "),
        ("class:header.title", "SYSTEM CLI"),
        ("class:header.sep", " | "),
        ("class:header.label", "Editor: "),
        ("class:header.value", selected_editor),
        ("class:header.sep", " | "),
        ("class:header.label", "Region: "),
        ("class:header.value", f"{primary} ({active_locales or 'none'})"),
        ("class:header.sep", " | "),
        ("class:header.label", "Lang: "),
        ("class:header.value", f"ui={ui_lang} chat={chat_lang}"),
        ("class:header.sep", " | "),
        ("class:header.label", "Scroll: "),
        ("class:header.value", "АГЕНТИ" if scroll_target == "agents" else "LOG"),
        ("class:header", " "),
    ]


def get_context() -> List[Tuple[str, str]]:
    """Generate context panel content for TUI."""
    from tui.cli_paths import CLEANUP_CONFIG_PATH, LOCALIZATION_CONFIG_PATH
    result: List[Tuple[str, str]] = []

    result.append(("class:context.label", " Cleanup config: "))
    result.append(("class:context.value", f"{CLEANUP_CONFIG_PATH}\n"))
    result.append(("class:context.label", " Locales config: "))
    result.append(("class:context.value", f"{LOCALIZATION_CONFIG_PATH}\n\n"))

    result.append(("class:context.title", " Commands\n"))
    result.append(("class:context.label", " /help\n"))
    result.append(("class:context.label", " /run <editor> [--dry]\n"))
    result.append(("class:context.label", " /modules <editor>\n"))
    result.append(("class:context.label", " /enable <editor> <id> | /disable <editor> <id>\n"))
    result.append(("class:context.label", " /install <editor>\n"))
    result.append(("class:context.label", " /smart <editor> <query...>\n"))
    result.append(("class:context.label", " /ask <question...>\n"))
    result.append(("class:context.label", " /locales ua us eu\n"))
    result.append(("class:context.label", " /monitor status|start|stop|source <watchdog|fs_usage|opensnoop>|sudo <on|off>\n"))
    result.append(("class:context.label", " /monitor-targets list|add <key>|remove <key>|clear|save\n"))
    result.append(("class:context.label", " /llm status|set provider <copilot>|set main <model>|set vision <model>\n"))
    result.append(("class:context.label", " /theme status|set <monaco|dracula|nord|gruvbox>\n"))
    result.append(("class:context.label", " /lang status|set ui <code>|set chat <code>\n"))
    result.append(("class:context.label", " /streaming status|on|off\n"))
    result.append(("class:context.label", " /gui_mode status|on|off|auto\n"))
    result.append(("class:context.label", " /trinity <task>\n"))

    return result


def get_status() -> List[Tuple[str, str]]:
    """Generate status bar content for TUI."""
    from system_cli.state import MenuLevel
    if state.menu_level != MenuLevel.NONE:
        mode_indicator = [("class:status.menu", " MENU "), ("class:status", " ")]
    else:
        if getattr(state, "agent_paused", False):
            mode_indicator = [("class:status.error", " PAUSED "), ("class:status", " ")]
        elif state.agent_processing:
            mode_indicator = [("class:status.processing", " PROCESSING "), ("class:status", " ")]
        else:
            mode_indicator = [("class:status.chat", " INPUT "), ("class:status", " ")]

    monitor_tag = f"MON:{'ON' if state.monitor_active else 'OFF'}:{state.monitor_source}"

    scroll_target = str(getattr(state, "ui_scroll_target", "log") or "log").strip().lower() or "log"
    if scroll_target == "agents":
        follow = bool(getattr(state, "ui_agents_follow", True))
        follow_tag = f"AGENTS:{'FOLLOW' if follow else 'FREE'}"
    else:
        follow = bool(getattr(state, "ui_log_follow", True))
        follow_tag = f"LOG:{'FOLLOW' if follow else 'FREE'}"

    paused_hint: list[tuple[str, str]] = []
    if getattr(state, "agent_paused", False):
        paused_hint = [("class:status", " | "), ("class:status.key", "Type: /resume")]

    return mode_indicator + [
        ("class:status.ready", f" {state.status} "),
        ("class:status", " "),
        ("class:status.key", monitor_tag),
        ("class:status", " | "),
        ("class:status.key", follow_tag),
        ("class:status", " | "),
        ("class:status.key", "F2: Menu"),
        ("class:status", " | "),
        ("class:status.key", "Ctrl+C: Quit"),
    ] + paused_hint


# Backward compatibility aliases
_get_render_log_snapshot = get_render_log_snapshot
_get_render_agents_snapshot = get_render_agents_snapshot
_trim_logs_if_needed = trim_logs_if_needed
_log_replace_last = log_replace_last
_log_reserve_line = log_reserve_line
_log_replace_at = log_replace_at
_get_header = get_header
_get_context = get_context
_get_status = get_status
