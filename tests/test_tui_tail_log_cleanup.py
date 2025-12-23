import threading
import time
import pathlib

from tui.agents import _tail_log_file


def test_tail_thread_stops(tmp_path):
    log_path = tmp_path / "cli.log"
    log_path.write_text("initial\n", encoding="utf-8")

    tail_active = threading.Event()
    tail_active.set()
    last_pos = [0]

    # Monkeypatch _process_log_line to use dummy logger
    # Instead of monkeypatching, we use the function with a small delay and stop soon
    t = threading.Thread(target=_tail_log_file, args=(tail_active, pathlib.Path(log_path), last_pos), daemon=True)
    t.start()

    # Append new content
    time.sleep(0.2)
    log_path.write_text("initial\nsecond line\n", encoding="utf-8")
    time.sleep(0.3)

    # Stop and join
    tail_active.clear()
    t.join(timeout=1.0)
    assert not t.is_alive()
