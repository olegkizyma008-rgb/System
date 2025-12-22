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

def check_self_healing_status() -> None:
    """Check the status of the self-healing module."""
    try:
        from tui.render import log
        from tui.agents import get_current_runtime
        
        runtime = get_current_runtime()
        if not runtime:
            # Create a temporary runtime for status check
            from core.trinity import TrinityRuntime
            runtime = TrinityRuntime(enable_self_healing=True)
        
        status = runtime.get_self_healing_status()
        if status is None:
            print("Self-healing module is disabled")
            return
        
        print("Self-Healing Status:")
        print(f"  Detected Issues: {status['detected_issues']}")
        print(f"  Repairs Attempted: {status['repairs_attempted']}")
        print(f"  Repairs Successful: {status['repairs_successful']}")
        print(f"  Last Check Position: {status['last_check_position']}")
    except Exception as e:
        print(f"Error checking self-healing status: {e}")

def trigger_self_healing_scan() -> None:
    """Trigger an immediate scan for code issues."""
    try:
        from tui.render import log
        from tui.agents import get_current_runtime
        
        runtime = get_current_runtime()
        if not runtime:
            # Create a temporary runtime for scanning
            from core.trinity import TrinityRuntime
            runtime = TrinityRuntime(enable_self_healing=True)
        
        issues = runtime.trigger_self_healing_scan()
        if issues is None:
            print("Self-healing module is disabled")
            return
        
        if not issues:
            print("No issues detected")
            return
        
        print(f"Detected {len(issues)} issues:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue['type']} in {issue['file']}:{issue['line'] or '?'}")
            print(f"     Severity: {issue['severity']}")
            print(f"     Message: {issue['message'][:100]}...")
    except Exception as e:
        print(f"Error during self-healing scan: {e}")

def check_vibe_assistant_status() -> None:
    """Check the status of Vibe CLI Assistant."""
    try:
        from tui.agents import get_current_runtime
        
        runtime = get_current_runtime()
        if not runtime:
            print("No active Trinity runtime found")
            return
        
        status = runtime.get_vibe_assistant_status()
        print("Vibe CLI Assistant Status:")
        print(f"  Name: {status['name']}")
        print(f"  Total Interventions: {status['interventions_total']}")
        print(f"  Active: {status['interventions_active']}")
        print(f"  Resolved: {status['interventions_resolved']}")
        print(f"  Cancelled: {status['interventions_cancelled']}")
        
        if status['current_pause']:
            print(f"\n⚠️  Current Pause Active:")
            print(f"  Reason: {status['current_pause'].get('reason', 'unknown')}")
            print(f"  Message: {status['current_pause'].get('message', 'no message')}")
        else:
            print("\n✅ No active pauses")
            
    except Exception as e:
        print(f"Error checking Vibe CLI Assistant status: {e}")

def handle_vibe_continue_command() -> None:
    """Handle continue command for Vibe CLI Assistant."""
    try:
        from tui.agents import get_current_runtime
        
        runtime = get_current_runtime()
        if not runtime:
            print("No active Trinity runtime found")
            return
        
        result = runtime.handle_vibe_assistant_command("/continue")
        print(result["message"])
        
        if result["action"] == "resume":
            print("✅ Execution will continue...")
        elif result["action"] == "error":
            print(f"❌ Error: {result['message']}")
            
    except Exception as e:
        print(f"Error handling continue command: {e}")

def handle_vibe_cancel_command() -> None:
    """Handle cancel command for Vibe CLI Assistant."""
    try:
        from tui.agents import get_current_runtime
        
        runtime = get_current_runtime()
        if not runtime:
            print("No active Trinity runtime found")
            return
        
        result = runtime.handle_vibe_assistant_command("/cancel")
        print(result["message"])
        
        if result["action"] == "cancel":
            print("✅ Task has been cancelled")
        elif result["action"] == "error":
            print(f"❌ Error: {result['message']}")
            
    except Exception as e:
        print(f"Error handling cancel command: {e}")

def handle_vibe_help_command() -> None:
    """Handle help command for Vibe CLI Assistant."""
    try:
        from tui.agents import get_current_runtime
        
        runtime = get_current_runtime()
        if not runtime:
            print("No active Trinity runtime found")
            return
        
        result = runtime.handle_vibe_assistant_command("/help")
        print(result["message"])
        
    except Exception as e:
        print(f"Error handling help command: {e}")

def start_eternal_engine_mode(task: str, hyper_mode: bool = False) -> None:
    """Start the system in eternal engine mode with Doctor Vibe."""
    try:
        from core.trinity import TrinityRuntime
        from tui.agents import set_current_runtime
        
        print(f"🚀 Starting Eternal Engine Mode with Doctor Vibe")
        print(f"   Task: {task}")
        print(f"   Hyper Mode: {'✅ ENABLED' if hyper_mode else '❌ DISABLED'}")
        
        # Create Trinity runtime with eternal engine settings
        runtime = TrinityRuntime(
            verbose=True,
            enable_self_healing=True,
            hyper_mode=hyper_mode
        )
        
        # Set as current runtime
        set_current_runtime(runtime)
        
        # Start eternal engine mode
        result = runtime.start_eternal_engine_mode(task)
        
        print(f"✅ Eternal engine completed successfully")
        if result and result.get("messages"):
            final_message = result["messages"][-1].content if result["messages"] else "Task completed"
            print(f"   Result: {final_message}")
        
    except Exception as e:
        print(f"❌ Eternal engine failed: {e}")
        import traceback
        traceback.print_exc()
    
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
    """Handle a slash command from the user."""
    parts = str(cmd or "").strip().split()
    if not parts:
        return
    command = parts[0].lower().strip()
    args = parts[1:]

    # Command dispatcher
    dispatch = {
        "/help": _cmd_help,
        "/h": _cmd_help,
        "/resume": lambda c, a, w: resume_paused_agent(),
        "/chat": _cmd_chat,
        "/trinity": _cmd_trinity_task,
        "/autopilot": _cmd_trinity_task,
        "/task": _cmd_trinity_task,
        "/agent-reset": _cmd_agent_reset,
        "/agent-on": _cmd_agent_on,
        "/agent-off": _cmd_agent_off,
        "/memory-clear": _cmd_memory_clear,
        "/memory": _cmd_memory,
    }

    handler = dispatch.get(command)
    if handler:
        handler(command, args, wait)
    else:
        from tui.render import log
        log(f"Unknown command: {command}", "error")


def _cmd_help(cmd, args, wait):
    from tui.render import log
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
    log("/memory stats|history|import|export|clear|help", "info")


def _cmd_chat(cmd, args, wait):
    from tui.render import log, trim_logs_if_needed
    from tui.agents import agent_send
    import threading
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


def _cmd_trinity_task(cmd, args, wait):
    from tui.render import log, trim_logs_if_needed
    from tui.agents import run_graph_agent_task
    import threading
    task = " ".join(args).strip()
    if not task:
        log(f"Usage: {cmd} <task>", "error")
        return
    log(f"{cmd} {task}", "user")
    
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


def _cmd_agent_reset(cmd, args, wait):
    from tui.render import log
    from tui.agents import agent_session
    agent_session.reset()
    log("Agent session reset.", "action")


def _cmd_agent_on(cmd, args, wait):
    from tui.render import log
    from tui.agents import agent_session
    agent_session.enabled = True
    log("Agent chat enabled.", "action")


def _cmd_agent_off(cmd, args, wait):
    from tui.render import log
    from tui.agents import agent_session
    agent_session.enabled = False
    log("Agent chat disabled.", "action")


def _cmd_memory_clear(cmd, args, wait):
    from tui.render import log
    target = args[0].lower().strip() if args else "working"
    try:
        from core.memory import clear_memory_tool
        res = clear_memory_tool(target)
        if res.get("status") == "success":
            log(f"Memory cleared: {res}", "action")
        else:
            log(f"Memory clear failed: {res.get('error')}", "error")
    except Exception as e:
        log(f"Error clearing memory: {e}", "error")


def _cmd_memory(cmd, args, wait):
    """Handle /memory commands for memory manager."""
    from tui.render import log
    try:
        from tui.memory_manager import handle_memory_chat_command
        result = handle_memory_chat_command(args)
        if result.get("status") == "success":
            message = result.get("message", "OK")
            log(message, "info")
        else:
            log(result.get("error", "Unknown error"), "error")
    except ImportError:
        log("Memory manager module not available", "error")
    except Exception as e:
        log(f"Memory command error: {e}", "error")


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
