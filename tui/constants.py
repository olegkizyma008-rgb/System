from __future__ import annotations

from typing import List, Tuple

from tui.state import MenuLevel


MAIN_MENU_ITEMS: List[Tuple[str, MenuLevel]] = [
    ("menu.item.custom_tasks", MenuLevel.CUSTOM_TASKS),
    ("menu.item.run_cleanup", MenuLevel.CLEANUP_EDITORS),
    ("menu.item.modules", MenuLevel.MODULE_EDITORS),
    ("menu.item.install", MenuLevel.INSTALL_EDITORS),
    ("menu.item.monitoring", MenuLevel.MONITORING),
    ("menu.item.settings", MenuLevel.SETTINGS),
]
