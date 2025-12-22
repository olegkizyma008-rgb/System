import os
import sqlite3
import tempfile
import pathlib

import pytest


def _make_sample_log(path: pathlib.Path) -> None:
    sample = [
        "15:08:07.830322  open              F=117      (R_____N____X___)  /Users/dev/Library/Application Support/Antigravity/Local Storage/leveldb",
        "15:08:07.830328  write             F=32   B=0x7",
        "15:08:07.830358  write             F=34   B=0x7",
        "15:08:07.830402  open              F=119      (R______________)  /Users/dev/Library/Application Support/Antigravity/Local Storage/leveldb/000097.ldb",
        "15:08:07.830475  fstatfs64         F=119",
    ]
    path.write_text("\n".join(sample) + "\n", encoding="utf-8")


def test_import_log_and_summary(tmp_path, monkeypatch):
    # Prepare a temporary DB and set env override
    db_path = tmp_path / "monitor_events.db"
    monkeypatch.setenv("SYSTEM_MONITOR_EVENTS_DB_PATH", str(db_path))

    # Create empty DB with events table
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, source TEXT, event_type TEXT, src_path TEXT, dest_path TEXT, is_directory INTEGER, target_key TEXT, pid INTEGER, process TEXT, raw_line TEXT)"
    )
    conn.commit()
    conn.close()

    sample = tmp_path / "fs.sample.log"
    _make_sample_log(sample)

    from tui.monitoring import tool_monitor_import_log, tool_monitor_summarize

    res = tool_monitor_import_log({"path": str(sample)})
    assert res.get("ok") is True
    assert res.get("imported") > 0

    # summary should run and include totals
    summ = tool_monitor_summarize({"limit": 50})
    assert summ.get("ok") is True
    assert "MONITOR SUMMARY" in summ.get("summary")

