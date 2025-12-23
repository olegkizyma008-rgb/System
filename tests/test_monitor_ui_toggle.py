from types import SimpleNamespace

from tui.keybindings import _handle_monitor_control_enter_ctx


def test_monitor_mode_toggle_ui(monkeypatch, tmp_path):
    logs = []
    st = SimpleNamespace()
    st.monitor_mode = "auto"
    st.monitor_active = False
    st.monitor_targets = {"editor:Code"}
    st.menu_index = 0

    ctx = {
        "state": st,
        "monitor_stop_selected": lambda: (True, "stopped"),
        "monitor_start_selected": lambda: (True, "started"),
        "monitor_service": SimpleNamespace(running=False),
        "fs_usage_service": SimpleNamespace(running=False),
        "opensnoop_service": SimpleNamespace(running=False),
        "log": lambda msg, level: logs.append((msg, level)),
        "save_monitor_settings": lambda: True,
    }

    # Toggle once (auto -> manual)
    _handle_monitor_control_enter_ctx(ctx)
    assert st.monitor_mode == "manual"
    assert logs and logs[-1][0].startswith("Monitor mode:")

    # Toggle again (manual -> auto)
    _handle_monitor_control_enter_ctx(ctx)
    assert st.monitor_mode == "auto"


def test_monitor_mode_hint_in_menu():
    from types import SimpleNamespace
    from tui.menu import _render_monitor_control_menu

    st = SimpleNamespace()
    st.monitor_active = False
    st.monitor_source = "watchdog"
    st.monitor_mode = "auto"
    st.monitor_use_sudo = False
    st.monitor_targets = set()
    st.ui_lang = "uk"

    def make_click(i):
        return lambda ev: None

    MenuLevel = type("ML", (), {"MAIN": "MAIN"})
    ctx = {
        "state": st,
        "make_click": make_click,
        "MONITOR_EVENTS_DB_PATH": "/tmp/db",
        "MenuLevel": MenuLevel,
        "tr": lambda k, l: k,
        "force_ui_update": lambda: None,
    }
    items = _render_monitor_control_menu(ctx)
    texts = [it[1] for it in items if len(it) > 1]
    from tui.i18n import tr
    hint = tr("menu.monitor.mode_hint", st.ui_lang)
    assert any(hint in t for t in texts)
