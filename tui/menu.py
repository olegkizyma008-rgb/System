from __future__ import annotations
import os
import time
from typing import Any, Callable, List, Sequence, Tuple
from prompt_toolkit.filters import Condition
from tui.themes import THEMES, get_theme_names

# Constants for repeated literals
STYLE_MENU_TITLE = "class:menu.title"
STYLE_MENU_ITEM = "class:menu.item"
STYLE_MENU_SELECTED = "class:menu.selected"


def build_menu(
    *,
    state: Any,
    MenuLevel: Any,
    tr: Callable[[str, str], str],
    lang_name: Callable[[str], str],
    MAIN_MENU_ITEMS: Sequence[Tuple[str, Any]],
    get_custom_tasks_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_monitoring_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_settings_menu_items: Callable[[], List[Tuple[str, Any]]],

    get_llm_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_llm_sub_menu_items: Callable[[Any], List[Tuple[str, Any]]],
    get_agent_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_automation_permissions_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_editors_list: Callable[[], List[Tuple[str, str]]],
    get_cleanup_cfg: Callable[[], Any],
    AVAILABLE_LOCALES: Sequence[Any],
    localization: Any,
    get_monitor_menu_items: Callable[[], List[Any]],
    normalize_menu_index: Callable[[List[Any]], None],
    MONITOR_TARGETS_PATH: str,
    MONITOR_EVENTS_DB_PATH: str,
    CLEANUP_CONFIG_PATH: str,
    LOCALIZATION_CONFIG_PATH: str,
    force_ui_update: Callable[[], None],
    on_enter: Callable[[], None],
) -> Tuple[Condition, Callable[[], List[Tuple[str, str]]]]:
    @Condition
    def show_menu() -> bool:
        return state.menu_level != MenuLevel.NONE

    last_click = {"time": 0, "idx": -1}

    def make_click(idx: int) -> Callable[[Any], None]:
        def _click(mouse_event: Any) -> None:
            from prompt_toolkit.mouse_events import MouseEventType
            
            event_type = getattr(mouse_event, 'event_type', None)
            
            if event_type == MouseEventType.MOUSE_MOVE:
                if state.menu_index != idx:
                    state.menu_index = idx
                    force_ui_update()
                return

            if event_type not in (MouseEventType.MOUSE_UP, MouseEventType.MOUSE_DOWN):
                return
            
            if event_type != MouseEventType.MOUSE_UP:
                return
            
            now = time.time()
            if last_click["idx"] == idx and now - last_click["time"] < 0.4:
                on_enter()
                force_ui_update()
            else:
                if state.menu_index != idx:
                    state.menu_index = idx
                    force_ui_update()
            
            last_click["idx"] = idx
            last_click["time"] = now
        return _click

    # Create context for menu handlers
    ctx = {
        "state": state, "MenuLevel": MenuLevel, "tr": tr, "lang_name": lang_name,
        "make_click": make_click, "force_ui_update": force_ui_update,
        "MAIN_MENU_ITEMS": MAIN_MENU_ITEMS,
        "get_custom_tasks_menu_items": get_custom_tasks_menu_items,
        "get_monitoring_menu_items": get_monitoring_menu_items,
        "get_settings_menu_items": get_settings_menu_items,
        "get_llm_menu_items": get_llm_menu_items,
        "get_llm_sub_menu_items": get_llm_sub_menu_items,
        "get_agent_menu_items": get_agent_menu_items,
        "get_automation_permissions_menu_items": get_automation_permissions_menu_items,
        "get_editors_list": get_editors_list,
        "get_cleanup_cfg": get_cleanup_cfg,
        "AVAILABLE_LOCALES": AVAILABLE_LOCALES,
        "localization": localization,
        "get_monitor_menu_items": get_monitor_menu_items,
        "normalize_menu_index": normalize_menu_index,
        "MONITOR_TARGETS_PATH": MONITOR_TARGETS_PATH,
        "MONITOR_EVENTS_DB_PATH": MONITOR_EVENTS_DB_PATH,
    }

    def get_menu_content() -> List[Tuple[str, str]]:
        """Main menu content dispatcher."""
        level = state.menu_level
        
        # Map menu levels to handler functions
        handlers = {
            MenuLevel.MAIN: _render_main_menu,
            MenuLevel.CUSTOM_TASKS: _render_custom_tasks_menu,
            MenuLevel.MONITORING: _render_monitoring_menu,
            MenuLevel.SETTINGS: _render_settings_menu,
            MenuLevel.LLM_SETTINGS: _render_llm_settings_menu,
            MenuLevel.AGENT_SETTINGS: _render_agent_settings_menu,
            MenuLevel.APPEARANCE: _render_appearance_menu,
            MenuLevel.LANGUAGE: _render_language_menu,
            MenuLevel.UNSAFE_MODE: _render_toggle_menu,
            MenuLevel.SELF_HEALING: _render_toggle_menu,
            MenuLevel.MEMORY_MANAGER: _render_memory_manager_menu,
            MenuLevel.AUTOMATION_PERMISSIONS: _render_automation_permissions_menu,
            MenuLevel.LAYOUT: _render_layout_menu,
            MenuLevel.DEV_SETTINGS: _render_dev_settings_menu,
            MenuLevel.MONITOR_CONTROL: _render_monitor_control_menu,
            MenuLevel.MONITOR_TARGETS: _render_monitor_targets_menu,
            MenuLevel.CLEANUP_EDITORS: _render_editors_menu,
            MenuLevel.MODULE_EDITORS: _render_editors_menu,
            MenuLevel.INSTALL_EDITORS: _render_editors_menu,
            MenuLevel.MODULE_LIST: _render_module_list_menu,
            MenuLevel.LOCALES: _render_locales_menu,
            MenuLevel.LOCALES: _render_locales_menu,
            MenuLevel.MCP_CLIENT_SETTINGS: _render_mcp_client_menu,
        }
        
        # Check for LLM sub-menus
        if level in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
            return _render_llm_sub_menu(ctx)
        
        handler = handlers.get(level)
        if handler:
            return handler(ctx)
        
        return [(STYLE_MENU_ITEM, "(menu)")]

    return show_menu, get_menu_content


# ============ Helper functions ============

def _get_item_style(i: int, menu_index: int) -> Tuple[str, str]:
    """Get prefix and style for menu item."""
    prefix = " > " if i == menu_index else "   "
    style = STYLE_MENU_SELECTED if i == menu_index else STYLE_MENU_ITEM
    return prefix, style


def _add_back_btn(result: List, ctx: dict):
    """Add back button to menu."""
    state, MenuLevel = ctx["state"], ctx["MenuLevel"]
    tr, force_ui_update = ctx["tr"], ctx["force_ui_update"]
    
    def _back_handler(mouse_event: Any):
        from prompt_toolkit.mouse_events import MouseEventType
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            state.menu_level = MenuLevel.MAIN
            state.menu_index = 0
            force_ui_update()
    
    result.append((STYLE_MENU_ITEM, " [ < " + tr("menu.back", state.ui_lang).upper() + " ] ", _back_handler))
    result.append(("", "\n\n"))


def _get_toggle_text(val: bool) -> List[Tuple[str, str]]:
    """Get toggle display text."""
    style = "class:toggle.on" if val else "class:toggle.off"
    label = " ON  " if val else " OFF "
    return [(STYLE_MENU_ITEM, "["), (style, label), (STYLE_MENU_ITEM, "]")]


def _get_slider_text(val: float, width: int = 10) -> List[Tuple[str, str]]:
    """Get slider display text."""
    filled = int(val * width)
    bar = "=" * filled + "|" + "-" * (width - filled - 1) if filled < width else "=" * (width - 1) + "|"
    return [(STYLE_MENU_ITEM, f"[{bar}] {val:.2f}")]


def _get_theme_preview(tname: str) -> List[Tuple[str, str]]:
    """Get theme preview colors."""
    t = THEMES.get(tname, {})
    border = t.get("frame.border", "#ffffff")
    title = t.get("header.title", "#ffffff")
    accent = t.get("log.action", "#ffffff")
    return [
        (STYLE_MENU_ITEM, "  "),
        (f"bg:{border}", "  "),
        (STYLE_MENU_ITEM, " "),
        (f"bg:{title}", "  "),
        (STYLE_MENU_ITEM, " "),
        (f"bg:{accent}", "  "),
    ]


def _clamp_menu_index(state, items_len: int):
    """Clamp menu index to valid range."""
    state.menu_index = max(0, min(state.menu_index, items_len - 1))


# ============ Menu renderers ============

def _render_main_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render main menu."""
    state, tr = ctx["state"], ctx["tr"]
    make_click = ctx["make_click"]
    MAIN_MENU_ITEMS = ctx["MAIN_MENU_ITEMS"]
    
    result = [(STYLE_MENU_TITLE, f" {tr('menu.main.title', state.ui_lang)}\n\n")]
    for i, item in enumerate(MAIN_MENU_ITEMS):
        name = item[0]
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{tr(name, state.ui_lang)}\n", make_click(i)))
    return result


def _render_custom_tasks_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render custom tasks menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.custom_tasks.title', state.ui_lang)}\n\n"))
    
    items = ctx["get_custom_tasks_menu_items"]()
    _clamp_menu_index(state, len(items))
    
    for i, itm in enumerate(items):
        if isinstance(itm, tuple) and len(itm) == 3 and itm[2] == "section":
            result.append((STYLE_MENU_TITLE, f"\n {tr(itm[0], state.ui_lang)}\n"))
        else:
            label = itm[0]
            prefix, style = _get_item_style(i, state.menu_index)
            result.append((style, f"{prefix}{tr(label, state.ui_lang)}\n", make_click(i)))
    return result


def _render_monitoring_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render monitoring menu."""
    state, tr = ctx["state"], ctx["tr"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.monitoring.title', state.ui_lang)}\n\n"))
    
    items = ctx["get_monitoring_menu_items"]()
    _clamp_menu_index(state, len(items))
    
    for i, itm in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{tr(itm[0], state.ui_lang)}\n"))
    return result


def _render_settings_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render settings menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.settings.title', state.ui_lang)}\n\n"))
    
    items = ctx["get_settings_menu_items"]()
    _clamp_menu_index(state, len(items))
    
    for i, item in enumerate(items):
        if isinstance(item, tuple) and len(item) == 3 and item[2] == "section":
            result.append((STYLE_MENU_TITLE, f"\n {tr(item[0], state.ui_lang)}\n"))
        else:
            label = item[0] if isinstance(item, tuple) else item
            prefix, style = _get_item_style(i, state.menu_index)
            # Handle localized string vs raw string
            display_label = tr(label, state.ui_lang) if "." in label else label
            result.append((style, f"{prefix}{display_label}\n", make_click(i)))
    return result


def _render_llm_settings_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render LLM settings menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.llm.title', state.ui_lang)}\n\n"))
    
    items = ctx["get_llm_menu_items"]()
    if not items:
        result.append((STYLE_MENU_ITEM, " (no items)\n"))
        return result
    
    _clamp_menu_index(state, len(items))
    for i, itm in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{itm[0]}\n", make_click(i)))
    return result


def _render_llm_sub_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render LLM sub-menu (Atlas, Tetyana, Grisha, Vision, Defaults)."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    
    section_key = state.menu_level.value.replace("llm_", "")
    section_label = section_key.upper() if section_key != "defaults" else "GLOBAL DEFAULTS"
    result.append((STYLE_MENU_TITLE, f" {tr('menu.llm.title', state.ui_lang)}: {section_label}\n\n"))
    
    items = ctx["get_llm_sub_menu_items"](state.menu_level)
    _clamp_menu_index(state, len(items))
    
    for i, item in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{item[0]}\n", make_click(i)))
    
    result.append((STYLE_MENU_ITEM, "\n Enter: Edit | Space: Cycle value\n"))
    return result


def _render_agent_settings_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render agent settings menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.agent.title', state.ui_lang)}\n\n"))
    
    items = ctx["get_agent_menu_items"]()
    if not items:
        result.append((STYLE_MENU_ITEM, " (no items)\n"))
        return result
    
    _clamp_menu_index(state, len(items))
    for i, itm in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{itm[0]}\n", make_click(i)))
    return result


def _render_appearance_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render appearance/theme menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.appearance.title', state.ui_lang)}\n\n"))
    
    themes = list(get_theme_names())
    _clamp_menu_index(state, len(themes))
    
    for i, t in enumerate(themes):
        prefix, style = _get_item_style(i, state.menu_index)
        mark = "[*]" if state.ui_theme == t else "[ ]"
        result.append((style, f"{prefix}{mark} {t}", make_click(i)))
        result.extend(_get_theme_preview(t))
        result.append(("", "\n"))
    return result


def _render_language_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render language menu."""
    state, tr, lang_name, make_click = ctx["state"], ctx["tr"], ctx["lang_name"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.language.title', state.ui_lang)}\n\n"))
    
    items = [
        (f"UI: {state.ui_lang} - {lang_name(state.ui_lang)}", "ui"),
        (f"Chat: {state.chat_lang} - {lang_name(state.chat_lang)}", "chat")
    ]
    _clamp_menu_index(state, len(items))
    
    for i, item in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{item[0]}\n", make_click(i)))
    
    result.append((STYLE_MENU_ITEM, "\n Enter: cycle | /lang set ui|chat <code>\n"))
    return result


def _render_toggle_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render toggle menu (unsafe mode, self-healing)."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    MenuLevel = ctx["MenuLevel"]
    
    result = []
    _add_back_btn(result, ctx)
    
    # Determine which toggle mode
    level = state.menu_level
    if level == MenuLevel.UNSAFE_MODE:
        title_key, label_key, attr = "menu.unsafe_mode.title", "menu.unsafe_mode.label", "ui_unsafe_mode"
    elif level == MenuLevel.SELF_HEALING:
        title_key, label_key, attr = "menu.self_healing.title", "menu.self_healing.label", "ui_self_healing"
    else:
        return [(STYLE_MENU_ITEM, "(unknown toggle)")]
    
    result.append((STYLE_MENU_TITLE, f" {tr(title_key, state.ui_lang)}\n\n"))
    on = bool(getattr(state, attr, False))
    result.append((STYLE_MENU_SELECTED, f" > {tr(label_key, state.ui_lang)} ", make_click(0)))
    result.extend(_get_toggle_text(on))
    result.append(("", "\n"))
    return result


def _render_automation_permissions_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render automation permissions menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.automation_permissions.title', state.ui_lang)}\n\n"))
    
    items = ctx["get_automation_permissions_menu_items"]()
    _clamp_menu_index(state, len(items))
    
    for i, itm in enumerate(items):
        label, key = itm[0], itm[1]
        prefix, style = _get_item_style(i, state.menu_index)
        
        # Build complete line with label and status
        line = f"{prefix}{label} "
        
        if key == "ui_execution_mode":
            mode = str(getattr(state, "ui_execution_mode", "native")).upper()
            line += f"[{mode}]"
        elif key == "automation_allow_shortcuts":
            on_off = "ON" if getattr(state, "automation_allow_shortcuts", False) else "OFF"
            line += f"[{on_off}]"
        elif key.startswith("env_"):
            # Show status for env vars
            var_map = {
                "env_shell": "TRINITY_ALLOW_SHELL",
                "env_write": "TRINITY_ALLOW_WRITE",
                "env_applescript": "TRINITY_ALLOW_APPLESCRIPT",
                "env_gui": "TRINITY_ALLOW_GUI",
                "env_hyper": "TRINITY_HYPER_MODE",
            }
            var = var_map.get(key)
            if var:
                val = str(os.getenv(var) or ("1" if var == "TRINITY_ALLOW_WRITE" else "0")).strip().lower()
                status = "ON" if val in {"1", "true", "yes", "on"} else "OFF"
                line += f"[{status}]"
        
        result.append((style, line + "\n", make_click(i)))
    
    return result


def _render_layout_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render layout menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.layout.title', state.ui_lang)}\n\n"))
    
    items = [(tr("menu.layout.left_panel_ratio", state.ui_lang), "ratio")]
    _clamp_menu_index(state, len(items))
    
    for i, itm in enumerate(items):
        label, key = itm[0], itm[1]
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{label} ", make_click(i)))
        
        if key == "ratio":
            result.extend(_get_slider_text(float(getattr(state, "ui_left_panel_ratio", 0.6))))
        
        result.append(("", "\n"))
    
    result.append((STYLE_MENU_ITEM, f"\n {tr('menu.layout.hint', state.ui_lang)}\n"))
    return result


def _render_dev_settings_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render dev settings menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.dev_settings.title', state.ui_lang)}\n\n"))
    
    provider = str(getattr(state, "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower()
    provider_label = "VIBE-CLI" if provider == "vibe-cli" else "CONTINUE"
    
    # Provider
    result.append((STYLE_MENU_SELECTED, f" > {tr('menu.dev_settings.provider_label', state.ui_lang)}: ", make_click(0)))
    style = "class:toggle.on" if provider == "vibe-cli" else "class:toggle.off"
    result.append((style, f" {provider_label} "))
    result.append(("", "\n\n"))

    # Doctor Vibe toggles
    vibe_on = os.getenv("TRINITY_DEV_BY_VIBE", "0").strip().lower() in {"1", "true", "yes", "on"}
    auto_apply = os.getenv("TRINITY_VIBE_AUTO_APPLY", "0").strip().lower() in {"1", "true", "yes", "on"}
    auto_resume = os.getenv("TRINITY_VIBE_AUTO_RESUME", "0").strip().lower() in {"1", "true", "yes", "on"}

    result.append((STYLE_MENU_ITEM, "\n"))
    result.append((STYLE_MENU_SELECTED, f" > {tr('menu.dev_settings.vibe_enabled', state.ui_lang)}: ", make_click(1)))
    result.extend(_get_toggle_text(vibe_on))
    result.append(("", "\n"))

    result.append((STYLE_MENU_SELECTED, f" > {tr('menu.dev_settings.auto_apply', state.ui_lang)}: ", make_click(2)))
    result.extend(_get_toggle_text(auto_apply))
    result.append(("", "\n"))

    result.append((STYLE_MENU_SELECTED, f" > {tr('menu.dev_settings.auto_resume', state.ui_lang)}: ", make_click(3)))
    result.extend(_get_toggle_text(auto_resume))
    result.append(("", "\n\n"))

    result.append((STYLE_MENU_ITEM, " Enter: Toggle item | Q/Esc: Back\n"))
    return result


def _render_monitor_control_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render monitor control menu."""
    state, make_click = ctx["state"], ctx["make_click"]
    MONITOR_EVENTS_DB_PATH = ctx["MONITOR_EVENTS_DB_PATH"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, " MONITORING (Enter: Start/Stop, S: Source, U: Sudo, Q/Esc: Back)\n"))
    
    state_line = "ACTIVE" if state.monitor_active else "INACTIVE"
    result.append((STYLE_MENU_ITEM, f" State: {state_line}\n"))
    result.append((STYLE_MENU_ITEM, f" Source: {state.monitor_source}\n"))
    # Mode toggle (auto/manual) - selectable via Enter
    result.append((STYLE_MENU_SELECTED, f" > Mode: {state.monitor_mode}\n", make_click(0)))
    style = "class:toggle.on" if state.monitor_mode == "auto" else "class:toggle.off"
    result.append((style, f" {state.monitor_mode.upper()} "))
    result.append(("", "\n"))
    
    if state.monitor_source in {"fs_usage", "opensnoop"}:
        sudo_line = "ON" if state.monitor_use_sudo else "OFF"
        result.append((STYLE_MENU_ITEM, f" Sudo: {sudo_line}\n"))
    
    result.append((STYLE_MENU_ITEM, f" Targets: {len(state.monitor_targets)} selected\n"))
    result.append((STYLE_MENU_ITEM, f" DB: {MONITOR_EVENTS_DB_PATH}\n\n"))
    
    action = "STOP" if state.monitor_active else "START"
    # Start/Stop is selectable as index 1
    result.append((STYLE_MENU_SELECTED, f" > {action}\n", make_click(1)))
    
    notes = {
        "watchdog": "Note: watchdog monitors directories (no process attribution).",
        "fs_usage": "Note: fs_usage attributes calls to process name; may require sudo.",
        "opensnoop": "Note: opensnoop traces open() calls; may require sudo.",
    }
    note = notes.get(state.monitor_source, "Note: source not implemented yet.")
    result.append((STYLE_MENU_ITEM, f"\n {note}\n"))
    # Small UI hint to make mode toggling discoverable (localized)
    from tui.i18n import tr
    hint = tr("menu.monitor.mode_hint", state.ui_lang)
    result.append((STYLE_MENU_ITEM, f" {hint}\n"))
    return result


def _render_monitor_targets_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render monitor targets menu."""
    state, make_click = ctx["state"], ctx["make_click"]
    MONITOR_TARGETS_PATH = ctx["MONITOR_TARGETS_PATH"]
    get_monitor_menu_items = ctx["get_monitor_menu_items"]
    normalize_menu_index = ctx["normalize_menu_index"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, " MONITORING TARGETS (Space: Toggle, Enter: Save, Q/Esc: Back)\n"))
    result.append((STYLE_MENU_ITEM, f" Config: {MONITOR_TARGETS_PATH}\n\n"))
    
    items = get_monitor_menu_items()
    normalize_menu_index(items)
    
    for i, it in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        
        if not getattr(it, "selectable", False):
            result.append((STYLE_MENU_TITLE, f"\n {it.label}\n"))
            continue
        
        on = it.key in state.monitor_targets
        mark = "[x]" if on else "[ ]"
        origin = f" ({it.origin})" if getattr(it, "origin", "") else ""
        result.append((style, f"{prefix}{mark} {it.label}{origin}\n", make_click(i)))
    return result


def _render_editors_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render editors menu (cleanup, modules, install)."""
    state, make_click = ctx["state"], ctx["make_click"]
    MenuLevel = ctx["MenuLevel"]
    
    result = []
    _add_back_btn(result, ctx)
    
    titles = {
        MenuLevel.CLEANUP_EDITORS: " RUN CLEANUP (Enter: Run, D: Dry-run, Q/Esc: Back)\n\n",
        MenuLevel.MODULE_EDITORS: " MODULES: CHOOSE EDITOR (Enter: Select, Q/Esc: Back)\n\n",
        MenuLevel.INSTALL_EDITORS: " INSTALL (Enter: Open installer, Q/Esc: Back)\n\n",
    }
    result.append((STYLE_MENU_TITLE, titles.get(state.menu_level, "")))
    
    editors = ctx["get_editors_list"]()
    for i, itm in enumerate(editors):
        key, label = itm[0], itm[1]
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{key} - {label}\n", make_click(i)))
    return result


def _render_module_list_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render module list menu."""
    state, make_click = ctx["state"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    
    editor = state.selected_editor
    if not editor:
        result.append((STYLE_MENU_TITLE, " MODULES (no editor selected)\n"))
        return result
    
    cfg = ctx["get_cleanup_cfg"]() or {}
    meta = cfg.get("editors", {}).get(editor, {})
    result.append((STYLE_MENU_TITLE, f" MODULES: {editor} (Space: Toggle, Q/Esc: Back)\n\n"))
    
    mods = meta.get("modules", [])
    if not mods:
        result.append((STYLE_MENU_ITEM, " (немає модулів – використайте /smart або /ask)\n"))
        return result
    
    for i, m in enumerate(mods):
        prefix, style = _get_item_style(i, state.menu_index)
        on = bool(m.get("enabled"))
        toggle_style = "class:toggle.on" if on else "class:toggle.off"
        mark = "ON" if on else "OFF"
        result.append((style, f"{prefix}{m.get('id')} - {m.get('name')} [", make_click(i)))
        result.append((toggle_style, f"{mark}"))
        result.append((style, "]\n"))
    return result


def _render_locales_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render locales menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    AVAILABLE_LOCALES = ctx["AVAILABLE_LOCALES"]
    localization = ctx["localization"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.locales.title', state.ui_lang)}\n\n"))
    
    for idx, loc in enumerate(AVAILABLE_LOCALES):
        prefix, style = _get_item_style(idx, state.menu_index)
        is_selected = loc.code in localization.selected
        is_primary = loc.code == localization.primary
        
        primary_mark = "●" if is_primary else " "
        active_mark = "●" if is_selected else " "
        
        result.append((style, f"{prefix}[P:{primary_mark}] [A:{active_mark}] {loc.code} - {loc.name} ({loc.group})\n", make_click(idx)))
    return result


def _render_memory_manager_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render memory manager menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, f" {tr('menu.memory_manager.title', state.ui_lang)}\n\n"))
    
    # Memory manager menu items
    items = [
        ("📊 Memory Statistics", "stats"),
        ("📚 Learning History", "learning_history"),
        ("🧠 Semantic Memory", "semantic"),
        ("🎬 Episodic Memory", "episodic"),
        ("⬇️ Import Examples", "import"),
        ("⬆️ Export Data", "export"),
        ("💾 Vector DB Management", "vector_db"),
    ]
    
    _clamp_menu_index(state, len(items))
    
    for i, (label, _) in enumerate(items):
        prefix, style = _get_item_style(i, state.menu_index)
        result.append((style, f"{prefix}{label}\n", make_click(i)))
    
    result.append(("", "\n"))
    
    # Show memory stats summary at bottom
    try:
        from core.memory import get_hierarchical_memory
        mem = get_hierarchical_memory()
        stats = mem.get_stats()
        
        working = stats.get("working_memory", {}).get("active_items", 0)
        episodic = stats.get("episodic_memory", {}).get("total_items", 0)
        semantic = stats.get("semantic_memory", {}).get("total_items", 0)
        
        result.append((STYLE_MENU_ITEM, f" Working: {working} | Episodic: {episodic} | Semantic: {semantic}\n"))
    except Exception:
        result.append((STYLE_MENU_ITEM, " [Memory stats unavailable]\n"))
    
    return result


def _render_mcp_client_menu(ctx: dict) -> List[Tuple[str, str]]:
    """Render MCP client settings menu."""
    state, tr, make_click = ctx["state"], ctx["tr"], ctx["make_click"]
    
    result = []
    _add_back_btn(result, ctx)
    result.append((STYLE_MENU_TITLE, " MCP CLIENT SETTINGS\n\n"))
    
    current = str(getattr(state, "mcp_client_type", "open_mcp")).strip().lower()
    
    if current == "open_mcp":
        label = "OPEN MCP (CopilotKit)"
        style = "class:toggle.on"
    elif current == "continue":
        label = "CONTINUE MCP"
        style = "class:toggle.on"
    else:
        label = "AUTO (Task-based)"
        style = "class:toggle.off" # Different style for Auto
    
    result.append((STYLE_MENU_SELECTED, f" > Current Client: ", make_click(0)))
    result.append((style, f" {label} "))
    result.append(("", "\n\n"))
    
    result.append((STYLE_MENU_ITEM, " Enter: Cycle through Open MCP -> Continue -> Auto\n"))
    
    # Note/Hint
    result.append((STYLE_MENU_ITEM, "\n Note: Auto mode uses Continue for DEV tasks and Open-MCP for others.\n"))
    return result


