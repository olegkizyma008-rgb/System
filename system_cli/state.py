from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple


class MenuLevel(Enum):
    NONE = "none"
    MAIN = "main"
    CUSTOM_TASKS = "custom_tasks"
    CLEANUP_EDITORS = "cleanup_editors"
    MODULE_EDITORS = "module_editors"
    MODULE_LIST = "module_list"
    INSTALL_EDITORS = "install_editors"
    LOCALES = "locales"
    MONITORING = "monitoring"
    MONITOR_TARGETS = "monitor_targets"
    MONITOR_CONTROL = "monitor_control"
    SETTINGS = "settings"
    UNSAFE_MODE = "unsafe_mode"
    LLM_SETTINGS = "llm_settings"
    AGENT_SETTINGS = "agent_settings"
    APPEARANCE = "appearance"
    LANGUAGE = "language"
    AUTOMATION_PERMISSIONS = "automation_permissions"
    LAYOUT = "layout"
    DEV_SETTINGS = "dev_settings"


@dataclass
class AppState:
    logs: List[Tuple[str, str]] = field(default_factory=list)
    status: str = "READY"
    menu_level: MenuLevel = MenuLevel.NONE
    menu_index: int = 0
    selected_editor: Optional[str] = None
    monitor_targets: Set[str] = field(default_factory=set)
    monitor_active: bool = False
    monitor_source: str = "watchdog"
    monitor_use_sudo: bool = False
    ui_theme: str = "monaco"
    ui_lang: str = "uk"
    chat_lang: str = "uk"
    ui_unsafe_mode: bool = False
    ui_streaming: bool = True
    ui_gui_mode: str = "auto"
    ui_execution_mode: str = "native"
    automation_allow_shortcuts: bool = False
    agent_processing: bool = False
    agent_paused: bool = False
    agent_pause_permission: Optional[str] = None
    agent_pause_message: Optional[str] = None
    agent_pause_pending_text: Optional[str] = None
    recording_analysis_waiting: bool = False
    recording_analysis_dir: Optional[str] = None
    recording_analysis_name: Optional[str] = None
    ui_scroll_target: str = "log"
    ui_log_follow: bool = True
    ui_log_cursor_y: int = 0
    ui_log_line_count: int = 1
    ui_agents_follow: bool = True
    ui_agents_cursor_y: int = 0
    ui_agents_line_count: int = 1
    ui_panel_min_width: int = 40
    ui_panel_max_width: int = 120
    ui_left_panel_ratio: float = 0.6
    ui_dev_code_provider: str = "vibe-cli"  # vibe-cli | continue


state = AppState()
