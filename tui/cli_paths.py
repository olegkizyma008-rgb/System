from __future__ import annotations

import os


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

CLEANUP_CONFIG_PATH = os.path.join(SCRIPT_DIR, "cleanup_modules.json")
LOCALIZATION_CONFIG_PATH = os.path.expanduser("~/.localization_cli.json")

SYSTEM_CLI_DIR = os.path.expanduser("~/.system_cli")
MONITOR_TARGETS_PATH = os.path.join(SYSTEM_CLI_DIR, "monitor_targets.json")
MONITOR_SETTINGS_PATH = os.path.join(SYSTEM_CLI_DIR, "monitor_settings.json")
MONITOR_EVENTS_DB_PATH = os.environ.get("SYSTEM_MONITOR_EVENTS_DB_PATH") or os.path.join(SYSTEM_CLI_DIR, "monitor_events.db")
LLM_SETTINGS_PATH = os.path.join(SYSTEM_CLI_DIR, "llm_settings.json")
UI_SETTINGS_PATH = os.path.join(SYSTEM_CLI_DIR, "ui_settings.json")
