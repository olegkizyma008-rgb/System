from __future__ import annotations

from typing import Any, Callable, List, Sequence, Tuple

from prompt_toolkit.key_binding import KeyBindings

from tui.themes import THEME_NAMES


def build_keybindings(
    *,
    state: Any,
    MenuLevel: Any,
    show_menu: Any,
    MAIN_MENU_ITEMS: Sequence[Tuple[str, Any]],
    get_custom_tasks_menu_items: Callable[[], List[Tuple[str, Any]]],
    TOP_LANGS: Sequence[str],
    lang_name: Callable[[str], str],
    log: Callable[[str, str], None],
    # persistence / side-effects
    save_ui_settings: Callable[[], Any],
    reset_agent_llm: Callable[[], Any],
    save_monitor_settings: Callable[[], Any],
    save_monitor_targets: Callable[[], Any],
    # menu helpers
    get_monitoring_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_settings_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_llm_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_llm_sub_menu_items: Callable[[Any], List[Tuple[str, Any]]],
    get_agent_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_automation_permissions_menu_items: Callable[[], List[Tuple[str, Any]]],
    get_editors_list: Callable[[], List[Tuple[str, str]]],
    # cleanup/module operations
    get_cleanup_cfg: Callable[[], Any],
    set_cleanup_cfg: Callable[[Any], None],
    load_cleanup_config: Callable[[], Any],
    run_cleanup: Callable[..., Tuple[bool, str]],
    perform_install: Callable[[Any, str], Tuple[bool, str]],
    find_module: Callable[[Any, str, str], Any],
    set_module_enabled: Callable[[Any, Any, bool], bool],
    # locales
    AVAILABLE_LOCALES: Sequence[Any],
    localization: Any,
    # monitoring targets
    get_monitor_menu_items: Callable[[], List[Any]],
    normalize_menu_index: Callable[[List[Any]], None],
    monitor_stop_selected: Callable[[], Tuple[bool, str]],
    monitor_start_selected: Callable[[], Tuple[bool, str]],
    monitor_resolve_watch_items: Callable[[Any], Any],
    monitor_service: Any,
    fs_usage_service: Any,
    opensnoop_service: Any,
    force_ui_update: Callable[[], None],
) -> Tuple[KeyBindings, Callable]:
    kb = KeyBindings()

def _find_window_by_name(event: Any, name: str) -> Any:
    try:
        for w in event.app.layout.find_all_windows():
            if getattr(w, "name", None) == name:
                return w
    except Exception:
        return None
    return None


def _scroll_named_window(event: Any, name: str, delta: int) -> None:
    w = _find_window_by_name(event, name)
    if w is None:
        return
    info = getattr(w, "render_info", None)
    if info is None:
        return
    try:
        max_scroll = max(0, int(info.content_height) - int(info.window_height))
        w.vertical_scroll = max(0, min(max_scroll, int(getattr(w, "vertical_scroll", 0)) + int(delta)))
    except Exception:
        return


def _is_section_item(item: Any) -> bool:
    return isinstance(item, tuple) and len(item) == 3 and item[2] == "section"


def _settings_next_selectable_index(items: List[Any], start: int, direction: int) -> int:
    if not items:
        return 0
    idx = max(0, min(int(start), len(items) - 1))
    step = 1 if direction >= 0 else -1
    
    # Search for the next non-section item in the given direction
    curr = idx
    while 0 <= curr < len(items):
        if not _is_section_item(items[curr]):
            return curr
        curr += step
        
    # Fallback: scan the entire list from the appropriate end
    indices = range(len(items)) if step > 0 else range(len(items) - 1, -1, -1)
    for i in indices:
        if not _is_section_item(items[i]):
            return i
            
    return 0


def _get_menu_max_index(state: Any, MenuLevel: Any, MAIN_MENU_ITEMS: Sequence[Any],
                        get_custom_tasks_menu_items: Callable, get_monitoring_menu_items: Callable,
                        get_editors_list: Callable, get_cleanup_cfg: Callable,
                        AVAILABLE_LOCALES: Sequence[Any], get_settings_menu_items: Callable,
                        get_automation_permissions_menu_items: Callable,
                        get_monitor_menu_items: Callable, get_llm_menu_items: Callable,
                        get_llm_sub_menu_items: Callable, get_agent_menu_items: Callable) -> int:
    lvl = state.menu_level
    
    # Registry of calculations for most menu levels
    calc_map = {
        MenuLevel.MAIN: lambda: len(MAIN_MENU_ITEMS) - 1,
        MenuLevel.CUSTOM_TASKS: lambda: max(0, len(get_custom_tasks_menu_items()) - 1),
        MenuLevel.MONITORING: lambda: max(0, len(get_monitoring_menu_items()) - 1),
        MenuLevel.LOCALES: lambda: len(AVAILABLE_LOCALES) - 1,
        MenuLevel.SETTINGS: lambda: max(0, len(get_settings_menu_items()) - 1),
        MenuLevel.AUTOMATION_PERMISSIONS: lambda: max(0, len(get_automation_permissions_menu_items()) - 1),
        MenuLevel.MONITOR_TARGETS: lambda: max(0, len(get_monitor_menu_items()) - 1),
        MenuLevel.LLM_SETTINGS: lambda: max(0, len(get_llm_menu_items()) - 1),
        MenuLevel.AGENT_SETTINGS: lambda: max(0, len(get_agent_menu_items()) - 1),
        MenuLevel.APPEARANCE: lambda: max(0, len(THEME_NAMES) - 1),
        MenuLevel.LANGUAGE: lambda: 1,
    }
    
    if lvl in calc_map:
        return calc_map[lvl]()
        
    # Handle composite or dynamic levels
    if lvl in {MenuLevel.CLEANUP_EDITORS, MenuLevel.MODULE_EDITORS, MenuLevel.INSTALL_EDITORS}:
        return max(0, len(get_editors_list()) - 1)
        
    if lvl == MenuLevel.MODULE_LIST:
        m_cfg = get_cleanup_cfg() or {}
        m_mods = m_cfg.get("editors", {}).get(state.selected_editor or "", {}).get("modules", [])
        return max(0, len(m_mods) - 1)
        
    if lvl in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
        return max(0, len(get_llm_sub_menu_items(lvl)) - 1)
        
    return 0

    @kb.add("c-c")
    def _(event):
        event.app.exit()

    @kb.add("f6")
    def _(event):
        if show_menu():
            return
        cur = str(getattr(state, "ui_scroll_target", "log") or "log")
        state.ui_scroll_target = "agents" if cur == "log" else "log"

    @kb.add("f3")
    def _(event):
        """Decrease left panel ratio."""
        state.ui_left_panel_ratio = max(0.2, float(getattr(state, "ui_left_panel_ratio", 0.6)) - 0.05)
        save_ui_settings()

    @kb.add("f4")
    def _(event):
        """Increase left panel ratio."""
        state.ui_left_panel_ratio = min(0.8, float(getattr(state, "ui_left_panel_ratio", 0.6)) + 0.05)
        save_ui_settings()

    @kb.add("pageup")
    def _(event):
        if show_menu():
            return
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        name = "agents" if target == "agents" else "log"
        if name == "log":
            state.ui_log_follow = False
            state.ui_log_cursor_y = max(0, int(getattr(state, "ui_log_cursor_y", 0)) - 10)
        elif name == "agents":
            state.ui_agents_follow = False
            state.ui_agents_cursor_y = max(0, int(getattr(state, "ui_agents_cursor_y", 0)) - 10)
        _scroll_named_window(event, name, -10)

    @kb.add("pagedown")
    def _(event):
        if show_menu():
            return
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        name = "agents" if target == "agents" else "log"
        if name == "log":
            state.ui_log_cursor_y = int(getattr(state, "ui_log_cursor_y", 0)) + 10
            if state.ui_log_cursor_y >= max(0, int(getattr(state, "ui_log_line_count", 1)) - 1):
                state.ui_log_follow = True
        elif name == "agents":
            state.ui_agents_cursor_y = int(getattr(state, "ui_agents_cursor_y", 0)) + 10
            if state.ui_agents_cursor_y >= max(0, int(getattr(state, "ui_agents_line_count", 1)) - 1):
                state.ui_agents_follow = True
        _scroll_named_window(event, name, 10)

    @kb.add("c-up")
    def _(event):
        if show_menu():
            return
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        name = "agents" if target == "agents" else "log"
        if name == "log":
            state.ui_log_follow = False
            state.ui_log_cursor_y = max(0, int(getattr(state, "ui_log_cursor_y", 0)) - 1)
        elif name == "agents":
            state.ui_agents_follow = False
            state.ui_agents_cursor_y = max(0, int(getattr(state, "ui_agents_cursor_y", 0)) - 1)
        _scroll_named_window(event, name, -1)

    @kb.add("c-down")
    def _(event):
        if show_menu():
            return
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        name = "agents" if target == "agents" else "log"
        if name == "log":
            state.ui_log_cursor_y = int(getattr(state, "ui_log_cursor_y", 0)) + 1
            if state.ui_log_cursor_y >= max(0, int(getattr(state, "ui_log_line_count", 1)) - 1):
                state.ui_log_follow = True
        elif name == "agents":
            state.ui_agents_cursor_y = int(getattr(state, "ui_agents_cursor_y", 0)) + 1
            if state.ui_agents_cursor_y >= max(0, int(getattr(state, "ui_agents_line_count", 1)) - 1):
                state.ui_agents_follow = True
        _scroll_named_window(event, name, 1)

    @kb.add("f2")
    def _(event):
        if state.menu_level == MenuLevel.NONE:
            state.menu_level = MenuLevel.MAIN
            state.menu_index = 0
            # Focus the menu window
            w = _find_window_by_name(event, "menu")
            if w:
                event.app.layout.focus(w)
        else:
            state.menu_level = MenuLevel.NONE
            state.menu_index = 0
            state.ui_scroll_target = "agents"
            # Focus back to input field
            w = _find_window_by_name(event, "input")
            if w:
                event.app.layout.focus(w)

    @kb.add("escape")
    @kb.add("q")
    def _(event):
        if state.menu_level == MenuLevel.MAIN:
            state.menu_level = MenuLevel.NONE
            state.menu_index = 0
            state.ui_scroll_target = "agents"
        elif state.menu_level in {
            MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS
        }:
            state.menu_level = MenuLevel.LLM_SETTINGS
            state.menu_index = 0
        elif state.menu_level in {
            MenuLevel.LLM_SETTINGS, MenuLevel.AGENT_SETTINGS, MenuLevel.APPEARANCE, MenuLevel.LANGUAGE, MenuLevel.LAYOUT, MenuLevel.UNSAFE_MODE,
            MenuLevel.AUTOMATION_PERMISSIONS, MenuLevel.DEV_SETTINGS, MenuLevel.LOCALES, MenuLevel.SELF_HEALING, MenuLevel.LEARNING_MODE
        }:
            state.menu_level = MenuLevel.SETTINGS
            state.menu_index = 0
        elif state.menu_level in {
            MenuLevel.SETTINGS, MenuLevel.CUSTOM_TASKS, MenuLevel.MONITORING, MenuLevel.CLEANUP_EDITORS,
            MenuLevel.MODULE_EDITORS, MenuLevel.INSTALL_EDITORS
        }:
            state.menu_level = MenuLevel.MAIN
            state.menu_index = 0
        elif state.menu_level == MenuLevel.MODULE_LIST:
            state.menu_level = MenuLevel.MODULE_EDITORS
            state.menu_index = 0
        elif state.menu_level == MenuLevel.MONITOR_CONTROL or state.menu_level == MenuLevel.MONITOR_TARGETS:
            state.menu_level = MenuLevel.MONITORING
            state.menu_index = 0
        else:
            # Not in menu, focus the input field
            w = _find_window_by_name(event, "input")
            if w:
                event.app.layout.focus(w)

    @kb.add("c-k")
    def _(event):
        """Copy active panel content to clipboard (Ctrl+K).
        
        Copies the entire content of the currently active/focused panel:
        - LOG panel (left side)
        - АГЕНТИ (AGENTS) panel (right side)
        
        Auto-detects which panel has focus or uses the currently active scroll target.
        Shows status message with byte count copied.
        """
        try:
            from tui.clipboard_utils import copy_to_clipboard
            from tui.render import get_logs, get_agent_messages
            
            # Determine which panel to copy from
            # Priority: 1) Currently focused panel, 2) Currently active scroll target
            target = str(getattr(state, "ui_scroll_target", "log") or "log")
            content = ""
            panel_name = target.upper()
            
            try:
                if target == "log":
                    logs = get_logs()
                    content = "".join(str(t or "") for _, t in logs)
                    panel_name = "LOG"
                else:
                    msgs = get_agent_messages()
                    content = "".join(str(t or "") for _, t in msgs)
                    panel_name = "АГЕНТИ"
            except Exception:
                # If render functions fail, try to get content from the panel
                pass
            
            if content:
                # Use new clipboard utility for better cross-platform support
                success = copy_to_clipboard(content, log)
                if not success:
                    log(f"Помилка: не вдалося скопіювати з панелі {panel_name}", "error")
            else:
                log(f"Панель {panel_name} порожня - нічого копіювати", "info")
                
        except Exception as e:
            log(f"Помилка копіювання: {str(e)}", "error")

    @kb.add("c-o")
    def _(event):

        """Toggle auto-copy on text selection (Ctrl+O).
        
        When enabled, selecting text with the mouse will automatically
        copy the selected text to the clipboard.
        """
        try:
            from tui.selection_tracker import (
                set_auto_copy_enabled, 
                SELECTION_AUTO_COPY_ENABLED,
                get_selection_stats
            )
            
            # Toggle
            stats = get_selection_stats()
            new_state = not stats.get("auto_copy_enabled", True)
            set_auto_copy_enabled(new_state)
            
            status = "Увімкнено" if new_state else "Вимкнено"
            log(f"Автокопіювання при виділенні: {status}", "action")
            
        except Exception as e:
            log(f"Помилка перемикання автокопіювання: {str(e)}", "error")

    @kb.add("up", filter=show_menu)
    def _(event):
        state.menu_index = max(0, state.menu_index - 1)
        if state.menu_level == MenuLevel.SETTINGS:
            items = get_settings_menu_items()
            state.menu_index = _settings_next_selectable_index(items, state.menu_index, -1)
        if state.menu_level == MenuLevel.MONITOR_TARGETS:
            items = get_monitor_menu_items()
            normalize_menu_index(items)
        force_ui_update()

    @kb.add("down", filter=show_menu)
    def _(event):
        max_idx = _get_menu_max_index(
            state, MenuLevel, MAIN_MENU_ITEMS, get_custom_tasks_menu_items,
            get_monitoring_menu_items, get_editors_list, get_cleanup_cfg,
            AVAILABLE_LOCALES, get_settings_menu_items, get_automation_permissions_menu_items,
            get_monitor_menu_items, get_llm_menu_items, get_llm_sub_menu_items,
            get_agent_menu_items
        )

        state.menu_index = min(max_idx, state.menu_index + 1)

        if state.menu_level == MenuLevel.SETTINGS:
            items = get_settings_menu_items()
            state.menu_index = _settings_next_selectable_index(items, state.menu_index, 1)

        if state.menu_level == MenuLevel.MONITOR_TARGETS:
            items = get_monitor_menu_items()
            normalize_menu_index(items)
            
        force_ui_update()

    @kb.add("left", filter=show_menu)
    def _(event):
        if state.menu_level == MenuLevel.LAYOUT:
            if state.menu_index == 0:  # Ratio slider
                p = float(getattr(state, "ui_left_panel_ratio", 0.6))
                state.ui_left_panel_ratio = max(0.2, p - 0.05)
                save_ui_settings()

    @kb.add("right", filter=show_menu)
    def _(event):
        if state.menu_level == MenuLevel.LAYOUT:
            if state.menu_index == 0:  # Ratio slider
                p = float(getattr(state, "ui_left_panel_ratio", 0.6))
                state.ui_left_panel_ratio = min(0.8, p + 0.05)
                save_ui_settings()

    @kb.add("d", filter=show_menu)
    def _(event):
        if state.menu_level != MenuLevel.CLEANUP_EDITORS:
            return

        editors = get_editors_list()
        if not editors:
            return
        key = editors[state.menu_index][0]
        state.selected_editor = key
        ok, msg = run_cleanup(load_cleanup_config(), key, dry_run=True)
        log(msg, "action" if ok else "error")

    def handle_module_list_space():
        editor = state.selected_editor
        if not editor: return
        cfg = get_cleanup_cfg() or {}
        meta = cfg.get("editors", {}).get(editor, {})
        mods = meta.get("modules", [])
        if not mods: return
        m = mods[state.menu_index]
        mid = m.get("id")
        if not mid: return
        ref = find_module(cfg, editor, str(mid))
        if not ref: return
        new_state = not bool(m.get("enabled"))
        if set_module_enabled(cfg, ref, new_state):
            set_cleanup_cfg(load_cleanup_config())
            log(f"{editor}/{mid}: {'ON' if new_state else 'OFF'}", "action")
        else:
            log("Не вдалося змінити модуль.", "error")

    def handle_llm_settings_space():
        items = get_llm_sub_menu_items(state.menu_level)
        if not items: return
        state.menu_index = max(0, min(state.menu_index, len(items) - 1))
        itm = items[state.menu_index]
        key = itm[1] if len(itm) > 1 else ""
        section = {MenuLevel.LLM_ATLAS: "atlas", MenuLevel.LLM_TETYANA: "tetyana", 
                   MenuLevel.LLM_GRISHA: "grisha", MenuLevel.LLM_VISION: "vision", 
                   MenuLevel.LLM_DEFAULTS: "defaults"}.get(state.menu_level, "")
        from tui.tools import tool_llm_set, tool_llm_status
        if key == "provider":
            cur_prov = tool_llm_status({"section": section}).get("provider", "copilot")
            provs = ["copilot", "openai", "anthropic", "gemini"]
            next_prov = provs[(provs.index(cur_prov) + 1) % len(provs)] if cur_prov in provs else "copilot"
            tool_llm_set({"section": section, "provider": next_prov})
            log(f"Provider set to: {next_prov}", "action")
        elif key in {"model", "main_model"}:
            start_status = tool_llm_status({"section": section})
            cur_mod = start_status.get("model") or start_status.get("main_model") or ""
            models = ["gpt-4.1", "gpt-4o", "gpt-4", "claude-3-5-sonnet-latest", "gemini-1.5-pro-002", "mistral-large-latest"]
            next_mod = models[(models.index(cur_mod) + 1) % len(models)] if cur_mod in models else "gpt-4o"
            tool_llm_set({"main_model": next_mod} if section == "defaults" else {"section": section, "model": next_mod})
            log(f"Model set to: {next_mod}", "action")
        elif key == "vision_model":
            cur_mod = tool_llm_status({"section": section}).get("vision_model", "")
            models = ["gpt-4.1-vision", "gpt-4o", "claude-3-opus", "gemini-1.5-flash"]
            next_mod = models[(models.index(cur_mod) + 1) % len(models)] if cur_mod in models else "gpt-4o"
            tool_llm_set({"vision_model": next_mod})
            log(f"Vision model set to: {next_mod}", "action")
        force_ui_update()

    @kb.add("space", filter=show_menu)
    def _(event):
        lvl = state.menu_level
        if lvl == MenuLevel.MODULE_LIST:
            handle_module_list_space()
        elif lvl == MenuLevel.LOCALES:
            loc = AVAILABLE_LOCALES[state.menu_index]
            if loc.code == localization.primary:
                log("Не можна вимкнути primary локаль.", "error")
                return
            if loc.code in localization.selected:
                localization.selected = [c for c in localization.selected if c != loc.code]
                log(f"Вимкнено: {loc.code}", "action")
            else:
                localization.selected.append(loc.code)
                log(f"Увімкнено: {loc.code}", "action")
            localization.save()
        elif lvl == MenuLevel.MONITOR_TARGETS:
            items = get_monitor_menu_items()
            if not items: return
            normalize_menu_index(items)
            it = items[state.menu_index]
            if not getattr(it, "selectable", False): return
            if it.key in state.monitor_targets:
                state.monitor_targets.remove(it.key)
                log(f"Monitor: OFF {it.label}", "action")
            else:
                state.monitor_targets.add(it.key)
                log(f"Monitor: ON {it.label}", "action")
            force_ui_update()
        elif lvl in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
            handle_llm_settings_space()

    @kb.add("s", filter=show_menu)
    def _(event):
        if state.menu_level != MenuLevel.MONITOR_CONTROL:
            return
        if state.monitor_active:
            log("Stop monitoring before changing source.", "error")
            return
        order = ["watchdog", "fs_usage", "opensnoop"]
        cur = state.monitor_source if state.monitor_source in order else "watchdog"
        idx = order.index(cur)
        state.monitor_source = order[(idx + 1) % len(order)]
        save_monitor_settings()
        log(f"Monitoring source: {state.monitor_source}", "action")

    @kb.add("u", filter=show_menu)
    def _(event):
        if state.menu_level != MenuLevel.MONITOR_CONTROL:
            return
        if state.monitor_active:
            log("Stop monitoring before changing sudo setting.", "error")
            return
        state.monitor_use_sudo = not state.monitor_use_sudo
        save_monitor_settings()
        log(f"Monitoring sudo: {'ON' if state.monitor_use_sudo else 'OFF'}", "action")

    def handle_automation_enter():
        items = get_automation_permissions_menu_items()
        if not items: return
        state.menu_index = max(0, min(state.menu_index, len(items) - 1))
        itm = items[state.menu_index]
        _, perm_key = itm[0], itm[1]
        if perm_key == "ui_execution_mode":
            cur = str(getattr(state, "ui_execution_mode", "native") or "native").strip().lower() or "native"
            state.ui_execution_mode = "gui" if cur == "native" else "native"
            log(f"Execution mode: {state.ui_execution_mode}", "action")
        elif perm_key == "automation_allow_shortcuts":
            state.automation_allow_shortcuts = not bool(getattr(state, "automation_allow_shortcuts", False))
            log(f"Shortcuts: {'ON' if state.automation_allow_shortcuts else 'OFF'}", "action")
        save_ui_settings()

    @kb.add("enter", filter=show_menu)
    def handle_menu_enter(event=None):
        lvl = state.menu_level
        if lvl == MenuLevel.MAIN:
            itm = MAIN_MENU_ITEMS[state.menu_index]
            state.menu_level, state.menu_index = itm[1], 0
        elif lvl == MenuLevel.CUSTOM_TASKS:
            items = get_custom_tasks_menu_items()
            if items:
                action = items[max(0, min(state.menu_index, len(items) - 1))][1]
                if callable(action):
                    try: ok, msg = action(); log(msg, "action" if ok else "error")
                    except Exception as e: log(f"Task failed: {e}", "error")
        elif lvl == MenuLevel.MONITORING:
            items = get_monitoring_menu_items()
            if items: state.menu_level, state.menu_index = items[max(0, min(state.menu_index, len(items) - 1))][1], 0
        elif lvl == MenuLevel.SETTINGS:
            items = get_settings_menu_items()
            if items:
                idx = _settings_next_selectable_index(items, max(0, min(state.menu_index, len(items) - 1)), 1)
                item = items[idx]
                if not _is_section_item(item): state.menu_level, state.menu_index = item[1], 0
        elif lvl == MenuLevel.LLM_SETTINGS:
            items = get_llm_menu_items()
            if items: state.menu_level, state.menu_index = items[max(0, min(state.menu_index, len(items) - 1))][1], 0
        elif lvl in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
             log("To edit model, use CLI: /llm set section=<name> model=<model>", "info")
        elif lvl == MenuLevel.UNSAFE_MODE:
            state.ui_unsafe_mode = not bool(getattr(state, "ui_unsafe_mode", False))
            save_ui_settings(); log(f"Unsafe: {'ON' if state.ui_unsafe_mode else 'OFF'}", "action")
        elif lvl == MenuLevel.SELF_HEALING:
            state.ui_self_healing = not bool(getattr(state, "ui_self_healing", False))
            save_ui_settings(); log(f"Self-healing: {'ON' if state.ui_self_healing else 'OFF'}", "action")
        elif lvl == MenuLevel.LEARNING_MODE:
            state.learning_mode = not bool(getattr(state, "learning_mode", False))
            save_ui_settings(); log(f"Learning: {'ON' if state.learning_mode else 'OFF'}", "action")
        elif lvl == MenuLevel.AUTOMATION_PERMISSIONS:
            handle_automation_enter()
        elif lvl == MenuLevel.DEV_SETTINGS:
            cur = str(getattr(state, "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower()
            state.ui_dev_code_provider = "continue" if cur == "vibe-cli" else "vibe-cli"
            save_ui_settings(); log(f"Dev provider: {state.ui_dev_code_provider.upper()}", "action")
        elif lvl == MenuLevel.APPEARANCE:
            themes = list(THEME_NAMES)
            state.ui_theme = themes[max(0, min(state.menu_index, len(themes) - 1))]
            save_ui_settings(); log(f"Theme set: {state.ui_theme}", "action")
        elif lvl == MenuLevel.LANGUAGE:
            langs = list(TOP_LANGS)
            if langs:
                idx = max(0, min(state.menu_index, 1))
                if idx == 0:
                    cur = state.ui_lang if state.ui_lang in langs else langs[0]
                    state.ui_lang = langs[(langs.index(cur) + 1) % len(langs)]
                    save_ui_settings(); log(f"UI lang: {state.ui_lang}", "action")
                else:
                    cur = state.chat_lang if state.chat_lang in langs else langs[0]
                    state.chat_lang = langs[(langs.index(cur) + 1) % len(langs)]
                    save_ui_settings(); reset_agent_llm(); log(f"Chat lang: {state.chat_lang}", "action")
        elif lvl == MenuLevel.CLEANUP_EDITORS:
            editors = get_editors_list()
            if editors:
                key = editors[state.menu_index][0]
                state.selected_editor = key; log(f"Clearing {key}...", "info")
                import threading
                def run_cleanup_thread():
                    import re
                    def cleanup_log(line: str):
                        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                        if clean_line.strip(): log(clean_line, "action"); force_ui_update()
                    ok, msg = run_cleanup(load_cleanup_config(), key, dry_run=False, log_callback=cleanup_log)
                    log(msg, "action" if ok else "error"); force_ui_update()
                threading.Thread(target=run_cleanup_thread, daemon=True).start()
        elif lvl == MenuLevel.MODULE_EDITORS:
            editors = get_editors_list()
            if editors: state.selected_editor, state.menu_level, state.menu_index = editors[state.menu_index][0], MenuLevel.MODULE_LIST, 0
        elif lvl == MenuLevel.INSTALL_EDITORS:
            editors = get_editors_list()
            if editors: ok, msg = perform_install(load_cleanup_config(), editors[state.menu_index][0]); log(msg, "action" if ok else "error")
        elif lvl == MenuLevel.LOCALES:
            loc = AVAILABLE_LOCALES[state.menu_index]
            localization.primary = loc.code
            localization.selected = [loc.code] + [c for c in localization.selected if c != loc.code]
            localization.save(); log(f"Primary set: {loc.code}", "action")
        elif lvl == MenuLevel.MONITOR_TARGETS:
            if save_monitor_targets(): log(f"Monitor targets saved", "action")
            else: log("Failed to save", "error")
            state.menu_level, state.menu_index = MenuLevel.MAIN, 0
        elif lvl == MenuLevel.MONITOR_CONTROL:
            if state.monitor_active:
                ok, msg = monitor_stop_selected()
                state.monitor_active = bool(monitor_service.running or fs_usage_service.running or opensnoop_service.running)
                log(msg, "action" if ok else "error")
            elif state.monitor_targets:
                ok, msg = monitor_start_selected()
                state.monitor_active = bool(monitor_service.running or fs_usage_service.running or opensnoop_service.running)
                log(msg, "action" if ok else "error")
            else: log("Select targets first", "error")

    return kb, handle_menu_enter
