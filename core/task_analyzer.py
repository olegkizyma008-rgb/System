from __future__ import annotations

import os
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class TaskAnalyzer:
    """Lightweight per-task logger and analyzer for Trinity runs.

    - Creates a dedicated log file per task
    - Records structured events and errors
    - Computes simple metrics and status
    - Cleans up file handlers to avoid leaks
    """

    def __init__(self, log_dir: str | None = None, screenshot_dir: str | None = None):
        self.logger = logging.getLogger("core.task_analyzer")
        self.logger.setLevel(logging.DEBUG)
        # Resolve default directories outside of repo to avoid dirty git status
        default_logs = os.environ.get("TRINITY_TASK_LOG_DIR")
        if not default_logs:
            default_logs = os.path.abspath("task_logs")
        default_shots = os.environ.get("TRINITY_TASK_SCREENSHOT_DIR")
        if not default_shots:
            default_shots = os.path.abspath("task_screenshots")

        self.log_dir = log_dir or default_logs
        self.screenshot_dir = screenshot_dir or default_shots

        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)

        self.task_history: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None

    def start_task_analysis(self, task_name: str, task_description: str) -> Dict[str, Any]:
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_task = {
            "task_id": task_id,
            "name": task_name,
            "description": task_description,
            "start_time": datetime.now().isoformat(),
            "status": "started",
            "logs": [],
            "screenshots": [],
            "errors": [],
            "metrics": {},
        }

        task_log_path = os.path.join(self.log_dir, f"{task_id}.log")
        self.current_task["log_file"] = task_log_path

        # Attach a file handler specific to this task
        fh = logging.FileHandler(task_log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)

        self.logger.info(f"🚀 Starting task analysis: {task_name}")
        self.logger.info(f"Task ID: {task_id}")
        self.logger.info(f"Description: {task_description}")

        return {"success": True, "task_id": task_id}

    def log_task_event(self, event_type: str, data: Dict[str, Any]) -> None:
        if not self.current_task:
            self.logger.warning("No active task to log to")
            return

        event = {"timestamp": datetime.now().isoformat(), "type": event_type, "data": data}
        self.current_task["logs"].append(event)

        msg = f"[{event_type.upper()}] {data.get('message', 'No message')}"
        if event_type == "error":
            self.logger.error(msg)
            self.current_task["errors"].append(event)
        elif event_type == "warning":
            self.logger.warning(msg)
        elif event_type == "info":
            self.logger.info(msg)
        else:
            self.logger.debug(msg)

    def capture_screenshot(self, description: str = "") -> Dict[str, Any]:
        if not self.current_task:
            return {"success": False, "error": "No active task"}
        try:
            from system_ai.tools.screenshot import take_screenshot
            res = take_screenshot()
            if res.get("status") == "success" and res.get("path"):
                src = res["path"]
                ext = os.path.splitext(src)[1] or ".png"
                dest = os.path.join(self.screenshot_dir, f"{self.current_task['task_id']}_s{len(self.current_task['screenshots'])+1}{ext}")
                try:
                    shutil.copyfile(src, dest)
                except Exception:
                    dest = src
                info = {
                    "path": dest,
                    "source_path": src,
                    "timestamp": datetime.now().isoformat(),
                    "description": description,
                }
                self.current_task["screenshots"].append(info)
                self.logger.info(f"📸 Captured screenshot: {description}")
                return {"success": True, "path": dest}
            err = res.get("error") or "Unknown screenshot error"
            self.log_task_event("error", {"message": err})
            return {"success": False, "error": err}
        except Exception as e:
            self.log_task_event("error", {"message": str(e)})
            return {"success": False, "error": str(e)}

    def analyze_task_execution(self) -> Dict[str, Any]:
        if not self.current_task:
            return {"success": False, "error": "No task to analyze"}

        self.current_task["end_time"] = datetime.now().isoformat()
        # Dynamic status based on error_count
        error_count = len(self.current_task.get("errors", []))
        self.current_task["status"] = "failed" if error_count > 0 else "completed"

        # Metrics
        try:
            from datetime import datetime as _dt
            st = _dt.fromisoformat(self.current_task["start_time"])  # type: ignore[arg-type]
            et = _dt.fromisoformat(self.current_task["end_time"])    # type: ignore[arg-type]
            duration = (et - st).total_seconds()
        except Exception:
            duration = 0.0

        self.current_task["metrics"] = {
            "duration_seconds": duration,
            "screenshot_count": len(self.current_task.get("screenshots", [])),
            "error_count": error_count,
            "log_count": len(self.current_task.get("logs", [])),
        }

        # Persist task JSON
        try:
            path = os.path.join(self.log_dir, f"{self.current_task['task_id']}_data.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.current_task, f, indent=2)
            self.logger.info(f"💾 Saved task data to {path}")
        except Exception as e:
            self.logger.exception(f"Failed to save task data: {e}")

        # Clean up file handler for this task to prevent leaks
        try:
            target = self.current_task.get("log_file")
            for h in self.logger.handlers:
                try:
                    if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == target:
                        self.logger.removeHandler(h)
                        h.close()
                except Exception:
                    # Do not fail cleanup entirely; log and continue
                    self.logger.exception("Failed to remove/close task file handler")
        except Exception:
            self.logger.exception("Unexpected error during handler cleanup")

        # Archive and return
        self.task_history.append(self.current_task)
        result = {
            "success": True,
            "task_id": self.current_task["task_id"],
            "status": self.current_task["status"],
            "metrics": self.current_task["metrics"],
        }
        self.current_task = None
        return result
