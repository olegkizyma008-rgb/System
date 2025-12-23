from __future__ import annotations

from typing import Any, Callable

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.widgets import Frame
from prompt_toolkit.layout.margins import ScrollbarMargin
from tui.state import state, MenuLevel

_app_state = {"instance": None}


def _cached_getter(getter: Callable[[], Any], *, ttl_s: float = 0.05) -> Callable[[], Any]:
    cache: dict[str, Any] = {"ts": 0.0, "value": None}

    def _inner() -> Any:
        try:
            import time

            now = time.monotonic()
            ts = float(cache.get("ts", 0.0))
            if (now - ts) < float(ttl_s):
                return cache.get("value")
            value = getter()
            cache["ts"] = now
            cache["value"] = value
            return value
        except Exception:
            return cache.get("value")
    
    # Expose the last cached value safely
    def _get_last_value() -> Any:
        return cache.get("value")
    
    setattr(_inner, "get_last_value", _get_last_value)

    return _inner

def _safe_cursor_position(get_text: Callable[[], Any], get_cursor: Callable[[], Point]) -> Callable[[], Point]:
    """Wrap cursor position getter to ensure it never exceeds actual line count."""
    def _inner() -> Point:
        try:
            cursor = get_cursor()
            
            # Use cached text if available to ensure consistency with what was just rendered
            # This prevents race conditions where text updates between render and cursor calc
            if hasattr(get_text, "get_last_value"):
                text = get_text.get_last_value()
            else:
                text = get_text()
                
            if not text:
                return Point(x=0, y=0)
            combined = "".join(str(t or "") for _, t in text) if isinstance(text, list) else str(text or "")
            if not combined:
                return Point(x=0, y=0)
            parts = combined.split("\n")
            line_count = max(1, len(parts))
            if combined.endswith("\n"):
                line_count = max(1, line_count - 1)
            valid_y = max(0, min(int(getattr(cursor, "y", 0) or 0), line_count - 1))
            return Point(x=0, y=valid_y)
        except Exception:
            return Point(x=0, y=0)
    return _inner

# Restored missing helper
def _safe_formatted_text(getter: Callable[[], Any], *, fallback_style: str = "") -> Callable[[], Any]:
    def _inner() -> Any:
        try:
            value = getter()
        except Exception:
            return [(fallback_style, " \n")]
        if not value:
            return [(fallback_style, " \n")]
        return value

    return _inner

def force_ui_update():
    app = _app_state.get("instance")
    if app:
        try:
            app.invalidate()
        except Exception:
            pass


def _handle_mouse_scroll_up(name: str, state: Any, scroll_delta: int):
    if name == "log":
        state.ui_log_follow = False
        state.ui_log_cursor_y = max(0, int(getattr(state, "ui_log_cursor_y", 0)) - scroll_delta)
    elif name == "agents":
        state.ui_agents_follow = False
        state.ui_agents_cursor_y = max(0, int(getattr(state, "ui_agents_cursor_y", 0)) - scroll_delta)
    
    from prompt_toolkit.application.current import get_app
    app = get_app()
    for w in app.layout.find_all_windows():
        if getattr(w, "name", None) == name:
            w.vertical_scroll = max(0, w.vertical_scroll - scroll_delta)

def _handle_mouse_scroll_down(name: str, state: Any, scroll_delta: int):
    if name == "log":
        state.ui_log_cursor_y = int(getattr(state, "ui_log_cursor_y", 0)) + scroll_delta
        if state.ui_log_cursor_y >= max(0, int(getattr(state, "ui_log_line_count", 1)) - 1):
            state.ui_log_follow = True
    elif name == "agents":
        state.ui_agents_cursor_y = int(getattr(state, "ui_agents_cursor_y", 0)) + scroll_delta
        if state.ui_agents_cursor_y >= max(0, int(getattr(state, "ui_agents_line_count", 1)) - 1):
            state.ui_agents_follow = True
    
    from prompt_toolkit.application.current import get_app
    app = get_app()
    for w in app.layout.find_all_windows():
        if getattr(w, "name", None) == name:
            info = w.render_info
            if info:
                max_scroll = max(0, info.content_height - info.window_height)
                w.vertical_scroll = min(max_scroll, w.vertical_scroll + scroll_delta)
            else:
                w.vertical_scroll += scroll_delta

def _handle_mouse_up(name: str, get_logs: Callable, get_agent_messages: Callable, get_context: Callable = None):
    try:
        from tui.state import state
        from tui.clipboard_utils import copy_to_clipboard
        
        if not state.selection_panel or state.selection_start_y is None or state.selection_end_y is None:
            return

        # Get vertical scroll offset
        from prompt_toolkit.application.current import get_app
        app = get_app()
        v_scroll = 0
        for wd in app.layout.find_all_windows():
            if getattr(wd, "name", None) == name:
                v_scroll = getattr(wd, "vertical_scroll", 0)
                break

        # Get full content
        content_lines = []
        if name == "log" and get_logs:
            content = "".join(str(t or "") for _, t in get_logs())
            content_lines = content.split("\n")
        elif name == "agents" and get_agent_messages:
            content = "".join(str(t or "") for _, t in get_agent_messages())
            content_lines = content.split("\n")
        elif name == "context" and get_context:
            content = "".join(str(t or "") for _, t in get_context())
            content_lines = content.split("\n")
            
        if not content_lines:
            return

        # Absolutize Y coordinates using scroll
        start_abs = min(state.selection_start_y, state.selection_end_y) + v_scroll
        end_abs = max(state.selection_start_y, state.selection_end_y) + v_scroll
        
        if start_abs == end_abs:
            # Simple click - copy the line
            if 0 <= start_abs < len(content_lines):
                copy_to_clipboard(content_lines[start_abs])
        else:
            # Dragged selection
            selected = "\n".join(content_lines[start_abs:end_abs+1])
            if selected:
                copy_to_clipboard(selected)
                
        # Clear selection state
        state.selection_panel = None
        state.selection_start_y = None
        state.selection_end_y = None
        
    except Exception:
        pass


def _create_mouse_handler(name: str, force_ui_update: Callable, get_logs: Callable = None, get_agent_messages: Callable = None, get_context: Callable = None):
    def _handler(mouse_event: Any):
        from prompt_toolkit.mouse_events import MouseEventType
        from tui.state import state
        
        scroll_delta = 10 
        
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            _handle_mouse_scroll_up(name, state, scroll_delta)
            force_ui_update()
            return None
            
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            _handle_mouse_scroll_down(name, state, scroll_delta)
            force_ui_update()
            return None
            
        if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
            state.selection_panel = name
            state.selection_start_y = mouse_event.position.y
            state.selection_end_y = mouse_event.position.y
            force_ui_update()
            return None

        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            if state.selection_panel == name:
                state.selection_end_y = mouse_event.position.y
                force_ui_update()
            return None
        
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            if hasattr(mouse_event, 'button') and mouse_event.button is not None:
                _handle_mouse_up(name, get_logs, get_agent_messages, get_context)
                force_ui_update()
            return NotImplemented
        
        return NotImplemented
    return _handler


def build_app(
    *,
    get_header: Callable[[], Any],
    get_context: Callable[[], Any],
    get_logs: Callable[[], Any],
    get_log_cursor_position: Callable[[], Point],
    get_agent_messages: Callable[[], Any] = None,
    get_agent_cursor_position: Callable[[], Point] | None = None,
    get_menu_content: Callable[[], Any],
    get_input_prompt: Callable[[], Any],
    get_prompt_width: Callable[[], int],
    get_status: Callable[[], Any],
    input_buffer: Buffer,
    input_key_bindings: KeyBindings | None = None,  # Added argument
    show_menu: Condition,
    kb: KeyBindings,
    style: BaseStyle,
) -> Application:

    # --- Interactive Header Helpers ---
    def header_callback_menu(*args):
        state.menu_level = MenuLevel.MAIN if state.menu_level == MenuLevel.NONE else MenuLevel.NONE
        state.menu_index = 0
        force_ui_update()

    def get_interactive_header() -> AnyFormattedText:
        base = _safe_formatted_text(get_header, fallback_style="class:header")()
        if not isinstance(base, list):
            base = [("", str(base))]
            
        cur_scroll = str(getattr(state, "ui_scroll_target", "log") or "log").upper()
        # Clean [ACTIVE] or [SCROLL] from base if it exists (some old get_header versions might have it)
        # But here we just append our dynamic labels
            
        # Add labels purely informational
        labels = [
             ("class:header", "  "),
             ("class:button", f"[ F2: {'CLOSE' if state.menu_level != MenuLevel.NONE else 'MENU'} ]"),
             ("class:header", " "),
             ("class:button", f"[ PgUp: LOGS {'[SCROLL]' if cur_scroll == 'LOG' else ''} ]"),
             ("class:header", " "),
             ("class:button", f"[ PgDn: AGENTS {'[SCROLL]' if cur_scroll == 'AGENTS' else ''} ]"),
             ("class:header", " "),
             ("class:button", f"[ Ctrl+K: COPY ]"),
             ("class:header", "  "),
        ]
        
        return base + labels

    header_window = Window(
        FormattedTextControl(get_interactive_header), 
        height=1, 
        style="class:header"
    )

    context_control = FormattedTextControl(_safe_formatted_text(get_context, fallback_style="class:context"))
    context_control.mouse_handler = _create_mouse_handler("context", force_ui_update, get_logs, get_agent_messages, get_context)
    
    context_window = Window(
        context_control, 
        style="class:context", 
        wrap_lines=True,
        right_margins=[ScrollbarMargin(display_arrows=True)],
    )
    setattr(context_window, "name", "context")

    safe_get_logs = _cached_getter(_safe_formatted_text(get_logs, fallback_style="class:log.info"))
    log_control = FormattedTextControl(
        safe_get_logs, 
        get_cursor_position=_safe_cursor_position(safe_get_logs, get_log_cursor_position),
        focusable=True,
    )
    log_control.mouse_handler = _create_mouse_handler("log", force_ui_update, get_logs, get_agent_messages, get_context)

    log_window = Window(
        log_control,
        wrap_lines=True,
        right_margins=[ScrollbarMargin(display_arrows=True)],
        style="class:log.window", # ensure background
    )
    setattr(log_window, "name", "log")

    # Agent messages panel (clean communication display)
    safe_get_agent_messages = _cached_getter(
        _safe_formatted_text(get_agent_messages or (lambda: []), fallback_style="class:agent.text")
    )
    if get_agent_messages:
        agent_control = FormattedTextControl(
            safe_get_agent_messages,
            get_cursor_position=_safe_cursor_position(safe_get_agent_messages, get_agent_cursor_position) if get_agent_cursor_position else None,
            focusable=True,
        )
        agent_control.mouse_handler = _create_mouse_handler("agents", force_ui_update, get_logs, get_agent_messages, get_context)

        agent_messages_window = Window(
            agent_control,
            wrap_lines=True,
            style="class:agent.panel",
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )
        setattr(agent_messages_window, "name", "agents")
    else:
        agent_messages_window = None

    menu_window = Window(
        FormattedTextControl(
            _safe_formatted_text(get_menu_content, fallback_style="class:menu.item"),
            focusable=True,
        ), 
        style="class:menu", 
        wrap_lines=True,
        right_margins=[ScrollbarMargin(display_arrows=True)],
    )
    setattr(menu_window, "name", "menu")

    def get_input_height():
        current_lines = input_buffer.document.line_count
        # Ensure at least 1 line, max 10 lines
        target = min(10, max(1, current_lines))
        return Dimension(min=target, preferred=target, max=target)

    input_window = Window(
        BufferControl(buffer=input_buffer, key_bindings=input_key_bindings), 
        style="class:input",
        wrap_lines=True, # Ensure long pastes are visible
        height=get_input_height, # Dynamic height based on content
        dont_extend_height=True,
    )
    setattr(input_window, "name", "input")

    input_area = VSplit(
        [
            Window(
                FormattedTextControl(get_input_prompt),
                width=lambda: get_prompt_width(),
                style="class:input",
                dont_extend_width=True,
                dont_extend_height=True,
                height=1,
            ),
            input_window,
        ],
    )

    def get_status_text() -> AnyFormattedText:
        return get_status()
    
    # Interactive status bar
    def get_interactive_status() -> AnyFormattedText:
         base = _safe_formatted_text(get_status_text, fallback_style="class:status")()
         if not isinstance(base, list):
             base = [("", str(base))]
         
         # Informational hint (no callback as requested)
         return base + [("class:status", "  "), ("class:button", f"[ F2: {'Close' if state.menu_level != MenuLevel.NONE else 'Menu'} ]")]

    status_window = Window(FormattedTextControl(get_interactive_status), height=1, style="class:status")

    # Build right panel: either agent messages or context/menu

    def get_log_title() -> str:
        return " LOG [ACTIVE] " if getattr(state, "ui_scroll_target", "log") == "log" else " LOG "

    main_body = HSplit(
        [
            Frame(header_window, style="class:frame.border"),
            VSplit(
                [
                    Frame(
                        log_window, 
                        title=get_log_title, 
                        style="class:frame.border",
                        width=lambda: Dimension(
                            weight=int(getattr(state, "ui_left_panel_ratio", 0.6) * 100),
                            min=getattr(state, "ui_panel_min_width", 40),
                        )
                    ),
                ] + [
                    ConditionalContainer(
                        Frame(
                            w,
                            title=lambda t=title: f" {t} [ACTIVE] " if getattr(state, "ui_scroll_target", "log") == "agents" and t == "АГЕНТИ" else f" {t} ",
                            style="class:frame.border",
                            width=lambda: Dimension(
                                weight=int((1.0 - getattr(state, "ui_left_panel_ratio", 0.6)) * 100),
                                min=getattr(state, "ui_panel_min_width", 40),
                            )
                        ),
                        filter=filt
                    ) for w, title, filt in [
                        (agent_messages_window, "АГЕНТИ", Condition(lambda: agent_messages_window is not None and state.menu_level == MenuLevel.NONE)),
                        (context_window, "КОНТЕКСТ", Condition(lambda: agent_messages_window is None and state.menu_level == MenuLevel.NONE)),
                        (menu_window, "MENU", Condition(lambda: state.menu_level != MenuLevel.NONE))
                    ] if w is not None
                ],
                height=Dimension(weight=1) 
            ),
            Frame(input_area, style="class:frame.border"), # Dynamic area height, glued to bottom, expands upwards
            status_window,
        ]
    )

    app = Application(
        layout=Layout(main_body, focused_element=input_window),
        key_bindings=kb,
        full_screen=True,
        style=style,
        mouse_support=True,
    )
    
    # Store global reference for UI updates
    _app_state["instance"] = app
    
    return app
