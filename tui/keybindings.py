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
    run_cleanup: Callable[[Any, str, bool], Tuple[bool, str]],
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
) -> KeyBindings:
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
        while 0 <= idx < len(items) and _is_section_item(items[idx]):
            idx += step
        if 0 <= idx < len(items):
            return idx
        # fallback: scan from beginning/end
        if step > 0:
            for i in range(0, len(items)):
                if not _is_section_item(items[i]):
                    return i
        else:
            for i in range(len(items) - 1, -1, -1):
                if not _is_section_item(items[i]):
                    return i
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
            MenuLevel.AUTOMATION_PERMISSIONS, MenuLevel.DEV_SETTINGS, MenuLevel.LOCALES
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
        """Copy active panel content to clipboard (Mac pbcopy)."""
        target = str(getattr(state, "ui_scroll_target", "log") or "log")
        import subprocess
        try:
            content = ""
            if target == "log":
                from tui.render import get_logs
                logs = get_logs()
                content = "".join(str(t or "") for _, t in logs)
            else:
                from tui.render import get_agent_messages
                msgs = get_agent_messages()
                content = "".join(str(t or "") for _, t in msgs)
            
            if content:
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(input=content.encode('utf-8'))
                log(f"Скопійовано {len(content)} символів з панелі {target.upper()}", "action")
        except Exception as e:
            log(f"Помилка копіювання: {e}", "error")

    @kb.add("c-l")
    def _(event):
        """Focus the input field."""
        w = _find_window_by_name(event, "input")
        if w:
            event.app.layout.focus(w)

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
        max_idx = 0
        if state.menu_level == MenuLevel.MAIN:
            max_idx = len(MAIN_MENU_ITEMS) - 1
        elif state.menu_level == MenuLevel.CUSTOM_TASKS:
            max_idx = max(0, len(get_custom_tasks_menu_items()) - 1)
        elif state.menu_level == MenuLevel.MONITORING:
            max_idx = max(0, len(get_monitoring_menu_items()) - 1)
        elif state.menu_level in {MenuLevel.CLEANUP_EDITORS, MenuLevel.MODULE_EDITORS, MenuLevel.INSTALL_EDITORS}:
            max_idx = max(0, len(get_editors_list()) - 1)
        elif state.menu_level == MenuLevel.MODULE_LIST:
            cfg = get_cleanup_cfg() or {}
            mods = cfg.get("editors", {}).get(state.selected_editor or "", {}).get("modules", [])
            max_idx = max(0, len(mods) - 1)
        elif state.menu_level == MenuLevel.LOCALES:
            max_idx = len(AVAILABLE_LOCALES) - 1
        elif state.menu_level == MenuLevel.SETTINGS:
            max_idx = max(0, len(get_settings_menu_items()) - 1)
        elif state.menu_level == MenuLevel.UNSAFE_MODE:
            max_idx = 0
        elif state.menu_level == MenuLevel.AUTOMATION_PERMISSIONS:
            max_idx = max(0, len(get_automation_permissions_menu_items()) - 1)
        elif state.menu_level == MenuLevel.MONITOR_TARGETS:
            max_idx = max(0, len(get_monitor_menu_items()) - 1)
        elif state.menu_level == MenuLevel.MONITOR_CONTROL:
            max_idx = 0
        elif state.menu_level == MenuLevel.LLM_SETTINGS:
            max_idx = max(0, len(get_llm_menu_items()) - 1)
        elif state.menu_level in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
            max_idx = max(0, len(get_llm_sub_menu_items(state.menu_level)) - 1)
        elif state.menu_level == MenuLevel.AGENT_SETTINGS:
            max_idx = max(0, len(get_agent_menu_items()) - 1)
        elif state.menu_level == MenuLevel.APPEARANCE:
            max_idx = max(0, len(THEME_NAMES) - 1)
        elif state.menu_level == MenuLevel.LANGUAGE:
            max_idx = 1
        elif state.menu_level == MenuLevel.LAYOUT:
            max_idx = 0
        elif state.menu_level == MenuLevel.DEV_SETTINGS:
            max_idx = 0

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
        ok, msg = run_cleanup(load_cleanup_config(), key, True)
        log(msg, "action" if ok else "error")

    @kb.add("space", filter=show_menu)
    def _(event):
        if state.menu_level == MenuLevel.MODULE_LIST:
            editor = state.selected_editor
            if not editor:
                return
            cfg = get_cleanup_cfg() or {}
            meta = cfg.get("editors", {}).get(editor, {})
            mods = meta.get("modules", [])
            if not mods:
                return
            m = mods[state.menu_index]
            mid = m.get("id")
            if not mid:
                return
            ref = find_module(cfg, editor, str(mid))
            if not ref:
                return
            new_state = not bool(m.get("enabled"))
            if set_module_enabled(cfg, ref, new_state):
                set_cleanup_cfg(load_cleanup_config())
                log(f"{editor}/{mid}: {'ON' if new_state else 'OFF'}", "action")
            else:
                log("Не вдалося змінити модуль.", "error")

        elif state.menu_level == MenuLevel.LOCALES:
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

        elif state.menu_level == MenuLevel.MONITOR_TARGETS:
            items = get_monitor_menu_items()
            if not items:
                return
            normalize_menu_index(items)
            it = items[state.menu_index]
            if not getattr(it, "selectable", False):
                return
            if it.key in state.monitor_targets:
                state.monitor_targets.remove(it.key)
                log(f"Monitor: OFF {it.label}", "action")
            else:
                state.monitor_targets.add(it.key)
                log(f"Monitor: ON {it.label}", "action")
            force_ui_update()

        elif state.menu_level in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
            items = get_llm_sub_menu_items(state.menu_level)
            if not items: return
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            itm = items[state.menu_index]
            key = itm[1] if len(itm) > 1 else ""
            
            section = ""
            if state.menu_level == MenuLevel.LLM_ATLAS: section = "atlas"
            elif state.menu_level == MenuLevel.LLM_TETYANA: section = "tetyana"
            elif state.menu_level == MenuLevel.LLM_GRISHA: section = "grisha"
            elif state.menu_level == MenuLevel.LLM_VISION: section = "vision"
            elif state.menu_level == MenuLevel.LLM_DEFAULTS: section = "defaults"
            
            from tui.tools import tool_llm_set, tool_llm_status
            
            if key == "provider":
                start_status = tool_llm_status({"section": section})
                cur_prov = start_status.get("provider", "copilot")
                provs = ["copilot", "openai", "anthropic", "gemini"]
                next_prov = provs[(provs.index(cur_prov) + 1) % len(provs)] if cur_prov in provs else "copilot"
                tool_llm_set({"section": section, "provider": next_prov})
                log(f"Provider set to: {next_prov}", "action")
                force_ui_update()
            elif key == "model" or key == "main_model":
                start_status = tool_llm_status({"section": section})
                # Check for model or main_model key
                cur_mod = start_status.get("model") or start_status.get("main_model") or ""
                models = ["gpt-4o", "gpt-4", "claude-3-5-sonnet-latest", "gemini-1.5-pro-002", "mistral-large-latest"]
                next_mod = models[(models.index(cur_mod) + 1) % len(models)] if cur_mod in models else "gpt-4o"
                if section == "defaults":
                    tool_llm_set({"main_model": next_mod})
                else:
                    tool_llm_set({"section": section, "model": next_mod})
                log(f"Model set to: {next_mod}", "action")
                force_ui_update()
            elif key == "vision_model":
                start_status = tool_llm_status({"section": section})
                cur_mod = start_status.get("vision_model", "")
                models = ["gpt-4.1-vision", "gpt-4o", "claude-3-opus", "gemini-1.5-flash"]
                next_mod = models[(models.index(cur_mod) + 1) % len(models)] if cur_mod in models else "gpt-4o"
                tool_llm_set({"vision_model": next_mod})
                log(f"Vision model set to: {next_mod}", "action")
                force_ui_update()

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

    @kb.add("enter", filter=show_menu)
    def handle_menu_enter(event=None):
        if state.menu_level == MenuLevel.MAIN:
            itm = MAIN_MENU_ITEMS[state.menu_index]
            lvl = itm[1]
            state.menu_level = lvl
            state.menu_index = 0
            return

        if state.menu_level == MenuLevel.CUSTOM_TASKS:
            items = get_custom_tasks_menu_items()
            if not items:
                return
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            itm = items[state.menu_index]
            _label, action = itm[0], itm[1]
            try:
                if not callable(action):
                    return
                ok, msg = action()
                log(msg, "action" if ok else "error")
            except Exception as e:
                log(f"Custom task failed: {e}", "error")
            return

        if state.menu_level == MenuLevel.MONITORING:
            items = get_monitoring_menu_items()
            if not items:
                return
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            itm = items[state.menu_index]
            _, lvl = itm[0], itm[1]
            state.menu_level = lvl
            state.menu_index = 0
            return

        if state.menu_level == MenuLevel.SETTINGS:
            items = get_settings_menu_items()
            if not items:
                return
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            state.menu_index = _settings_next_selectable_index(items, state.menu_index, 1)
            item = items[state.menu_index]
            if _is_section_item(item):
                return
            _, lvl = item[0], item[1]
            state.menu_level = lvl
            state.menu_index = 0
            return

        if state.menu_level == MenuLevel.LLM_SETTINGS:
            items = get_llm_menu_items()
            if not items:
                return
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            _, lvl = items[state.menu_index][0], items[state.menu_index][1]
            state.menu_level = lvl
            state.menu_index = 0
            return
            
        if state.menu_level in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
             log("To edit model, use CLI: /llm set section=<name> model=<model>", "info")
             return

        if state.menu_level == MenuLevel.UNSAFE_MODE:
            state.ui_unsafe_mode = not bool(getattr(state, "ui_unsafe_mode", False))
            save_ui_settings()
            log(f"Unsafe mode: {'ON' if state.ui_unsafe_mode else 'OFF'}", "action")
            return

        if state.menu_level == MenuLevel.AUTOMATION_PERMISSIONS:
            items = get_automation_permissions_menu_items()
            if not items:
                return
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            itm = items[state.menu_index]
            _, perm_key = itm[0], itm[1]
            if perm_key == "ui_execution_mode":
                cur = str(getattr(state, "ui_execution_mode", "native") or "native").strip().lower() or "native"
                state.ui_execution_mode = "gui" if cur == "native" else "native"
                log(f"Execution mode: {state.ui_execution_mode}", "action")
            if perm_key == "automation_allow_shortcuts":
                state.automation_allow_shortcuts = not bool(getattr(state, "automation_allow_shortcuts", False))
                log(f"Shortcuts: {'ON' if state.automation_allow_shortcuts else 'OFF'}", "action")
            save_ui_settings()
            return

        if state.menu_level == MenuLevel.DEV_SETTINGS:
            # Toggle between vibe-cli and continue
            cur = str(getattr(state, "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower()
            state.ui_dev_code_provider = "continue" if cur == "vibe-cli" else "vibe-cli"
            save_ui_settings()
            log(f"Dev code provider: {state.ui_dev_code_provider.upper()}", "action")
            return

        if state.menu_level == MenuLevel.APPEARANCE:
            themes = list(THEME_NAMES)
            state.menu_index = max(0, min(state.menu_index, len(themes) - 1))
            state.ui_theme = themes[state.menu_index]
            save_ui_settings()
            log(f"Theme set: {state.ui_theme}", "action")
            return

        if state.menu_level == MenuLevel.LANGUAGE:
            langs = list(TOP_LANGS)
            if not langs:
                return
            state.menu_index = max(0, min(state.menu_index, 1))
            if state.menu_index == 0:
                cur = state.ui_lang if state.ui_lang in langs else langs[0]
                state.ui_lang = langs[(langs.index(cur) + 1) % len(langs)]
                save_ui_settings()
                log(f"UI language set: {state.ui_lang} ({lang_name(state.ui_lang)})", "action")
                return

            cur = state.chat_lang if state.chat_lang in langs else langs[0]
            state.chat_lang = langs[(langs.index(cur) + 1) % len(langs)]
            save_ui_settings()
            reset_agent_llm()
            log(f"Chat language set: {state.chat_lang} ({lang_name(state.chat_lang)})", "action")
            return

        if state.menu_level == MenuLevel.CLEANUP_EDITORS:
            editors = get_editors_list()
            if not editors:
                return
            key = editors[state.menu_index][0]
            state.selected_editor = key
            ok, msg = run_cleanup(load_cleanup_config(), key, False)
            log(msg, "action" if ok else "error")
            return

        if state.menu_level == MenuLevel.MODULE_EDITORS:
            editors = get_editors_list()
            if not editors:
                return
            key = editors[state.menu_index][0]
            state.selected_editor = key
            set_cleanup_cfg(load_cleanup_config())
            state.menu_level = MenuLevel.MODULE_LIST
            state.menu_index = 0
            return

        if state.menu_level == MenuLevel.INSTALL_EDITORS:
            editors = get_editors_list()
            if not editors:
                return
            key = editors[state.menu_index][0]
            state.selected_editor = key
            ok, msg = perform_install(load_cleanup_config(), key)
            log(msg, "action" if ok else "error")
            return

        if state.menu_level == MenuLevel.LOCALES:
            loc = AVAILABLE_LOCALES[state.menu_index]
            localization.primary = loc.code
            if loc.code not in localization.selected:
                localization.selected.insert(0, loc.code)
            else:
                localization.selected = [loc.code] + [c for c in localization.selected if c != loc.code]
            localization.save()
            log(f"Primary встановлено: {loc.code}", "action")
            return

        if state.menu_level == MenuLevel.MONITOR_TARGETS:
            if save_monitor_targets():
                log(f"Saved monitor targets: {', '.join(sorted(state.monitor_targets)) or '(none)'}", "action")
            else:
                log("Failed to save monitor targets.", "error")
            state.menu_level = MenuLevel.MAIN
            state.menu_index = 0
            return

        if state.menu_level == MenuLevel.MONITOR_CONTROL:
            if state.monitor_active:
                ok, msg = monitor_stop_selected()
                state.monitor_active = bool(monitor_service.running or fs_usage_service.running or opensnoop_service.running)
                log(msg, "action" if ok else "error")
                return

            if not state.monitor_targets:
                log("Monitoring: обери цілі у 'Monitoring Targets' (потрібні хрестики) і натисни Save.", "error")
                return

            watch_items = monitor_resolve_watch_items(state.monitor_targets)
            if state.monitor_source == "watchdog" and not watch_items:
                log("Monitoring: не вдалося знайти локальні директорії для вибраних цілей.", "error")
                return

            ok, msg = monitor_start_selected()
            state.monitor_active = bool(monitor_service.running or fs_usage_service.running or opensnoop_service.running)
            log(msg, "action" if ok else "error")
            return

    return kb, handle_menu_enter
