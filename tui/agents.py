"""Agent session and LLM interaction for TUI.

Provides:
- AgentTool and AgentSession dataclasses
- Agent initialization and LLM setup
- Streaming and non-streaming agent responses
- Task complexity detection
- Greeting detection
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from tui.state import state
from i18n import lang_name
from tui.cli_paths import SYSTEM_CLI_DIR, LLM_SETTINGS_PATH

# Optional imports
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
    from providers.copilot import CopilotLLM
except Exception:
    CopilotLLM = None
    HumanMessage = SystemMessage = AIMessage = ToolMessage = None


@dataclass
class AgentTool:
    """A tool available to the agent."""
    name: str
    description: str
    handler: Any


@dataclass
class AgentSession:
    """Session state for the agent."""
    enabled: bool = True
    messages: List[Any] = field(default_factory=list)
    tools: List[AgentTool] = field(default_factory=list)
    llm: Any = None
    llm_signature: str = ""

    def reset(self) -> None:
        """Reset the message history."""
        self.messages = []


# Global agent session instance
agent_session = AgentSession()

# Chat mode flag
agent_chat_mode: bool = True

# Global Trinity runtime reference
_current_runtime: Optional[Any] = None

def get_current_runtime() -> Optional[Any]:
    """Get the current Trinity runtime instance."""
    global _current_runtime
    return _current_runtime

def set_current_runtime(runtime: Any) -> None:
    """Set the current Trinity runtime instance."""
    global _current_runtime
    _current_runtime = runtime


def load_env() -> None:
    """Load environment variables from .env file."""
    from tui.cli_paths import SCRIPT_DIR
    
    if load_dotenv is not None:
        load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
    else:
        # Fallback: load .env file manually
        env_path = os.path.join(SCRIPT_DIR, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            os.environ[key] = value
            except Exception:
                pass
    os.environ["SYSTEM_RAG_ENABLED"] = "1"


def get_llm_signature() -> str:
    """Get a signature string for current LLM settings."""
    provider = str(os.getenv("LLM_PROVIDER") or "copilot").strip().lower()
    model = str(os.getenv("COPILOT_MODEL") or "").strip()
    vision = str(os.getenv("COPILOT_VISION_MODEL") or "").strip()
    return f"{provider}:{model}:{vision}"


def ensure_agent_ready() -> Tuple[bool, str]:
    """Ensure the agent LLM is initialized and ready."""
    if CopilotLLM is None or SystemMessage is None or HumanMessage is None:
        return False, "LLM недоступний (нема langchain_core або providers/copilot.py)"

    load_env()
    
    # Import and load LLM settings
    try:
        from tui.cli import _load_llm_settings
        _load_llm_settings()
    except Exception:
        pass
    
    sig = get_llm_signature()

    provider = str(os.getenv("LLM_PROVIDER") or "copilot").strip().lower() or "copilot"
    if provider != "copilot":
        return False, f"Unsupported LLM provider: {provider}"

    if agent_session.llm is None or agent_session.llm_signature != sig:
        agent_session.llm = CopilotLLM(
            model_name=os.getenv("COPILOT_MODEL"), 
            vision_model_name=os.getenv("COPILOT_VISION_MODEL")
        )
        agent_session.llm_signature = sig
    return True, "OK"


def is_complex_task(text: str) -> bool:
    """Detect if text represents a complex multi-step task."""
    t = str(text or "").strip()
    if not t:
        return False
    if t.startswith("/"):
        return False
    # Heuristics: long, multi-sentence, multi-line, or multi-step language.
    if "\n" in t:
        return True
    if len(t) >= 240:
        return True
    if t.count(".") + t.count("!") + t.count("?") >= 3:
        return True
    lower = t.lower()
    keywords = [
        "потім",
        "далі",
        "крок",
        "steps",
        "step",
        "і потім",
        "спочатку",
        "зроби",
        "налаштуй",
        "автоматиз",
        "перевір",
        "знайди",
        "відкрий",
        "запусти",
        "включи",
        "після",
        "пересвідчись",
        "гугл",
        "google",
        "youtube",
        "онлайн",
        "фільм",
    ]
    return sum(1 for k in keywords if k in lower) >= 2


def is_greeting(text: str) -> bool:
    """Detect if text is a simple greeting."""
    t = str(text or "").strip().lower()
    if not t:
        return False
    t = re.sub(r"[\s\t\n\r\.,!\?;:]+", " ", t).strip()
    greetings = {
        "привіт",
        "привiт",
        "вітаю",
        "доброго дня",
        "добрий день",
        "добрий вечір",
        "доброго вечора",
        "добрий ранок",
        "доброго ранку",
        "hello",
        "hi",
        "hey",
    }
    return t in greetings


def load_llm_settings() -> None:
    """Load LLM settings from file and set environment variables."""
    try:
        from tui.agents import load_env
        load_env()
        
        # Defaults
        default_provider = str(os.getenv("LLM_PROVIDER") or "copilot").strip().lower() or "copilot"
        default_main = str(os.getenv("COPILOT_MODEL") or "gpt-4o").strip() or "gpt-4o"
        default_vision = str(os.getenv("COPILOT_VISION_MODEL") or "").strip()
        if not default_vision or default_vision == "gpt-4o":
            default_vision = "gpt-4.1"

        data = {}
        if os.path.exists(LLM_SETTINGS_PATH):
            with open(LLM_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

        # 1. Global Defaults
        provider = str(data.get("provider") or default_provider).strip().lower()
        main_model = str(data.get("main_model") or default_main).strip()
        vision_model = str(data.get("vision_model") or default_vision).strip()
        if vision_model == "gpt-4o": 
            vision_model = "gpt-4.1"

        os.environ["LLM_PROVIDER"] = provider
        os.environ["COPILOT_MODEL"] = main_model
        os.environ["COPILOT_VISION_MODEL"] = vision_model

        # 2. Per-Agent Config
        # Helper to get setting with fallback
        def _get_setting(section: str, key: str, fallback: str) -> str:
            val = str((data.get(section) or {}).get(key) or "").strip()
            return val if val else fallback

        # Atlas
        os.environ["ATLAS_PROVIDER"] = _get_setting("atlas", "provider", provider)
        os.environ["ATLAS_MODEL"] = _get_setting("atlas", "model", "gpt-4.1") # Default Atlas to Smart model

        # Tetyana (Executor - needs speed/reliability)
        os.environ["TETYANA_PROVIDER"] = _get_setting("tetyana", "provider", provider)
        os.environ["TETYANA_MODEL"] = _get_setting("tetyana", "model", "gpt-4o")

        # Grisha (Verifier - needs reasoning)
        os.environ["GRISHA_PROVIDER"] = _get_setting("grisha", "provider", provider)
        os.environ["GRISHA_MODEL"] = _get_setting("grisha", "model", "gpt-4.1")

        # Vision Tool (needs Vision model)
        os.environ["VISION_TOOL_PROVIDER"] = _get_setting("vision", "provider", provider)
        os.environ["VISION_TOOL_MODEL"] = _get_setting("vision", "model", vision_model)

    except Exception:
        return


def save_llm_settings(provider: str = None, main_model: str = None, vision_model: str = None, section: str = None, model: str = None) -> bool:
    """
    Save LLM settings.
    If section is provided (atlas|tetyana|grisha|vision), updates that section.
    Otherwise updates global defaults.
    """
    try:
        os.makedirs(SYSTEM_CLI_DIR, exist_ok=True)
        data = {}
        if os.path.exists(LLM_SETTINGS_PATH):
            with open(LLM_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

        if section:
            # Update specific section
            sec_data = data.get(section) or {}
            if provider:
                sec_data["provider"] = str(provider).strip().lower()
            if model:
                 # Standardize model names
                if model == "gpt-4o": val = "gpt-4o"
                elif model == "gpt-4.1": val = "gpt-4.1"
                else: val = str(model).strip()
                sec_data["model"] = val
            data[section] = sec_data
        else:
            # Update global defaults
            if provider:
                data["provider"] = str(provider).strip().lower()
            if main_model:
                data["main_model"] = str(main_model).strip()
            if vision_model:
                 data["vision_model"] = "gpt-4.1" if str(vision_model).strip() == "gpt-4o" else str(vision_model).strip()

        with open(LLM_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # Refreshes env vars immediately
        load_llm_settings()
        return True
    except Exception:
        return False


def reset_agent_llm() -> None:
    """Reset the agent LLM (forces re-initialization on next use)."""
    agent_session.llm = None
    agent_session.llm_signature = ""



def init_agent_tools() -> None:
    """Initialize agent tools and add them to the session."""
    if agent_session.tools:
        return

    from tui.tools import (
        tool_scan_traces, tool_list_dir, tool_organize_desktop_wrapper,
        tool_read_file, tool_grep, tool_open_app, tool_open_url,
        tool_chrome_open_url, tool_chrome_active_tab, tool_take_screenshot,
        tool_run_shell_wrapper, tool_run_shortcut, tool_run_automator,
        tool_run_applescript, tool_create_module, tool_llm_status,
        tool_llm_set, tool_ui_theme_status, tool_ui_theme_set,
        tool_ui_streaming_status, tool_ui_streaming_set
    )
    from tui.commands import tool_app_command
    from tui.monitoring import (
        tool_monitor_status, tool_monitor_set_source, tool_monitor_set_use_sudo,
        tool_monitor_start, tool_monitor_stop, tool_monitor_set_mode
    )

    agent_session.tools = [
        AgentTool(name="scan_traces", description="Scan typical macOS paths for traces of an editor. args: {editor}", handler=tool_scan_traces),
        AgentTool(name="list_dir", description="List directory entries. args: {path}", handler=tool_list_dir),
        AgentTool(
            name="organize_desktop",
            description="Delete Desktop screenshots + move remaining files into a target folder by extension (requires CONFIRM_SHELL). args: {desktop_path?, target_folder_name?}",
            handler=tool_organize_desktop_wrapper,
        ),
        AgentTool(name="read_file", description="Read file lines. args: {path, limit?}", handler=tool_read_file),
        AgentTool(name="grep", description="Grep by regex under root. args: {root, query, max_files?, max_hits?}", handler=tool_grep),
        AgentTool(name="open_app", description="Open a macOS app by name. args: {name}", handler=tool_open_app),
        AgentTool(name="open_url", description="Open a URL (or file) using macOS open. args: {url}", handler=tool_open_url),
        AgentTool(name="chrome_open_url", description="Open a URL specifically in Google Chrome. args: {url}", handler=tool_chrome_open_url),
        AgentTool(name="chrome_active_tab", description="Get Google Chrome active tab (title + url). args: {}", handler=tool_chrome_active_tab),
        AgentTool(name="take_screenshot", description="Take screenshot of focused window or target app. args: {app_name?}", handler=tool_take_screenshot),
        AgentTool(name="run_shell", description="Run a shell command (requires CONFIRM_SHELL). args: {command}", handler=tool_run_shell_wrapper),
        AgentTool(name="run_shortcut", description="Run a macOS Shortcut by name (requires CONFIRM_SHELL). args: {name}", handler=tool_run_shortcut),
        AgentTool(name="run_automator", description="Run an Automator workflow (requires CONFIRM_SHELL). args: {workflow_path}", handler=tool_run_automator),
        AgentTool(name="run_applescript", description="Run AppleScript (requires CONFIRM_APPLESCRIPT). args: {script}", handler=tool_run_applescript),
        AgentTool(
            name="create_module",
            description="Create cleanup module (.sh file + add to cleanup_modules.json). args: {editor,id,name,description?,enabled?,script?,script_content?,overwrite?}",
            handler=tool_create_module,
        ),
        AgentTool(
            name="app_command",
            description="Execute a CLI command. args: {command}",
            handler=tool_app_command,
        ),
        AgentTool(
            name="monitor_status",
            description="Get monitoring status. args: {}",
            handler=lambda _args: tool_monitor_status(),
        ),
        AgentTool(
            name="monitor_set_source",
            description="Set monitoring source. args: {source: watchdog|fs_usage|opensnoop}",
            handler=tool_monitor_set_source,
        ),
        AgentTool(
            name="monitor_set_use_sudo",
            description="Toggle sudo usage for monitoring source fs_usage. args: {use_sudo: true|false}",
            handler=tool_monitor_set_use_sudo,
        ),
        AgentTool(
            name="monitor_set_mode",
            description="Set monitoring mode. args: {mode: auto|manual}",
            handler=lambda args: tool_monitor_set_mode(args),
        ),
        AgentTool(
            name="monitor_start",
            description="Start monitoring using current settings & targets. args: {}",
            handler=lambda _args: tool_monitor_start(),
        ),
        AgentTool(
            name="monitor_stop",
            description="Stop monitoring. args: {}",
            handler=lambda _args: tool_monitor_stop(),
        ),
        AgentTool(
            name="llm_status",
            description="Get LLM configuration status. args: {}",
            handler=lambda _args: tool_llm_status(),
        ),
        AgentTool(
            name="llm_set",
            description="Set LLM configuration. args: {provider, main_model, vision_model}",
            handler=tool_llm_set,
        ),
        AgentTool(
            name="ui_theme_status",
            description="Get UI theme status. args: {}",
            handler=lambda _args: tool_ui_theme_status(),
        ),
        AgentTool(
            name="ui_theme_set",
            description="Set UI theme. args: {theme}",
            handler=tool_ui_theme_set,
        ),
        AgentTool(
            name="ui_streaming_status",
            description="Get UI streaming status. args: {}",
            handler=lambda _args: tool_ui_streaming_status(),
        ),
        AgentTool(
            name="ui_streaming_set",
            description="Set UI streaming status. args: {streaming: true|false}",
            handler=tool_ui_streaming_set,
        ),
    ]


def agent_send(user_text: str) -> Tuple[bool, str]:
    """Send a message to the agent."""
    from tui.agents import is_greeting, _agent_send_with_stream, _agent_send_no_stream
    
    if is_greeting(user_text):
        greeting = "Привіт! Чим можу допомогти?"
        if bool(getattr(state, "ui_streaming", True)):
            try:
                from tui.render import log
                log(greeting, "action")
            except Exception:
                pass
        return True, greeting
    
    use_stream = bool(getattr(state, "ui_streaming", True))
    if use_stream:
        return _agent_send_with_stream(user_text)

    return _agent_send_no_stream(user_text)


def _agent_send_with_stream(user_text: str) -> Tuple[bool, str]:
    from tui.render import log, log_reserve_line, log_replace_at
    from tui.agents import ensure_agent_ready, agent_session
    
    ok, msg = ensure_agent_ready()
    if not ok:
        return False, msg

    try:
        sys_msg = SystemMessage(content="You are an expert macOS assistant.")
        user_msg = HumanMessage(content=user_text)
        agent_session.messages.append(user_msg)

        idx = log_reserve_line("action")
        full_text = ""

        # Dummy implementation for now, real one should use llm.stream
        for chunk in agent_session.llm.stream([sys_msg] + agent_session.messages):
            content = getattr(chunk, "content", "")
            if content:
                full_text += content
                log_replace_at(idx, full_text, "action")
                # Update UI
                try:
                    from tui.layout import force_ui_update
                    force_ui_update()
                except Exception:
                    pass

        agent_session.messages.append(AIMessage(content=full_text))
        return True, full_text
    except Exception as e:
        return False, str(e)


def _agent_send_no_stream(user_text: str) -> Tuple[bool, str]:
    from tui.agents import ensure_agent_ready, agent_session
    
    ok, msg = ensure_agent_ready()
    if not ok:
        return False, msg

    try:
        sys_msg = SystemMessage(content="You are an expert macOS assistant.")
        user_msg = HumanMessage(content=user_text)
        agent_session.messages.append(user_msg)

        resp = agent_session.llm.invoke([sys_msg] + agent_session.messages)
        full_text = str(getattr(resp, "content", "") or "").strip()
        
        agent_session.messages.append(AIMessage(content=full_text))
        return True, full_text
    except Exception as e:
        return False, str(e)


def run_graph_agent_task(
    user_text: str,
    *,
    allow_file_write: bool,
    allow_shell: bool,
    allow_applescript: bool,
    allow_gui: bool,
    allow_shortcuts: bool = False,
    gui_mode: str = "auto",
) -> None:
    """Execute a task using the Trinity graph agent."""
    from tui.render import log, log_agent_message, log_reserve_line, log_replace_at, trim_logs_if_needed
    from tui.commands import set_agent_pause
    from tui.messages import AgentType
    from tui.agents import load_env
    
    try:
        os.environ["TRINITY_ALLOW_GENERAL"] = "1"
        os.environ["TRINITY_ROUTING_MODE"] = "all"
        load_env()
        from core.trinity import TrinityRuntime, TrinityPermissions
        
        permissions = TrinityPermissions(
            allow_shell=allow_shell,
            allow_applescript=allow_applescript,
            allow_file_write=allow_file_write,
            allow_gui=allow_gui,
            allow_shortcuts=allow_shortcuts,
            hyper_mode=False,
        )
        
        log("[ATLAS] Initializing NeuroMac System (Atlas/Tetyana/Grisha)...", "info")

        # Initial message for Agents panel
        try:
            from tui.render import get_agent_messages_buffer
            buf = get_agent_messages_buffer()
            # Clear previous context if needed, or just append
            buf.add(AgentType.ATLAS, "[VOICE] Розпочинаю виконання...", is_technical=False)
        except Exception:
            pass
        
        use_stream = bool(getattr(state, "ui_streaming", True))
        accumulated_by_agent: Dict[str, str] = {}
        stream_line_by_agent: Dict[str, int] = {}

        on_stream_callback = (
            lambda agent_name, delta: _handle_agent_stream(
                agent_name, delta, accumulated_by_agent, stream_line_by_agent
            )
            if use_stream
            else None
        )
        gui_mode_val = str(gui_mode or "auto").strip().lower() or "auto"
        
        # Log file tail thread to stream real-time logs from Trinity
        from pathlib import Path
        log_file_path = Path.home() / ".system_cli" / "logs" / "cli.log"
        
        tail_active = threading.Event()
        tail_active.set()
        last_position = [0]
        
        # Get current file position (start from end to only show new logs)
        if log_file_path.exists():
            try:
                last_position[0] = log_file_path.stat().st_size
            except Exception:
                pass
        
        tail_thread = threading.Thread(
            target=_tail_log_file, 
            args=(tail_active, log_file_path, last_position), 
            daemon=True
        )
        tail_thread.start()

        chat_lang = getattr(state, "chat_lang", "en")
        # Use state setting for self-healing and learning mode
        enable_self_healing = bool(getattr(state, "ui_self_healing", False))
        learning_mode = bool(getattr(state, "learning_mode", False))
        
        runtime = TrinityRuntime(
            verbose=False, 
            permissions=permissions, 
            on_stream=on_stream_callback, 
            preferred_language=chat_lang,
            enable_self_healing=enable_self_healing,
            learning_mode=learning_mode
        )
        
        # Set the current runtime for global access
        set_current_runtime(runtime)
        
        # Enrich Trinity Registry with TUI tools
        if not agent_session.tools:
             try:
                 # Initialize TUI tools if not already done
                 init_agent_tools()
             except Exception:
                 pass
                 
        if agent_session.tools:
            for tool in agent_session.tools:
                # Only register if not already present (Trinity core tools take precedence or we overwrite?)
                # We'll overwrite to ensure TUI-specific wrappers (like monitor_start logging) are used.
                runtime.registry.register_tool(tool.name, tool.handler, tool.description)

        
        exec_mode = str(getattr(state, "ui_execution_mode", "native") or "native").strip().lower() or "native"
        log("[ATLAS] Starting task processing...", "info")
        
        # Force UI update before long-running operation
        try:
            from tui.layout import force_ui_update
            force_ui_update()
        except Exception:
            pass
        
        # Process the event loop in a separate helper to reduce complexity
        _process_graph_events(runtime, user_text, gui_mode_val, exec_mode, use_stream, stream_line_by_agent)
                
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"DEBUG ERROR: {e}")
        print(err_msg)
        log(f"[TRINITY] Runtime error: {e}", "error")
        # Log to hidden debug log if needed, or just standard log
        # For now, let's put it in the info log so we can see it
        # but maybe it's too long. Let's just log the last line of the traceback.
        log(f"Traceback: {err_msg.splitlines()[-1]}", "info")
        return
    finally:
        # Stop tailing and ensure thread exits cleanly
        try:
            tail_active.clear()
        except Exception:
            pass
        try:
            tail_thread.join(timeout=1.0)
        except Exception:
            pass

    log("[TRINITY] ✓ Task completed.", "action")
    trim_logs_if_needed()


def _handle_agent_stream(agent_name: str, delta: str, accumulated_by_agent: dict, stream_line_by_agent: dict) -> None:
    if not delta: return
    from tui.render import log_agent_message, log_replace_at, log_reserve_line
    from tui.messages import AgentType
    
    prev = accumulated_by_agent.get(agent_name, "")
    curr = prev + delta
    accumulated_by_agent[agent_name] = curr

    idx = stream_line_by_agent.get(agent_name)
    if idx is None:
        idx = log_reserve_line("action")
        stream_line_by_agent[agent_name] = idx

    tag = str(agent_name or "TRINITY").strip().upper() or "TRINITY"
    log_replace_at(idx, f"[{tag}] {curr}", "action")
    
    try:
        agent_type_map = {
            "atlas": AgentType.ATLAS,
            "tetyana": AgentType.TETYANA,
            "grisha": AgentType.GRISHA,
            "vibe": AgentType.VIBE,
        }
        agent_type = agent_type_map.get(agent_name.lower(), AgentType.SYSTEM)
        log_agent_message(agent_type, curr)

        # Mark TUI state to indicate recent Vibe activity (for status bar blink)
        if agent_name and agent_name.lower() == "vibe":
            try:
                from tui.state import state
                import time
                state.vibe_last_update = time.time()
            except Exception:
                pass
    except Exception:
        pass

    try:
        from tui.layout import force_ui_update
        force_ui_update()
    except Exception: pass

def _tail_log_file(tail_active: threading.Event, log_file_path: Any, last_position: list):
    """Tail log file and display new lines in TUI."""
    from tui.render import log
    while tail_active.is_set():
        try:
            if not log_file_path.exists():
                threading.Event().wait(0.1) # reduced wait
                continue
            
            current_size = log_file_path.stat().st_size
            if current_size > last_position[0]:
                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position[0])
                    new_content = f.read()
                    last_position[0] = f.tell()
                
                for line in new_content.strip().split('\n'):
                    if not line: continue
                    _process_log_line(line, log)
        except Exception: pass
        threading.Event().wait(0.3)

def _categorize_log_message(msg: str, line: str) -> tuple:
    """Categorize log message and return (category, formatted_message)."""
    msg_lower = msg.lower()
    
    if 'result for' in msg_lower:
        has_error = any(x in msg_lower for x in ['error', 'failed', 'exception', '"status": "error"', 'permission_required'])
        return ('tool_fail', '✗ ' + msg) if has_error else ('tool_success', '✓ ' + msg)
    
    if 'execute' in msg_lower and ('tool' in msg_lower or 'name' in msg_lower):
        return 'tool_run', '⚙ ' + msg
    
    if '[blocked]' in msg_lower:
        return 'tool_fail', '✗ ' + msg
    
    if 'error' in msg_lower or 'ERROR' in line:
        return 'error', msg
    
    if '[TRACE]' in line or 'DEBUG' in line:
        return 'info', msg
    
    return 'action', msg


def _process_log_line(line: str, log: Callable):
    """Process a log line and display in TUI."""
    parts = line.split('|')
    msg = parts[-1].strip() if len(parts) >= 2 else line.strip()
    
    cat, formatted_msg = _categorize_log_message(msg, line)
    
    if len(formatted_msg) > 150:
        formatted_msg = formatted_msg[:147] + '...'
    
    if formatted_msg:
        log(formatted_msg, cat)
    
    try:
        from tui.layout import force_ui_update
        force_ui_update()
    except Exception:
        pass

# Backward compatibility aliases
_load_env = load_env
_get_llm_signature = get_llm_signature
_ensure_agent_ready = ensure_agent_ready
_is_complex_task = is_complex_task
_is_greeting = is_greeting
_reset_agent_llm = reset_agent_llm
_agent_send = agent_send
_agent_send_with_stream = _agent_send_with_stream
_agent_send_no_stream = _agent_send_no_stream
_run_graph_agent_task = run_graph_agent_task

def _process_graph_events(runtime, user_text, gui_mode_val, exec_mode, use_stream, stream_line_by_agent):
    """Process Trinity graph events and update TUI."""
    from tui.render import log, log_agent_message, log_reserve_line, log_replace_at
    from tui.commands import set_agent_pause
    from tui.messages import AgentType

    event_count = 0
    try:
        limit = int(getattr(state, "ui_recursion_limit", 100))
    except Exception:
        limit = 100
    for event in runtime.run(user_text, gui_mode=gui_mode_val, execution_mode=exec_mode, recursion_limit=limit):
        event_count += 1
        print(f"DEBUG: Event {event_count} received")
        
        for node_name, state_update in event.items():
            if not state_update or not isinstance(state_update, dict):
                continue
            
            print(f"DEBUG: Processing node {node_name}")
            result = _process_single_event(node_name, state_update, use_stream, stream_line_by_agent, user_text)
            if result == "paused":
                return


def _extract_message_content(last_msg) -> str:
    """Extract content string from message object."""
    if not last_msg:
        return ""
    if hasattr(last_msg, "content"):
        return str(last_msg.content or "")
    if isinstance(last_msg, dict):
        return str(last_msg.get("content", ""))
    return str(last_msg)


def _process_single_event(node_name, state_update, use_stream, stream_line_by_agent, user_text) -> str:
    """Process a single graph event. Returns 'paused' if execution should stop."""
    from tui.render import log, log_agent_message, log_reserve_line, log_replace_at, log_agent_final
    from tui.commands import set_agent_pause
    from tui.messages import AgentType
    
    agent_name = node_name.capitalize()
    tag = str(node_name or agent_name or "TRINITY").strip().upper() or "TRINITY"
    messages = state_update.get("messages", [])
    last_msg = messages[-1] if messages else None
    content = _extract_message_content(last_msg)
    
    # Log to TUI (Left Panel - General Log)
    _log_to_tui(tag, content, agent_name, use_stream, stream_line_by_agent)
    
    # Update agent panel (Right Panel - Chat)
    # Filter out ToolMessages and empty content to keep chat "natural"
    show_in_chat = True
    try:
        # Use global references from module imports
        if ToolMessage and isinstance(last_msg, ToolMessage):
            show_in_chat = False
        elif not content.strip():
            show_in_chat = False
    except Exception:
        pass

    if show_in_chat:
        _update_agent_panel(agent_name, content)
    
    # Check for pause
    pause_info = state_update.get("pause_info")
    if pause_info:
        perm = pause_info.get("permission", "unknown")
        pane = pause_info.get("mac_pane")
        msg = pause_info.get("message", "Permission required")
        set_agent_pause(pending_text=user_text, permission=perm, message=msg, mac_pane=pane)
        log(f"[{tag}] ⚠️ PAUSED: {msg}", "error")
        return "paused"
    
    return "continue"


def _log_to_tui(tag: str, content: str, agent_name: str, use_stream: bool, stream_line_by_agent: dict):
    """Log event to TUI using appropriate method."""
    from tui.render import log, log_reserve_line, log_replace_at
    
    if not use_stream:
        log(f"[{tag}] {content}", "info")
    else:
        idx = stream_line_by_agent.get(agent_name)
        if idx is None:
            idx = log_reserve_line("action")
            stream_line_by_agent[agent_name] = idx
        log_replace_at(idx, f"[{tag}] {content}", "action")


def _update_agent_panel(agent_name: str, content: str):
    """Update agent message panel."""
    try:
        from tui.render import log_agent_message, log_agent_final
        from tui.messages import AgentType
        
        agent_type_map = {
            "atlas": AgentType.ATLAS,
            "tetyana": AgentType.TETYANA,
            "grisha": AgentType.GRISHA,
        }
        agent_type = agent_type_map.get(agent_name.lower(), AgentType.SYSTEM)
        log_agent_message(agent_type, content)
        log_agent_final(agent_type, content)
    except Exception:
        pass
