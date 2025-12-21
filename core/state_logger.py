"""State initialization logger for Trinity system diagnostics."""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class StateInitLogger:
    """Logger for Trinity state initialization diagnostics."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize the state logger."""
        self.logger = logging.getLogger("trinity.state_init")
        
        # Create logs directory in project root (or use ~/.system_cli as fallback)
        project_root = Path(__file__).parent.parent
        log_dir = project_root / "logs"
        
        # Fallback to home directory if project root not accessible
        if not log_dir.parent.exists():
            log_dir = Path.home() / ".system_cli" / "logs"
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up file handler
        if log_file is None:
            log_file = log_dir / f"trinity_state_{datetime.now().strftime('%Y%m%d')}.log"
        
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)
        
        # Format with detailed info
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)

        # Add Analysis JSONL Handler (Atlas Analysis)
        try:
            analysis_log = log_dir / "atlas_analysis.jsonl"
            # Use RotatingFileHandler if available, else FileHandler
            # But we don't want to import logging.handlers if not needed, though it is standard.
            import logging.handlers
            json_handler = logging.handlers.RotatingFileHandler(
                analysis_log,
                maxBytes=50 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8"
            )
            json_handler.setLevel(logging.DEBUG)
            
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
                    }
                    return json.dumps(log_obj, ensure_ascii=False)
            
            json_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(json_handler)
        except Exception:
            pass # Fail silently if we can't set up analysis log

        self.logger.setLevel(logging.DEBUG)

    def log_initial_state(self, task: str, state: Dict[str, Any]) -> None:
        """Log the initial state creation."""
        self.logger.info("=" * 80)
        self.logger.info("TRINITY STATE INITIALIZATION")
        self.logger.info(f"Task: {task[:100]}...")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info("-" * 80)
        
        # Log key fields
        self.logger.debug(f"initial_agent: {state.get('current_agent')}")
        self.logger.debug(f"task_type: {state.get('task_type')}")
        self.logger.debug(f"is_dev: {state.get('is_dev')}")
        self.logger.debug(f"execution_mode: {state.get('execution_mode')}")
        self.logger.debug(f"gui_mode: {state.get('gui_mode')}")
        
        # Log meta_config
        meta = state.get('meta_config', {})
        self.logger.debug(f"meta_config.strategy: {meta.get('strategy')}")
        self.logger.debug(f"meta_config.verification_rigor: {meta.get('verification_rigor')}")
        self.logger.debug(f"meta_config.recovery_mode: {meta.get('recovery_mode')}")

    def log_state_transition(
        self,
        from_agent: str,
        to_agent: str,
        step_count: int,
        last_status: str,
        reason: Optional[str] = None
    ) -> None:
        """Log a state transition between agents."""
        self.logger.info(f"TRANSITION: {from_agent} -> {to_agent} (step {step_count}, status: {last_status})")
        if reason:
            self.logger.debug(f"  Reason: {reason}")

    def log_meta_config_update(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Log meta_config changes."""
        self.logger.debug("META_CONFIG UPDATE:")
        for key in set(list(old_config.keys()) + list(new_config.keys())):
            old_val = old_config.get(key)
            new_val = new_config.get(key)
            if old_val != new_val:
                self.logger.debug(f"  {key}: {old_val} -> {new_val}")

    def log_state_validation(self, state: Dict[str, Any], is_valid: bool, errors: Optional[list] = None) -> None:
        """Log state validation results."""
        if is_valid:
            self.logger.debug("✓ State validation PASSED")
        else:
            self.logger.warning("✗ State validation FAILED")
            if errors:
                for error in errors:
                    self.logger.error(f"  - {error}")

    def log_plan_execution(
        self,
        step_num: int,
        description: str,
        status: str,
        details: Optional[str] = None
    ) -> None:
        """Log plan step execution."""
        self.logger.info(f"PLAN STEP [{step_num}] {status}: {description}")
        if details:
            self.logger.debug(f"  Details: {details}")

    def log_error(self, context: str, error: Exception, state_snapshot: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with context."""
        self.logger.error(f"ERROR in {context}: {type(error).__name__}: {str(error)}")
        
        if state_snapshot:
            self.logger.debug("State snapshot at error:")
            safe_snapshot = {
                k: str(v)[:200] if isinstance(v, str) else v 
                for k, v in state_snapshot.items()
            }
            self.logger.debug(json.dumps(safe_snapshot, indent=2, default=str))

    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        self.logger.info("PERFORMANCE METRICS:")
        for key, value in metrics.items():
            self.logger.info(f"  {key}: {value}")


# Global instance
_state_logger: Optional[StateInitLogger] = None


def get_state_logger() -> StateInitLogger:
    """Get or create the global state logger."""
    global _state_logger
    if _state_logger is None:
        _state_logger = StateInitLogger()
    return _state_logger


def log_initial_state(task: str, state: Dict[str, Any]) -> None:
    """Convenience function to log initial state."""
    get_state_logger().log_initial_state(task, state)


def log_state_transition(
    from_agent: str,
    to_agent: str,
    step_count: int,
    last_status: str,
    reason: Optional[str] = None
) -> None:
    """Convenience function to log state transition."""
    get_state_logger().log_state_transition(from_agent, to_agent, step_count, last_status, reason)
