from __future__ import annotations
import time
from typing import Any, Callable, List, Sequence, Tuple
from prompt_toolkit.filters import Condition
from tui.themes import THEMES, get_theme_names

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
            
            # Hover highlight
            if event_type == MouseEventType.MOUSE_MOVE:
                if state.menu_index != idx:
                    state.menu_index = idx
                    force_ui_update()
                return

            # Selection (click/double-click)
            if event_type not in (MouseEventType.MOUSE_UP, MouseEventType.MOUSE_DOWN):
                return
            
            # Only act on MOUSE_UP (button release)
            if event_type != MouseEventType.MOUSE_UP:
                return
            
            now = time.time()
            # Double click detection (mac standard style)
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

    def get_toggle_text(val: bool) -> List[Tuple[str, str]]:
        style = "class:toggle.on" if val else "class:toggle.off"
        label = " ON  " if val else " OFF "
        return [("class:menu.item", "["), (style, label), ("class:menu.item", "]")]

    def get_slider_text(val: float, width: int = 10) -> List[Tuple[str, str]]:
        filled = int(val * width)
        bar = "=" * filled + "|" + "-" * (width - filled - 1) if filled < width else "=" * (width - 1) + "|"
        return [("class:menu.item", f"[{bar}] {val:.2f}")]

    def get_theme_preview(tname: str) -> List[Tuple[str, str]]:
        t = THEMES.get(tname, {})
        border = t.get("frame.border", "#ffffff")
        title = t.get("header.title", "#ffffff")
        accent = t.get("log.action", "#ffffff")
        # Visual block representation
        return [
            ("class:menu.item", "  "),
            (f"bg:{border}", "  "),
            ("class:menu.item", " "),
            (f"bg:{title}", "  "),
            ("class:menu.item", " "),
            (f"bg:{accent}", "  "),
        ]

    def get_menu_content() -> List[Tuple[str, str]]:
        result: List[Tuple[str, str]] = []

        def add_back_btn(res):
            def _back_handler(mouse_event: Any):
                from prompt_toolkit.mouse_events import MouseEventType
                if mouse_event.event_type == MouseEventType.MOUSE_UP:
                    state.menu_level = MenuLevel.MAIN
                    state.menu_index = 0
                    force_ui_update()
            
            # Back button is informational/mouse-clickable but not yet selectable via keys 0-N
            # so we use a neutral style.
            res.append(("class:menu.item", " [ < " + tr("menu.back", state.ui_lang).upper() + " ] ", _back_handler))
            res.append(("", "\n\n"))

        if state.menu_level == MenuLevel.MAIN:
            result.append(("class:menu.title", f" {tr('menu.main.title', state.ui_lang)}\n\n"))
            for i, item in enumerate(MAIN_MENU_ITEMS):
                name, _ = item[0], item[1]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{tr(name, state.ui_lang)}\n", handler))
            return result

        if state.menu_level == MenuLevel.CUSTOM_TASKS:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.custom_tasks.title', state.ui_lang)}\n\n"))
            items = get_custom_tasks_menu_items()
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, itm in enumerate(items):
                label = itm[0]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{tr(label, state.ui_lang)}\n", handler))
            return result

        if state.menu_level == MenuLevel.MONITORING:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.monitoring.title', state.ui_lang)}\n\n"))
            items = get_monitoring_menu_items()
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, itm in enumerate(items):
                label = itm[0]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                result.append((style_cls, f"{prefix}{tr(label, state.ui_lang)}\n"))
            return result

        if state.menu_level == MenuLevel.SETTINGS:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.settings.title', state.ui_lang)}\n\n"))
            items = get_settings_menu_items()
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, item in enumerate(items):
                if isinstance(item, tuple) and len(item) == 3 and item[2] == "section":
                    result.append(("class:menu.title", f"\n {tr(item[0], state.ui_lang)}\n"))
                else:
                    label = item[0] if isinstance(item, tuple) else item
                    prefix = " > " if i == state.menu_index else "   "
                    style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                    handler = make_click(i)
                    result.append((style_cls, f"{prefix}{tr(label, state.ui_lang)}\n", handler))
            return result

        if state.menu_level == MenuLevel.LLM_SETTINGS:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.llm.title', state.ui_lang)}\n\n"))
            items = get_llm_menu_items()
            if not items:
                result.append(("class:menu.item", " (no items)\n"))
                return result
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, itm in enumerate(items):
                label = itm[0]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{label}\n", handler))
            return result

        if state.menu_level in {MenuLevel.LLM_ATLAS, MenuLevel.LLM_TETYANA, MenuLevel.LLM_GRISHA, MenuLevel.LLM_VISION, MenuLevel.LLM_DEFAULTS}:
            add_back_btn(result)
            section_key = state.menu_level.value.replace("llm_", "")
            section_label = section_key.upper() if section_key != "defaults" else "GLOBAL DEFAULTS"
            result.append(("class:menu.title", f" {tr('menu.llm.title', state.ui_lang)}: {section_label}\n\n"))
            items = get_llm_sub_menu_items(state.menu_level)
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, item in enumerate(items):
                label = item[0]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{label}\n", handler))
            result.append(("class:menu.item", "\n Enter: Edit | Space: Cycle value\n"))
            return result

        if state.menu_level == MenuLevel.AGENT_SETTINGS:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.agent.title', state.ui_lang)}\n\n"))
            items = get_agent_menu_items()
            if not items:
                result.append(("class:menu.item", " (no items)\n"))
                return result
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, itm in enumerate(items):
                label = itm[0]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{label}\n", handler))
            return result

        if state.menu_level == MenuLevel.APPEARANCE:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.appearance.title', state.ui_lang)}\n\n"))
            themes = list(get_theme_names())
            state.menu_index = max(0, min(state.menu_index, len(themes) - 1))
            for i, t in enumerate(themes):
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                mark = "[*]" if state.ui_theme == t else "[ ]"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{mark} {t}", handler))
                result.extend(get_theme_preview(t))
                result.append(("", "\n"))
            return result

        if state.menu_level == MenuLevel.LANGUAGE:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.language.title', state.ui_lang)}\n\n"))
            items = [
                (f"UI: {state.ui_lang} - {lang_name(state.ui_lang)}", "ui"),
                (f"Chat: {state.chat_lang} - {lang_name(state.chat_lang)}", "chat")
            ]
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, item in enumerate(items):
                label = item[0]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{label}\n", handler))
            result.append(("class:menu.item", "\n Enter: cycle | /lang set ui|chat <code>\n"))
            return result

        if state.menu_level == MenuLevel.UNSAFE_MODE:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.unsafe_mode.title', state.ui_lang)}\n\n"))
            on = bool(getattr(state, "ui_unsafe_mode", False))
            prefix = " > "
            handler = make_click(0)
            result.append(("class:menu.selected", f"{prefix}{tr('menu.unsafe_mode.label', state.ui_lang)} ", handler))
            result.extend(get_toggle_text(on))
            result.append(("", "\n"))
            return result

        if state.menu_level == MenuLevel.AUTOMATION_PERMISSIONS:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.automation_permissions.title', state.ui_lang)}\n\n"))
            items = get_automation_permissions_menu_items()
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, itm in enumerate(items):
                label, key = itm[0], itm[1]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{label} ", handler))
                
                if key == "ui_execution_mode":
                    mode = str(getattr(state, "ui_execution_mode", "native")).upper()
                    result.append(("class:menu.item", f"[{mode}]"))
                elif key == "automation_allow_shortcuts":
                    on = bool(getattr(state, "automation_allow_shortcuts", False))
                    result.extend(get_toggle_text(on))
                
                result.append(("", "\n"))
            return result

        if state.menu_level == MenuLevel.LAYOUT:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.layout.title', state.ui_lang)}\n\n"))
            items = [
                (tr("menu.layout.left_panel_ratio", state.ui_lang), "ratio"),
            ]
            state.menu_index = max(0, min(state.menu_index, len(items) - 1))
            for i, itm in enumerate(items):
                label, key = itm[0], itm[1]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{label} ", handler))
                
                if key == "ratio":
                    val = float(getattr(state, "ui_left_panel_ratio", 0.6))
                    result.extend(get_slider_text(val))
                
                result.append(("", "\n"))
            result.append(("class:menu.item", f"\n {tr('menu.layout.hint', state.ui_lang)}\n"))
            return result

        if state.menu_level == MenuLevel.DEV_SETTINGS:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.dev_settings.title', state.ui_lang)}\n\n"))
            provider = str(getattr(state, "ui_dev_code_provider", "vibe-cli") or "vibe-cli").strip().lower()
            provider_label = "VIBE-CLI" if provider == "vibe-cli" else "CONTINUE"
            prefix = " > "
            handler = make_click(0)
            result.append(("class:menu.selected", f"{prefix}{tr('menu.dev_settings.provider_label', state.ui_lang)}: ", handler))
            style = "class:toggle.on" if provider == "vibe-cli" else "class:toggle.off"
            result.append((style, f" {provider_label} "))
            result.append(("", "\n\n"))
            result.append(("class:menu.item", " Enter: Toggle between VIBE-CLI / CONTINUE\n"))
            return result


        if state.menu_level == MenuLevel.MONITOR_CONTROL:
            add_back_btn(result)
            result.append(("class:menu.title", " MONITORING (Enter: Start/Stop, S: Source, U: Sudo, Q/Esc: Back)\n"))
            state_line = "ACTIVE" if state.monitor_active else "INACTIVE"
            result.append(("class:menu.item", f" State: {state_line}\n"))
            result.append(("class:menu.item", f" Source: {state.monitor_source}\n"))
            if state.monitor_source in {"fs_usage", "opensnoop"}:
                sudo_line = "ON" if state.monitor_use_sudo else "OFF"
                result.append(("class:menu.item", f" Sudo: {sudo_line}\n"))
            result.append(("class:menu.item", f" Targets: {len(state.monitor_targets)} selected\n"))
            result.append(("class:menu.item", f" DB: {MONITOR_EVENTS_DB_PATH}\n\n"))
            action = "STOP" if state.monitor_active else "START"
            handler = make_click(0)
            result.append(("class:menu.selected", f" > {action}\n", handler))
            if state.monitor_source == "watchdog":
                result.append(("class:menu.item", "\n Note: watchdog monitors directories (no process attribution).\n"))
            elif state.monitor_source == "fs_usage":
                result.append(("class:menu.item", "\n Note: fs_usage attributes calls to process name; may require sudo.\n"))
            elif state.monitor_source == "opensnoop":
                result.append(("class:menu.item", "\n Note: opensnoop traces open() calls; may require sudo.\n"))
            else:
                result.append(("class:menu.item", "\n Note: source not implemented yet.\n"))
            return result

        if state.menu_level == MenuLevel.MONITOR_TARGETS:
            add_back_btn(result)
            result.append(("class:menu.title", " MONITORING TARGETS (Space: Toggle, Enter: Save, Q/Esc: Back)\n"))
            result.append(("class:menu.item", f" Config: {MONITOR_TARGETS_PATH}\n\n"))

            items = get_monitor_menu_items()
            normalize_menu_index(items)

            for i, it in enumerate(items):
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"

                if not getattr(it, "selectable", False):
                    result.append(("class:menu.title", f"\n {it.label}\n"))
                    continue

                on = it.key in state.monitor_targets
                mark = "[x]" if on else "[ ]"
                origin = f" ({it.origin})" if getattr(it, "origin", "") else ""
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{mark} {it.label}{origin}\n", handler))
            return result

        if state.menu_level == MenuLevel.CLEANUP_EDITORS:
            add_back_btn(result)
            result.append(("class:menu.title", " RUN CLEANUP (Enter: Run, D: Dry-run, Q/Esc: Back)\n\n"))
            editors = get_editors_list()
            for i, itm in enumerate(editors):
                key, label = itm[0], itm[1]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{key} - {label}\n", handler))
            return result

        if state.menu_level == MenuLevel.MODULE_EDITORS:
            add_back_btn(result)
            result.append(("class:menu.title", " MODULES: CHOOSE EDITOR (Enter: Select, Q/Esc: Back)\n\n"))
            editors = get_editors_list()
            for i, itm in enumerate(editors):
                key, label = itm[0], itm[1]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{key} - {label}\n", handler))
            return result

        if state.menu_level == MenuLevel.MODULE_LIST:
            add_back_btn(result)
            editor = state.selected_editor
            if not editor:
                result.append(("class:menu.title", " MODULES (no editor selected)\n"))
                return result

            cfg = get_cleanup_cfg() or {}
            meta = cfg.get("editors", {}).get(editor, {})
            result.append(("class:menu.title", f" MODULES: {editor} (Space: Toggle, Q/Esc: Back)\n\n"))
            mods = meta.get("modules", [])
            if not mods:
                result.append(("class:menu.item", " (немає модулів – використайте /smart або /ask)\n"))
                return result

            for i, m in enumerate(mods):
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                on = bool(m.get("enabled"))
                toggle_style = "class:toggle.on" if on else "class:toggle.off"
                mark = "ON" if on else "OFF"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{m.get('id')} - {m.get('name')} [", handler))
                result.append((toggle_style, f"{mark}"))
                result.append((style_cls, "]\n"))
            return result

        if state.menu_level == MenuLevel.INSTALL_EDITORS:
            add_back_btn(result)
            result.append(("class:menu.title", " INSTALL (Enter: Open installer, Q/Esc: Back)\n\n"))
            editors = get_editors_list()
            for i, itm in enumerate(editors):
                key, label = itm[0], itm[1]
                prefix = " > " if i == state.menu_index else "   "
                style_cls = "class:menu.selected" if i == state.menu_index else "class:menu.item"
                handler = make_click(i)
                result.append((style_cls, f"{prefix}{key} - {label}\n", handler))
            return result

        if state.menu_level == MenuLevel.LOCALES:
            add_back_btn(result)
            result.append(("class:menu.title", f" {tr('menu.locales.title', state.ui_lang)}\n\n"))
            for idx, loc in enumerate(AVAILABLE_LOCALES):
                prefix = " > " if idx == state.menu_index else "   "
                style_cls = "class:menu.selected" if idx == state.menu_index else "class:menu.item"

                is_selected = loc.code in localization.selected
                is_primary = loc.code == localization.primary

                primary_mark = "●" if is_primary else " "
                active_mark = "●" if is_selected else " "

                result.append(
                    (
                        style_cls,
                        f"{prefix}[P:{primary_mark}] [A:{active_mark}] {loc.code} - {loc.name} ({loc.group})\n",
                        make_click(idx)
                    )
                )
            return result

        result.append(("class:menu.item", "(menu)"))
        return result

    return show_menu, get_menu_content
