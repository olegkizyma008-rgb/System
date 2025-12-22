"""File monitoring service for TUI.

Provides:
- MonitorSummaryService for aggregating file events
- Database operations for monitor events
- Settings persistence
- Target resolution for editors and browsers
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from system_cli.state import state
from tui.cli_paths import (
    SYSTEM_CLI_DIR,
    MONITOR_SETTINGS_PATH,
    MONITOR_TARGETS_PATH,
    MONITOR_EVENTS_DB_PATH,
)
import shutil



def load_monitor_settings() -> None:
    """Load monitor settings from file."""
    try:
        from tui.agents import load_env
        load_env()
        
        if not os.path.exists(MONITOR_SETTINGS_PATH):
            if str(os.getenv("SUDO_PASSWORD") or "").strip():
                state.monitor_use_sudo = True
            return

        with open(MONITOR_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        src = str(data.get("source") or "").strip().lower()
        if src in {"watchdog", "fs_usage", "opensnoop"}:
            state.monitor_source = src
        # mode can be 'auto' or 'manual' (default auto)
        mode = str(data.get("mode") or "auto").strip().lower()
        if mode in {"auto", "manual"}:
            state.monitor_mode = mode
        else:
            state.monitor_mode = "auto"
        use_sudo = data.get("use_sudo")
        if isinstance(use_sudo, bool):
            state.monitor_use_sudo = use_sudo
        # If mode is auto, let the system choose sensible targets
        try:
            if state.monitor_mode == "auto":
                monitor_auto_select_targets()
        except Exception:
            pass
    except Exception:
        return


def save_monitor_settings() -> bool:
    """Save monitor settings to file."""
    try:
        os.makedirs(SYSTEM_CLI_DIR, exist_ok=True)
        payload = {
            "source": state.monitor_source,
            "use_sudo": bool(state.monitor_use_sudo),
            # mode: 'auto' or 'manual'
            "mode": str(state.monitor_mode or "auto").strip().lower(),
        }
        with open(MONITOR_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_monitor_targets() -> None:
    """Load monitor targets from file."""
    try:
        if not os.path.exists(MONITOR_TARGETS_PATH):
            return
        with open(MONITOR_TARGETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        selected = data.get("selected") or []
        if isinstance(selected, list):
            state.monitor_targets = {str(x) for x in selected if x}
    except Exception:
        return


def monitor_auto_select_targets() -> None:
    """Auto-select monitor targets based on running processes and common editors/browsers.

    Populates `state.monitor_targets` with entries like `editor:Code`, `browser:Google Chrome`, and `network:all`.
    This is a best-effort heuristic and is safe to call repeatedly.
    """
    try:
        import subprocess

        proc = subprocess.run(["ps", "-ax", "-o", "comm="], capture_output=True, text=True)
        out = (proc.stdout or "").strip().splitlines()
        names = [os.path.basename(x).strip() for x in out if x]

        editors = set()
        browsers = set()

        for n in names:
            ln = n.lower()
            if any(k in ln for k in ["code", "vscode", "sublime", "pycharm", "idea", "windsurf"]):
                editors.add(n)
            if any(k in ln for k in ["chrome", "safari", "firefox", "chromium"]):
                browsers.add(n)

        new_targets = set()
        for e in sorted(editors)[:3]:
            new_targets.add(f"editor:{e}")
        for b in sorted(browsers)[:3]:
            new_targets.add(f"browser:{b}")

        # Add a generic network target to allow network-level monitoring where supported
        new_targets.add("network:all")

        # If nothing found, include the home dir as fallback
        if not new_targets:
            new_targets.add("home:~/")

        state.monitor_targets = new_targets
        save_monitor_targets()
    except Exception:
        return


def tool_monitor_set_mode(args: dict) -> dict:
    """Agent tool: set monitoring mode to 'auto' or 'manual'.

    If set to 'auto', this will run the auto target selection immediately.
    """
    mode = str((args or {}).get("mode") or "auto").strip().lower()
    if mode not in {"auto", "manual"}:
        return {"status": "error", "error": "mode must be 'auto' or 'manual'"}
    state.monitor_mode = mode
    saved = save_monitor_settings()
    if mode == "auto":
        monitor_auto_select_targets()
    return {"status": "success", "mode": mode, "saved": bool(saved)}


def save_monitor_targets() -> bool:
    """Save monitor targets to file."""
    try:
        os.makedirs(SYSTEM_CLI_DIR, exist_ok=True)
        payload = {"selected": sorted(state.monitor_targets)}
        with open(MONITOR_TARGETS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def monitor_get_sudo_password() -> str:
    """Get SUDO_PASSWORD from environment."""
    from tui.agents import load_env
    load_env()
    return str(os.getenv("SUDO_PASSWORD") or "").strip()


def monitor_db_read_since_id(db_path: str, last_id: int, limit: int = 5000) -> List[Dict[str, Any]]:
    """Read monitor events from database since given ID."""
    rows: List[Dict[str, Any]] = []
    try:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(
                "SELECT id, ts, source, event_type, src_path, dest_path, is_directory, target_key, pid, process, raw_line "
                "FROM events WHERE id > ? ORDER BY id ASC LIMIT ?",
                (int(last_id or 0), int(limit)),
            )
            for r in cur.fetchall():
                rows.append(
                    {
                        "id": int(r[0] or 0),
                        "ts": int(r[1] or 0),
                        "source": str(r[2] or ""),
                        "event_type": str(r[3] or ""),
                        "src_path": str(r[4] or ""),
                        "dest_path": str(r[5] or ""),
                        "is_directory": bool(int(r[6] or 0)),
                        "target_key": str(r[7] or ""),
                        "pid": int(r[8] or 0),
                        "process": str(r[9] or ""),
                        "raw_line": str(r[10] or ""),
                    }
                )
        finally:
            conn.close()
    except Exception:
        return []
    return rows


def monitor_db_get_max_id(db_path: str) -> int:
    """Get maximum event ID from database."""
    try:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute("SELECT MAX(id) FROM events")
            row = cur.fetchone()
            if not row:
                return 0
            return int(row[0] or 0)
        finally:
            conn.close()
    except Exception:
        return 0


def format_monitor_summary(
    *,
    title: str,
    source: str,
    targets: List[str],
    ts_from: int,
    ts_to: int,
    total_events: int,
    by_target: Dict[str, int],
    by_type: Dict[str, int],
    top_paths: Dict[str, List[Tuple[str, int]]],
    include_processes: bool,
    top_processes: List[Tuple[str, int]],
) -> str:
    """Format monitor summary as human-readable string."""
    lines: List[str] = []
    lines.append(title)
    lines.append(f"source={source} targets={len(targets)} events={total_events}")
    lines.append(f"ts_range={ts_from}..{ts_to}")
    if targets:
        lines.append("targets: " + ", ".join(targets[:20]) + ("" if len(targets) <= 20 else " ..."))
    if by_target:
        top_t = sorted(by_target.items(), key=lambda x: x[1], reverse=True)[:10]
        lines.append("top_targets: " + ", ".join([f"{k}={v}" for k, v in top_t]))
    if by_type:
        top_e = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]
        lines.append("top_event_types: " + ", ".join([f"{k}={v}" for k, v in top_e]))
    if include_processes and top_processes:
        lines.append("top_processes: " + ", ".join([f"{k}={v}" for k, v in top_processes[:10]]))
    if top_paths:
        for tk, paths in list(top_paths.items())[:10]:
            if not paths:
                continue
            p = ", ".join([f"{path}({cnt})" for path, cnt in paths[:5]])
            lines.append(f"paths[{tk}]: {p}")
    return "\n".join(lines)


def monitor_resolve_watch_items(targets: Set[str]) -> List[Tuple[str, str]]:
    """Resolve monitor targets to (path, target_key) tuples."""
    home = os.path.expanduser("~")
    items: List[Tuple[str, str]] = []

    def add_if_dir(path: str, target_key: str) -> None:
        if os.path.isdir(path):
            items.append((path, target_key))

    for t in sorted(targets):
        if t.startswith("browser:"):
            name = t.split(":", 1)[1]
            low = name.lower()
            if low == "safari":
                add_if_dir(os.path.join(home, "Library", "Safari"), t)
                add_if_dir(os.path.join(home, "Library", "Containers", "com.apple.Safari"), t)
            elif "chrome" in low:
                add_if_dir(os.path.join(home, "Library", "Application Support", "Google", "Chrome"), t)
                add_if_dir(os.path.join(home, "Library", "Caches", "Google", "Chrome"), t)
            elif "chromium" in low:
                add_if_dir(os.path.join(home, "Library", "Application Support", "Chromium"), t)
                add_if_dir(os.path.join(home, "Library", "Caches", "Chromium"), t)
            elif "firefox" in low:
                add_if_dir(os.path.join(home, "Library", "Application Support", "Firefox"), t)
                add_if_dir(os.path.join(home, "Library", "Caches", "Firefox"), t)
            else:
                add_if_dir(os.path.join(home, "Library", "Application Support", name), t)
                add_if_dir(os.path.join(home, "Library", "Caches", name), t)

        if t.startswith("editor:"):
            editor_key = t.split(":", 1)[1]
            add_if_dir(os.path.join(home, "Library", "Application Support", editor_key), t)
            add_if_dir(os.path.join(home, "Library", "Caches", editor_key), t)

    # unique by (path,target)
    seen: Set[Tuple[str, str]] = set()
    uniq: List[Tuple[str, str]] = []
    for p, k in items:
        key = (p, k)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((p, k))
    return uniq


@dataclass
class MonitorMenuItem:
    """Menu item for monitor targets selection."""
    key: str
    label: str
    selectable: bool
    category: str
    origin: str = ""


@dataclass
class MonitorSummaryService:
    """Service for aggregating and ingesting monitor summaries."""
    db_path: str
    interval_sec: int = 30
    flush_threshold: int = 250
    thread: Optional[threading.Thread] = None
    running: bool = False
    stop_event: threading.Event = field(default_factory=threading.Event)
    last_id: int = 0
    session_start_ts: int = 0
    session_end_ts: int = 0
    total_events: int = 0
    totals_by_target: Counter = field(default_factory=Counter)
    totals_by_type: Counter = field(default_factory=Counter)
    totals_by_process: Counter = field(default_factory=Counter)
    totals_paths_by_target: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    last_flush_ts: int = 0

    def _ingest(self, text: str, metadata: Dict[str, Any]) -> bool:
        """Ingest summary into RAG pipeline."""
        try:
            from tui.agents import load_env
            load_env()
            from system_ai.rag.rag_pipeline import RagPipeline

            rp = RagPipeline(persist_dir="~/.system_cli/chroma")
            return bool(rp.ingest_text(text, metadata=metadata))
        except Exception:
            return False

    def _flush(self, *, kind: str, targets: List[str], source: str) -> None:
        """Flush pending events to summary."""
        batch = monitor_db_read_since_id(self.db_path, self.last_id, limit=5000)
        if not batch:
            return

        self.last_id = max(self.last_id, max(int(x.get("id") or 0) for x in batch))
        ts_values = [int(x.get("ts") or 0) for x in batch if int(x.get("ts") or 0) > 0]
        ts_from = min(ts_values) if ts_values else int(time.time())
        ts_to = max(ts_values) if ts_values else int(time.time())

        by_target = Counter()
        by_type = Counter()
        by_process = Counter()
        paths_by_target: Dict[str, Counter] = defaultdict(Counter)

        for e in batch:
            tk = str(e.get("target_key") or "")
            et = str(e.get("event_type") or "")
            by_target[tk] += 1
            by_type[et] += 1
            src = str(e.get("src_path") or "")
            if src:
                paths_by_target[tk][src] += 1
            proc = str(e.get("process") or "").strip()
            if proc:
                by_process[proc] += 1

        self.total_events += len(batch)
        self.totals_by_target.update(by_target)
        self.totals_by_type.update(by_type)
        self.totals_by_process.update(by_process)
        for tk, c in paths_by_target.items():
            self.totals_paths_by_target[tk].update(c)
        self.session_end_ts = max(self.session_end_ts, ts_to)

        top_paths: Dict[str, List[Tuple[str, int]]] = {}
        for tk, c in paths_by_target.items():
            top_paths[tk] = c.most_common(10)

        include_processes = bool(by_process)
        summary_text = format_monitor_summary(
            title=f"MONITOR SUMMARY ({kind})",
            source=str(source or ""),
            targets=targets,
            ts_from=ts_from,
            ts_to=ts_to,
            total_events=len(batch),
            by_target=dict(by_target),
            by_type=dict(by_type),
            top_paths=top_paths,
            include_processes=include_processes,
            top_processes=by_process.most_common(10),
        )

        meta = {
            "type": "monitor_summary",
            "kind": kind,
            "source": str(source or ""),
            "targets": targets,
            "events": int(len(batch)),
            "ts_from": int(ts_from),
            "ts_to": int(ts_to),
        }
        ok = self._ingest(summary_text, meta)
        if ok:
            self.last_flush_ts = int(time.time())

    def _run(self) -> None:
        """Background thread for periodic flushing."""
        while not self.stop_event.wait(timeout=max(5, int(self.interval_sec))):
            if not self.running:
                break
            try:
                targets = sorted(getattr(state, "monitor_targets", set()) or set())
                source = str(getattr(state, "monitor_source", "") or "")
                self._flush(kind="periodic", targets=targets, source=source)
            except Exception:
                continue

        # Final flush on stop
        try:
            targets = sorted(getattr(state, "monitor_targets", set()) or set())
            source = str(getattr(state, "monitor_source", "") or "")
            self._flush(kind="final", targets=targets, source=source)
        except Exception:
            pass

        # Session summary
        if self.total_events > 0:
            try:
                targets = sorted(getattr(state, "monitor_targets", set()) or set())
                source = str(getattr(state, "monitor_source", "") or "")

                top_paths_total: Dict[str, List[Tuple[str, int]]] = {}
                for tk, c in self.totals_paths_by_target.items():
                    top_paths_total[tk] = c.most_common(10)

                session_text = format_monitor_summary(
                    title="MONITOR SESSION SUMMARY",
                    source=str(source or ""),
                    targets=targets,
                    ts_from=int(self.session_start_ts or 0),
                    ts_to=int(self.session_end_ts or 0),
                    total_events=int(self.total_events),
                    by_target=dict(self.totals_by_target),
                    by_type=dict(self.totals_by_type),
                    top_paths=top_paths_total,
                    include_processes=bool(self.totals_by_process),
                    top_processes=self.totals_by_process.most_common(10),
                )

                meta = {
                    "type": "monitor_summary",
                    "kind": "session",
                    "source": str(source or ""),
                    "targets": targets,
                    "events": int(self.total_events),
                    "ts_from": int(self.session_start_ts or 0),
                    "ts_to": int(self.session_end_ts or 0),
                }
                self._ingest(session_text, meta)
            except Exception:
                pass

        self.running = False

    def start(self) -> None:
        """Start the summary service."""
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        self.session_start_ts = int(time.time())
        self.session_end_ts = int(self.session_start_ts)
        self.last_flush_ts = 0
        self.total_events = 0
        self.totals_by_target = Counter()
        self.totals_by_type = Counter()
        self.totals_by_process = Counter()
        self.totals_paths_by_target = defaultdict(Counter)
        self.last_id = monitor_db_get_max_id(self.db_path)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the summary service."""
        if not self.running:
            return
        self.stop_event.set()
        try:
            if self.thread:
                self.thread.join(timeout=8)
        except Exception:
            pass
        self.thread = None
        self.running = False


# Global service instance
monitor_summary_service = MonitorSummaryService(db_path=MONITOR_EVENTS_DB_PATH)


def _monitor_startup_log() -> None:
    """Log monitor startup details (DB path, existence, size, settings)."""
    try:
        db = MONITOR_EVENTS_DB_PATH
        exists = os.path.exists(db)
        size = os.path.getsize(db) if exists else 0
        from tui.cli import _maybe_log_monitor_ingest

        _maybe_log_monitor_ingest(
            f"Monitor startup: db={db} exists={exists} size={size} source={getattr(state,'monitor_source','')} use_sudo={getattr(state,'monitor_use_sudo',False)} targets={len(getattr(state,'monitor_targets',set()) or set())}"
        )
    except Exception:
        return


# Run startup log once
_monitor_startup_log()



def monitor_start_selected() -> Tuple[bool, str]:
    """Start the selected monitoring source."""
    from tui.cli import monitor_service, fs_usage_service, opensnoop_service
    src = state.monitor_source
    if src == "watchdog":
        return monitor_service.start()
    elif src == "fs_usage":
        return fs_usage_service.start()
    elif src == "opensnoop":
        return opensnoop_service.start()
    return False, f"Unknown source: {src}"


def monitor_stop_selected() -> Tuple[bool, str]:
    """Stop the selected monitoring source."""
    from tui.cli import monitor_service, fs_usage_service, opensnoop_service
    src = state.monitor_source
    if src == "watchdog":
        return monitor_service.stop()
    elif src == "fs_usage":
        return fs_usage_service.stop()
    elif src == "opensnoop":
        return opensnoop_service.stop()
    return False, f"Unknown source: {src}"


def monitor_summary_start_if_needed() -> None:
    """Start summary service if monitoring is active."""
    if state.monitor_active:
        monitor_summary_service.start()


def monitor_summary_stop_if_needed() -> None:
    """Stop summary service."""
    monitor_summary_service.stop()


def tool_monitor_status() -> Dict[str, Any]:
    """Get monitoring status."""
    return {
        "ok": True,
        "active": bool(state.monitor_active),
        "source": state.monitor_source,
        "use_sudo": bool(state.monitor_use_sudo),
        "targets_count": len(state.monitor_targets),
        "db": MONITOR_EVENTS_DB_PATH,
    }


def tool_monitor_set_source(args: Dict[str, Any]) -> Dict[str, Any]:
    """Set monitoring source."""
    src = str(args.get("source") or "").strip().lower()
    if src not in {"watchdog", "fs_usage", "opensnoop"}:
        return {"ok": False, "error": "Invalid source. Use watchdog|fs_usage|opensnoop"}
    if state.monitor_active:
        return {"ok": False, "error": "Stop monitoring before changing source"}
    
    from tui.agents import load_env
    load_env()
    state.monitor_source = src
    if src in {"fs_usage", "opensnoop"} and not state.monitor_use_sudo:
        if str(os.getenv("SUDO_PASSWORD") or "").strip():
            state.monitor_use_sudo = True
    save_monitor_settings()
    return {"ok": True, "source": state.monitor_source}


def tool_monitor_set_use_sudo(args: Dict[str, Any]) -> Dict[str, Any]:
    """Toggle sudo usage for monitoring."""
    use_sudo = args.get("use_sudo")
    if not isinstance(use_sudo, bool):
        raw = str(use_sudo or "").strip().lower()
        if raw in {"1", "true", "yes", "on", "enable", "enabled"}:
            use_sudo = True
        elif raw in {"0", "false", "no", "off", "disable", "disabled"}:
            use_sudo = False
        else:
            return {"ok": False, "error": "use_sudo must be boolean"}
    
    if state.monitor_active:
        return {"ok": False, "error": "Stop monitoring before changing sudo setting"}
    state.monitor_use_sudo = bool(use_sudo)
    save_monitor_settings()
    return {"ok": True, "use_sudo": state.monitor_use_sudo}


def tool_monitor_summarize(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create an on-demand summary of recent monitor events and return text.

    Args (optional):
      - limit: maximum number of recent events to include (default 5000)
    """
    try:
        limit = int(args.get("limit") or 5000)
    except Exception:
        limit = 5000

    try:
        max_id = monitor_db_get_max_id(MONITOR_EVENTS_DB_PATH)
        start_id = max(0, int(max_id) - int(limit))
        batch = monitor_db_read_since_id(MONITOR_EVENTS_DB_PATH, start_id, limit=limit)
        if not batch:
            return {"ok": True, "summary": "No recent events"}

        ts_values = [int(x.get("ts") or 0) for x in batch if int(x.get("ts") or 0) > 0]
        ts_from = min(ts_values) if ts_values else int(time.time())
        ts_to = max(ts_values) if ts_values else int(time.time())

        by_target = Counter()
        by_type = Counter()
        by_process = Counter()
        paths_by_target: Dict[str, Counter] = defaultdict(Counter)

        for e in batch:
            tk = str(e.get("target_key") or "")
            et = str(e.get("event_type") or "")
            by_target[tk] += 1
            by_type[et] += 1
            src = str(e.get("src_path") or "")
            if src:
                paths_by_target[tk][src] += 1
            proc = str(e.get("process") or "").strip()
            if proc:
                by_process[proc] += 1

        top_paths: Dict[str, List[Tuple[str, int]]] = {}
        for tk, c in paths_by_target.items():
            top_paths[tk] = c.most_common(10)

        include_processes = bool(by_process)
        summary_text = format_monitor_summary(
            title="MONITOR SUMMARY (manual)",
            source=str(getattr(state, "monitor_source", "") or ""),
            targets=sorted(getattr(state, "monitor_targets", set()) or set()),
            ts_from=int(ts_from),
            ts_to=int(ts_to),
            total_events=len(batch),
            by_target=dict(by_target),
            by_type=dict(by_type),
            top_paths=top_paths,
            include_processes=include_processes,
            top_processes=by_process.most_common(10),
        )

        return {"ok": True, "summary": summary_text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_monitor_import_log(args: Dict[str, Any]) -> Dict[str, Any]:
    """Import a fs_usage or opensnoop log file into monitor DB.

    Args:
      - path: path to the log file
    """
    path = str(args.get("path") or "").strip()
    if not path:
        return {"ok": False, "error": "Missing path"}
    if not os.path.exists(path):
        return {"ok": False, "error": "File not found"}
    try:
        from tui.cli import _ProcTraceService

        svc = _ProcTraceService("fs_usage", ["fs_usage", "-w", "-f", "filesys"])
        count = 0
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                svc._parse_and_insert(ln)
                count += 1
        return {"ok": True, "imported": count}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_monitor_start() -> Dict[str, Any]:
    """Start monitoring."""
    if state.monitor_active:
        return {"ok": True, "message": "Monitoring already active"}
    if not state.monitor_targets:
        return {"ok": False, "error": "No targets selected"}
    
    ok, msg = monitor_start_selected()
    # Note: monitor_service and others are still in cli.py, 
    # so we might need to check if they are running.
    # For now assume ok means they are running or starting.
    state.monitor_active = ok 
    if ok:
        monitor_summary_start_if_needed()
    return {"ok": ok, "message": msg, "active": state.monitor_active}


def tool_monitor_stop() -> Dict[str, Any]:
    """Stop monitoring."""
    ok, msg = monitor_stop_selected()
    state.monitor_active = False
    monitor_summary_stop_if_needed()
    return {"ok": ok, "message": msg, "active": state.monitor_active}


def tool_monitor_targets(args: Dict[str, Any]) -> Dict[str, Any]:
    """Manage monitoring targets (tool handler)."""
    action = str(args.get("action") or "status").strip().lower()
    key = str(args.get("key") or "").strip()
    if action in {"status", "list", "ls"}:
        return {"ok": True, "targets": sorted(state.monitor_targets)}
    if action == "add":
        if not key:
            return {"ok": False, "error": "Missing key"}
        state.monitor_targets.add(key)
        return {"ok": True, "targets": sorted(state.monitor_targets)}
    if action in {"remove", "rm"}:
        if not key:
            return {"ok": False, "error": "Missing key"}
        if key in state.monitor_targets:
            state.monitor_targets.remove(key)
        return {"ok": True, "targets": sorted(state.monitor_targets)}
    if action == "clear":
        state.monitor_targets = set()
        return {"ok": True, "targets": []}
    if action == "save":
        ok = save_monitor_targets()
        return {"ok": ok, "targets": sorted(state.monitor_targets)}
    return {"ok": False, "error": f"Unknown action: {action}"}


# Backward compatibility aliases
_load_monitor_settings = load_monitor_settings
_save_monitor_settings = save_monitor_settings
_load_monitor_targets = load_monitor_targets
_save_monitor_targets = save_monitor_targets
_monitor_get_sudo_password = monitor_get_sudo_password
_monitor_db_read_since_id = monitor_db_read_since_id
_monitor_db_get_max_id = monitor_db_get_max_id
_format_monitor_summary = format_monitor_summary
_monitor_resolve_watch_items = monitor_resolve_watch_items
_MonitorSummaryService = MonitorSummaryService
_monitor_start_selected = monitor_start_selected
_monitor_stop_selected = monitor_stop_selected
_monitor_summary_start_if_needed = monitor_summary_start_if_needed
_monitor_summary_stop_if_needed = monitor_summary_stop_if_needed
_tool_monitor_status = tool_monitor_status
_tool_monitor_set_source = tool_monitor_set_source
_tool_monitor_set_use_sudo = tool_monitor_set_use_sudo
_tool_monitor_start = tool_monitor_start
_tool_monitor_stop = tool_monitor_stop
_tool_monitor_targets = tool_monitor_targets
_tool_monitor_summarize = tool_monitor_summarize
_tool_monitor_import_log = tool_monitor_import_log


def tool_monitor_flush(args: Dict[str, Any]) -> Dict[str, Any]:
    """Force a manual flush of monitor events into the RAG ingestion pipeline."""
    try:
        targets = sorted(getattr(state, "monitor_targets", set()) or set())
        source = str(getattr(state, "monitor_source", "") or "")
        monitor_summary_service._flush(kind="manual", targets=targets, source=source)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_tool_monitor_flush = tool_monitor_flush
