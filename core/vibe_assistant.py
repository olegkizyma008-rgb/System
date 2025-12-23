"""
Vibe CLI Assistant - Human-in-the-loop intervention system for Trinity Runtime.

This module handles communication between Trinity agents and human operators
when automatic resolution fails or critical issues are detected.
"""

from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime

class VibeCLIAssistant:
    """
    Vibe CLI Assistant handles human intervention requests from Trinity agents.
    
    Responsibilities:
    - Display pause messages to users
    - Collect user input for resolution
    - Provide context about current issues
    - Maintain intervention history
    """
    
    def __init__(self, name: str = "Doctor Vibe"):
        self.name = name
        self.intervention_history: List[Dict[str, Any]] = []
        self.current_pause_context: Optional[Dict[str, Any]] = None
        # Optional callback to publish live updates (runtime/TUI can subscribe)
        self._on_update: Optional[callable] = None
        
        # Auto-repair integration
        self.auto_repair_enabled: bool = True
        self._self_healer = None  # Set by Trinity runtime
        self._on_repair_complete: Optional[callable] = None
    
    def handle_pause_request(self, pause_context: Dict[str, Any]) -> None:
        """
        Handle a pause request from Trinity agents.
        
        Args:
            pause_context: Context about why the pause was requested
        """
        self.current_pause_context = pause_context
        
        # Add to intervention history
        intervention_record = {
            "timestamp": datetime.now().isoformat(),
            "reason": pause_context.get("reason", "unknown"),
            "message": pause_context.get("message", ""),
            "status": "active"
        }
        self.intervention_history.append(intervention_record)
        
        # Initialize live output buffer on pause context
        try:
            if isinstance(self.current_pause_context, dict) and "live_output" not in self.current_pause_context:
                self.current_pause_context["live_output"] = []
        except Exception:
            pass

        # Publish initial pause summary and print for interactive CLI
        self._publish_update(f"PAUSE CREATED: {pause_context.get('message', '')}")
        self._display_pause_message(pause_context)

    def set_update_callback(self, cb: callable) -> None:
        """Set a callback to receive live updates from the Vibe assistant.

        The callback is called with a single string argument describing the
        latest update. The runtime/TUI can use this to stream output live.
        """
        self._on_update = cb

    def _publish_update(self, message: str) -> None:
        """Publish a short live update and append it to the current pause context."""
        try:
            # Append to per-pause live output buffer
            if isinstance(self.current_pause_context, dict):
                buf = self.current_pause_context.setdefault("live_output", [])
                buf.append(f"{datetime.now().isoformat()} - {message}")
                # Keep buffer reasonably small
                if len(buf) > 200:
                    del buf[:-200]
        except Exception:
            pass

        # Call runtime/TUI callback if provided
        try:
            if self._on_update:
                self._on_update(message)
        except Exception:
            pass
    
    def _display_pause_message(self, pause_context: Dict[str, Any]) -> None:
        """Display pause message to the user."""
        print("\n" + "="*60)
        print(f"🚨 {self.name}: ВИКОНАННЯ ЗАВДАННЯ ПРИПИНЕНО")
        print("="*60)
        print(f"Причина: {pause_context.get('reason', 'невідома')}")
        print(f"Повідомлення: {pause_context.get('message', 'немає повідомлення')}")
        
        if pause_context.get('suggested_action'):
            print(f"Рекомендовані дії: {pause_context.get('suggested_action')}")
        
        if pause_context.get('issues'):
            print("\n🔍 Виявлені критичні помилки:")
            for i, issue in enumerate(pause_context['issues'], 1):
                if not isinstance(issue, dict):
                    print(f"  {i}. [Невідома помилка - некоректний формат]")
                    continue
                issue_type = issue.get('type', 'unknown')
                issue_file = issue.get('file', 'unknown')
                issue_line = issue.get('line', '?')
                issue_severity = issue.get('severity', 'unknown')
                issue_message = issue.get('message', 'no message')[:80]
                
                print(f"  {i}. {issue_type} в {issue_file}:{issue_line}")
                print(f"     Серйозність: {issue_severity}")
                print(f"     Повідомлення: {issue_message}...")
        
        # Diagnostics: diffs, files, stack traces (if available)
        diagnostics = pause_context.get('diagnostics') or {}
        if diagnostics:
            print("\n🔍 Діагностика:")
            files = diagnostics.get('files') or []
            if files:
                print(f"  Файли: {', '.join(files[:10])}{'...' if len(files)>10 else ''}")

            diffs = diagnostics.get('diffs') or []
            if diffs:
                print("  Diff preview:")
                for d in diffs[:2]:
                    fname = d.get('file') or '<unknown>'
                    diff_text = d.get('diff') or ''
                    # show up to first 6 lines of diff preview
                    preview_lines = '\n'.join((diff_text or '').splitlines()[:6])
                    print(f"  --- {fname} ---")
                    for l in preview_lines.splitlines():
                        print(f"    {l}")
                    if len((diff_text or '').splitlines()) > 6:
                        print("    ...diff truncated...")

            stack = diagnostics.get('stack_trace')
            if stack:
                print("  Stack trace (tail):")
                tail = '\n'.join(str(stack).splitlines()[-6:])
                for l in tail.splitlines():
                    print(f"    {l}")

        print("\n💡 Doctor Vibe рекомендує:")
        print("   - Перевірте виявлені помилки")
        print("   - Виправте проблеми в коді або конфігурації")
        print("   - Переконайтеся, що всі залежності встановлено")
        print("   - Використовуйте /continue після виправлення")
        
        print("\n📝 Доступні команди:")
        print("   - /continue  - Продовжити виконання після виправлення")
        print("   - /cancel    - Скасувати поточне завдання")
        print("   - /help      - Показати додаткову інформацію")
        print("="*60 + "\n")

        # Also publish a short live message for CLI/TUI
        try:
            self._publish_update(f"Displayed pause: {pause_context.get('reason', '')} - {pause_context.get('message', '')}")
        except Exception:
            pass
    
    def handle_user_command(self, command: str) -> Dict[str, Any]:
        """
        Handle user commands during pause state.
        
        Args:
            command: User input command
            
        Returns:
            Dict with action result
        """
        command = command.strip().lower()
        
        if command == "/continue":
            return self._handle_continue_command()
        elif command == "/cancel":
            return self._handle_cancel_command()
        elif command == "/help":
            return self._handle_help_command()
        else:
            return {
                "action": "invalid",
                "message": f"Невідома команда: {command}. Будь ласка, використовуйте /continue, /cancel або /help"
            }
    
    def _handle_continue_command(self) -> Dict[str, Any]:
        """Handle continue command from user."""
        if not self.current_pause_context:
            return {
                "action": "error",
                "message": "Немає активної паузи для продовження"
            }
        
        # Update intervention history
        for record in self.intervention_history:
            if record["status"] == "active":
                record["status"] = "resolved"
                record["resolved_at"] = datetime.now().isoformat()
                record["resolution"] = "user_continue"
                break
        
        # Publish continue and clear current pause context
        pause_context = self.current_pause_context
        try:
            self._publish_update("User issued /continue - resuming execution")
        except Exception:
            pass
        self.current_pause_context = None
        
        return {
            "action": "resume",
            "message": f"{self.name}: Продовження виконання після виправлення проблем",
            "original_context": pause_context
        }
    
    def _handle_cancel_command(self) -> Dict[str, Any]:
        """Handle cancel command from user."""
        if not self.current_pause_context:
            return {
                "action": "error",
                "message": "Немає активної паузи для скасування"
            }
        
        # Update intervention history
        for record in self.intervention_history:
            if record["status"] == "active":
                record["status"] = "cancelled"
                record["resolved_at"] = datetime.now().isoformat()
                record["resolution"] = "user_cancel"
                break
        
        # Publish cancel and clear current pause context
        pause_context = self.current_pause_context
        try:
            self._publish_update("User issued /cancel - task cancelled")
        except Exception:
            pass
        self.current_pause_context = None
        
        return {
            "action": "cancel",
            "message": f"{self.name}: Завдання скасовано користувачем",
            "original_context": pause_context
        }
    
    def _handle_help_command(self) -> Dict[str, Any]:
        """Handle help command from user."""
        help_message = f"""
📖 {self.name} - Довідка по командам:

🟢 /continue  - Продовжити виконання завдання після виправлення проблем
🔴 /cancel    - Скасувати поточне завдання
💡 /help      - Показати цю довідку

💻 Поради по виправленню помилок:
1. Перевірте виявлені критичні помилки
2. Виправте проблеми в коді або конфігурації
3. Переконайтеся, що всі залежності встановлено
4. Перевірте права доступу до файлів
5. Використовуйте /continue після виправлення

🎨 Рекомендована тема: hacker-vibe
   Використовуйте ./cli.sh --theme hacker-vibe для найкращого досвіду!
"""
        
        print(help_message)
        
        return {
            "action": "help_shown",
            "message": "Довідка показана користувачу"
        }
    
    def get_intervention_history(self) -> List[Dict[str, Any]]:
        """Get the history of interventions."""
        return self.intervention_history
    
    def get_current_pause_status(self) -> Optional[Dict[str, Any]]:
        """Get the current pause status."""
        return self.current_pause_context
    
    def clear_pause_state(self) -> None:
        """Clear the current pause state."""
        self.current_pause_context = None
    
    # =========================================================================
    # AUTO-REPAIR INTEGRATION
    # =========================================================================
    
    def set_self_healer(self, self_healer, on_repair_complete: Optional[callable] = None) -> None:
        """
        Set the self-healer reference and optional callback.
        
        Args:
            self_healer: CodeSelfHealer instance from Trinity
            on_repair_complete: Optional callback when repair completes
        """
        self._self_healer = self_healer
        self._on_repair_complete = on_repair_complete
    
    def attempt_auto_repair(self, issue_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt automatic repair using self-healing module.
        
        This method is called by Trinity router when a pause is detected
        and auto_repair_enabled is True.
        
        Args:
            issue_context: Context about the issue (from pause_context)
            
        Returns:
            Dict with repair result: {"success": bool, "message": str, "action": str}
        """
        if not self.auto_repair_enabled:
            return {
                "success": False,
                "message": "Auto-repair is disabled",
                "action": "wait_for_human"
            }
        
        if not self._self_healer:
            return {
                "success": False,
                "message": "Self-healer not configured",
                "action": "wait_for_human"
            }
        
        try:
            print(f"\n🔧 {self.name}: Спроба автоматичного виправлення...")
            
            # Extract error info from issue context
            error_message = issue_context.get("message", "")
            issues = issue_context.get("issues", [])
            
            # If we have structured issues, try to repair them
            repairs_attempted = 0
            repairs_successful = 0
            
            if issues:
                for issue_dict in issues[:3]:  # Limit to 3 repairs per attempt
                    # Convert dict back to CodeIssue if needed
                    repair_result = self._self_healer.quick_repair(
                        error_type=issue_dict.get("type", "unknown"),
                        file_path=issue_dict.get("file", ""),
                        message=issue_dict.get("message", ""),
                        line_number=issue_dict.get("line")
                    )
                    repairs_attempted += 1
                    if repair_result:
                        repairs_successful += 1
            else:
                # Try quick repair based on error message
                repair_result = self._self_healer.quick_repair_from_message(error_message)
                repairs_attempted = 1
                if repair_result:
                    repairs_successful = 1
            
            if repairs_successful > 0:
                print(f"✅ {self.name}: Виправлено {repairs_successful}/{repairs_attempted} помилок")
                
                # Call callback if set
                if self._on_repair_complete:
                    self._on_repair_complete({
                        "success": True,
                        "repairs_attempted": repairs_attempted,
                        "repairs_successful": repairs_successful
                    })
                
                # Update intervention history
                for record in self.intervention_history:
                    if record["status"] == "active":
                        record["status"] = "auto_repaired"
                        record["resolved_at"] = datetime.now().isoformat()
                        record["resolution"] = f"auto_repair: {repairs_successful} fixes"
                        break
                
                # Clear pause context - system can resume
                self.current_pause_context = None
                
                return {
                    "success": True,
                    "message": f"Auto-repair successful: {repairs_successful}/{repairs_attempted} fixes applied",
                    "action": "resume"
                }
            else:
                print(f"⚠️ {self.name}: Автоматичне виправлення не вдалося. Потрібне ручне втручання.")
                return {
                    "success": False,
                    "message": "Auto-repair failed - manual intervention required",
                    "action": "wait_for_human"
                }
                
        except Exception as e:
            print(f"❌ {self.name}: Помилка при автовиправленні: {e}")
            return {
                "success": False,
                "message": f"Auto-repair error: {str(e)}",
                "action": "wait_for_human"
            }
    
    def should_attempt_auto_repair(self, pause_context: Dict[str, Any]) -> bool:
        """
        Determine if auto-repair should be attempted for this pause context.
        
        Args:
            pause_context: The pause context to evaluate
            
        Returns:
            True if auto-repair should be attempted
        """
        if not self.auto_repair_enabled or not self._self_healer:
            return False
        
        reason = pause_context.get("reason", "")
        
        # Auto-repair is suitable for these reasons
        auto_repairable_reasons = {
            "critical_issues_detected",
            "repeated_failures", 
            "planning_failure",
            "runtime_error",
            "syntax_error",
            "import_error"
        }
        
        # Check if auto-resume is available (set by Trinity)
        auto_resume = pause_context.get("auto_resume_available", False)
        
        return reason in auto_repairable_reasons or auto_resume