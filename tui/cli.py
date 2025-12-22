#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Єдиний і основний інтерфейс керування системою.

Можливості:
- Управління очисткою по редакторах: Windsurf / VS Code / Antigravity / Cursor
- Керування модулями очистки (enable/disable)
- Режим "нова установка" (відкриття DMG/ZIP/URL)
- LLM-режим: smart-plan (побудова патернів/модулів) і /ask (одноразовий запит)
- Менеджер локалізацій (список/primary) - збереження в ~/.localization_cli.json

Запуск:
  python3 cli.py            # TUI
  python3 cli.py run --editor windsurf --dry-run

Примітка: скрипт навмисно не прив'язується до версій редакторів.
"""

import argparse
import atexit
from collections import Counter, defaultdict
import ctypes
import glob
import json
import os
import plistlib
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from i18n import TOP_LANGS, lang_name, normalize_lang, tr
from tui.state import AppState, MenuLevel, state
from tui.logger import setup_logging, get_logger, log_exception, log_command_execution, setup_root_file_logging

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Point
from prompt_toolkit.styles import DynamicStyle, Style
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition

from tui.layout import build_app, force_ui_update
from tui.menu import build_menu
from tui.keybindings import build_keybindings
from tui.app import TuiRuntime, run_tui as tui_run_tui
from tui.constants import MAIN_MENU_ITEMS
from tui.cli_defaults import DEFAULT_CLEANUP_CONFIG
from tui.cli_localization import AVAILABLE_LOCALES, LocalizationConfig


# Setup root logging immediately
try:
    setup_root_file_logging(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
except Exception:
    pass
from tui.themes import THEME_NAMES, THEMES
from tui.messages import MessageBuffer, AgentType
from tui.cli_paths import (
    CLEANUP_CONFIG_PATH,
    LLM_SETTINGS_PATH,
    LOCALIZATION_CONFIG_PATH,
    MONITOR_EVENTS_DB_PATH,
    MONITOR_SETTINGS_PATH,
    MONITOR_TARGETS_PATH,
    SCRIPT_DIR,
    SYSTEM_CLI_DIR,
    UI_SETTINGS_PATH,
)

# New modular imports
from tui.permissions import (
    macos_open_privacy_pane as _macos_open_privacy_pane_new,
    macos_screen_recording_preflight as _macos_screen_recording_preflight_new,
    macos_screen_recording_request_prompt as _macos_screen_recording_request_prompt_new,
    macos_accessibility_is_trusted as _macos_accessibility_is_trusted_new,
    macos_accessibility_request_prompt as _macos_accessibility_request_prompt_new,
    macos_automation_check_system_events as _macos_automation_check_system_events_new,
    permissions_wizard as _permissions_wizard_new,
    CommandPermissions as CommandPermissionsNew,
    is_confirmed_run as _is_confirmed_run_new,
    is_confirmed_shell as _is_confirmed_shell_new,
    is_confirmed_applescript as _is_confirmed_applescript_new,
    is_confirmed_gui as _is_confirmed_gui_new,
    is_confirmed_shortcuts as _is_confirmed_shortcuts_new,
    permissions_from_text as _permissions_from_text_new,
)

from tui.render import (
    get_render_log_snapshot as _get_render_log_snapshot_new,
    get_render_agents_snapshot as _get_render_agents_snapshot_new,
    log as _log_new,
    log_agent_message as _log_agent_message_new,
    log_reserve_line as _log_reserve_line_new,
    log_replace_at as _log_replace_at_new,
    trim_logs_if_needed as _trim_logs_if_needed_new,
    get_logs as _get_logs_new,
    get_agent_messages as _get_agent_messages_new,
    get_agent_cursor_position as _get_agent_cursor_position_new,
    get_log_cursor_position as _get_log_cursor_position_new,
    get_header as _get_header_new,
    get_context as _get_context_new,
    get_status as _get_status_new,
    get_agent_messages_buffer,
    get_agent_messages_lock,
    get_logs_lock,
)

from tui.cleanup import (
    load_cleanup_config as _load_cleanup_config_new,
    save_cleanup_config as _save_cleanup_config_new,
    list_editors as _list_editors_new,
    resolve_editor_arg as _resolve_editor_arg_new,
    find_module as _find_module_new,
    set_module_enabled as _set_module_enabled_new,
    script_env as _script_env_new,
    run_script as _run_script_new,
    run_cleanup as _run_cleanup_new,
    perform_install as _perform_install_new,
    scan_traces as _scan_traces_new,
    get_editors_list as _get_editors_list_new,
    ModuleRef,
)

from tui.agents import (
    AgentTool as AgentToolNew,
    AgentSession as AgentSessionNew,
    agent_session as agent_session_new,
    agent_chat_mode as agent_chat_mode_new,
    load_env as _load_env_new,
    get_llm_signature as _get_llm_signature_new,
    ensure_agent_ready as _ensure_agent_ready_new,
    is_complex_task as _is_complex_task_new,
    is_greeting as _is_greeting_new,
    reset_agent_llm as _reset_agent_llm_new,
    agent_send as _agent_send_new,
    _agent_send_with_stream as _agent_send_with_stream_new,
    _agent_send_no_stream as _agent_send_no_stream_new,
    run_graph_agent_task as _run_graph_agent_task_new,
    load_llm_settings as _load_llm_settings_new,
    save_llm_settings as _save_llm_settings_new,
    init_agent_tools as _init_agent_tools_new,
)

from tui.monitoring import (
    load_monitor_settings as _load_monitor_settings_new,
    save_monitor_settings as _save_monitor_settings_new,
    load_monitor_targets as _load_monitor_targets_new,
    save_monitor_targets as _save_monitor_targets_new,
    monitor_get_sudo_password as _monitor_get_sudo_password_new,
    monitor_db_read_since_id as _monitor_db_read_since_id_new,
    monitor_db_get_max_id as _monitor_db_get_max_id_new,
    format_monitor_summary as _format_monitor_summary_new,
    monitor_resolve_watch_items as _monitor_resolve_watch_items_new,
    MonitorSummaryService as MonitorSummaryServiceNew,
    MonitorMenuItem as MonitorMenuItemNew,
    monitor_summary_service as monitor_summary_service_new,
    monitor_start_selected as _monitor_start_selected_new,
    monitor_stop_selected as _monitor_stop_selected_new,
    monitor_summary_start_if_needed as _monitor_summary_start_if_needed_new,
    monitor_summary_stop_if_needed as _monitor_summary_stop_if_needed_new,
    tool_monitor_status as _tool_monitor_status_new,
    tool_monitor_set_source as _tool_monitor_set_source_new,
    tool_monitor_set_use_sudo as _tool_monitor_set_use_sudo_new,
    tool_monitor_start as _tool_monitor_start_new,
    tool_monitor_stop as _tool_monitor_stop_new,
    tool_monitor_targets as _tool_monitor_targets_new,
)

from tui.recordings import (
    recordings_base_dir as _recordings_base_dir_new,
    recordings_last_path as _recordings_last_path_new,
    recordings_save_last as _recordings_save_last_new,
    recordings_load_last as _recordings_load_last_new,
    recordings_list_session_dirs as _recordings_list_session_dirs_new,
    recordings_read_meta as _recordings_read_meta_new,
    recordings_update_meta as _recordings_update_meta_new,
    recordings_ensure_meta_name as _recordings_ensure_meta_name_new,
    recordings_resolve_last_dir as _recordings_resolve_last_dir_new,
    extract_automation_title as _extract_automation_title_new,
    extract_automation_prompt as _extract_automation_prompt_new,
    get_recorder_service as _get_recorder_service_new,
    custom_tasks_allowed as _custom_tasks_allowed_new,
    custom_task_recorder_start as _custom_task_recorder_start_new,
    custom_task_recorder_stop as _custom_task_recorder_stop_new,
    custom_task_recorder_open_last as _custom_task_recorder_open_last_new,
    analyze_recording_bg as _analyze_recording_bg_new,
    start_recording_analysis as _start_recording_analysis_new,
)

from tui.commands import (
    clear_agent_pause_state as _clear_agent_pause_state_new,
    set_agent_pause as _set_agent_pause_new,
    resume_paused_agent as _resume_paused_agent_new,
    handle_command as _handle_command_new,
    tool_app_command as _tool_app_command_new,
    handle_input as _handle_input_new,
    get_input_prompt as _get_input_prompt_new,
    get_prompt_width as _get_prompt_width_new,
    parse_command,
    is_command,
)

from tui.tools import (
    tool_scan_traces as _tool_scan_traces_new,
    tool_list_dir as _tool_list_dir_new,
    tool_organize_desktop_wrapper as _tool_organize_desktop_wrapper_new,
    tool_chrome_open_url as _tool_chrome_open_url_new,
    tool_chrome_active_tab as _tool_chrome_active_tab_new,
    tool_open_url as _tool_open_url_new,
    tool_open_app as _tool_open_app_new,
    tool_run_shell_wrapper as _tool_run_shell_wrapper_new,
    tool_run_shortcut as _tool_run_shortcut_new,
    tool_run_automator as _tool_run_automator_new,
    tool_run_applescript as _tool_run_applescript_new,
    tool_read_file as _tool_read_file_new,
    tool_grep as _tool_grep_new,
    tool_take_screenshot as _tool_take_screenshot_new,
    tool_create_module as _tool_create_module_new,
    tool_llm_status as _tool_llm_status_new,
    tool_llm_set as _tool_llm_set_new,
    tool_ui_theme_status as _tool_ui_theme_status_new,
    tool_ui_theme_set as _tool_ui_theme_set_new,
    tool_ui_streaming_status as _tool_ui_streaming_status_new,
    tool_ui_streaming_set as _tool_ui_streaming_set_new,
)



def _macos_open_privacy_pane(pane: str) -> None:
    _macos_open_privacy_pane_new(pane)


def _macos_screen_recording_preflight() -> Optional[bool]:
    return _macos_screen_recording_preflight_new()


def _macos_screen_recording_request_prompt() -> Optional[bool]:
    return _macos_screen_recording_request_prompt_new()


def _macos_accessibility_is_trusted() -> Optional[bool]:
    return _macos_accessibility_is_trusted_new()


def _macos_accessibility_request_prompt() -> Optional[bool]:
    return _macos_accessibility_request_prompt_new()


def _macos_automation_check_system_events(*, prompt: bool) -> Optional[bool]:
    return _macos_automation_check_system_events_new(prompt=prompt)


def _permissions_wizard(
    *,
    require_accessibility: bool,
    require_screen_recording: bool,
    require_automation: bool,
    prompt: bool,
    open_settings: bool,
) -> Dict[str, Any]:
    return _permissions_wizard_new(
        require_accessibility=require_accessibility,
        require_screen_recording=require_screen_recording,
        require_automation=require_automation,
        prompt=prompt,
        open_settings=open_settings,
    )


try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover
    FileSystemEventHandler = object  # type: ignore
    Observer = None  # type: ignore

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

# LLM provider (optional)
try:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage  # type: ignore

    from providers.copilot import CopilotLLM  # type: ignore
except Exception:
    CopilotLLM = None  # type: ignore
    HumanMessage = SystemMessage = AIMessage = ToolMessage = None  # type: ignore

try:
    from system_ai.recorder import RecorderService  # type: ignore
except Exception:
    RecorderService = None  # type: ignore


AgentTool = AgentToolNew
AgentSession = AgentSessionNew
agent_session = agent_session_new
agent_chat_mode = agent_chat_mode_new

_agent_messages_buffer = get_agent_messages_buffer()
_agent_messages_lock = get_agent_messages_lock()
_logs_lock = get_logs_lock()
_logs_need_trim: bool = False
_thread_log_override = threading.local()

_render_log_cache: Dict[str, Any] = {"ts": 0.0, "logs": [], "cursor": Point(x=0, y=0)}
_render_log_cache_ttl_s: float = 0.2


def _get_render_log_snapshot() -> Tuple[List[Tuple[str, str]], Point]:
    return _get_render_log_snapshot_new()


_render_agents_cache: Dict[str, Any] = {"ts": 0.0, "messages": [], "cursor": Point(x=0, y=0)}
_render_agents_cache_ttl_s: float = 0.2


def _get_render_agents_snapshot() -> Tuple[List[Tuple[str, str]], Point]:
    return _get_render_agents_snapshot_new()


def _trim_logs_if_needed() -> None:
    _trim_logs_if_needed_new()


def _is_complex_task(text: str) -> bool:
    return _is_complex_task_new(text)


def _is_greeting(text: str) -> bool:
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


def _run_graph_agent_task(
    user_text: str,
    *,
    allow_file_write: bool,
    allow_shell: bool,
    allow_applescript: bool,
    allow_gui: bool,
    allow_shortcuts: bool = False,
    gui_mode: str = "auto",
) -> None:
    _run_graph_agent_task_new(
        user_text,
        allow_file_write=allow_file_write,
        allow_shell=allow_shell,
        allow_applescript=allow_applescript,
        allow_gui=allow_gui,
        allow_shortcuts=allow_shortcuts,
        gui_mode=gui_mode,
    )




def log(text: str, category: str = "info") -> None:
    _log_new(text, category)


def log_agent_message(agent_type: AgentType, message: str) -> None:
    _log_agent_message_new(agent_type, message)


def _log_replace_last(text: str, category: str = "info") -> None:
    _log_replace_at_new(index=-1, text=text, category=category)


def _log_reserve_line(category: str = "info") -> int:
    return _log_reserve_line_new(category)


def _log_replace_at(index: int, text: str, category: str = "info") -> None:
    _log_replace_at_new(index, text, category)


def _load_cleanup_config() -> Dict[str, Any]:
    return _load_cleanup_config_new()


def _save_cleanup_config(cfg: Dict[str, Any]) -> None:
    _save_cleanup_config_new(cfg)



def get_logs() -> List[Tuple[str, str]]:
    return _get_logs_new()


def get_agent_messages() -> List[Tuple[str, str]]:
    return _get_agent_messages_new()


def get_agent_cursor_position() -> Point:
    return _get_agent_cursor_position_new()


def _list_editors(cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    return _get_editors_list_new(cfg)


def _resolve_editor_arg(cfg: Dict[str, Any], editor: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    return _resolve_editor_arg_new(cfg, editor)


def _find_module(cfg: Dict[str, Any], editor: str, module_id: str) -> Optional[Any]:
    return _find_module_new(cfg, editor, module_id)


def _set_module_enabled(cfg: Dict[str, Any], ref: Any, enabled: bool) -> bool:
    return _set_module_enabled_new(cfg, ref, enabled)


def _script_env() -> Dict[str, str]:
    return _script_env_new()


def _run_script(script_path: str) -> int:
    return _run_script_new(script_path)


def _run_cleanup(cfg: Dict[str, Any], editor: str, dry_run: bool = False, **kwargs) -> Tuple[bool, str]:
    """Wrapper for cleanup runner. Accepts optional keyword args (e.g., log_callback) and forwards them."""
    try:
        return _run_cleanup_new(cfg, editor, dry_run, **kwargs)
    except TypeError:
        # Fallback for older signature: call without kwargs
        return _run_cleanup_new(cfg, editor, dry_run)


def _perform_install(cfg: Dict[str, Any], editor: str) -> Tuple[bool, str]:
    return _perform_install_new(cfg, editor)


def _load_env() -> None:
    _load_env_new()



def _monitor_get_sudo_password() -> str:
    _load_env()
    return str(os.getenv("SUDO_PASSWORD") or "").strip()


def _load_monitor_settings() -> None:
    _load_monitor_settings_new()


def _maybe_log_monitor_ingest(message: str) -> None:
    try:
        fn = globals().get("log")
        if callable(fn):
            fn(message, "info")
    except Exception:
        return


def _monitor_db_read_since_id(db_path: str, last_id: int, limit: int = 5000) -> List[Dict[str, Any]]:
    return _monitor_db_read_since_id_new(db_path, last_id, limit)


def _monitor_db_get_max_id(db_path: str) -> int:
    return _monitor_db_get_max_id_new(db_path)


def _format_monitor_summary(
    *,
    title: str,
    source: str,
    targets: List[str],
    ts_from: int,
    ts_to: int,
    total_events: int,
    by_target: Dict[str, int],
    by_type: Dict[str, int],
    top_paths: Dict[str, List[Tuple[str, int]]],
    include_processes: bool,
    top_processes: List[Tuple[str, int]],
) -> str:
    return _format_monitor_summary_new(
        title=title,
        source=source,
        targets=targets,
        ts_from=ts_from,
        ts_to=ts_to,
        total_events=total_events,
        by_target=by_target,
        by_type=by_type,
        top_paths=top_paths,
        include_processes=include_processes,
        top_processes=top_processes,
    )


def _save_monitor_settings() -> bool:
    return _save_monitor_settings_new()


def _load_monitor_targets() -> None:
    _load_monitor_targets_new()


def _save_monitor_targets() -> bool:
    return _save_monitor_targets_new()


def _monitor_resolve_watch_items(targets: Set[str]) -> List[Tuple[str, str]]:
    return _monitor_resolve_watch_items_new(targets)



def _load_ui_settings() -> None:
    """Load UI settings from file."""
    try:
        _load_env()
        if not os.path.exists(UI_SETTINGS_PATH):
            env_unsafe = _env_bool(os.getenv("SYSTEM_CLI_UNSAFE_MODE"))
            if env_unsafe is None:
                env_unsafe = _env_bool(os.getenv("SYSTEM_CLI_AUTO_CONFIRM"))
            if env_unsafe is not None:
                state.ui_unsafe_mode = bool(env_unsafe)
            return
        
        with open(UI_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        state.ui_theme = str(data.get("theme") or "monaco").strip().lower()
        state.ui_lang = normalize_lang(data.get("ui_lang"))
        state.chat_lang = normalize_lang(data.get("chat_lang"))
        state.ui_streaming = bool(data.get("streaming", True))
        state.ui_gui_mode = str(data.get("gui_mode") or "auto").strip().lower()
        state.ui_execution_mode = str(data.get("execution_mode") or "native").strip().lower()
        
        if "unsafe_mode" in data:
            state.ui_unsafe_mode = bool(data.get("unsafe_mode"))
        
        state.automation_allow_shortcuts = bool(data.get("automation_allow_shortcuts", False))
        state.ui_left_panel_ratio = float(data.get("left_panel_ratio", 0.6))
        state.ui_scroll_target = str(data.get("scroll_target", "log"))
        state.ui_log_follow = bool(data.get("log_follow", True))
        state.ui_agents_follow = bool(data.get("agents_follow", True))
        state.ui_dev_code_provider = str(data.get("dev_code_provider", "vibe-cli")).strip().lower()
        state.ui_self_healing = bool(data.get("self_healing", False))
        state.learning_mode = bool(data.get("learning_mode", False))
        rl = int(data.get("recursion_limit", 100))
        state.ui_recursion_limit = max(1, rl)
        
        # Load MCP Client State
        try:
            from mcp_integration.core.mcp_client_manager import get_mcp_client_manager
            mgr = get_mcp_client_manager()
            state.mcp_client_type = mgr.active_client.value
        except ImportError:
            pass
            
    except Exception:
        pass


def _save_ui_settings() -> bool:
    try:
        os.makedirs(SYSTEM_CLI_DIR, exist_ok=True)
        payload = {
            "theme": str(state.ui_theme or "monaco").strip().lower() or "monaco",
            "ui_lang": normalize_lang(state.ui_lang),
            "chat_lang": normalize_lang(state.chat_lang),
            "streaming": bool(getattr(state, "ui_streaming", True)),
            "gui_mode": str(getattr(state, "ui_gui_mode", "auto") or "auto").strip().lower() or "auto",
            "execution_mode": str(getattr(state, "ui_execution_mode", "native") or "native").strip().lower() or "native",
            "unsafe_mode": bool(state.ui_unsafe_mode),
            "automation_allow_shortcuts": bool(getattr(state, "automation_allow_shortcuts", False)),
            "left_panel_ratio": float(getattr(state, "ui_left_panel_ratio", 0.6)),
            "scroll_target": str(getattr(state, "ui_scroll_target", "log")),
            "log_follow": bool(getattr(state, "ui_log_follow", True)),
            "agents_follow": bool(getattr(state, "ui_agents_follow", True)),
            "dev_code_provider": str(getattr(state, "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower() or "vibe-cli",
            "self_healing": bool(getattr(state, "ui_self_healing", False)),
            "learning_mode": bool(getattr(state, "learning_mode", False)),
            "recursion_limit": int(getattr(state, "ui_recursion_limit", 100)),
            "mcp_client_type": str(getattr(state, "mcp_client_type", "open_mcp")).strip().lower(),
        }
        with open(UI_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _get_reply_language_label() -> str:
    # Keep internal prompts English; this only sets desired assistant output language.
    return lang_name(state.chat_lang)


def _load_llm_settings() -> None:
    return _load_llm_settings_new()


def _save_llm_settings(provider: str, main_model: str, vision_model: str) -> bool:
    return _save_llm_settings_new(provider, main_model, vision_model)


def _get_llm_signature() -> str:
    return "|".join(
        [
            str(os.getenv("LLM_PROVIDER") or ""),
            str(os.getenv("COPILOT_MODEL") or ""),
            str(os.getenv("COPILOT_VISION_MODEL") or ""),
        ]
    )


def _reset_agent_llm() -> None:
    return _reset_agent_llm_new()


def _monitor_start_selected() -> Tuple[bool, str]:
    return _monitor_start_selected_new()


def _monitor_stop_selected() -> Tuple[bool, str]:
    return _monitor_stop_selected_new()


def _scan_traces(editor: str) -> Dict[str, List[str]]:
    return _scan_traces_new(editor)


def _get_editors_list() -> List[Tuple[str, str]]:
    # The underlying implementation expects a cleanup config dict argument.
    # Load current cleanup config and forward it to the function so the
    # TUI can render editors without error.
    try:
        cfg = _load_cleanup_config()
    except Exception:
        cfg = {}
    return _get_editors_list_new(cfg)


def _apply_default_monitor_targets() -> None:
    # Optional logic to add default targets
    pass


def _monitor_db_insert(
    db_path: str,
    *,
    source: str,
    event_type: str,
    src_path: str,
    dest_path: str,
    is_directory: bool,
    target_key: str,
    pid: int = 0,
    process: str = "",
    raw_line: str = "",
) -> None:
    try:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO events(ts, source, event_type, src_path, dest_path, is_directory, target_key, pid, process, raw_line) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    int(time.time()),
                    str(source),
                    str(event_type),
                    str(src_path),
                    str(dest_path),
                    1 if is_directory else 0,
                    str(target_key),
                    int(pid or 0),
                    str(process or ""),
                    str(raw_line or ""),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return


def _ensure_agent_ready() -> Tuple[bool, str]:
    if CopilotLLM is None or SystemMessage is None or HumanMessage is None:
        return False, "LLM недоступний (нема langchain_core або providers/copilot.py)"

    _load_env()
    _load_llm_settings()
    sig = _get_llm_signature()

    provider = str(os.getenv("LLM_PROVIDER") or "copilot").strip().lower() or "copilot"
    if provider != "copilot":
        return False, f"Unsupported LLM provider: {provider}"

    if agent_session.llm is None or agent_session.llm_signature != sig:
        agent_session.llm = CopilotLLM(model_name=os.getenv("COPILOT_MODEL"), vision_model_name=os.getenv("COPILOT_VISION_MODEL"))
        agent_session.llm_signature = sig
    return True, "OK"


def _is_confirmed_run(text: str) -> bool:
    return "confirm_run" in text.lower()


def _is_confirmed_shell(text: str) -> bool:
    return "confirm_shell" in text.lower()


def _is_confirmed_applescript(text: str) -> bool:
    return "confirm_applescript" in text.lower()


def _is_confirmed_gui(text: str) -> bool:
    return "confirm_gui" in text.lower()


def _is_confirmed_shortcuts(text: str) -> bool:
    return "confirm_shortcuts" in text.lower()


@dataclass
class CommandPermissions:
    allow_run: bool = False
    allow_shell: bool = False
    allow_applescript: bool = False
    allow_gui: bool = False


def _permissions_from_text(text: str) -> CommandPermissions:
    return CommandPermissions(
        allow_run=_is_confirmed_run(text),
        allow_shell=_is_confirmed_shell(text),
        allow_applescript=_is_confirmed_applescript(text),
        allow_gui=_is_confirmed_gui(text),
    )


_agent_last_permissions = CommandPermissions()


def _safe_abspath(path: str) -> str:
    expanded = os.path.expanduser(str(path or "")).strip()
    if not expanded:
        return ""
    if os.path.isabs(expanded):
        return expanded

    raw = expanded
    if raw.startswith("./"):
        raw = raw[2:]

    cleanup_dir = os.path.join(SCRIPT_DIR, "cleanup_scripts")
    base = os.path.basename(raw)

    candidates = [
        os.path.abspath(os.path.join(SCRIPT_DIR, raw)),
        os.path.abspath(os.path.join(cleanup_dir, raw)),
        os.path.abspath(os.path.join(cleanup_dir, base)),
        os.path.abspath(os.path.join(SCRIPT_DIR, base)),
    ]

    for p in candidates:
        if os.path.exists(p):
            return p

    return candidates[0]


def _tool_scan_traces(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_scan_traces_new(args)


def _tool_list_dir(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_list_dir_new(args)


def _tool_organize_desktop_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_organize_desktop_wrapper_new(args)


def _tool_chrome_open_url(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_chrome_open_url_new(args)


def _tool_chrome_active_tab(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_chrome_active_tab_new(args)


def _tool_open_url(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_open_url_new(args)


def _tool_open_app(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_open_app_new(args)


def _tool_run_shell_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_run_shell_wrapper_new(args)


def _tool_run_shortcut(args: Dict[str, Any], allow_shell: bool) -> Dict[str, Any]:
    return _tool_run_shortcut_new(args, allow_shell)


def _tool_run_automator(args: Dict[str, Any], allow_shell: bool) -> Dict[str, Any]:
    return _tool_run_automator_new(args, allow_shell)


def _tool_run_applescript(args: Dict[str, Any], allow_applescript: Optional[bool] = None) -> Dict[str, Any]:
    return _tool_run_applescript_new(args, allow_applescript)


def _tool_read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_read_file_new(args)


def _tool_grep(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_grep_new(args)


def _tool_take_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_take_screenshot_new(args)


def _tool_create_module(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_create_module_new(args)



def _init_agent_tools() -> None:
    return _init_agent_tools_new()


def _agent_send_with_stream(user_text: str) -> Tuple[bool, str]:
    """Stream agent response in real-time (chat-only; no execution)."""
    ok, msg = _ensure_agent_ready()
    if not ok:
        return False, msg

    _load_ui_settings()

    # Set processing state
    state.agent_processing = True

    system_prompt = (
        "You are a chat assistant inside a macOS automation TUI.\n"
        "Chat mode is for discussion, clarification, and planning only.\n"
        "Do NOT execute actions.\n"
        "If the user wants something executed, instruct them to use /task <...> (Trinity).\n\n"
        f"Reply in {lang_name(state.chat_lang)}. Be concise and practical.\n"
    )

    if not agent_session.messages:
        agent_session.messages = [SystemMessage(content=system_prompt)]
    else:
        try:
            if SystemMessage and isinstance(agent_session.messages[0], SystemMessage):
                agent_session.messages[0] = SystemMessage(content=system_prompt)
        except Exception:
            pass

    agent_session.messages.append(HumanMessage(content=str(user_text or "")))

    llm = agent_session.llm
    
    # Start streaming response
    try:
        try:
            from tui.layout import force_ui_update
            force_ui_update()
        except ImportError:
            pass

        accumulated_content = ""

        # Reserve a line for assistant streaming output
        stream_idx = _log_reserve_line("action")

        def _on_delta(piece: str) -> None:
            nonlocal accumulated_content, stream_idx
            accumulated_content += piece
            # Guard against out-of-range index after log trimming
            if 0 <= stream_idx < len(state.logs):
                _log_replace_at(stream_idx, accumulated_content, "action")
            else:
                # Index became invalid after trimming, reserve new line
                stream_idx = _log_reserve_line("action")
                _log_replace_at(stream_idx, accumulated_content, "action")
            try:
                from tui.layout import force_ui_update
                force_ui_update()
            except Exception:
                pass

        if hasattr(llm, "invoke_with_stream"):
            resp = llm.invoke_with_stream(agent_session.messages, on_delta=_on_delta)
        else:
            resp = llm.invoke(agent_session.messages)
            accumulated_content = str(getattr(resp, "content", "") or "")
            # Guard against out-of-range index after log trimming
            if 0 <= stream_idx < len(state.logs):
                _log_replace_at(stream_idx, accumulated_content, "action")
            else:
                # Index became invalid after trimming, reserve new line
                stream_idx = _log_reserve_line("action")
                _log_replace_at(stream_idx, accumulated_content, "action")

        final_message = resp if isinstance(resp, AIMessage) else AIMessage(content=str(getattr(resp, "content", "") or ""))
        if not accumulated_content:
            accumulated_content = str(getattr(final_message, "content", "") or "")
            # Guard against out-of-range index after log trimming
            if 0 <= stream_idx < len(state.logs):
                _log_replace_at(stream_idx, accumulated_content, "action")
            else:
                # Index became invalid after trimming, reserve new line
                stream_idx = _log_reserve_line("action")
                _log_replace_at(stream_idx, accumulated_content, "action")

        agent_session.messages.append(final_message)

        return True, accumulated_content

    except Exception as e:
        return False, f"Streaming error: {str(e)}"
    finally:
        state.agent_processing = False
        _trim_logs_if_needed()


def _agent_send_no_stream(user_text: str) -> Tuple[bool, str]:
    ok, msg = _ensure_agent_ready()
    if not ok:
        return False, msg

    _load_ui_settings()
    state.agent_processing = True

    system_prompt = (
        "You are a chat assistant inside a macOS automation TUI.\n"
        "Chat mode is for discussion, clarification, and planning only.\n"
        "Do NOT execute actions.\n"
        "If the user wants something executed, instruct them to use /task <...> (Trinity).\n\n"
        f"Reply in {lang_name(state.chat_lang)}. Be concise and practical.\n"
    )

    if not agent_session.messages:
        agent_session.messages = [SystemMessage(content=system_prompt)]
    else:
        try:
            if SystemMessage and isinstance(agent_session.messages[0], SystemMessage):
                agent_session.messages[0] = SystemMessage(content=system_prompt)
        except Exception:
            pass

    agent_session.messages.append(HumanMessage(content=str(user_text or "")))

    llm = agent_session.llm

    try:
        resp = llm.invoke(agent_session.messages)
        final_message = resp if isinstance(resp, AIMessage) else AIMessage(content=str(getattr(resp, "content", "") or ""))
        agent_session.messages.append(final_message)
        return True, str(getattr(final_message, "content", "") or "")
    finally:
        state.agent_processing = False
        _trim_logs_if_needed()


def _tool_ui_streaming_status() -> Dict[str, Any]:
    return _tool_ui_streaming_status_new()


def _tool_ui_streaming_set(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_ui_streaming_set_new(args)


def _agent_send(user_text: str) -> Tuple[bool, str]:
    if bool(getattr(state, "ui_streaming", True)):
        return _agent_send_with_stream_new(user_text)
    return _agent_send_no_stream_new(user_text)





@dataclass
class _DummyProcService:
    running: bool = False

    def start(self, *args: Any, **kwargs: Any) -> Tuple[bool, str]:
        self.running = True
        return True, "Monitoring started."

    def stop(self) -> Tuple[bool, str]:
        self.running = False
        return True, "Monitoring stopped."


monitor_service = _DummyProcService()


class _ProcTraceService:
    """Simple process-trace service wrapper around fs_usage/opensnoop.

    It spawns the tool, reads stdout lines and tries to parse pid/process/path
    and writes events into the monitor DB using `_monitor_db_insert`.
    This is intentionally minimal and fails gracefully when tool is absent or
    blocked by SIP.
    """

    def __init__(self, cmd_name: str, cmd_base: list):
        self.cmd_name = str(cmd_name)
        self.cmd_base = list(cmd_base)
        self.proc = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.running = False

    def _parse_and_insert(self, line: str) -> None:
        try:
            # naive parsing: look for pid and path
            pid = 0
            process = ""
            path = ""
            # PID: first integer token after timestamp (fallback)
            m = re.search(r"\b(\d{2,7})\b", line)
            if m:
                try:
                    pid = int(m.group(1))
                except Exception:
                    pid = 0
            # path: first token starting with /
            m2 = re.search(r"(/[^\s]+)", line)
            if m2:
                path = m2.group(1)
            # process: try last token (often contains execname), prefer token with dot+digits
            m_proc = re.search(r"([A-Za-z0-9_\-\.]+(?:\.[0-9]+)?)\s*$", line)
            if m_proc:
                process = m_proc.group(1)

            # If pid wasn't found, try to resolve by process name using pgrep
            if not pid and process:
                try:
                    out = subprocess.check_output(["pgrep", "-f", process], text=True).strip().splitlines()
                    if out:
                        pid = int(out[0])
                except Exception:
                    pass

            # Insert into DB using existing utility
            try:
                _monitor_db_insert(
                    MONITOR_EVENTS_DB_PATH,
                    source=self.cmd_name,
                    event_type="access",
                    src_path=path or "",
                    dest_path="",
                    is_directory=False,
                    target_key="",
                    pid=int(pid or 0),
                    process=str(process or ""),
                    raw_line=str(line or ""),
                )
            except Exception:
                return
        except Exception:
            return

    def _reader(self, stream: Any) -> None:
        try:
            for ln in iter(stream.readline, ""):
                if self.stop_event.is_set():
                    break
                if not ln:
                    continue
                line = str(ln or "").strip()
                if not line:
                    continue
                self._parse_and_insert(line)
        except Exception:
            return

    def start(self, pid: Optional[int] = None) -> Tuple[bool, str]:
        if self.running:
            return True, f"{self.cmd_name} already running"
        # check availability
        if shutil.which(self.cmd_base[0]) is None:
            return False, f"{self.cmd_base[0]} not found on PATH"

        cmd = list(self.cmd_base)
        if pid:
            # pass pid as positional argument for tools like fs_usage
            cmd += [str(int(pid))]

        # Optionally run under sudo if environment / state indicates it
        use_sudo = False
        try:
            from tui.state import state as _st
            use_sudo = bool(getattr(_st, "monitor_use_sudo", False))
        except Exception:
            use_sudo = False
        if not use_sudo:
            # also allow explicit env override
            use_sudo = bool(str(os.environ.get("FORCE_MONITOR_SUDO") or "").strip())

        if use_sudo:
            sudo_pwd = str(os.environ.get("SUDO_PASSWORD") or "").strip()
            cmd = ["sudo", "-S"] + cmd

        try:
            self.stop_event.clear()
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE if use_sudo and sudo_pwd else None, text=True)
            if use_sudo and sudo_pwd and self.proc.stdin:
                try:
                    # supply password
                    self.proc.stdin.write(sudo_pwd + "\n")
                    self.proc.stdin.flush()
                except Exception:
                    pass
            if self.proc.stdout:
                self.thread = threading.Thread(target=self._reader, args=(self.proc.stdout,), daemon=True)
                self.thread.start()
            self.running = True
            return True, f"{self.cmd_name} started"
        except Exception as e:
            return False, f"Failed to start {self.cmd_name}: {e}"

    def stop(self) -> Tuple[bool, str]:
        try:
            self.stop_event.set()
            if self.proc:
                try:
                    self.proc.terminate()
                except Exception:
                    pass
            if self.thread:
                try:
                    self.thread.join(timeout=2)
                except Exception:
                    pass
        finally:
            self.proc = None
            self.thread = None
            self.running = False
        return True, f"{self.cmd_name} stopped"


fs_usage_service = _ProcTraceService("fs_usage", ["fs_usage", "-w", "-f", "filesys"])
opensnoop_service = _ProcTraceService("opensnoop", ["opensnoop"])


recorder_service: Any = None
recorder_last_session_dir: str = ""


def _recordings_base_dir() -> str:
    return _recordings_base_dir_new()


def _recordings_last_path() -> str:
    return _recordings_last_path_new()


def _recordings_save_last(dir_path: str) -> None:
    _recordings_save_last_new(dir_path)


def _recordings_load_last() -> str:
    return _recordings_load_last_new()


def _recordings_list_session_dirs(limit: int = 10) -> List[str]:
    return _recordings_list_session_dirs_new(limit)


def _recordings_read_meta(dir_path: str) -> Dict[str, Any]:
    return _recordings_read_meta_new(dir_path)


def _recordings_update_meta(dir_path: str, updates: Dict[str, Any]) -> None:
    _recordings_update_meta_new(dir_path, updates)


def _extract_automation_title(text: str) -> str:
    return _extract_automation_title_new(text)


def _extract_automation_prompt(text: str) -> str:
    return _extract_automation_prompt_new(text)


def _analyze_recording_bg(rec_dir: str, name: str, user_context: str) -> None:
    _analyze_recording_bg_new(
        rec_dir=rec_dir, 
        name=name, 
        user_context=user_context,
        log_fn=log,
        force_ui_update_fn=force_ui_update
    )


def _start_recording_analysis(*, rec_dir: str, name: str, user_context: str) -> None:
    _start_recording_analysis_new(rec_dir=rec_dir, name=name, user_context=user_context)


def _recordings_ensure_meta_name(dir_path: str) -> str:
    return _recordings_ensure_meta_name_new(dir_path)


def _recordings_resolve_last_dir() -> str:
    return _recordings_resolve_last_dir_new()


def _open_in_finder(path: str) -> Tuple[bool, str]:
    # This remains in cli.py as it is a UI utility
    p = str(path or "").strip()
    if not p:
        return False, "Empty path"
    if not os.path.exists(p):
        return False, f"Not found: {p}"
    try:
        proc = subprocess.run(["/usr/bin/open", p], capture_output=True, text=True)
        if int(proc.returncode or 0) == 0:
            return True, f"Opened: {p}"
        proc2 = subprocess.run(["/usr/bin/open", "-a", "Finder", p], capture_output=True, text=True)
        if int(proc2.returncode or 0) == 0:
            return True, f"Opened: {p}"
        err = ((proc.stderr or "") + "\n" + (proc2.stderr or "")).strip()
        out = ((proc.stdout or "") + "\n" + (proc2.stdout or "")).strip()
        tail = (err or out).strip()
        tail = tail[-1200:] if tail else ""
        return False, f"Failed to open: {p}" + ("\n" + tail if tail else "")
    except Exception as e:
        return False, f"Failed to open: {p}\n{e}"


def _get_recorder_service() -> Any:
    return _get_recorder_service_new()



def _monitor_summary_start_if_needed() -> None:
    _monitor_summary_start_if_needed_new()


def _monitor_summary_stop_if_needed() -> None:
    _monitor_summary_stop_if_needed_new()


def _ensure_cleanup_cfg_loaded() -> None:
    global cleanup_cfg
    if cleanup_cfg is not None:
        return
    cleanup_cfg = _load_cleanup_config()


def _get_cleanup_cfg() -> Any:
    global cleanup_cfg
    _ensure_cleanup_cfg_loaded()
    return cleanup_cfg


def _set_cleanup_cfg(cfg: Any) -> None:
    global cleanup_cfg
    cleanup_cfg = cfg

def _get_custom_tasks_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    """Return custom tasks menu items."""
    return [
        ("menu.custom.section.recorder", None, "section"),
        ("menu.custom.recorder_start", "recorder_start", None),
        ("menu.custom.recorder_stop", "recorder_stop", None),
        ("menu.custom.section.recordings", None, "section"),
        ("menu.custom.recorder_open_last", "recorder_open_last", None),
        ("menu.custom.recording_analyze_last", "recording_analyze_last", None),
        ("menu.custom.section.automations", None, "section"),
        ("menu.custom.automation_run_last", "automation_run_last", None),
    ]


def _get_monitoring_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    """Return monitoring menu items."""
    return [
        ("menu.monitoring.start_stop", MenuLevel.MONITOR_CONTROL, None),
        ("menu.monitoring.targets", MenuLevel.MONITOR_TARGETS, None),
    ]


def _custom_task_automation_run_dir(rec_dir: str) -> Tuple[bool, str]:
    ok, msg = _custom_tasks_allowed()
    if not ok:
        return False, msg

    if not bool(getattr(state, "ui_unsafe_mode", False)):
        return False, "Enable Unsafe mode (Settings -> Unsafe mode) to run automation"

    pw = _permissions_wizard(
        require_accessibility=True,
        require_screen_recording=False,
        require_automation=True,
        prompt=True,
        open_settings=True,
    )
    missing = pw.get("missing") or []
    if missing:
        return False, f"Missing permissions: {', '.join(missing)}"

    meta = _recordings_read_meta(rec_dir)
    prompt = str(meta.get("automation_prompt") or "").strip()
    if not prompt:
        return False, "No automation prompt in this recording. Run Analyze first."

    title = str(meta.get("automation_title") or "").strip() or str(meta.get("name") or "").strip() or "Automation"
    # Native-first. GUI is fallback controlled by gui_mode.
    gui_mode = str(getattr(state, "ui_gui_mode", "auto") or "auto").strip().lower() or "auto"

    def _runner() -> None:
        state.agent_processing = True
        try:
            log(f"[AUTO] {title}", "action")
            unsafe_mode = bool(getattr(state, "ui_unsafe_mode", False))
            allow_file_write = unsafe_mode
            allow_shell = unsafe_mode
            allow_applescript = unsafe_mode
            allow_gui = unsafe_mode
            allow_shortcuts = bool(getattr(state, "automation_allow_shortcuts", False))
            _run_graph_agent_task(
                prompt,
                allow_file_write=allow_file_write,
                allow_shell=allow_shell,
                allow_applescript=allow_applescript,
                allow_gui=allow_gui,
                allow_shortcuts=allow_shortcuts,
                gui_mode=gui_mode,
            )
        finally:
            state.agent_processing = False
            _trim_logs_if_needed()
            try:
                from tui.layout import force_ui_update

                force_ui_update()
            except Exception:
                pass

    threading.Thread(target=_runner, daemon=True).start()
    return True, "Automation started"


def _custom_task_automation_run_last() -> Tuple[bool, str]:
    ok, msg = _custom_tasks_allowed()
    if not ok:
        return False, msg

    rec_dir = _recordings_resolve_last_dir()
    if not rec_dir:
        return False, "Немає останнього запису"
    return _custom_task_automation_run_dir(rec_dir)


def _custom_task_automation_permissions_help() -> Tuple[bool, str]:
    ok, msg = _custom_tasks_allowed()
    if not ok:
        return False, msg

    if str(state.ui_lang or "").strip().lower() == "uk":
        body = (
            "Дозволи macOS для Recorder + Automation:\n\n"
            "1) Accessibility (Доступність):\n"
            "   System Settings -> Privacy & Security -> Accessibility\n"
            "   Увімкни для застосунку, з якого запускаєш SYSTEM CLI (Terminal / iTerm / VS Code / Windsurf).\n\n"
            "2) Screen Recording (Запис екрана):\n"
            "   System Settings -> Privacy & Security -> Screen Recording\n"
            "   Увімкни для того ж застосунку (щоб зберігались screenshots у записі).\n\n"
            "3) Automation (Автоматизація):\n"
            "   System Settings -> Privacy & Security -> Automation\n"
            "   Дозволь застосунку-джерелу керувати: \"System Events\" (і за потреби ClearVPN).\n\n"
            "4) Якщо GUI-автоматизація не клікає/не бачить UI:\n"
            "   Перезапусти застосунок-джерело після видачі дозволів.\n"
        )
    else:
        body = (
            "macOS permissions for Recorder + Automation:\n\n"
            "1) Accessibility:\n"
            "   System Settings -> Privacy & Security -> Accessibility\n"
            "   Enable for the app running SYSTEM CLI (Terminal / iTerm / VS Code / Windsurf).\n\n"
            "2) Screen Recording:\n"
            "   System Settings -> Privacy & Security -> Screen Recording\n"
            "   Enable for the same app (for screenshots during recording).\n\n"
            "3) Automation:\n"
            "   System Settings -> Privacy & Security -> Automation\n"
            "   Allow the source app to control \"System Events\" (and ClearVPN if prompted).\n\n"
            "4) If GUI automation doesn't interact with UI:\n"
            "   Restart the source app after granting permissions.\n"
        )

    log(body, "info")
    return True, "OK"


def _custom_tasks_allowed() -> Tuple[bool, str]:
    return _custom_tasks_allowed_new()


def _custom_task_windsurf_register() -> Tuple[bool, str]:
    ok, msg = _custom_tasks_allowed()
    if not ok:
        return False, msg

    script_path = os.path.join(SCRIPT_DIR, "custom_tasks", "windsurf_registration.py")
    if not os.path.exists(script_path):
        return False, f"Not found: {script_path}"

    result: Dict[str, Any] = {"returncode": None, "stdout": "", "stderr": ""}

    def _runner() -> None:
        proc = subprocess.run(
            [sys.executable, script_path],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        result["returncode"] = int(proc.returncode)
        result["stdout"] = str(proc.stdout or "")
        result["stderr"] = str(proc.stderr or "")

    run_in_terminal(_runner)

    rc = result.get("returncode")
    out = (result.get("stdout") or "")
    err = (result.get("stderr") or "")

    tail = ""
    combined = (out + "\n" + err).strip()
    if combined:
        tail = combined[-2000:]

    if rc == 0:
        return True, "Windsurf registration finished" + ("\n" + tail if tail else "")
    return False, f"Windsurf registration failed (code={rc})" + ("\n" + tail if tail else "")


def _custom_task_recorder_start() -> Tuple[bool, str]:
    return _custom_task_recorder_start_new()


def _custom_task_recorder_stop() -> Tuple[bool, str]:
    return _custom_task_recorder_stop_new()


def _custom_task_recorder_open_last() -> Tuple[bool, str]:
    return _custom_task_recorder_open_last_new()


def _custom_task_recording_analyze_last() -> Tuple[bool, str]:
    ok, msg = _custom_tasks_allowed()
    if not ok:
        return False, msg

    rec_dir = _recordings_resolve_last_dir()
    if not rec_dir:
        return False, "Немає останнього запису"

    ok_llm, llm_msg = _ensure_agent_ready()
    if not ok_llm:
        return False, llm_msg

    pw = _permissions_wizard(
        require_accessibility=False,
        require_screen_recording=True,
        require_automation=False,
        prompt=True,
        open_settings=True,
    )
    missing = pw.get("missing") or []
    if missing:
        return False, "Screen Recording permission required for analysis (screenshots needed for richer LLM context)"

    meta = _recordings_read_meta(rec_dir)
    name = str(meta.get("name") or "").strip() or _recordings_ensure_meta_name(rec_dir)

    state.recording_analysis_waiting = True
    state.recording_analysis_dir = rec_dir
    state.recording_analysis_name = name
    try:
        state.menu_level = MenuLevel.NONE
    except Exception:
        pass
    try:
        from tui.layout import force_ui_update

        force_ui_update()
    except Exception:
        pass

    if not isinstance(state.ui_lang, str):
        state.ui_lang = ''
    if not hasattr(state, 'ui_lang') or not isinstance(state.ui_lang, str):
        state.ui_lang = ''
    else:
        state.ui_lang = str(state.ui_lang).strip().lower()

    if state.ui_lang == 'uk':
        # Add logic for 'uk' if necessary
        pass

def _get_llm_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    return [
        ("Global Defaults", MenuLevel.LLM_DEFAULTS, None),
        ("Atlas (Planner)", MenuLevel.LLM_ATLAS, None),
        ("Tetyana (Executor)", MenuLevel.LLM_TETYANA, None),
        ("Grisha (Verifier)", MenuLevel.LLM_GRISHA, None),
        ("System Vision", MenuLevel.LLM_VISION, None),
    ]


def _get_llm_sub_menu_items(level: Any) -> List[Tuple[str, Any]]:
    """Get LLM settings sub-menu items for a specific agent/section."""
    if not isinstance(level, MenuLevel):
        raise TypeError(f"Expected level to be of type MenuLevel, got {type(level).__name__}")
    
    # Determine section from level
    section = ""
    if not isinstance(level, MenuLevel):
        raise TypeError(f"Expected level to be of type MenuLevel, got {type(level).__name__}")

    # Determine section from level
    section = ""
    if level == MenuLevel.LLM_ATLAS:
        section = "atlas"
    elif level == MenuLevel.LLM_TETYANA:
        section = "tetyana"
    elif level == MenuLevel.LLM_GRISHA:
        section = "grisha"
    elif level == MenuLevel.LLM_VISION:
        section = "vision"
    elif level == MenuLevel.LLM_DEFAULTS:
        section = "defaults"
    else:
        return []
    status = {}
    try:
        status_res = _tool_llm_status_new({"section": section})
        if isinstance(status_res, dict):
            status = status_res
    except Exception:
        pass
    prov = str(status.get("provider", "copilot"))
    mod = str(status.get("model", ""))

    if section == "defaults":
        main_mod = str(status.get("main_model", ""))
        vis_mod = str(status.get("vision_model", ""))
        return [
            (f"Provider: {prov}", "provider", None),
            (f"Main Model: {main_mod}", "main_model", None),
            (f"Vision Model: {vis_mod}", "vision_model", None),
        ]

    return [
        (f"Provider: {prov}", "provider", None),
        (f"Model: {mod}", "model", None),
    ]


def _get_agent_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    mode = "ON" if agent_chat_mode and agent_session.enabled else "OFF"
    unsafe = "ON" if bool(getattr(state, "ui_unsafe_mode", False)) else "OFF"
    learning = "ON" if bool(getattr(state, "learning_mode", False)) else "OFF"
    step_limit = int(getattr(state, "ui_recursion_limit", 100))
    return [
        (f"Agent: {mode}", None, None),
        (f"Unsafe mode: {unsafe}", None, None),
        (f"Learning mode: {learning}", "learning_mode", None),
        (f"Step limit: {step_limit}", "ui_recursion_limit", None),
    ]


def _get_automation_permissions_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    shortcuts = "ON" if bool(getattr(state, "automation_allow_shortcuts", False)) else "OFF"
    exec_mode = str(getattr(state, "ui_execution_mode", "native") or "native").strip().lower() or "native"
    exec_label = "NATIVE" if exec_mode == "native" else "GUI"
    
    def _env_on_off(var, default="0"):
        val = str(os.getenv(var) or default).strip().lower()
        return "ON" if val in {"1", "true", "yes", "on"} else "OFF"
        
    return [
        (f"Execution mode: {exec_label}", "ui_execution_mode", None),
        (f"Shortcuts: {shortcuts}", "automation_allow_shortcuts", None),
        (f"Allow Shell: {_env_on_off('TRINITY_ALLOW_SHELL')}", "env_shell", None),
        (f"Allow Write: {_env_on_off('TRINITY_ALLOW_WRITE', '1')}", "env_write", None),
        (f"Allow AppleScript: {_env_on_off('TRINITY_ALLOW_APPLESCRIPT')}", "env_applescript", None),
        (f"Allow GUI: {_env_on_off('TRINITY_ALLOW_GUI')}", "env_gui", None),
        (f"Hyper Mode (Auto): {_env_on_off('TRINITY_HYPER_MODE')}", "env_hyper", None),
    ]


def _handle_automation_permissions_enter(ctx: Dict[str, Any]):
    """Handle enter key in automation permissions menu."""
    state, log = ctx["state"], ctx["log"]
    items = _get_automation_permissions_menu_items()
    if not items:
        return
    idx = max(0, min(state.menu_index, len(items) - 1))
    key = items[idx][1]
    
    if key == "ui_execution_mode":
        cur = str(getattr(state, "ui_execution_mode", "native") or "native").strip().lower()
        state.ui_execution_mode = "gui" if cur == "native" else "native"
        _save_ui_settings()
        log(f"Execution mode set to: {state.ui_execution_mode.upper()}", "action")
    elif key == "automation_allow_shortcuts":
        new_val = not bool(getattr(state, "automation_allow_shortcuts", False))
        state.automation_allow_shortcuts = new_val
        _save_ui_settings()
        _update_env_var("TRINITY_ALLOW_SHORTCUTS", "1" if new_val else "0")
        log(f"Shortcuts: {'ON' if new_val else 'OFF'}", "action")
    elif key.startswith("env_"):
        var_map = {
            "env_shell": "TRINITY_ALLOW_SHELL",
            "env_write": "TRINITY_ALLOW_WRITE",
            "env_applescript": "TRINITY_ALLOW_APPLESCRIPT",
            "env_gui": "TRINITY_ALLOW_GUI",
            "env_hyper": "TRINITY_HYPER_MODE",
        }
        var = var_map.get(key)
        if var:
            cur_val = str(os.getenv(var) or ("1" if var == "TRINITY_ALLOW_WRITE" else "0")).strip().lower()
            new_val = "0" if cur_val in {"1", "true", "yes", "on"} else "1"
            if _update_env_var(var, new_val):
                os.environ[var] = new_val
                log(f"{var} set to: {'ON' if new_val == '1' else 'OFF'}", "action")
            else:
                log(f"Failed to update {var} in .env", "error")
    
    ctx["force_ui_update"]()


def _update_env_var(key: str, value: str) -> bool:
    """Update or add a variable in the .env file."""
    env_path = os.path.join(_repo_root, ".env")
    try:
        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            new_lines.append(f"{key}={value}\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        return False


def _get_dev_settings_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    """Return dev settings menu items for code provider selection."""
    provider = str(getattr(state, "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower()
    provider_label = "VIBE-CLI" if provider == "vibe-cli" else "CONTINUE"
    return [
        (f"Code Provider: {provider_label}", "ui_dev_code_provider", None),
    ]


def _get_settings_menu_items() -> List[Tuple[str, Any, Optional[str]]]:
    """Return settings menu items."""
    return [
        ("menu.settings.section.appearance", None, "section"),
        ("menu.settings.appearance", MenuLevel.APPEARANCE, None),
        ("menu.settings.language", MenuLevel.LANGUAGE, None),
        ("menu.settings.locales", MenuLevel.LOCALES, None),
        ("menu.settings.section.agent", None, "section"),
        ("menu.settings.llm", MenuLevel.LLM_SETTINGS, None),
        ("menu.settings.agent", MenuLevel.AGENT_SETTINGS, None),
        ("menu.settings.unsafe_mode", MenuLevel.UNSAFE_MODE, None),
        ("menu.settings.self_healing", MenuLevel.SELF_HEALING, None),
        ("menu.settings.memory_manager", MenuLevel.MEMORY_MANAGER, None),
        ("menu.settings.section.automation", None, "section"),
        ("menu.settings.automation_permissions", MenuLevel.AUTOMATION_PERMISSIONS, None),
        ("menu.settings.mcp_settings", "mcp_settings", None),
    ]


def run_tui() -> None:
    def _style_factory() -> Style:
        theme = str(getattr(state, "ui_theme", "monaco") or "monaco").strip().lower()
        if theme not in THEMES:
            theme = "monaco"
        return Style.from_dict(THEMES.get(theme, THEMES["monaco"]))

    style = DynamicStyle(_style_factory)

    get_custom_tasks_menu_items_cb = globals().get("_get_custom_tasks_menu_items") or (lambda: [])
    get_monitoring_menu_items_cb = globals().get("_get_monitoring_menu_items") or (lambda: [])
    get_settings_menu_items_cb = globals().get("_get_settings_menu_items") or (lambda: [])
    get_llm_menu_items_cb = globals().get("_get_llm_menu_items") or (lambda: [])
    get_llm_sub_menu_items_cb = globals().get("_get_llm_sub_menu_items") or (lambda _: [])
    get_agent_menu_items_cb = globals().get("_get_agent_menu_items") or (lambda: [])
    get_automation_permissions_menu_items_cb = globals().get("_get_automation_permissions_menu_items") or (lambda: [])

    kb, handle_menu_enter = build_keybindings(
        state=state,
        MenuLevel=MenuLevel,
        show_menu=Condition(lambda: state.menu_level != MenuLevel.NONE), # Temporary placeholder
        MAIN_MENU_ITEMS=MAIN_MENU_ITEMS,
        get_custom_tasks_menu_items=get_custom_tasks_menu_items_cb,
        TOP_LANGS=TOP_LANGS,
        lang_name=lang_name,
        log=log,
        save_ui_settings=_save_ui_settings,
        reset_agent_llm=_reset_agent_llm,
        save_monitor_settings=_save_monitor_settings,
        save_monitor_targets=_save_monitor_targets,
        get_monitoring_menu_items=get_monitoring_menu_items_cb,
        get_settings_menu_items=get_settings_menu_items_cb,
        get_llm_menu_items=get_llm_menu_items_cb,
        get_llm_sub_menu_items=get_llm_sub_menu_items_cb,
        get_agent_menu_items=get_agent_menu_items_cb,
        get_automation_permissions_menu_items=_get_automation_permissions_menu_items,
        handle_automation_permissions_enter=_handle_automation_permissions_enter,
        get_editors_list=_get_editors_list,
        get_cleanup_cfg=_get_cleanup_cfg,
        set_cleanup_cfg=_set_cleanup_cfg,
        load_cleanup_config=_load_cleanup_config,
        run_cleanup=_run_cleanup,
        perform_install=_perform_install,
        find_module=_find_module,
        set_module_enabled=_set_module_enabled,
        AVAILABLE_LOCALES=AVAILABLE_LOCALES,
        localization=localization,
        get_monitor_menu_items=_get_monitor_menu_items,
        normalize_menu_index=_normalize_menu_index,
        monitor_stop_selected=_monitor_stop_selected,
        monitor_start_selected=_monitor_start_selected,
        monitor_resolve_watch_items=_monitor_resolve_watch_items,
        monitor_service=monitor_service,
        fs_usage_service=fs_usage_service,
        opensnoop_service=opensnoop_service,
        force_ui_update=force_ui_update,
    )

    show_menu, get_menu_content = build_menu(
        state=state,
        MenuLevel=MenuLevel,
        tr=lambda k, l: tr(k, l),
        lang_name=lang_name,
        MAIN_MENU_ITEMS=MAIN_MENU_ITEMS,
        get_custom_tasks_menu_items=get_custom_tasks_menu_items_cb,
        get_monitoring_menu_items=get_monitoring_menu_items_cb,
        get_settings_menu_items=get_settings_menu_items_cb,
        get_llm_menu_items=get_llm_menu_items_cb,
        get_llm_sub_menu_items=get_llm_sub_menu_items_cb,
        get_agent_menu_items=get_agent_menu_items_cb,
        get_automation_permissions_menu_items=get_automation_permissions_menu_items_cb,
        get_editors_list=_get_editors_list,
        get_cleanup_cfg=_get_cleanup_cfg,
        AVAILABLE_LOCALES=AVAILABLE_LOCALES,
        localization=localization,
        get_monitor_menu_items=_get_monitor_menu_items,
        normalize_menu_index=_normalize_menu_index,
        MONITOR_TARGETS_PATH=MONITOR_TARGETS_PATH,
        MONITOR_EVENTS_DB_PATH=MONITOR_EVENTS_DB_PATH,
        CLEANUP_CONFIG_PATH=CLEANUP_CONFIG_PATH,
        LOCALIZATION_CONFIG_PATH=LOCALIZATION_CONFIG_PATH,
        force_ui_update=force_ui_update,
        on_enter=handle_menu_enter,
    )

    input_kb = KeyBindings()

    @input_kb.add("enter")
    @input_kb.add("c-j")
    def _(event):
        buff = event.current_buffer
        if buff.text.strip():
            buff.validate_and_handle()
        else:
            # If empty, maybe they just want a newline if it's multiline? 
            # No, usually Enter on empty does nothing or clears.
            buff.text = ""

    @input_kb.add("escape", "enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    @input_kb.add("c-v")
    def _(event):
        """Handle paste from clipboard."""
        from prompt_toolkit.clipboard import ClipboardData
        data = event.app.clipboard.get_data()
        if data.text:
            event.current_buffer.insert_text(data.text)

    app = build_app(
        input_key_bindings=input_kb,
        get_header=get_header,
        get_context=get_context,
        get_logs=get_logs,
        get_log_cursor_position=get_log_cursor_position,
        get_agent_messages=get_agent_messages,
        get_agent_cursor_position=get_agent_cursor_position,
        get_menu_content=get_menu_content,
        get_input_prompt=get_input_prompt,
        get_prompt_width=get_prompt_width,
        get_status=get_status,
        input_buffer=input_buffer,
        show_menu=show_menu,
        kb=kb,
        style=style,
    )

    runtime = TuiRuntime(
        app=app,
        log=log,
        load_monitor_targets=_load_monitor_targets,
        load_monitor_settings=_load_monitor_settings,
        load_ui_settings=_load_ui_settings,
        load_env=_load_env,
        load_llm_settings=_load_llm_settings,
        apply_default_monitor_targets=_apply_default_monitor_targets,
        save_ui_settings=_save_ui_settings,
    )
    tui_run_tui(runtime)


def _tool_app_command(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_app_command_new(args)


def _tool_monitor_status() -> Dict[str, Any]:
    return _tool_monitor_status_new()


def _tool_monitor_set_source(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_monitor_set_source_new(args)


def _tool_monitor_set_use_sudo(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_monitor_set_use_sudo_new(args)


def _tool_monitor_start() -> Dict[str, Any]:
    return _tool_monitor_start_new()


def _tool_monitor_stop() -> Dict[str, Any]:
    return _tool_monitor_stop_new()


def _tool_monitor_targets(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_monitor_targets_new(args)


def _scan_installed_apps(app_dirs: List[str]) -> List[str]:
    apps: List[str] = []
    for d in app_dirs:
        try:
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if name.endswith(".app"):
                    apps.append(name[:-4])
        except Exception:
            continue
    # unique preserve order
    seen: Set[str] = set()
    out: List[str] = []
    for a in apps:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def _scan_installed_app_paths(app_dirs: List[str]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for d in app_dirs:
        try:
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if not name.endswith(".app"):
                    continue
                app_name = name[:-4]
                out.append((app_name, os.path.join(d, name)))
        except Exception:
            continue
    # unique by name, prefer first occurrence
    seen: Set[str] = set()
    uniq: List[Tuple[str, str]] = []
    for app_name, app_path in out:
        if app_name in seen:
            continue
        seen.add(app_name)
        uniq.append((app_name, app_path))
    return uniq


def _read_bundle_id(app_path: str) -> str:
    try:
        plist_path = os.path.join(app_path, "Contents", "Info.plist")
        if not os.path.exists(plist_path):
            return ""
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)
        bid = data.get("CFBundleIdentifier")
        return str(bid) if bid else ""
    except Exception:
        return ""


def _get_installed_browsers() -> List[str]:
    app_dirs = ["/Applications", os.path.expanduser("~/Applications")]
    installed = _scan_installed_app_paths(app_dirs)
    keywords_name = [
        "safari",
        "chrome",
        "chromium",
        "firefox",
        "brave",
        "arc",
        "edge",
        "opera",
        "vivaldi",
        "orion",
        "tor",
        "duckduckgo",
        "waterfox",
        "librewolf",
        "zen",
        "yandex",
    ]
    keywords_bundle = [
        "safari",
        "chrome",
        "chromium",
        "firefox",
        "brave",
        "arc",
        "edge",
        "opera",
        "vivaldi",
        "orion",
        "torbrowser",
        "duckduckgo",
        "browser",
    ]
    browsers: List[str] = []
    for app_name, app_path in installed:
        low = app_name.lower()
        if any(k in low for k in keywords_name):
            browsers.append(app_name)
            continue
        bid = _read_bundle_id(app_path).lower()
        if bid and any(k in bid for k in keywords_bundle):
            browsers.append(app_name)
    return sorted({b for b in browsers}, key=lambda x: x.lower())


@dataclass
class MonitorMenuItem:
    key: str
    label: str
    selectable: bool
    category: str
    origin: str = ""


def _get_monitor_menu_items() -> List[MonitorMenuItem]:
    items: List[MonitorMenuItem] = []

    # Editors (from cleanup config)
    items.append(MonitorMenuItem(key="__hdr_editors__", label="EDITORS", selectable=False, category="header"))
    for key, label in _get_editors_list():
        items.append(MonitorMenuItem(key=f"editor:{key}", label=f"{key} - {label}", selectable=True, category="editor"))

    # Browsers (auto-detected)
    items.append(MonitorMenuItem(key="__hdr_browsers__", label="BROWSERS", selectable=False, category="header"))
    app_dirs = ["/Applications", os.path.expanduser("~/Applications")]
    installed_paths = dict(_scan_installed_app_paths(app_dirs))
    browsers = _get_installed_browsers()
    if not browsers:
        items.append(MonitorMenuItem(key="__no_browsers__", label="(no browsers detected in /Applications)", selectable=False, category="note"))
    else:
        for app in browsers:
            origin = ""
            p = installed_paths.get(app, "")
            if p:
                origin = os.path.dirname(p)
            items.append(MonitorMenuItem(key=f"browser:{app}", label=app, selectable=True, category="browser", origin=origin))

    return items


def _normalize_menu_index(items: List[MonitorMenuItem]) -> None:
    if not items:
        state.menu_index = 0
        return

    state.menu_index = max(0, min(state.menu_index, len(items) - 1))
    if items[state.menu_index].selectable:
        return

    # move to nearest selectable
    for direction in (1, -1):
        idx = state.menu_index
        while 0 <= idx < len(items):
            if items[idx].selectable:
                state.menu_index = idx
                return
            idx += direction
    state.menu_index = 0


localization = LocalizationConfig.load()
cleanup_cfg = None


def log_agent_message(agent: AgentType, text: str) -> None:
    _log_agent_message_new(agent, text)


def log(text: str, category: str = "info") -> None:
    _log_new(text, category)


def get_header():
    return _get_header_new()


def get_context():
    return _get_context_new()


def get_log_cursor_position():
    try:
        _, cursor = _get_render_log_snapshot()
        y = int(getattr(cursor, "y", 0) or 0)
    except Exception:
        y = 0
    return Point(x=0, y=y)


# ================== MENU CONTENT ==================


def _clear_agent_pause_state() -> None:
    _clear_agent_pause_state_new()


def _set_agent_pause(*, pending_text: str, permission: str, message: str) -> None:
    _set_agent_pause_new(pending_text=pending_text, permission=permission, message=message)


def _resume_paused_agent() -> None:
    _resume_paused_agent_new()


def _handle_command(cmd: str) -> None:
    _handle_command_new(cmd)

def _handle_input(buff: Buffer) -> None:
    _handle_input_new(buff)


input_buffer = Buffer(multiline=True, accept_handler=_handle_input)


def get_input_prompt():
    return _get_input_prompt_new()


def get_prompt_width() -> int:
    return 55 if state.menu_level != MenuLevel.NONE else 3


def get_status():
    return _get_status_new()


# ================== KEY BINDINGS ==================


def _tool_llm_status() -> Dict[str, Any]:
    return _tool_llm_status_new()


def _tool_llm_set(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_llm_set_new(args)


def _tool_ui_theme_status() -> Dict[str, Any]:
    return _tool_ui_theme_status_new()


def _tool_ui_theme_set(args: Dict[str, Any]) -> Dict[str, Any]:
    return _tool_ui_theme_set_new(args)


# ================== CLI SUBCOMMANDS ==================

def cli_main(argv: List[str]) -> None:
    # Setup logging
    verbose = "--verbose" in argv or "-v" in argv
    logger = setup_logging(verbose=verbose, name="trinity.cli")
    logger.info(f"CLI started with arguments: {argv}")
    
    parser = argparse.ArgumentParser(prog="cli.py", description="System CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("tui", help="Запустити TUI (за замовчуванням)")

    p_list = sub.add_parser("list-editors", help="Список редакторів")

    p_list_mod = sub.add_parser("list-modules", help="Список модулів")
    p_list_mod.add_argument("--editor")

    p_run = sub.add_parser("run", help="Запустити очищення")
    p_run.add_argument("--editor")
    p_run.add_argument("--dry-run", action="store_true")

    p_enable = sub.add_parser("enable", help="Увімкнути модуль")
    p_enable.add_argument("--editor")
    p_enable.add_argument("--id", required=True)

    p_disable = sub.add_parser("disable", help="Вимкнути модуль")
    p_disable.add_argument("--editor")
    p_disable.add_argument("--id", required=True)

    p_install = sub.add_parser("install", help="Нова установка")
    p_install.add_argument("--editor")

    p_smart = sub.add_parser("smart-plan", help="LLM smart-plan")
    p_smart.add_argument("--editor")
    p_smart.add_argument("--query", required=True)

    p_ask = sub.add_parser("ask", help="LLM ask")
    p_ask.add_argument("--question", required=True)

    p_agent_chat = sub.add_parser("agent-chat", help="Agent chat (single-shot)")
    p_agent_chat.add_argument("--message", required=True)

    p_self_healing_status = sub.add_parser("self-healing-status", help="Check self-healing status")
    p_self_healing_scan = sub.add_parser("self-healing-scan", help="Trigger immediate self-healing scan")
    
    p_vibe_status = sub.add_parser("vibe-status", help="Check Vibe CLI Assistant status")
    p_vibe_continue = sub.add_parser("vibe-continue", help="Continue execution after Vibe CLI Assistant pause")
    p_vibe_cancel = sub.add_parser("vibe-cancel", help="Cancel current task from Vibe CLI Assistant pause")
    p_vibe_help = sub.add_parser("vibe-help", help="Show Vibe CLI Assistant help")
    
    p_eternal_engine = sub.add_parser("eternal-engine", help="Start eternal engine mode with Doctor Vibe")
    p_eternal_engine.add_argument("--task", required=True, help="Task to execute in eternal engine mode")
    p_eternal_engine.add_argument("--hyper", action="store_true", help="Enable hyper mode (unlimited permissions)")

    # Screenshots management
    p_screens = sub.add_parser("screenshots", help="List or open task screenshots")
    p_screens.add_argument("action", choices=["list", "open"], help="Action: list or open")
    p_screens.add_argument("--count", type=int, default=10, help="Number of items to list (default 10)")

    sub.add_parser("agent-reset", help="Reset in-memory agent session")
    sub.add_parser("agent-on", help="Enable agent chat")
    sub.add_parser("agent-off", help="Disable agent chat")

    args = parser.parse_args(argv)
    logger.debug(f"Parsed command: {args.command}")

    if not args.command or args.command == "tui":
        return _handle_tui_command(logger)

    try:
        cfg = _load_cleanup_config()
        logger.debug("Cleanup config loaded successfully")

        resolved_editor, editor_note = _get_resolved_editor(args, cfg, logger)
        
        # Dispatch command
        handlers = {
            "list-editors": lambda: _handle_list_editors(cfg, logger),
            "list-modules": lambda: _handle_list_modules(args, cfg, resolved_editor, logger),
            "run": lambda: _handle_run_command(args, cfg, resolved_editor, logger),
            "enable": lambda: _handle_module_toggle(args, cfg, resolved_editor, logger, True),
            "disable": lambda: _handle_module_toggle(args, cfg, resolved_editor, logger, False),
            "install": lambda: _handle_install_command(args, cfg, resolved_editor, logger),
            "smart-plan": lambda: _handle_smart_plan(args, cfg, resolved_editor, logger),
            "ask": lambda: _handle_ask_command(args, cfg, logger),
        }
        
        if args.command in handlers:
            handlers[args.command]()
            return

    except SystemExit:
        raise
    except Exception as e:
        log_exception(logger, e, f"Command execution: {args.command}")
        raise

    # Secondary Dispatch
    sec_dispatch = {
        "agent-reset": lambda: _handle_agent_reset(logger),
        "agent-on": lambda: _handle_agent_toggle(logger, True),
        "agent-off": lambda: _handle_agent_toggle(logger, False),
        "self-healing-status": lambda: _handle_self_healing_status(logger),
        "self-healing-scan": lambda: _handle_self_healing_scan(logger),
        "vibe-status": lambda: _handle_vibe_command(logger, "status"),
        "vibe-continue": lambda: _handle_vibe_command(logger, "continue"),
        "vibe-cancel": lambda: _handle_vibe_command(logger, "cancel"),
        "vibe-help": lambda: _handle_vibe_command(logger, "help"),
        "eternal-engine": lambda: _handle_eternal_engine(args, logger),
    }

    if args.command in sec_dispatch:
        sec_dispatch[args.command]()
        return

    if args.command == "screenshots":
        return _handle_screenshots_command(args)
        
    if args.command == "agent-chat":
        return _handle_agent_chat_command(args, logger)


# --- CLI Command Handlers ---

def _handle_tui_command(logger: Any):
    logger.info("Starting TUI mode")
    try:
        run_tui()
        logger.info("TUI mode exited successfully")
    except Exception as e:
        log_exception(logger, e, "TUI mode")
        raise
    return

def _get_resolved_editor(args: Any, cfg: Dict[str, Any], logger: Any) -> Tuple[Optional[str], Optional[str]]:
    if not hasattr(args, "editor"): return None, None
    res, note = _resolve_editor_arg(cfg, getattr(args, "editor", None))
    if note:
        logger.warning(note)
        try: print(note, file=sys.stderr)
        except Exception as e:
            logger.debug(f"Failed to print editor note to stderr: {e}")
    return res, note

def _handle_list_editors(cfg: Dict[str, Any], logger: Any):
    logger.info("Listing editors")
    for key, label in _list_editors(cfg): print(f"{key}: {label}")
    logger.info("Editors listed successfully")

def _handle_list_modules(args: Any, cfg: Dict[str, Any], resolved_editor: Optional[str], logger: Any):
    editor = resolved_editor or getattr(args, "editor", None)
    logger.info(f"Listing modules for editor: {editor}")
    meta = cfg.get("editors", {}).get(editor)
    if not meta:
        logger.error(f"Unknown editor: {editor}")
        print(f"Unknown editor: {editor}")
        raise SystemExit(1)
    for m in meta.get("modules", []):
        mark = "ON" if m.get("enabled") else "OFF"
        print(f"[{mark}] {m.get('id')} - {m.get('name')} (script={m.get('script')})")
    logger.info(f"Modules listed for {editor}")

def _handle_run_command(args: Any, cfg: Dict[str, Any], resolved_editor: Optional[str], logger: Any):
    editor = resolved_editor or getattr(args, "editor", None)
    logger.info(f"Running cleanup for editor: {editor}, dry_run={args.dry_run}")
    ok, msg = _run_cleanup(cfg, editor, dry_run=args.dry_run)
    print(msg); logger.info(f"Cleanup completed: {msg}")
    raise SystemExit(0 if ok else 1)

def _handle_module_toggle(args: Any, cfg: Dict[str, Any], resolved_editor: Optional[str], logger: Any, enabled: bool):
    editor = resolved_editor or getattr(args, "editor", None)
    logger.info(f"{'Enable' if enabled else 'Disable'} module {args.id} for editor {editor}")
    ref = _find_module(cfg, editor, args.id)
    if not ref:
        logger.error(f"Module not found: {args.id}"); print("Module not found")
        raise SystemExit(1)
    if _set_module_enabled(cfg, ref, enabled):
        logger.info(f"Module {args.id} {'enabled' if enabled else 'disabled'} successfully")
        print("OK"); raise SystemExit(0)
    logger.error(f"Failed to {'enable' if enabled else 'disable'} module {args.id}")
    print("Failed"); raise SystemExit(1)

def _handle_install_command(args: Any, cfg: Dict[str, Any], resolved_editor: Optional[str], logger: Any):
    editor = resolved_editor or getattr(args, "editor", None)
    logger.info(f"Starting installation for editor: {editor}")
    ok, msg = _perform_install(cfg, editor)
    print(msg); logger.info(f"Installation completed: {msg}")
    raise SystemExit(0 if ok else 1)

def _handle_smart_plan(args: Any, cfg: Dict[str, Any], resolved_editor: Optional[str], logger: Any):
    editor = resolved_editor or getattr(args, "editor", None)
    logger.info(f"Running smart-plan for editor {editor} with query: {args.query}")
    ok, msg = _llm_smart_plan(cfg, editor, args.query)
    print(msg); logger.info(f"Smart-plan completed: {msg}")
    raise SystemExit(0 if ok else 1)

def _handle_ask_command(args: Any, cfg: Dict[str, Any], logger: Any):
    logger.info(f"Running LLM ask with question: {args.question}")
    ok, msg = _llm_ask(cfg, args.question)
    print(msg); logger.info(f"LLM ask completed: {msg}")
    raise SystemExit(0 if ok else 1)

def _handle_agent_reset(logger: Any):
    logger.info("Resetting agent session"); agent_session.reset()
    logger.info("Agent session reset successfully"); print("OK")

def _handle_agent_toggle(logger: Any, enabled: bool):
    logger.info(f"{'Enabling' if enabled else 'Disabling'} agent chat")
    agent_session.enabled = enabled
    logger.info(f"Agent chat {'enabled' if enabled else 'disabled'}"); print("OK")

def _handle_self_healing_status(logger: Any):
    logger.info("Checking self-healing status")
    from tui.commands import check_self_healing_status
    check_self_healing_status()

def _handle_self_healing_scan(logger: Any):
    logger.info("Triggering self-healing scan")
    from tui.commands import trigger_self_healing_scan
    trigger_self_healing_scan()

def _handle_vibe_command(logger: Any, action: str):
    logger.info(f"Vibe CLI Assistant {action} command")
    from tui.commands import (
        check_vibe_assistant_status, handle_vibe_continue_command,
        handle_vibe_cancel_command, handle_vibe_help_command
    )
    if action == "status": check_vibe_assistant_status()
    elif action == "continue": handle_vibe_continue_command()
    elif action == "cancel": handle_vibe_cancel_command()
    elif action == "help": handle_vibe_help_command()

def _handle_eternal_engine(args: Any, logger: Any):
    logger.info(f"Starting eternal engine mode with task: {args.task}")
    from tui.commands import start_eternal_engine_mode
    start_eternal_engine_mode(args.task, args.hyper)

def _handle_screenshots_command(args: Any):
    if args.action == "list":
        from tui.tools import tool_list_screenshots
        out = tool_list_screenshots({"count": getattr(args, "count", 10)})
        if not out.get("ok"):
            print(out.get("error") or "Error listing screenshots")
            raise SystemExit(1)
        items = out.get("items") or []
        if not items:
            print(f"No screenshots found in {out.get('root')}.")
            raise SystemExit(0)
        for i in items:
            sz = i.get("size")
            print(f"{i.get('name')}  {sz} bytes")
        raise SystemExit(0)
    elif args.action == "open":
        from tui.tools import tool_open_screenshots
        out = tool_open_screenshots({})
        if not out.get("ok"):
            print(out.get("error") or "Error opening screenshots directory")
            raise SystemExit(1)
        print(f"Opened {out.get('root')} in Finder")
        raise SystemExit(0)

def _handle_agent_chat_command(args: Any, logger: Any):
    """Handle chat messages from CLI."""
    logger.info(f"Agent chat message: {args.message}")
    msg = str(args.message or "").strip()

    try:
        # 1. Slash commands
        if _try_process_slash_command(msg, logger):
            raise SystemExit(0)

        # 2. Greetings
        if _is_greeting(msg):
            logger.debug("Greeting detected")
            print("Привіт! Чим можу допомогти?")
            raise SystemExit(0)

        # 3. Complex tasks
        if _is_complex_task(msg):
            _handle_complex_task_cli(msg, logger)
            raise SystemExit(0)

        # 4. Standard message
        _handle_standard_agent_message(msg, logger)
        raise SystemExit(0)
        
    except SystemExit:
        raise
    except Exception as e:
        log_exception(logger, e, "Agent chat")
        raise


def _try_process_slash_command(msg: str, logger: Any) -> bool:
    """Detect and execute slash command. Returns True if handled."""
    parts = msg.split()
    cmd_idx = next((i for i, p in enumerate(parts) if p.startswith("/")), None)
    if cmd_idx is None:
        return False
        
    cmd = " ".join(parts[cmd_idx:]).strip()
    logger.debug(f"Processing slash command: {cmd}")
    _load_ui_settings()
    out = _tool_app_command({"command": cmd})
    
    if not out.get("ok"):
        error_msg = str(out.get("error") or "Unknown error")
        logger.error(f"Slash command failed: {error_msg}")
        print(error_msg)
        raise SystemExit(1)
        
    for _, line in (out.get("lines") or []):
        if line:
            print(line)
    logger.info("Slash command executed successfully")
    return True


def _handle_complex_task_cli(msg: str, logger: Any):
    """Delegate complex task to Trinity Graph Agent."""
    logger.info("Complex task detected, delegating to Trinity Graph Agent...")
    from tui.agents import run_graph_agent_task
    run_graph_agent_task(
        msg,
        allow_file_write=True,
        allow_shell=True,
        allow_applescript=True,
        allow_gui=True,
        allow_shortcuts=True,
        gui_mode="auto"
    )
    logger.info("Graph task completed")


def _handle_standard_agent_message(msg: str, logger: Any):
    """Send standard message to agent."""
    logger.info("Sending message to agent")
    ok, answer = _agent_send_no_stream(msg)
    print(answer)
    logger.info(f"Agent response sent, status: {ok}")
    if not ok:
        raise SystemExit(1)

def main() -> None:
    try:
        cli_main(sys.argv[1:])
    except Exception as e:
        logger = get_logger("trinity.cli")
        log_exception(logger, e, "main()")
        sys.exit(1)


if __name__ == "__main__":
    main()
