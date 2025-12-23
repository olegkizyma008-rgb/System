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
    get_automation_permissions_menu_items: Callable[[], List[Tuple[str, Any, Optional[str]]]],
    handle_automation_permissions_enter: Callable[[Dict[str, Any]], None],
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

    # Context object for helpers
    ctx = {
        "state": state, "MenuLevel": MenuLevel, "show_menu": show_menu, 
        "log": log, "force_ui_update": force_ui_update, "save_ui_settings": save_ui_settings,
        "reset_agent_llm": reset_agent_llm, "save_monitor_settings": save_monitor_settings,
        "save_monitor_targets": save_monitor_targets, "get_editors_list": get_editors_list,
        "get_cleanup_cfg": get_cleanup_cfg, "set_cleanup_cfg": set_cleanup_cfg,
        "load_cleanup_config": load_cleanup_config, "run_cleanup": run_cleanup,
        "localization": localization, "AVAILABLE_LOCALES": AVAILABLE_LOCALES,
        "monitor_service": monitor_service, "fs_usage_service": fs_usage_service,
        "opensnoop_service": opensnoop_service, "monitor_stop_selected": monitor_stop_selected,
        "monitor_start_selected": monitor_start_selected, "normalize_menu_index": normalize_menu_index,
        "get_monitor_menu_items": get_monitor_menu_items, "get_settings_menu_items": get_settings_menu_items,
        "get_monitoring_menu_items": get_monitoring_menu_items, "get_custom_tasks_menu_items": get_custom_tasks_menu_items,
        "MAIN_MENU_ITEMS": MAIN_MENU_ITEMS, "TOP_LANGS": TOP_LANGS, "get_llm_menu_items": get_llm_menu_items,
        "get_llm_sub_menu_items": get_llm_sub_menu_items, "get_agent_menu_items": get_agent_menu_items,
        "get_automation_permissions_menu_items": get_automation_permissions_menu_items,
        "handle_automation_permissions_enter": handle_automation_permissions_enter,
        "perform_install": perform_install, "find_module": find_module, "set_module_enabled": set_module_enabled,
    }

    _register_global_keys(kb)
    _register_navigation_keys(kb, state, show_menu)
    _register_layout_keys(kb, state, save_ui_settings)
    _register_clipboard_keys(kb, state, log)
    _register_menu_movement_keys(kb, ctx)
    _register_action_keys(kb, ctx)

    @kb.add("enter", filter=show_menu)
    def handle_menu_enter(event=None):
        _handle_menu_enter_dispatch(ctx)

    return kb, handle_menu_enter

def _register_global_keys(kb: KeyBindings):
    @kb.add("c-c")
    def _(event):
        event.app.exit()

def _register_navigation_keys(kb: KeyBindings, state: Any, show_menu: Callable):
    @kb.add("f6")
    def _(event):
        if not show_menu():
            cur = str(getattr(state, "ui_scroll_target", "log") or "log")
            state.ui_scroll_target = "agents" if cur == "log" else "log"

    def scroll(event, delta):
        if show_menu(): return
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        name = "agents" if target == "agents" else "log"
        if name == "log":
            state.ui_log_follow = delta > 0
            state.ui_log_cursor_y = max(0, int(getattr(state, "ui_log_cursor_y", 0)) + delta)
        else:
            state.ui_agents_follow = delta > 0
            state.ui_agents_cursor_y = max(0, int(getattr(state, "ui_agents_cursor_y", 0)) + delta)
        _scroll_named_window(event, name, delta)

    @kb.add("pageup")
    def _(event): scroll(event, -10)
    @kb.add("pagedown")
    def _(event): scroll(event, 10)
    @kb.add("c-up")
    def _(event): scroll(event, -1)
    @kb.add("c-down")
    def _(event): scroll(event, 1)

def _register_layout_keys(kb: KeyBindings, state: Any, save_ui_settings: Callable):
    @kb.add("f3")
    def _(event):
        state.ui_left_panel_ratio = max(0.2, float(getattr(state, "ui_left_panel_ratio", 0.6)) - 0.05)
        save_ui_settings()

    @kb.add("f4")
    def _(event):
        state.ui_left_panel_ratio = min(0.8, float(getattr(state, "ui_left_panel_ratio", 0.6)) + 0.05)
        save_ui_settings()

def _register_clipboard_keys(kb: KeyBindings, state: Any, log: Callable):
    @kb.add("c-k")
    def _(event):
        _handle_copy_to_clipboard(state, log)

    @kb.add("c-o")
    def _(event):
        _toggle_auto_copy(log)


def _handle_copy_to_clipboard(state: Any, log: Callable):
    """Handle Ctrl+K: copy current panel content to clipboard."""
    try:
        from tui.clipboard_utils import copy_to_clipboard
        from tui.render import get_logs, get_agent_messages
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        
        if target == "log":
            content = "".join(str(t or "") for _, t in get_logs())
            pname = "LOG"
        else:
            content = "".join(str(t or "") for _, t in get_agent_messages())
            pname = "АГЕНТИ"
        
        if not content:
            log(f"Панель {pname} порожня", "info")
            return
        if not copy_to_clipboard(content, log):
            log(f"Помилка: не вдалося скопіювати з панелі {pname}", "error")
    except Exception as e:
        log(f"Помилка копіювання: {str(e)}", "error")


def _toggle_auto_copy(log: Callable):
    """Toggle auto-copy mode."""
    try:
        from tui.selection_tracker import set_auto_copy_enabled, get_selection_stats
        enabled = not get_selection_stats().get("auto_copy_enabled", True)
        set_auto_copy_enabled(enabled)
        log(f"Автокопіювання: {'Увімкнено' if enabled else 'Вимкнено'}", "action")
    except Exception as e:
        log(f"Помилка: {str(e)}", "error")

def _register_menu_movement_keys(kb: KeyBindings, ctx: Dict[str, Any]):
    """Register menu navigation keys (f2, up/down, etc.)."""
    state, show_menu = ctx["state"], ctx["show_menu"]
    MenuLevel, force_ui_update = ctx["MenuLevel"], ctx["force_ui_update"]

    @kb.add("f2")
    def _handle_f2(event):
        if state.menu_level == MenuLevel.NONE:
            state.menu_level, state.menu_index = MenuLevel.MAIN, 0
            w = _find_window_by_name(event, "menu")
            if w:
                event.app.layout.focus(w)
        else:
            state.menu_level, state.menu_index, state.ui_scroll_target = MenuLevel.NONE, 0, "agents"
            w = _find_window_by_name(event, "input")
            if w:
                event.app.layout.focus(w)

    @kb.add("escape")
    @kb.add("q")
    def _handle_esc_q(event):
        _handle_menu_escape(ctx, event)

    @kb.add("up", filter=show_menu)
    def _handle_up(event):
        state.menu_index = max(0, state.menu_index - 1)
        if state.menu_level == MenuLevel.SETTINGS:
            state.menu_index = _settings_next_selectable_index(ctx["get_settings_menu_items"](), state.menu_index, -1)
        if state.menu_level == MenuLevel.MONITOR_TARGETS:
            ctx["normalize_menu_index"](ctx["get_monitor_menu_items"]())
        force_ui_update()

    @kb.add("down", filter=show_menu)
    def _handle_down(event):
        state.menu_index = min(_get_menu_max_index_from_ctx(ctx), state.menu_index + 1)
        if state.menu_level == MenuLevel.SETTINGS:
            state.menu_index = _settings_next_selectable_index(ctx["get_settings_menu_items"](), state.menu_index, 1)
        if state.menu_level == MenuLevel.MONITOR_TARGETS:
            ctx["normalize_menu_index"](ctx["get_monitor_menu_items"]())
        force_ui_update()

    @kb.add("left", filter=show_menu)
    def _handle_left(event):
        if state.menu_level == MenuLevel.LAYOUT and state.menu_index == 0:
            state.ui_left_panel_ratio = max(0.2, float(getattr(state, "ui_left_panel_ratio", 0.6)) - 0.05)
            ctx["save_ui_settings"]()

    @kb.add("right", filter=show_menu)
    def _handle_right(event):
        if state.menu_level == MenuLevel.LAYOUT and state.menu_index == 0:
            state.ui_left_panel_ratio = min(0.8, float(getattr(state, "ui_left_panel_ratio", 0.6)) + 0.05)
            ctx["save_ui_settings"]()


def _register_action_keys(kb: KeyBindings, ctx: Dict[str, Any]):
    """Register menu action keys (space, d, s, u)."""
    state, show_menu, log = ctx["state"], ctx["show_menu"], ctx["log"]
    MenuLevel = ctx["MenuLevel"]

    @kb.add("space", filter=show_menu)
    def _handle_space(event):
        _process_menu_space_action(ctx)

    @kb.add("d", filter=show_menu)
    def _handle_d(event):
        if state.menu_level == MenuLevel.CLEANUP_EDITORS:
            _execute_dry_run_cleanup(ctx)

    @kb.add("s", filter=show_menu)
    def _handle_s(event):
        if state.menu_level == MenuLevel.MONITOR_CONTROL and not state.monitor_active:
            _cycle_monitor_source(ctx)

    @kb.add("u", filter=show_menu)
    def _handle_u(event):
        if state.menu_level == MenuLevel.MONITOR_CONTROL and not state.monitor_active:
            _toggle_monitor_sudo(ctx)


def _process_menu_space_action(ctx: Dict[str, Any]):
    """Process space key in menu."""
    state, MenuLevel = ctx["state"], ctx["MenuLevel"]
    lvl = state.menu_level
    if lvl == MenuLevel.MODULE_LIST:
        _handle_module_list_space(ctx)
    elif lvl == MenuLevel.LOCALES:
        _handle_locales_toggle(ctx)
    elif lvl == MenuLevel.MONITOR_TARGETS:
        _handle_monitor_targets_toggle(ctx)
    elif lvl in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
        _handle_llm_settings_space(ctx)
    elif lvl == MenuLevel.AGENT_SETTINGS:
        _handle_agent_settings_enter(ctx)


def _execute_dry_run_cleanup(ctx: Dict[str, Any]):
    """Execute dry-run cleanup."""
    state, log = ctx["state"], ctx["log"]
    editors = ctx["get_editors_list"]()
    if editors:
        state.selected_editor = editors[state.menu_index][0]
        ok, msg = ctx["run_cleanup"](ctx["load_cleanup_config"](), state.selected_editor, dry_run=True)
        log(msg, "action" if ok else "error")


def _cycle_monitor_source(ctx: Dict[str, Any]):
    """Cycle monitoring data source."""
    state, log = ctx["state"], ctx["log"]
    order = ["watchdog", "fs_usage", "opensnoop"]
    cur = state.monitor_source if state.monitor_source in order else "watchdog"
    state.monitor_source = order[(order.index(cur) + 1) % len(order)]
    ctx["save_monitor_settings"]()
    log(f"Monitoring source: {state.monitor_source}", "action")


def _toggle_monitor_sudo(ctx: Dict[str, Any]):
    """Toggle sudo for monitoring."""
    state, log = ctx["state"], ctx["log"]
    state.monitor_use_sudo = not state.monitor_use_sudo
    ctx["save_monitor_settings"]()
    log(f"Monitoring sudo: {'ON' if state.monitor_use_sudo else 'OFF'}", "action")

def _handle_menu_escape(ctx, event):
    """Handle escape/q key press in menu navigation."""
    state, MenuLevel = ctx["state"], ctx["MenuLevel"]
    
    # Level -> Parent level mapping
    llm_submenus = {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}
    settings_submenus = {MenuLevel.LLM_SETTINGS, MenuLevel.AGENT_SETTINGS, MenuLevel.APPEARANCE, MenuLevel.LANGUAGE, 
                         MenuLevel.LAYOUT, MenuLevel.UNSAFE_MODE, MenuLevel.AUTOMATION_PERMISSIONS, 
                         MenuLevel.DEV_SETTINGS, MenuLevel.LOCALES, MenuLevel.SELF_HEALING, MenuLevel.MEMORY_MANAGER,
                         MenuLevel.MCP_CLIENT_SETTINGS}
    main_submenus = {MenuLevel.SETTINGS, MenuLevel.CUSTOM_TASKS, MenuLevel.MONITORING, 
                     MenuLevel.CLEANUP_EDITORS, MenuLevel.MODULE_EDITORS, MenuLevel.INSTALL_EDITORS}
    
    target_level, target_scroll = _get_escape_target(state.menu_level, MenuLevel, llm_submenus, settings_submenus, main_submenus)
    
    if target_level is not None:
        state.menu_level, state.menu_index = target_level, 0
        if target_scroll:
            state.ui_scroll_target = target_scroll
    else:
        w = _find_window_by_name(event, "input")
        if w:
            event.app.layout.focus(w)


def _get_escape_target(current_level, MenuLevel, llm_submenus, settings_submenus, main_submenus):
    """Get target menu level after escape. Returns (level, scroll_target)."""
    if current_level == MenuLevel.MAIN:
        return MenuLevel.NONE, "agents"
    if current_level in llm_submenus:
        return MenuLevel.LLM_SETTINGS, None
    if current_level in settings_submenus:
        return MenuLevel.SETTINGS, None
    if current_level in main_submenus:
        return MenuLevel.MAIN, None
    if current_level == MenuLevel.MODULE_LIST:
        return MenuLevel.MODULE_EDITORS, None
    if current_level in {MenuLevel.MONITOR_CONTROL, MenuLevel.MONITOR_TARGETS}:
        return MenuLevel.MONITORING, None
    return None, None

def _handle_module_list_space(ctx):
    state, log = ctx["state"], ctx["log"]
    editor = state.selected_editor
    if not editor: return
    cfg = ctx["get_cleanup_cfg"]() or {}
    mods = cfg.get("editors", {}).get(editor, {}).get("modules", [])
    if not mods: return
    m = mods[state.menu_index]
    mid = m.get("id")
    ref = ctx["find_module"](cfg, editor, str(mid))
    if ref:
        en = not bool(m.get("enabled"))
        if ctx["set_module_enabled"](cfg, ref, en):
            ctx["set_cleanup_cfg"](ctx["load_cleanup_config"]())
            log(f"{editor}/{mid}: {'ON' if en else 'OFF'}", "action")
    else: log("Не вдалося змінити модуль.", "error")

def _handle_llm_settings_space(ctx):
    state, log = ctx["state"], ctx["log"]
    items = ctx["get_llm_sub_menu_items"](state.menu_level)
    if not items: return
    itm = items[max(0, min(state.menu_index, len(items) - 1))]
    key = itm[1] if len(itm) > 1 else ""
    sec = {ctx["MenuLevel"].LLM_ATLAS: "atlas", ctx["MenuLevel"].LLM_TETYANA: "tetyana", 
           ctx["MenuLevel"].LLM_GRISHA: "grisha", ctx["MenuLevel"].LLM_VISION: "vision", 
           ctx["MenuLevel"].LLM_DEFAULTS: "defaults"}.get(state.menu_level, "")
    from tui.tools import tool_llm_set, tool_llm_status
    if key == "provider":
        cur = tool_llm_status({"section": sec}).get("provider", "copilot")
        p = ["copilot", "openai", "anthropic", "gemini"]
        nxt = p[(p.index(cur)+1)%len(p)] if cur in p else "copilot"
        tool_llm_set({"section": sec, "provider": nxt}); log(f"Provider set to: {nxt}", "action")
    elif key in {"model", "main_model"}:
        start_status = tool_llm_status({"section": sec})
        cur = start_status.get("model") or start_status.get("main_model") or ""
        m = ["gpt-4.1", "gpt-4o", "gpt-4", "claude-3-5-sonnet-latest", "gemini-1.5-pro-002", "mistral-large-latest"]
        nxt = m[(m.index(cur)+1)%len(m)] if cur in m else "gpt-4o"
        tool_llm_set({"main_model": nxt} if sec=="defaults" else {"section": sec, "model": nxt})
        log(f"Model set to: {nxt}", "action")
    elif key == "vision_model":
        cur = tool_llm_status({"section": sec}).get("vision_model", "")
        m = ["gpt-4.1-vision", "gpt-4o", "claude-3-opus", "gemini-1.5-flash"]
        nxt = m[(m.index(cur) + 1) % len(m)] if cur in m else "gpt-4o"
        tool_llm_set({"vision_model": nxt})
        log(f"Vision model set to: {nxt}", "action")
    ctx["force_ui_update"]()

def _handle_locales_toggle(ctx):
    loc = ctx["AVAILABLE_LOCALES"][ctx["state"].menu_index]
    lz = ctx["localization"]
    if loc.code == lz.primary: return ctx["log"]("Не можна вимкнути primary локаль.", "error")
    if loc.code in lz.selected: lz.selected = [c for c in lz.selected if c != loc.code]
    else: lz.selected.append(loc.code)
    lz.save(); ctx["log"](f"Вимкнено: {loc.code}" if loc.code not in lz.selected else f"Увімкнено: {loc.code}", "action")

def _handle_monitor_targets_toggle(ctx):
    items = ctx["get_monitor_menu_items"]()
    if not items: return
    it = items[ctx["state"].menu_index]
    if not getattr(it, "selectable", False): return
    if it.key in ctx["state"].monitor_targets:
        ctx["state"].monitor_targets.remove(it.key)
        ctx["log"](f"Monitor: OFF {it.label}", "action")
    else:
        ctx["state"].monitor_targets.add(it.key)
        ctx["log"](f"Monitor: ON {it.label}", "action")
    ctx["force_ui_update"]()

def _handle_menu_enter_dispatch(ctx):
    state, MenuLevel = ctx["state"], ctx["MenuLevel"]
    lvl = state.menu_level

    _llm_sub_hint = lambda: ctx["log"]("To edit model, use CLI: /llm set section=<name> model=<model>", "info")
    
    dispatch = _get_menu_enter_dispatch(ctx, state, MenuLevel, _llm_sub_hint)
    if lvl in dispatch: dispatch[lvl]()

def _get_menu_enter_dispatch(ctx, state, MenuLevel, _llm_sub_hint):
    return {
        MenuLevel.MAIN: lambda: _set_menu(state, ctx["MAIN_MENU_ITEMS"][state.menu_index][1]),
        MenuLevel.CUSTOM_TASKS: lambda: _run_custom_task(ctx),
        MenuLevel.MONITORING: lambda: _set_menu_from_items(state, ctx["get_monitoring_menu_items"]()),
        MenuLevel.SETTINGS: lambda: _handle_settings_enter(ctx),
        MenuLevel.LLM_SETTINGS: lambda: _set_menu_from_items(state, ctx["get_llm_menu_items"]()),
        MenuLevel.AGENT_SETTINGS: lambda: _handle_agent_settings_enter(ctx),
        MenuLevel.UNSAFE_MODE: lambda: _handle_general_toggle_ctx(ctx, "ui_unsafe_mode", "Unsafe"),
        MenuLevel.SELF_HEALING: lambda: _handle_general_toggle_ctx(ctx, "ui_self_healing", "Self-healing"),
        MenuLevel.MEMORY_MANAGER: lambda: _handle_memory_manager_enter(ctx),
        MenuLevel.AUTOMATION_PERMISSIONS: lambda: ctx.get("handle_automation_permissions_enter", lambda c: None)(ctx),
        MenuLevel.DEV_SETTINGS: lambda: _handle_dev_settings_enter(ctx),
        MenuLevel.APPEARANCE: lambda: _set_theme(ctx),
        MenuLevel.LANGUAGE: lambda: _handle_language_menu_enter_ctx(ctx),
        MenuLevel.CLEANUP_EDITORS: lambda: _handle_cleanup_editors_enter_ctx(ctx),
        MenuLevel.MODULE_EDITORS: lambda: _handle_module_editors_enter(ctx),
        MenuLevel.INSTALL_EDITORS: lambda: _handle_install_editors_enter(ctx),
        MenuLevel.LOCALES: lambda: _handle_locales_enter(ctx),
        MenuLevel.MONITOR_TARGETS: lambda: _handle_monitor_targets_enter(ctx),
        MenuLevel.MONITOR_CONTROL: lambda: _handle_monitor_control_enter_ctx(ctx),
        MenuLevel.MCP_CLIENT_SETTINGS: lambda: _handle_mcp_client_enter_ctx(ctx),
        **{ml: _llm_sub_hint for ml in [MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS]}
    }

def _handle_mcp_client_enter_ctx(ctx):
    """Handle enter key in MCP client menu."""
    state, log = ctx["state"], ctx["log"]
    
    # 0: open_mcp, 1: continue, 2: auto
    clients = ["open_mcp", "continue", "auto"]
    current = str(getattr(state, "mcp_client_type", "open_mcp")).strip().lower()
    
    try:
        idx = clients.index(current)
    except ValueError:
        idx = 0
        
    next_idx = (idx + 1) % len(clients)
    new_client = clients[next_idx]
    
    try:
        from mcp_integration.core.mcp_client_manager import get_mcp_client_manager, MCPClientType
        mgr = get_mcp_client_manager()
        
        # Switch in backend
        if mgr.switch_client(MCPClientType(new_client)):
            # Update UI state
            state.mcp_client_type = new_client
            log(f"MCP Client Mode: {new_client.upper()}", "action")
        else:
            log(f"Failed to switch to {new_client}", "error")
            
    except Exception as e:
        log(f"Error switching client: {e}", "error")
    
    ctx["force_ui_update"]()

def _handle_agent_settings_enter(ctx):
    state, log = ctx["state"], ctx["log"]
    items = ctx["get_agent_menu_items"]()
    if not items:
        return
    idx = max(0, min(state.menu_index, len(items) - 1))
    _, key = items[idx][0], items[idx][1]
    if key == "ui_recursion_limit":
        cur = int(getattr(state, "ui_recursion_limit", 100))
        options = [50, 100, 200, 500]
        try:
            ni = (options.index(cur) + 1) % len(options)
            nxt = options[ni]
        except Exception:
            nxt = 100
        state.ui_recursion_limit = int(nxt)
        ctx["save_ui_settings"]()
        log(f"Step limit set: {nxt}", "action")
    elif key == "learning_mode":
        new_val = not bool(getattr(state, "learning_mode", False))
        state.learning_mode = new_val
        ctx["save_ui_settings"]()
        log(f"Learning mode: {'ON' if new_val else 'OFF'}", "action")


def _handle_dev_settings_enter(ctx):
    """Handle enter in DEV settings menu (toggle provider and Doctor Vibe settings)."""
    state, log = ctx["state"], ctx["log"]
    idx = max(0, min(state.menu_index, 3))

    if idx == 0:
        # Toggle provider
        _toggle_dev_provider(ctx)
        return

    var_map = {1: "TRINITY_DEV_BY_VIBE", 2: "TRINITY_VIBE_AUTO_APPLY", 3: "TRINITY_VIBE_AUTO_RESUME"}
    var = var_map.get(idx)
    if not var:
        return

    cur_val = str(os.getenv(var) or "0").strip().lower()
    new_val = "0" if cur_val in {"1", "true", "yes", "on"} else "1"

    try:
        from tui.cli import _update_env_var
        ok = _update_env_var(var, new_val)
        if ok:
            os.environ[var] = new_val
            log(f"{var} set to: {'ON' if new_val == '1' else 'OFF'}", "action")
        else:
            log(f"Failed to update {var} in .env", "error")
    except Exception as e:
        log(f"Error toggling {var}: {e}", "error")

    if var == "TRINITY_DEV_BY_VIBE":
        try:
            state.ui_dev_code_provider = "vibe-cli" if os.getenv("TRINITY_DEV_BY_VIBE", "0").strip().lower() in {"1","true","yes","on"} else "continue"
            ctx["save_ui_settings"]()
        except Exception:
            pass

    ctx["force_ui_update"]()

def _set_menu(state, new_lvl):
    state.menu_level, state.menu_index = new_lvl, 0

def _set_menu_from_items(state, items):
    if items: _set_menu(state, items[max(0, min(state.menu_index, len(items) - 1))][1])

def _run_custom_task(ctx):
    items = ctx["get_custom_tasks_menu_items"]()
    if not items: return
    action = items[max(0, min(ctx["state"].menu_index, len(items) - 1))][1]
    if callable(action):
        try: ok, msg = action(); ctx["log"](msg, "action" if ok else "error")
        except Exception as e: ctx["log"](f"Task failed: {e}", "error")

def _handle_settings_enter(ctx):
    items = ctx["get_settings_menu_items"]()
    if not items: return
    idx = _settings_next_selectable_index(items, ctx["state"].menu_index, 1)
    item = items[idx]
    if not _is_section_item(item):
        action = item[1]
        # Handle special actions (non-MenuLevel items)
        if action == "mcp_settings":
            _set_menu(ctx["state"], ctx["MenuLevel"].MCP_CLIENT_SETTINGS)
        else:
            _set_menu(ctx["state"], action)

def _handle_general_toggle_ctx(ctx, attr, label):
    new_val = not bool(getattr(ctx["state"], attr, False))
    setattr(ctx["state"], attr, new_val)
    ctx["save_ui_settings"]()
    ctx["log"](f"{label}: {'ON' if new_val else 'OFF'}", "action")

def _toggle_dev_provider(ctx):
    cur = str(getattr(ctx["state"], "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower()
    ctx["state"].ui_dev_code_provider = "continue" if cur == "vibe-cli" else "vibe-cli"
    ctx["save_ui_settings"](); ctx["log"](f"Dev provider: {ctx['state'].ui_dev_code_provider.upper()}", "action")

def _set_theme(ctx):
    themes = list(THEME_NAMES)
    ctx["state"].ui_theme = themes[max(0, min(ctx["state"].menu_index, len(themes) - 1))]
    ctx["save_ui_settings"](); ctx["log"](f"Theme set: {ctx['state'].ui_theme}", "action")

def _handle_language_menu_enter_ctx(ctx):
    langs = list(ctx["TOP_LANGS"])
    if not langs: return
    if ctx["state"].menu_index == 0:
        cur = ctx["state"].ui_lang if ctx["state"].ui_lang in langs else langs[0]
        ctx["state"].ui_lang = langs[(langs.index(cur) + 1) % len(langs)]
        ctx["log"](f"UI lang: {ctx['state'].ui_lang}", "action")
    else:
        cur = ctx["state"].chat_lang if ctx["state"].chat_lang in langs else langs[0]
        ctx["state"].chat_lang = langs[(langs.index(cur) + 1) % len(langs)]
        ctx["reset_agent_llm"](); ctx["log"](f"Chat lang: {ctx['state'].chat_lang}", "action")
    ctx["save_ui_settings"]()

def _handle_cleanup_editors_enter_ctx(ctx):
    editors = ctx["get_editors_list"]()
    if not editors: return
    key = editors[ctx["state"].menu_index][0]
    ctx["state"].selected_editor = key
    ctx["log"](f"Starting cleanup: {key}...", "info")
    import threading
    def run_cleanup_thread():
        import re
        # Ensure log panel follows new output
        try:
            ctx["state"].ui_log_follow = True
        except Exception:
            pass
        ctx["force_ui_update"]()

        try:
            def cleanup_log(line: str):
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                if clean_line.strip():
                    ctx["log"](clean_line, "action")
                    try:
                        ctx["force_ui_update"]()
                    except Exception:
                        pass

            ok, msg = ctx["run_cleanup"](ctx["load_cleanup_config"](), key, dry_run=False, log_callback=cleanup_log)
            ctx["log"](msg, "action" if ok else "error")
            ctx["force_ui_update"]()
        except Exception as e:
            try:
                ctx["log"](f"Cleanup thread error: {e}", "error")
                ctx["force_ui_update"]()
            except Exception:
                pass

    threading.Thread(target=run_cleanup_thread, daemon=True).start()

def _handle_module_editors_enter(ctx):
    items = ctx["get_editors_list"]()
    if items: ctx["state"].selected_editor, ctx["state"].menu_level, ctx["state"].menu_index = items[ctx["state"].menu_index][0], ctx["MenuLevel"].MODULE_LIST, 0

def _handle_install_editors_enter(ctx):
    items = ctx["get_editors_list"]()
    if items: ok, msg = ctx["perform_install"](ctx["load_cleanup_config"](), items[ctx["state"].menu_index][0]); ctx["log"](msg, "action" if ok else "error")

def _handle_locales_enter(ctx):
    loc = ctx["AVAILABLE_LOCALES"][ctx["state"].menu_index]
    ctx["localization"].primary = loc.code
    ctx["localization"].selected = [loc.code] + [c for c in ctx["localization"].selected if c != loc.code]
    ctx["localization"].save(); ctx["log"](f"Primary set: {loc.code}", "action")

def _handle_memory_manager_enter(ctx):
    """Handle enter key in memory manager menu."""
    state, log = ctx["state"], ctx["log"]
    idx = state.menu_index
    
    # Memory manager menu items mapping
    actions = [
        "stats",           # 0: Memory Statistics
        "learning_history", # 1: Learning History  
        "semantic",        # 2: Semantic Memory
        "episodic",        # 3: Episodic Memory
        "import",          # 4: Import Examples
        "export",          # 5: Export Data
        "vector_db",       # 6: Vector DB Management
    ]
    
    if idx >= len(actions):
        return
    
    action = actions[idx]
    
    try:
        from core.memory import get_hierarchical_memory
        from tui.memory_manager import handle_memory_action
        
        result = handle_memory_action(action, get_hierarchical_memory())
        if result.get("status") == "success":
            log(result.get("message", f"Memory action '{action}' completed"), "action")
        else:
            log(result.get("error", f"Memory action '{action}' failed"), "error")
    except ImportError:
        # memory_manager module not yet created, show placeholder
        log(f"Memory Manager: {action} (module not yet implemented)", "info")
    except Exception as e:
        log(f"Memory error: {e}", "error")
    
    ctx["force_ui_update"]()

def _handle_monitor_targets_enter(ctx):
    if ctx["save_monitor_targets"](): ctx["log"](f"Monitor targets saved", "action")
    else: ctx["log"]("Failed to save", "error")
    _set_menu(ctx["state"], ctx["MenuLevel"].MAIN)

def _handle_monitor_control_enter_ctx(ctx):
    st = ctx["state"]
    # If the selected menu index is 0, toggle monitor mode (auto/manual)
    try:
        if int(getattr(st, "menu_index", 0)) == 0:
            cur = str(getattr(st, "monitor_mode", "auto") or "auto").strip().lower()
            new = "manual" if cur == "auto" else "auto"
            st.monitor_mode = new
            try:
                # persist settings if provided
                if "save_monitor_settings" in ctx and callable(ctx["save_monitor_settings"]):
                    ctx["save_monitor_settings"]()
            except Exception:
                pass
            ctx["log"](f"Monitor mode: {st.monitor_mode.upper()}", "action")
            return
    except Exception:
        pass

    # Otherwise, treat it as Start/Stop action (index 1)
    if st.monitor_active:
        ok, msg = ctx["monitor_stop_selected"]()
        st.monitor_active = bool(ctx["monitor_service"].running or ctx["fs_usage_service"].running or ctx["opensnoop_service"].running)
        ctx["log"](msg, "action" if ok else "error")
    elif st.monitor_targets:
        ok, msg = ctx["monitor_start_selected"]()
        st.monitor_active = bool(ctx["monitor_service"].running or ctx["fs_usage_service"].running or ctx["opensnoop_service"].running)
        ctx["log"](msg, "action" if ok else "error")
    else:
        ctx["log"]("Select targets first", "error")

def _get_menu_max_index_from_ctx(ctx):
    return _get_menu_max_index(
        ctx["state"], ctx["MenuLevel"], ctx["MAIN_MENU_ITEMS"], ctx["get_custom_tasks_menu_items"],
        ctx["get_monitoring_menu_items"], ctx["get_editors_list"], ctx["get_cleanup_cfg"],
        ctx["AVAILABLE_LOCALES"], ctx["get_settings_menu_items"], ctx["get_automation_permissions_menu_items"],
        ctx["get_monitor_menu_items"], ctx["get_llm_menu_items"], ctx["get_llm_sub_menu_items"],
        ctx["get_agent_menu_items"]
    )

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
    calc_map = _get_menu_param_calculators(MenuLevel, MAIN_MENU_ITEMS, get_custom_tasks_menu_items, get_monitoring_menu_items, AVAILABLE_LOCALES, get_settings_menu_items, get_automation_permissions_menu_items, get_monitor_menu_items, get_llm_menu_items, get_agent_menu_items)
    
    if lvl in calc_map:
        return calc_map[lvl]()

    # Handle composite or dynamic levels that can't be resolved via calc_map
    if lvl in {MenuLevel.CLEANUP_EDITORS, MenuLevel.MODULE_EDITORS, MenuLevel.INSTALL_EDITORS}:
        try:
            return max(0, len(get_editors_list()) - 1)
        except Exception:
            return 0
        
    if lvl == MenuLevel.MODULE_LIST:
        try:
            m_cfg = get_cleanup_cfg() or {}
            m_mods = m_cfg.get("editors", {}).get(state.selected_editor or "", {}).get("modules", [])
            return max(0, len(m_mods) - 1)
        except Exception:
            return 0
        
    if lvl in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
        try:
            return max(0, len(get_llm_sub_menu_items(lvl)) - 1)
        except Exception:
            return 0
        
    return 0

def _get_menu_param_calculators(MenuLevel, MAIN_MENU_ITEMS, get_custom_tasks_menu_items, get_monitoring_menu_items, AVAILABLE_LOCALES, get_settings_menu_items, get_automation_permissions_menu_items, get_monitor_menu_items, get_llm_menu_items, get_agent_menu_items):
    return {
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
        MenuLevel.MCP_CLIENT_SETTINGS: lambda: 1, # 2 items: open_mcp, continue
        MenuLevel.LANGUAGE: lambda: 1,
    }
        
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

