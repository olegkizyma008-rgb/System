"""Self-Healing Code Module for Trinity Runtime.

This module provides automatic code analysis, error detection, and self-repair
capabilities through Trinity's planning and execution pipeline.

Key capabilities:
- Code structure analysis via project_structure_final.txt
- Error detection from logs (exceptions, import errors, JSON parse failures)
- Self-repair planning through Trinity (using Atlas for fixes)
- Verification loop to confirm fixes and prevent regression
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class IssueType(Enum):
    """Types of code issues that can be detected."""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"
    JSON_PARSE_ERROR = "json_parse_error"
    MISSING_MODULE = "missing_module"
    TYPE_ERROR = "type_error"
    INDENTATION_ERROR = "indentation_error"
    ATTRIBUTE_ERROR = "attribute_error"
    KEY_ERROR = "key_error"
    LOGIC_ERROR = "logic_error"


class IssueSeverity(Enum):
    """Severity levels for code issues."""
    CRITICAL = "critical"  # System cannot function
    HIGH = "high"          # Major feature broken
    MEDIUM = "medium"      # Partial functionality affected
    LOW = "low"            # Minor issue, workaround exists


@dataclass
class CodeIssue:
    """Represents a detected code issue."""
    issue_type: IssueType
    severity: IssueSeverity
    file_path: str
    line_number: Optional[int] = None
    message: str = ""
    stack_trace: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.issue_type.value,
            "severity": self.severity.value,
            "file": self.file_path,
            "line": self.line_number,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class RepairAction:
    """Represents a single repair action."""
    action_type: str  # "edit", "create", "delete", "run_command"
    target_file: str
    description: str
    content: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


@dataclass
class RepairPlan:
    """A plan to fix one or more code issues."""
    issue: CodeIssue
    actions: List[RepairAction] = field(default_factory=list)
    estimated_risk: str = "low"  # low, medium, high
    requires_backup: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class CodeSelfHealer:
    """
    Self-healing module that monitors and repairs code through Trinity.
    
    Architecture:
    1. Analyze structure via project_structure_final.txt
    2. Monitor logs for error patterns
    3. Generate repair plans via LLM
    4. Execute repairs through Trinity's tool chain
    5. Verify fixes through testing/linting
    """
    
    # Error patterns to detect in logs
    ERROR_PATTERNS = [
        # Python exceptions
        (r"^(\w+Error): (.+)$", IssueType.RUNTIME_ERROR),
        (r"SyntaxError: (.+)", IssueType.SYNTAX_ERROR),
        (r"IndentationError: (.+)", IssueType.INDENTATION_ERROR),
        (r"ImportError: (.+)", IssueType.IMPORT_ERROR),
        (r"ModuleNotFoundError: (.+)", IssueType.MISSING_MODULE),
        (r"TypeError: (.+)", IssueType.TYPE_ERROR),
        (r"AttributeError: (.+)", IssueType.ATTRIBUTE_ERROR),
        (r"KeyError: (.+)", IssueType.KEY_ERROR),
        # JSON parse errors
        (r"json\.decoder\.JSONDecodeError: (.+)", IssueType.JSON_PARSE_ERROR),
        (r"JSONDecodeError: (.+)", IssueType.JSON_PARSE_ERROR),
        (r"\[.*\] LLM JSON parsing.*error: (.+)", IssueType.JSON_PARSE_ERROR),
        # File/path related
        (r"File \"([^\"]+)\", line (\d+)", None),  # Stack trace pattern
    ]
    
    # Critical files that need extra care
    CRITICAL_FILES = {
        "core/trinity.py",
        "core/agents/atlas.py",
        "core/agents/tetyana.py",
        "core/agents/grisha.py",
        "core/verification.py",
        "core/mcp.py",
    }
    
    def __init__(
        self,
        project_root: Optional[str] = None,
        log_path: Optional[str] = None,
        on_stream: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialize the self-healing module.
        
        Args:
            project_root: Root directory of the project (defaults to git root)
            log_path: Path to log file to monitor (defaults to logs/cli.log)
            on_stream: Optional callback for streaming status updates
        """
        self.project_root = project_root or self._get_git_root()
        self.log_path = log_path or os.path.join(self.project_root, "logs", "cli.log")
        self.structure_path = os.path.join(self.project_root, "project_structure_final.txt")
        self.on_stream = on_stream
        self.logger = logging.getLogger("system_cli.self_healer")
        
        # Issue tracking
        self.detected_issues: List[CodeIssue] = []
        self.repair_history: List[Tuple[CodeIssue, RepairPlan, bool]] = []
        self._last_log_position = 0
        
        # Trinity runtime reference (set externally)
        self._trinity_runtime = None
    
    def set_trinity_runtime(self, runtime) -> None:
        """Set the Trinity runtime for executing repairs."""
        self._trinity_runtime = runtime
    
    def _get_git_root(self) -> str:
        """Get the git repository root."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return os.getcwd()
    
    def _stream(self, message: str, level: str = "info") -> None:
        """Stream a status message."""
        if self.on_stream:
            try:
                self.on_stream(message, level)
            except Exception:
                pass
        self.logger.log(
            getattr(logging, level.upper(), logging.INFO),
            message
        )
    
    # =========================================================================
    # STRUCTURE ANALYSIS
    # =========================================================================
    
    def analyze_structure(self) -> Dict[str, Any]:
        """
        Parse project_structure_final.txt to get file inventory.
        
        Returns:
            Dict with file lists, directories, and metadata
        """
        structure = {
            "files": [],
            "directories": [],
            "python_files": [],
            "config_files": [],
            "test_files": [],
            "metadata": {},
        }
        
        if not os.path.exists(self.structure_path):
            self._stream(f"Structure file not found: {self.structure_path}", "warning")
            return structure
        
        try:
            with open(self.structure_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract metadata section
            metadata_match = re.search(r"## Metadata\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
            if metadata_match:
                for line in metadata_match.group(1).strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        structure["metadata"][key.strip()] = val.strip()
            
            # Parse tree structure
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Extract filename from tree chars
                match = re.search(r"[├└─│\s]+(.+)", line)
                if match:
                    item = match.group(1).strip()
                    if not item:
                        continue
                    
                    if "/" in item or item.endswith(os.sep):
                        structure["directories"].append(item.rstrip("/"))
                    else:
                        structure["files"].append(item)
                        if item.endswith(".py"):
                            structure["python_files"].append(item)
                        if item.endswith((".json", ".yaml", ".yml", ".toml", ".ini")):
                            structure["config_files"].append(item)
                        if item.startswith("test_") or "_test.py" in item:
                            structure["test_files"].append(item)
            
            self._stream(f"Analyzed structure: {len(structure['files'])} files, {len(structure['directories'])} dirs")
            
        except Exception as e:
            self._stream(f"Error parsing structure: {e}", "error")
        
        return structure
    
    def get_file_content(self, relative_path: str) -> Optional[str]:
        """Read file content by relative path."""
        full_path = os.path.join(self.project_root, relative_path)
        try:
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            self._stream(f"Error reading {relative_path}: {e}", "error")
        return None
    
    # =========================================================================
    # ERROR DETECTION
    # =========================================================================
    
    def detect_errors(self, max_lines: int = 1000) -> List[CodeIssue]:
        """
        Scan log file for error patterns.
        
        Args:
            max_lines: Maximum lines to read from end of log
            
        Returns:
            List of detected CodeIssue objects
        """
        issues: List[CodeIssue] = []
        
        if not os.path.exists(self.log_path):
            self._stream(f"Log file not found: {self.log_path}", "warning")
            return issues
        
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                # Seek to last known position or read from end
                f.seek(self._last_log_position)
                lines = f.readlines()
                self._last_log_position = f.tell()
            
            if not lines:
                return issues
            
            # Take last N lines if too many
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
            
            # Process lines looking for error patterns
            current_stack: List[str] = []
            current_file: Optional[str] = None
            current_line: Optional[int] = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for file/line in stack trace
                file_match = re.search(r'File "([^"]+)", line (\d+)', line)
                if file_match:
                    current_file = file_match.group(1)
                    current_line = int(file_match.group(2))
                    current_stack.append(line)
                    continue
                
                # Check error patterns
                for pattern, issue_type in self.ERROR_PATTERNS:
                    if issue_type is None:
                        continue
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        severity = self._classify_severity(
                            issue_type, current_file, match.group(1) if match.lastindex else ""
                        )
                        issue = CodeIssue(
                            issue_type=issue_type,
                            severity=severity,
                            file_path=current_file or "unknown",
                            line_number=current_line,
                            message=match.group(1) if match.lastindex else line,
                            stack_trace="\n".join(current_stack[-10:]),
                        )
                        issues.append(issue)
                        current_stack = []
                        current_file = None
                        current_line = None
                        break
            
            if issues:
                self._stream(f"Detected {len(issues)} issues from logs")
                self.detected_issues.extend(issues)
            
        except Exception as e:
            self._stream(f"Error scanning logs: {e}", "error")
        
        return issues
    
    def _classify_severity(
        self,
        issue_type: IssueType,
        file_path: Optional[str],
        message: str,
    ) -> IssueSeverity:
        """Classify issue severity based on type and location."""
        # Critical files get higher severity
        if file_path:
            rel_path = file_path.replace(self.project_root + "/", "")
            if rel_path in self.CRITICAL_FILES:
                return IssueSeverity.HIGH
        
        # Syntax/indentation errors are usually critical
        if issue_type in {IssueType.SYNTAX_ERROR, IssueType.INDENTATION_ERROR}:
            return IssueSeverity.CRITICAL
        
        # Import errors can be critical
        if issue_type in {IssueType.IMPORT_ERROR, IssueType.MISSING_MODULE}:
            return IssueSeverity.HIGH
        
        # JSON parse errors are medium (usually recoverable)
        if issue_type == IssueType.JSON_PARSE_ERROR:
            return IssueSeverity.MEDIUM
        
        return IssueSeverity.MEDIUM
    
    # =========================================================================
    # REPAIR PLANNING
    # =========================================================================
    
    def plan_repair(self, issue: CodeIssue) -> Optional[RepairPlan]:
        """
        Generate a repair plan for an issue using Trinity.
        
        Args:
            issue: The CodeIssue to fix
            
        Returns:
            RepairPlan or None if planning failed
        """
        if not self._trinity_runtime:
            self._stream("Trinity runtime not set, cannot plan repair", "error")
            return None
        
        self._stream(f"Planning repair for {issue.issue_type.value} in {issue.file_path}")
        
        # Build context for LLM
        context = self._build_repair_context(issue)
        if not context:
            return None
        
        # Generate repair prompt
        repair_prompt = self._build_repair_prompt(issue, context)
        
        try:
            # Use Trinity's LLM to generate repair plan
            from langchain_core.messages import HumanMessage, SystemMessage
            
            llm = self._trinity_runtime.verifier.llm if hasattr(self._trinity_runtime, 'verifier') else None
            if not llm:
                self._stream("LLM not available for repair planning", "error")
                return None
            
            response = llm.invoke([
                SystemMessage(content=self._get_repair_system_prompt()),
                HumanMessage(content=repair_prompt),
            ])
            
            # Parse repair plan from response
            plan = self._parse_repair_response(issue, response.content)
            if plan:
                self._stream(f"Generated repair plan with {len(plan.actions)} actions")
            return plan
            
        except Exception as e:
            self._stream(f"Error planning repair: {e}", "error")
            return None
    
    def _build_repair_context(self, issue: CodeIssue) -> Optional[Dict[str, Any]]:
        """Build context for repair planning."""
        context: Dict[str, Any] = {
            "issue": issue.to_dict(),
            "file_content": None,
            "surrounding_code": None,
        }
        
        # Get file content if available
        if issue.file_path and issue.file_path != "unknown":
            rel_path = issue.file_path.replace(self.project_root + "/", "")
            content = self.get_file_content(rel_path)
            if content:
                context["file_content"] = content
                # Get surrounding lines if line number known
                if issue.line_number:
                    lines = content.split("\n")
                    start = max(0, issue.line_number - 10)
                    end = min(len(lines), issue.line_number + 10)
                    context["surrounding_code"] = "\n".join(lines[start:end])
        
        return context
    
    def _get_repair_system_prompt(self) -> str:
        """Get system prompt for repair planning."""
        return """You are a code repair specialist for the Trinity AI system.
Your task is to analyze code issues and generate precise repair actions.

IMPORTANT RULES:
1. Make minimal changes - only fix what's broken
2. Preserve existing functionality
3. Follow the existing code style
4. For critical files, be extra cautious
5. Always include verification steps

Output your repair plan as JSON with this structure:
{
    "analysis": "Brief analysis of the issue",
    "actions": [
        {
            "action_type": "edit|create|delete|run_command",
            "target_file": "path/to/file.py",
            "description": "What this action does",
            "content": "new content or command",
            "start_line": 10,
            "end_line": 15
        }
    ],
    "verification": ["step 1", "step 2"],
    "risk": "low|medium|high"
}"""
    
    def _build_repair_prompt(self, issue: CodeIssue, context: Dict[str, Any]) -> str:
        """Build the repair prompt."""
        parts = [
            f"## Issue to Fix",
            f"Type: {issue.issue_type.value}",
            f"Severity: {issue.severity.value}",
            f"File: {issue.file_path}",
        ]
        
        if issue.line_number:
            parts.append(f"Line: {issue.line_number}")
        
        parts.append(f"Message: {issue.message}")
        
        if issue.stack_trace:
            parts.append(f"\n## Stack Trace\n```\n{issue.stack_trace}\n```")
        
        if context.get("surrounding_code"):
            parts.append(f"\n## Surrounding Code\n```python\n{context['surrounding_code']}\n```")
        
        parts.append("\n## Generate a repair plan as JSON")
        
        return "\n".join(parts)
    
    def _parse_repair_response(self, issue: CodeIssue, response: str) -> Optional[RepairPlan]:
        """Parse LLM response into RepairPlan."""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]+\}", response)
            if not json_match:
                return None
            
            data = json.loads(json_match.group(0))
            
            actions = []
            for action_data in data.get("actions", []):
                action = RepairAction(
                    action_type=action_data.get("action_type", "edit"),
                    target_file=action_data.get("target_file", issue.file_path),
                    description=action_data.get("description", ""),
                    content=action_data.get("content"),
                    start_line=action_data.get("start_line"),
                    end_line=action_data.get("end_line"),
                )
                actions.append(action)
            
            return RepairPlan(
                issue=issue,
                actions=actions,
                estimated_risk=data.get("risk", "medium"),
                requires_backup=data.get("risk", "medium") != "low",
            )
            
        except Exception as e:
            self._stream(f"Error parsing repair response: {e}", "error")
            return None
    
    # =========================================================================
    # REPAIR EXECUTION
    # =========================================================================
    
    def execute_repair(self, plan: RepairPlan) -> bool:
        """
        Execute a repair plan through Trinity.
        
        Args:
            plan: The RepairPlan to execute
            
        Returns:
            True if repair was successful
        """
        if not plan.actions:
            self._stream("No actions in repair plan", "warning")
            return False
        
        if not self._trinity_runtime:
            self._stream("Trinity runtime not set", "error")
            return False
        
        self._stream(f"Executing repair plan ({len(plan.actions)} actions)")
        
        # Create backup if required
        if plan.requires_backup:
            self._create_backup(plan)
        
        success = True
        for i, action in enumerate(plan.actions):
            self._stream(f"Action {i+1}/{len(plan.actions)}: {action.description}")
            try:
                if action.action_type == "edit":
                    success = self._execute_edit_action(action)
                elif action.action_type == "create":
                    success = self._execute_create_action(action)
                elif action.action_type == "delete":
                    success = self._execute_delete_action(action)
                elif action.action_type == "run_command":
                    success = self._execute_command_action(action)
                else:
                    self._stream(f"Unknown action type: {action.action_type}", "warning")
                    continue
                
                if not success:
                    self._stream(f"Action failed: {action.description}", "error")
                    break
                    
            except Exception as e:
                self._stream(f"Action error: {e}", "error")
                success = False
                break
        
        # Record repair attempt
        self.repair_history.append((plan.issue, plan, success))
        
        if success:
            self._stream("Repair completed successfully")
        else:
            self._stream("Repair failed - restore from backup if needed", "error")
        
        return success
    
    def _create_backup(self, plan: RepairPlan) -> None:
        """Create backup of files to be modified."""
        backup_dir = os.path.join(self.project_root, ".self_healing_backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for action in plan.actions:
            if action.target_file and action.action_type in {"edit", "delete"}:
                full_path = os.path.join(self.project_root, action.target_file)
                if os.path.exists(full_path):
                    backup_name = f"{os.path.basename(action.target_file)}.{timestamp}.bak"
                    backup_path = os.path.join(backup_dir, backup_name)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        with open(backup_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        self._stream(f"Backed up: {action.target_file}")
                    except Exception as e:
                        self._stream(f"Backup failed: {e}", "warning")
    
    def _execute_edit_action(self, action: RepairAction) -> bool:
        """Execute an edit action on a file."""
        full_path = os.path.join(self.project_root, action.target_file)
        
        if not os.path.exists(full_path):
            self._stream(f"File not found: {action.target_file}", "error")
            return False
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if action.start_line and action.end_line and action.content:
                # Replace specific lines
                start_idx = action.start_line - 1
                end_idx = action.end_line
                new_lines = action.content.split("\n")
                lines[start_idx:end_idx] = [l + "\n" for l in new_lines]
            elif action.content:
                # Replace entire file
                lines = [l + "\n" for l in action.content.split("\n")]
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            self._stream(f"Edit failed: {e}", "error")
            return False
    
    def _execute_create_action(self, action: RepairAction) -> bool:
        """Create a new file."""
        full_path = os.path.join(self.project_root, action.target_file)
        
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(action.content or "")
            return True
        except Exception as e:
            self._stream(f"Create failed: {e}", "error")
            return False
    
    def _execute_delete_action(self, action: RepairAction) -> bool:
        """Delete a file."""
        full_path = os.path.join(self.project_root, action.target_file)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
            return True
        except Exception as e:
            self._stream(f"Delete failed: {e}", "error")
            return False
    
    def _execute_command_action(self, action: RepairAction) -> bool:
        """Execute a shell command."""
        if not action.content:
            return False
        
        try:
            result = subprocess.run(
                action.content,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_root,
            )
            if result.returncode != 0:
                self._stream(f"Command failed: {result.stderr}", "error")
                return False
            return True
        except Exception as e:
            self._stream(f"Command error: {e}", "error")
            return False
    
    # =========================================================================
    # CONTINUOUS HEALING LOOP
    # =========================================================================
    
    def healing_loop(
        self,
        interval: float = 30.0,
        max_repairs_per_cycle: int = 3,
        auto_repair: bool = True,
    ) -> None:
        """
        Continuously monitor for errors and attempt repairs.
        
        Args:
            interval: Seconds between monitoring cycles
            max_repairs_per_cycle: Maximum repairs to attempt per cycle
            auto_repair: If True, automatically attempt repairs
        """
        self._stream("Starting self-healing monitoring loop")
        
        while True:
            try:
                # Detect new issues
                issues = self.detect_errors()
                
                if issues and auto_repair:
                    # Sort by severity (critical first)
                    issues.sort(key=lambda x: {
                        IssueSeverity.CRITICAL: 0,
                        IssueSeverity.HIGH: 1,
                        IssueSeverity.MEDIUM: 2,
                        IssueSeverity.LOW: 3,
                    }.get(x.severity, 4))
                    
                    # Attempt repairs
                    repairs_done = 0
                    for issue in issues[:max_repairs_per_cycle]:
                        plan = self.plan_repair(issue)
                        if plan:
                            success = self.execute_repair(plan)
                            repairs_done += 1
                            if not success:
                                break
                    
                    if repairs_done > 0:
                        self._stream(f"Completed {repairs_done} repairs this cycle")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self._stream("Healing loop stopped by user")
                break
            except Exception as e:
                self._stream(f"Healing loop error: {e}", "error")
                time.sleep(interval)
    
    # =========================================================================
    # VERIFICATION
    # =========================================================================
    
    def verify_fix(self, issue: CodeIssue) -> bool:
        """
        Verify that an issue has been fixed.
        
        Args:
            issue: The issue that was fixed
            
        Returns:
            True if issue appears to be resolved
        """
        # For syntax errors, try importing the module
        if issue.issue_type in {IssueType.SYNTAX_ERROR, IssueType.INDENTATION_ERROR}:
            if issue.file_path and issue.file_path.endswith(".py"):
                return self._verify_python_syntax(issue.file_path)
        
        # For import errors, try importing
        if issue.issue_type in {IssueType.IMPORT_ERROR, IssueType.MISSING_MODULE}:
            return self._verify_import(issue.message)
        
        # Default: run a quick check
        return self._run_quick_test()
    
    def _verify_python_syntax(self, file_path: str) -> bool:
        """Verify Python file has valid syntax."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            compile(content, file_path, "exec")
            return True
        except SyntaxError:
            return False
        except Exception:
            return True  # Non-syntax errors are acceptable
    
    def _verify_import(self, module_hint: str) -> bool:
        """Try to verify an import works."""
        # Extract module name from error message
        match = re.search(r"'(\w+)'", module_hint)
        if not match:
            return True  # Can't verify
        
        module = match.group(1)
        try:
            __import__(module)
            return True
        except ImportError:
            return False
    
    def _run_quick_test(self) -> bool:
        """Run a quick sanity test."""
        try:
            result = subprocess.run(
                ["python", "-c", "import core.trinity; print('OK')"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of self-healing module."""
        return {
            "detected_issues": len(self.detected_issues),
            "repairs_attempted": len(self.repair_history),
            "repairs_successful": sum(1 for _, _, success in self.repair_history if success),
            "last_check_position": self._last_log_position,
            "project_root": self.project_root,
            "log_path": self.log_path,
        }
