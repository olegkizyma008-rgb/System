"""Background SonarQube scanner for Trinity.

Best-effort background job that fetches Sonar issues and indexes them into Context7
or local Context7 store. Controlled via env vars:
- TRINITY_SONAR_BACKGROUND=1 to enable
- TRINITY_SONAR_SCAN_INTERVAL (minutes, default 60)
"""
from __future__ import annotations

import os
import threading
import time
from typing import Optional

from core.trinity import TrinityRuntime


class SonarBackgroundScanner:
    def __init__(self, runtime: TrinityRuntime, interval_minutes: int = 60):
        self.runtime = runtime
        self.interval = max(1, int(interval_minutes))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="SonarScanner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                # best-effort; do not crash
                pass
            # sleep in small chunks so stop reacts quickly
            slept = 0
            to_sleep = self.interval * 60
            while slept < to_sleep and not self._stop_event.is_set():
                time.sleep(1)
                slept += 1

    def run_once(self) -> None:
        """Perform a single fetch+index operation. Use for tests and manual invocation."""
        try:
            # Use runtime helper to enrich context (which already indexes into MCP/Context7)
            dummy_state = {"is_dev": True, "retrieved_context": "", "original_task": "Sonar background scan"}
            new_state = self.runtime._enrich_context_with_sonar(dummy_state)
            return new_state
        except Exception:
            pass
        return None
