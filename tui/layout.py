from __future__ import annotations

from typing import Any, Callable

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
# Added import for MenuLevel
# Assuming MenuLevel is in system_cli.state or tui.state. 
# Based on existing imports 'from system_cli.state import state', let's guess MenuLevel is there or locally defined?
# Wait, in tui/cli.py: line 1637: MenuLevel=MenuLevel passed to build_menu.
# MenuLevel is often an IntEnum. It seems to be missing in layout.py
# I will add 'from tui.state import MenuLevel' if it exists, or check where it is.
# Actually, let's fix the missing _safe_formatted_text first.

from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.widgets import Frame
from prompt_toolkit.layout.margins import ScrollbarMargin
from system_cli.state import state, MenuLevel

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
    show_menu: Condition,
    kb: KeyBindings,
    style: BaseStyle,
) -> Application:

    # --- Interactive Header Helpers ---
    def header_callback_menu():
        state.menu_level = MenuLevel.MAIN if state.menu_level == MenuLevel.NONE else MenuLevel.NONE
        state.menu_index = 0
        force_ui_update()

    def header_callback_logs():
        state.ui_scroll_target = "log"
        force_ui_update()

    def header_callback_agents():
        state.ui_scroll_target = "agents"
        force_ui_update()

    def get_interactive_header() -> AnyFormattedText:
        base = _safe_formatted_text(get_header, fallback_style="class:header")()
        # Ensure base is list
        if not isinstance(base, list):
            base = [("", str(base))]
            
        # Add clickable buttons styled
        # We append them to the header text
        # Format: [ MENU ] [ LOGS ] [ AGENTS ]
        
        btn_style = "class:button"
        
        buttons = [
             ("class:header", "  "),
             (btn_style, "[ F2: MENU ]", header_callback_menu),
             ("class:header", " "),
             (btn_style, "[ PgUp: LOGS ]", header_callback_logs),
             ("class:header", " "),
             (btn_style, "[ PgDn: AGENTS ]", header_callback_agents),
             ("class:header", "  "),
        ]
        
        return base + buttons

    header_window = Window(
        FormattedTextControl(get_interactive_header), 
        height=1, 
        style="class:header"
    )

    context_window = Window(
        FormattedTextControl(_safe_formatted_text(get_context, fallback_style="class:context")), 
        style="class:context", 
        wrap_lines=True,
        right_margins=[ScrollbarMargin(display_arrows=True)],
    )

    safe_get_logs = _cached_getter(_safe_formatted_text(get_logs, fallback_style="class:log.info"))
    log_window = Window(
        FormattedTextControl(safe_get_logs, get_cursor_position=_safe_cursor_position(safe_get_logs, get_log_cursor_position)),
        wrap_lines=False,
        right_margins=[ScrollbarMargin(display_arrows=True)],
        style="class:log.window" # ensure background
    )
    setattr(log_window, "name", "log")

    # Agent messages panel (clean communication display)
    safe_get_agent_messages = _cached_getter(
        _safe_formatted_text(get_agent_messages or (lambda: []), fallback_style="class:agent.text")
    )
    if get_agent_messages:
        agent_messages_window = Window(
            FormattedTextControl(
                safe_get_agent_messages,
                get_cursor_position=_safe_cursor_position(safe_get_agent_messages, get_agent_cursor_position) if get_agent_cursor_position else None,
            ),
            wrap_lines=False,
            style="class:agent.panel",
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )
        setattr(agent_messages_window, "name", "agents")
    else:
        agent_messages_window = None

    menu_window = Window(
        FormattedTextControl(_safe_formatted_text(get_menu_content, fallback_style="class:menu.item")), 
        style="class:menu", 
        wrap_lines=True,
        right_margins=[ScrollbarMargin(display_arrows=True)],
    )

    input_area = VSplit(
        [
            Window(
                FormattedTextControl(get_input_prompt),
                width=lambda: get_prompt_width(),
                style="class:input",
                dont_extend_width=True,
            ),
            Window(BufferControl(buffer=input_buffer), style="class:input"),
        ]
    )

    def get_status_text() -> AnyFormattedText:
        return get_status()
    
    # Interactive status bar
    def status_callback_menu():
         state.menu_level = MenuLevel.MAIN if state.menu_level == MenuLevel.NONE else MenuLevel.NONE

    def get_interactive_status() -> AnyFormattedText:
         base = _safe_formatted_text(get_status_text, fallback_style="class:status")()
         if not isinstance(base, list):
             base = [("", str(base))]
         
         # Add help hint
         return base + [("class:status", "  "), ("class:button", "[ Click/F2 For Menu ]", status_callback_menu)]

    status_window = Window(FormattedTextControl(get_interactive_status), height=1, style="class:status")

    # Build right panel: either agent messages or context/menu
    right_panel_items = [
        ConditionalContainer(
            Frame(
                agent_messages_window,
                title="АГЕНТИ",
                style="class:frame.border",
                width=Dimension(min=40, max=60),
            ) if agent_messages_window else Window(),
            filter=Condition(lambda: agent_messages_window is not None and not show_menu()),
        ),
        ConditionalContainer(
            Frame(
                context_window,
                title="КОНТЕКСТ",
                style="class:frame.border",
                width=Dimension(min=40, max=55),
            ),
            filter=Condition(lambda: agent_messages_window is None and not show_menu()),
        ),
        ConditionalContainer(
            Frame(
                menu_window,
                title="MENU",
                style="class:frame.border",
                width=Dimension(min=45, max=70),
            ),
            filter=show_menu,
        ),
    ]

    main_body = HSplit(
        [
            Frame(header_window, style="class:frame.border"),
            VSplit(
                [
                    Frame(
                        log_window, 
                        title="LOG", 
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
                            title=title,
                            style="class:frame.border",
                            width=lambda: Dimension(
                                weight=int((1.0 - getattr(state, "ui_left_panel_ratio", 0.6)) * 100),
                                min=getattr(state, "ui_panel_min_width", 40),
                                max=getattr(state, "ui_panel_max_width", 120),
                            )
                        ),
                        filter=filt
                    ) for w, title, filt in [
                        (agent_messages_window, "АГЕНТИ", Condition(lambda: agent_messages_window is not None and not show_menu())),
                        (context_window, "КОНТЕКСТ", Condition(lambda: agent_messages_window is None and not show_menu())),
                        (menu_window, "MENU", show_menu)
                    ] if w is not None
                ]
            ),
            Frame(input_area, style="class:frame.border", height=4), # Increased height for multiline Paste
            status_window,
        ]
    )

    app = Application(
        layout=Layout(main_body),
        key_bindings=kb,
        full_screen=True,
        style=style,
        mouse_support=True,
    )
    
    # Store global reference for UI updates
    _app_state["instance"] = app
    
    return app
