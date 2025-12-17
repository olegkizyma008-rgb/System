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
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
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
        error_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(error_handler)
    except Exception as e:
        print(f"Failed to setup error log file: {e}", file=sys.stderr)
    
    # 3. Debug log file (debug messages only, for detailed troubleshooting)
    try:
        debug_handler = logging.handlers.RotatingFileHandler(
            DEBUG_LOG_FILE,
            maxBytes=20 * 1024 * 1024,  # 20 MB
            backupCount=3,
            encoding="utf-8"
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(debug_handler)
    except Exception as e:
        print(f"Failed to setup debug log file: {e}", file=sys.stderr)
    
    # 4. Memory handler (for TUI display)
    _memory_handler.setLevel(logging.DEBUG)
    _memory_handler.setFormatter(logging.Formatter(LOG_FORMAT_SIMPLE, datefmt=DATE_FORMAT))
    logger.addHandler(_memory_handler)
    
    # 5. Console handler (if verbose)
    if verbose:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT_SIMPLE, datefmt=DATE_FORMAT))
        logger.addHandler(console_handler)
    
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
