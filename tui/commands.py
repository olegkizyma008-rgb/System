"""Command handling for TUI.

Provides:
- Agent pause state management
- Input prompt generation
- Command parsing utilities
"""

from __future__ import annotations

import threading
from typing import Optional, Tuple

from system_cli.state import state


def clear_agent_pause_state() -> None:
    """Clear agent pause state."""
    state.agent_paused = False
    state.agent_pause_permission = None
    state.agent_pause_message = None
    state.agent_pause_pending_text = None


def set_agent_pause(*, pending_text: str, permission: str, message: str) -> None:
    """Set agent pause state with pending command."""
    state.agent_paused = True
    state.agent_pause_permission = str(permission or "").strip() or None
    state.agent_pause_message = str(message or "").strip() or None
    state.agent_pause_pending_text = str(pending_text or "").strip() or None


def get_input_prompt() -> str:
    """Get the input prompt string based on current state."""
    from i18n import tr
    
    if getattr(state, "recording_analysis_waiting", False):
        rl = str(getattr(state, "recording_analysis_name", "") or "").strip() or "recording"
        return f"[{rl}] > "

    if getattr(state, "agent_paused", False):
        perm = str(getattr(state, "agent_pause_permission", "") or "").strip()
        if perm == "shell":
            return tr("prompt.confirm_shell") + " "
        if perm == "applescript":
            return tr("prompt.confirm_applescript") + " "
        if perm == "gui":
            return tr("prompt.confirm_gui") + " "
        if perm == "run":
            return tr("prompt.confirm_run") + " "
        return tr("prompt.paused") + " "

    try:
        ml = state.menu_level
        from system_cli.state import MenuLevel
        if ml != MenuLevel.NONE:
            return ""
    except Exception:
        pass

    return tr("prompt.default") + " "


def get_prompt_width() -> int:
    """Get the width of the current prompt in characters."""
    return len(get_input_prompt())


def parse_command(text: str) -> Tuple[str, list]:
    """Parse command text into command name and arguments."""
    parts = str(text or "").strip().split()
    if not parts:
        return "", []
    command = parts[0].lower().strip()
    args = parts[1:]
    return command, args


def is_command(text: str) -> bool:
    """Check if text is a slash command."""
    return str(text or "").strip().startswith("/")



def resume_paused_agent() -> None:
    """Resume a paused agent session."""
    if not state.agent_paused:
        return
    
    from tui.render import log
    text = str(state.agent_pause_pending_text or "").strip()
    msg = str(state.agent_pause_message or "").strip()
    
    log(f"Resuming agent with: {text}", "action")
    clear_agent_pause_state()
    
    # Trigger graph task again with the same text
    from tui.agents import run_graph_agent_task
    import threading
    threading.Thread(
        target=run_graph_agent_task,
        args=(text,),
        kwargs={
            "allow_file_write": True,
            "allow_shell": True,
            "allow_applescript": True,
            "allow_gui": True,
            "allow_shortcuts": True,
        },
        daemon=True,
    ).start()

def handle_input(buff: Any) -> None:
    """Handle user input from the TUI buffer."""
    from tui.render import log
    
    raw = str(getattr(buff, "text", "") or "")
    text = raw.strip()
    buff.text = ""

    if getattr(state, "recording_analysis_waiting", False):
        from tui.recordings import recordings_resolve_last_dir, recordings_read_meta, recordings_ensure_meta_name, start_recording_analysis
        rec_dir = str(getattr(state, "recording_analysis_dir", "") or "").strip() or recordings_resolve_last_dir()
        meta = recordings_read_meta(rec_dir) if rec_dir else {}
        name = str(getattr(state, "recording_analysis_name", "") or "").strip() or str(meta.get("name") or "").strip() or recordings_ensure_meta_name(rec_dir)
        state.recording_analysis_waiting = False
        state.recording_analysis_dir = None
        state.recording_analysis_name = None
        if not rec_dir:
            log("Немає останнього запису", "error")
            return
        start_recording_analysis(rec_dir=rec_dir, name=name, user_context=text)
        if text:
            log(text, "user")
        return

    if not text:
        return

    if getattr(state, "agent_paused", False) and not text.lower().startswith(("/resume", "/help", "/h")):
        log(str(getattr(state, "agent_pause_message", "") or "Стан паузи. Дай дозвіл і введи /resume."), "error")
        return

    if is_command(text):
        handle_command(text)
        return

    # Default to trinity task
    handle_command(f"/task {text}")

def handle_command(cmd: str, wait: bool = False) -> None:
    """Handle a slash command from the user.
    
    Args:
        cmd: The command string.
        wait: If True, waits for the command thread to finish (useful for CLI/tools).
    """
    from tui.render import log, trim_logs_if_needed
    from tui.agents import agent_session, agent_send, run_graph_agent_task
    from tui.cleanup import load_cleanup_config, run_cleanup, find_module, set_module_enabled, perform_install
    from tui.monitoring import (
        tool_monitor_status, tool_monitor_start, tool_monitor_stop, 
        tool_monitor_set_source, tool_monitor_set_use_sudo
    )
    import threading
    import os
    
    parts = str(cmd or "").strip().split()
    if not parts:
        return
    command = parts[0].lower().strip()
    args = parts[1:]

    if command == "/help" or command == "/h":
        log("/help | /resume", "info")
        log("/run <editor> [--dry] | /modules <editor> | /enable <editor> <id> | /disable <editor> <id>", "info")
        log("/install <editor> | /locales <codes...>", "info")
        log("/monitor status|start|stop|source <watchdog|fs_usage|opensnoop>|sudo <on|off>", "info")
        log("/monitor-targets list|add <key>|remove <key>|clear|save", "info")
        log("/llm status|set provider <copilot>|set main <model>|set vision <model>", "info")
        log("/theme status|set <monaco|dracula|nord|gruvbox>", "info")
        log("/lang status|set ui <code>|set chat <code>", "info")
        log("/streaming status|on|off", "info")
        log("/gui_mode status|on|off|auto", "info")
        log("/task <task> | /trinity <task> | /autopilot <task>", "info")
        log("/chat <message> (discussion only; execution via /task)", "info")
        log("/bootstrap <project_name> [parent_dir]", "info")
        log("/agent-reset | /agent-on | /agent-off", "info")
        return

    if command == "/resume":
        resume_paused_agent()
        return

    if command == "/chat":
        msg = " ".join(args).strip()
        if not msg:
            log("Usage: /chat <message>", "error")
            return
        log(msg, "user")
        def _run_chat():
            state.agent_processing = True
            try:
                ok, answer = agent_send(msg)
                if answer:
                    log(answer, "action" if ok else "error")
            finally:
                state.agent_processing = False
                trim_logs_if_needed()
        threading.Thread(target=_run_chat, daemon=True).start()
        return

    if command in {"/trinity", "/autopilot", "/task"}:
        task = " ".join(args).strip()
        if not task:
            log(f"Usage: {command} <task>", "error")
            return
        log(f"{command} {task}", "user")
        def _run_trinity():
            state.agent_processing = True
            try:
                run_graph_agent_task(
                    task,
                    allow_file_write=True,
                    allow_shell=True,
                    allow_applescript=True,
                    allow_gui=True,
                    allow_shortcuts=True,
                )
            finally:
                state.agent_processing = False
                trim_logs_if_needed()
        
        t = threading.Thread(target=_run_trinity, daemon=not wait)
        t.start()
        if wait:
            t.join()
        return

    if command == "/agent-reset":
        agent_session.reset()
        log("Agent session reset.", "action")
        return

    if command == "/agent-on":
        agent_session.enabled = True
        log("Agent chat enabled.", "action")
        return

    if command == "/agent-off":
        agent_session.enabled = False
        log("Agent chat disabled.", "action")
        return

    # More commands can be added here...
    log(f"Unknown command: {command}", "error")


def tool_app_command(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a CLI command (tool handler)."""
    cmd = str(args.get("command") or "").strip()
    if not cmd:
        return {"ok": False, "error": "No command provided"}

    # This is complex because it captures logs.
    # We pass wait=True to ensure it finishes before the tool call returns.
    try:
        handle_command(cmd, wait=True)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Backward compatibility aliases
_clear_agent_pause_state = clear_agent_pause_state
_set_agent_pause = set_agent_pause
get_input_prompt = get_input_prompt
get_prompt_width = get_prompt_width
_resume_paused_agent = resume_paused_agent
_handle_command = handle_command
_tool_app_command = tool_app_command
_handle_input = handle_input
