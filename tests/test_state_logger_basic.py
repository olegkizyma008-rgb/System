import pathlib
from datetime import datetime

from core.state_logger import log_initial_state


def test_state_logger_writes_file(tmp_path, monkeypatch):
    # Redirect logs dir to tmp by monkeypatching Path.home to tmp
    monkeypatch.setenv("HOME", str(tmp_path))

    state = {
        "current_agent": "atlas",
        "task_type": "DEV",
        "is_dev": True,
        "execution_mode": "native",
        "gui_mode": "auto",
        "meta_config": {
            "strategy": "hybrid",
            "verification_rigor": "standard",
            "recovery_mode": "local_fix",
        }
    }
    log_initial_state("Dummy task", state)

    # Expect a trinity_state_YYYYMMDD.log file either under project logs or ~/.system_cli/logs
    today = datetime.now().strftime('%Y%m%d')
    home_log_file = tmp_path / ".system_cli" / "logs" / f"trinity_state_{today}.log"
    project_log_file = pathlib.Path(__file__).parent.parent / "logs" / f"trinity_state_{today}.log"
    log_file = home_log_file if home_log_file.exists() else project_log_file
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "TRINITY STATE INITIALIZATION" in content
