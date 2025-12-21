#!/usr/bin/env python3
"""Powerful logging system for CLI.

Logs to:
- ~/.system_cli/logs/cli.log (all messages)
- ~/.system_cli/logs/errors.log (errors only)
- Console (if verbose)
- Memory buffer (for TUI display)
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Log directory
LOGS_DIR = Path.home() / ".system_cli" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log files
CLI_LOG_FILE = LOGS_DIR / "cli.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"
DEBUG_LOG_FILE = LOGS_DIR / "debug.log"
ANALYSIS_LOG_FILE = LOGS_DIR / "atlas_analysis.jsonl"

# Backup log files (keep last 5 versions)
CLI_LOG_BACKUP = LOGS_DIR / "cli_{}.log"
ERROR_LOG_BACKUP = LOGS_DIR / "errors_{}.log"
DEBUG_LOG_BACKUP = LOGS_DIR / "debug_{}.log"
ANALYSIS_LOG_BACKUP = LOGS_DIR / "atlas_analysis_{}.jsonl"

# Rotate logs if they exceed 5MB
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
MAX_BACKUPS = 5

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
LOG_FORMAT_SIMPLE = "%(asctime)s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class MemoryHandler(logging.Handler):
    """Store logs in memory for TUI display."""
    
    def __init__(self, max_records: int = 1000):
        super().__init__()
        self.records = []
        self.max_records = max_records
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.records.append({
                "level": record.levelname,
                "message": msg,
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "logger": record.name,
            })
            # Keep only last N records
            if len(self.records) > self.max_records:
                self.records = self.records[-self.max_records:]
        except Exception:
            self.handleError(record)
    
    def get_records(self) -> list:
        """Get all stored records."""
        return self.records.copy()
    
    def clear(self) -> None:
        """Clear all records."""
        self.records.clear()


# Global memory handler
_memory_handler = MemoryHandler()



# JSON Formatter
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "thread": record.threadName,
        }
        if hasattr(record, "tui_category"):
            log_obj["tui_category"] = record.tui_category
        if hasattr(record, "agent_type"):
            log_obj["agent_type"] = str(record.agent_type)
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)

def setup_logging(verbose: bool = False, name: str = "system_cli") -> logging.Logger:
    """Setup comprehensive logging system.
    
    Args:
        verbose: If True, also log to console
        name: Logger name
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Don't propagate to parent loggers
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    
    # 1. Main log file (all messages)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            CLI_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Force DEBUG level
        # Detailed format including thread name
        detailed_fmt = "%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        file_handler.setFormatter(logging.Formatter(detailed_fmt, datefmt=DATE_FORMAT))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup main log file: {e}", file=sys.stderr)
    
    # 2. Error log file (errors only)
    try:
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(detailed_fmt, datefmt=DATE_FORMAT))
        logger.addHandler(error_handler)
    except Exception as e:
        print(f"Failed to setup error log file: {e}", file=sys.stderr)
    
    # 3. Debug log file (debug messages only) - same detailed format
    try:
        debug_handler = logging.handlers.RotatingFileHandler(
            DEBUG_LOG_FILE,
            maxBytes=20 * 1024 * 1024,  # 20 MB
            backupCount=3,
            encoding="utf-8"
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(logging.Formatter(detailed_fmt, datefmt=DATE_FORMAT))
        logger.addHandler(debug_handler)
    except Exception as e:
        print(f"Failed to setup debug log file: {e}", file=sys.stderr)
    # 4. AI Analysis Log (JSONL) - Structured for AI analysis
    try:
        analysis_handler = logging.handlers.RotatingFileHandler(
            ANALYSIS_LOG_FILE,
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=5,
            encoding="utf-8"
        )
        analysis_handler.setLevel(logging.DEBUG)
        analysis_handler.setFormatter(JSONFormatter())
        logger.addHandler(analysis_handler)
    except Exception as e:
        print(f"Failed to setup analysis log file: {e}", file=sys.stderr)
    # 4. AI JSON Log (Machine readable)
    try:
        json_log_file = LOGS_DIR / "ai.log.jsonl"
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=3,
            encoding="utf-8"
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
    except Exception as e:
        print(f"Failed to setup AI JSON log file: {e}", file=sys.stderr)

    # 5. Console handler (if verbose)
    if verbose:
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT_SIMPLE, datefmt=DATE_FORMAT))
            logger.addHandler(console_handler)
        except Exception as e:
            print(f"Failed to setup console handler: {e}", file=sys.stderr)

    # 6. Memory handler (for TUI display)
    _memory_handler.setLevel(logging.INFO) # Keep TUI display cleaner (INFO+), or DEBUG if preferred? User asked for detailed logs "for me" (likely file), but TUI shouldn't be spammed.
    _memory_handler.setFormatter(logging.Formatter(LOG_FORMAT_SIMPLE, datefmt=DATE_FORMAT))
    logger.addHandler(_memory_handler)
    
    return logger


def get_logger(name: str = "system_cli") -> logging.Logger:
    """Get or create logger."""
    return logging.getLogger(name)


def get_memory_logs() -> list:
    """Get all logs from memory buffer."""
    return _memory_handler.get_records()


def clear_memory_logs() -> None:
    """Clear memory buffer."""
    _memory_handler.clear()


def log_exception(logger: logging.Logger, exc: Exception, context: str = "") -> None:
    """Log exception with full traceback."""
    msg = f"Exception occurred{f' in {context}' if context else ''}"
    logger.exception(msg)



def log_command_execution(logger: logging.Logger, cmd: str, cwd: Optional[str] = None, 
                          returncode: Optional[int] = None, stdout: str = "", 
                          stderr: str = "") -> None:
    """Log command execution details."""
    logger.debug(f"Command: {cmd}")
    if cwd:
        logger.debug(f"Working directory: {cwd}")
    if returncode is not None:
        logger.debug(f"Return code: {returncode}")
    if stdout:
        logger.debug(f"STDOUT:\n{stdout}")
    if stderr:
        logger.warning(f"STDERR:\n{stderr}")

def trace(logger: logging.Logger, event: str, data: Optional[dict] = None) -> None:
    """Log structured trace event for AI analysis."""
    import json
    try:
        payload = {"event": event}
        if data:
            payload.update(data)
        # Log as INFO but with a special marker or just rely on JSONFormatter to pick it up if we pass extra
        # Actually, let's just log the dict as a message, JSONFormatter might double encode if we are not careful.
        # But JSONFormatter expects record.getMessage().
        # If we want clean JSONL, we should probably use the logger.info(msg) where msg is the JSON string,
        # OR rely on the fact that JSONFormatter wraps everything.
        # Let's just log a clear message that it's a trace.
        logger.info(f"TRACE: {event} - {json.dumps(data, ensure_ascii=False) if data else '{}'}")
    except Exception:
        logger.debug(f"TRACE: {event} (serialization failed)")

def trace(logger: logging.Logger, event: str, data: Optional[dict] = None) -> None:
    """Log structured trace event for AI analysis."""
    import json
    try:
        payload = {"event": event}
        if data:
            payload.update(data)
        serialized = json.dumps(payload, ensure_ascii=False)
        logger.debug(f"[TRACE] {serialized}")
    except Exception:
        logger.debug(f"[TRACE] {event} (serialization failed)")


def get_log_files_info() -> dict:
    """Get information about log files."""
    info = {
        "logs_dir": str(LOGS_DIR),
        "files": {}
    }
    
    for log_file in [CLI_LOG_FILE, ERROR_LOG_FILE, DEBUG_LOG_FILE]:
        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            info["files"][log_file.name] = {
                "path": str(log_file),
                "size_mb": round(size_mb, 2),
                "exists": True
            }
        else:
            info["files"][log_file.name] = {
                "path": str(log_file),
                "exists": False
            }
    
    return info


# Initialize default logger on module import
_default_logger = setup_logging(verbose=False)


def setup_root_file_logging(root_dir: str) -> None:
    """Setup logging to root directory files (Left/Right screens)."""
    logs_dir = Path(root_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Analysis Handler (Shared)
    analysis_handler = None
    try:
        analysis_log_path = logs_dir / "atlas_analysis.jsonl"
        analysis_handler = logging.handlers.RotatingFileHandler(
            analysis_log_path,
            maxBytes=50 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        analysis_handler.setLevel(logging.DEBUG)
        analysis_handler.setFormatter(JSONFormatter())
    except Exception as e:
        print(f"Failed to setup analysis log handler: {e}", file=sys.stderr)

    # Left Screen Logger (Main Logs)
    left_logger = logging.getLogger("system_cli.left")
    left_logger.setLevel(logging.DEBUG)
    left_logger.propagate = False
    
    try:
        left_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "left_screen.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        left_handler.setFormatter(logging.Formatter(LOG_FORMAT_SIMPLE, datefmt=DATE_FORMAT))
        left_logger.addHandler(left_handler)
        if analysis_handler:
            left_logger.addHandler(analysis_handler)
    except Exception as e:
        print(f"Failed to setup left screen log: {e}", file=sys.stderr)

    # Right Screen Logger (Agent Messages)
    right_logger = logging.getLogger("system_cli.right")
    right_logger.setLevel(logging.DEBUG)
    right_logger.propagate = False

    try:
        right_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "right_screen.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        right_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt=DATE_FORMAT))
        right_logger.addHandler(right_handler)
        if analysis_handler:
            right_logger.addHandler(analysis_handler)
    except Exception as e:
        print(f"Failed to setup right screen log: {e}", file=sys.stderr)
