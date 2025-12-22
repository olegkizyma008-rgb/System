"""Agent Delegation System for Trinity.

This module manages delegation between Doctor Vibe and Tetyana:
- Doctor Vibe: Primary agent for DEV tasks and code operations
- Tetyana: Fallback agent for operations requiring elevated permissions

When Doctor Vibe encounters permission issues, he can delegate to Tetyana.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import os
import logging

logger = logging.getLogger("system_cli.delegation")


class DelegationReason(Enum):
    """Reasons for delegating from Doctor Vibe to Tetyana."""
    PERMISSION_DENIED = "permission_denied"
    ACCESS_DENIED = "access_denied"
    OPERATION_NOT_PERMITTED = "operation_not_permitted"
    REQUIRES_SUDO = "requires_sudo"
    FILE_LOCKED = "file_locked"
    RESOURCE_BUSY = "resource_busy"


class AgentRole(Enum):
    """Agent roles in Trinity system."""
    DOCTOR_VIBE = "doctor_vibe"  # Primary DEV agent
    TETYANA = "tetyana"          # Executor/fallback agent
    ATLAS = "atlas"              # Planner agent
    GRISHA = "grisha"            # Verifier agent


class DelegationRequest:
    """Request to delegate task from one agent to another."""
    
    def __init__(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        reason: DelegationReason,
        task_description: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.reason = reason
        self.task_description = task_description
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.error_message = error_message
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_agent.value,
            "to": self.to_agent.value,
            "reason": self.reason.value,
            "task": self.task_description,
            "tool": self.tool_name,
            "args": self.tool_args,
            "error": self.error_message,
            "context": self.context
        }


class DelegationManager:
    """Manages task delegation between agents."""
    
    # Permission-related error patterns
    PERMISSION_PATTERNS = [
        "permission denied",
        "access denied",
        "operation not permitted",
        "requires sudo",
        "requires elevated",
        "requires administrator",
        "file is locked",
        "resource busy",
        "cannot access",
        "not allowed",
        "доступ заборонено",
        "потрібні права",
        "файл заблоковано"
    ]
    
    # Tools that Tetyana can handle better (require system access)
    TETYANA_PREFERRED_TOOLS = {
        "run_shell",
        "run_applescript",
        "open_app",
        "kill_process",
        "system_cleanup_stealth",
        "system_cleanup_windsurf",
        "system_spoof_hardware",
        "click_mouse",
        "type_text",
        "press_key",
        "move_mouse"
    }
    
    def __init__(self):
        self.delegation_history: List[DelegationRequest] = []
        self.vibe_enabled = self._is_vibe_enabled()
    
    @staticmethod
    def _is_vibe_enabled() -> bool:
        """Check if Doctor Vibe is enabled."""
        return str(os.environ.get("TRINITY_DEV_BY_VIBE") or "").strip().lower() in {"1", "true", "yes", "on"}
    
    def should_delegate_to_tetyana(
        self,
        tool_name: str,
        error_result: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[DelegationReason]]:
        """
        Determine if Doctor Vibe should delegate to Tetyana.
        
        Args:
            tool_name: Name of the tool being executed
            error_result: Optional error result from tool execution
            
        Returns:
            Tuple of (should_delegate, reason)
        """
        # If Doctor Vibe is not enabled, no delegation needed
        if not self.vibe_enabled:
            return False, None
        
        # Check if tool execution failed with permission error
        if error_result and error_result.get("status") == "error":
            error_msg = str(error_result.get("error", "")).lower()
            
            for pattern in self.PERMISSION_PATTERNS:
                if pattern in error_msg:
                    # Determine specific reason
                    if "permission denied" in error_msg or "доступ заборонено" in error_msg:
                        return True, DelegationReason.PERMISSION_DENIED
                    elif "access denied" in error_msg:
                        return True, DelegationReason.ACCESS_DENIED
                    elif "not permitted" in error_msg:
                        return True, DelegationReason.OPERATION_NOT_PERMITTED
                    elif "sudo" in error_msg or "elevated" in error_msg:
                        return True, DelegationReason.REQUIRES_SUDO
                    elif "locked" in error_msg or "заблоковано" in error_msg:
                        return True, DelegationReason.FILE_LOCKED
                    elif "busy" in error_msg:
                        return True, DelegationReason.RESOURCE_BUSY
                    else:
                        return True, DelegationReason.PERMISSION_DENIED
        
        # Check if tool is better handled by Tetyana (system operations)
        if tool_name in self.TETYANA_PREFERRED_TOOLS:
            # Only delegate if it's a system-critical operation
            # Doctor Vibe can still try first, but Tetyana is preferred
            return False, None  # Let Doctor Vibe try first
        
        return False, None
    
    def create_delegation_request(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        reason: DelegationReason,
        error_message: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> DelegationRequest:
        """
        Create a delegation request from Doctor Vibe to Tetyana.
        
        Args:
            tool_name: Tool that failed for Doctor Vibe
            tool_args: Arguments for the tool
            reason: Reason for delegation
            error_message: Error message from failed attempt
            task_description: Human-readable task description
            
        Returns:
            DelegationRequest object
        """
        if not task_description:
            task_description = f"Execute {tool_name} with elevated permissions"
        
        request = DelegationRequest(
            from_agent=AgentRole.DOCTOR_VIBE,
            to_agent=AgentRole.TETYANA,
            reason=reason,
            task_description=task_description,
            tool_name=tool_name,
            tool_args=tool_args,
            error_message=error_message,
            context={
                "vibe_enabled": self.vibe_enabled,
                "original_attempt": True
            }
        )
        
        self.delegation_history.append(request)
        logger.info(f"[Delegation] Doctor Vibe → Tetyana: {tool_name} (reason: {reason.value})")
        
        return request
    
    def format_delegation_message(self, request: DelegationRequest) -> str:
        """
        Format delegation request message for Tetyana.
        
        Args:
            request: Delegation request
            
        Returns:
            Formatted message for Tetyana
        """
        reason_text = {
            DelegationReason.PERMISSION_DENIED: "недостатньо прав доступу",
            DelegationReason.ACCESS_DENIED: "доступ заборонено",
            DelegationReason.OPERATION_NOT_PERMITTED: "операція не дозволена",
            DelegationReason.REQUIRES_SUDO: "потрібні права адміністратора",
            DelegationReason.FILE_LOCKED: "файл заблоковано",
            DelegationReason.RESOURCE_BUSY: "ресурс зайнятий"
        }
        
        reason_uk = reason_text.get(request.reason, "технічні проблеми")
        
        msg = f"""[DELEGATION FROM DOCTOR VIBE]

Doctor Vibe не зміг виконати операцію через {reason_uk}.

Завдання: {request.task_description}
Інструмент: {request.tool_name}
Аргументи: {request.tool_args}
"""
        
        if request.error_message:
            msg += f"\nПомилка: {request.error_message}"
        
        msg += """

Tetyana, будь ласка, виконай цю операцію з підвищеними правами.
Doctor Vibe потім продовжить розробку після успішного виконання.
"""
        
        return msg
    
    def get_delegation_stats(self) -> Dict[str, Any]:
        """Get statistics about delegation requests."""
        total = len(self.delegation_history)
        if total == 0:
            return {
                "total_delegations": 0,
                "by_reason": {},
                "by_tool": {}
            }
        
        by_reason = {}
        by_tool = {}
        
        for request in self.delegation_history:
            reason = request.reason.value
            tool = request.tool_name
            
            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_tool[tool] = by_tool.get(tool, 0) + 1
        
        return {
            "total_delegations": total,
            "by_reason": by_reason,
            "by_tool": by_tool,
            "vibe_enabled": self.vibe_enabled
        }


# Global delegation manager instance
delegation_manager = DelegationManager()


def should_delegate_to_tetyana(
    tool_name: str,
    error_result: Optional[Dict[str, Any]] = None
) -> tuple[bool, Optional[DelegationReason]]:
    """
    Check if Doctor Vibe should delegate to Tetyana.
    
    Convenience function that uses global delegation manager.
    """
    return delegation_manager.should_delegate_to_tetyana(tool_name, error_result)


def create_tetyana_delegation(
    tool_name: str,
    tool_args: Dict[str, Any],
    reason: DelegationReason,
    error_message: Optional[str] = None,
    task_description: Optional[str] = None
) -> str:
    """
    Create delegation request and return formatted message for Tetyana.
    
    Convenience function that uses global delegation manager.
    """
    request = delegation_manager.create_delegation_request(
        tool_name=tool_name,
        tool_args=tool_args,
        reason=reason,
        error_message=error_message,
        task_description=task_description
    )
    return delegation_manager.format_delegation_message(request)
