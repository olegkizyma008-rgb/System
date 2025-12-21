from typing import Annotated, TypedDict, Literal, List, Dict, Any, Optional, Callable
import json
import os
import subprocess
import re
import time
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from core.agents.atlas import get_atlas_prompt, get_atlas_plan_prompt
from core.agents.tetyana import get_tetyana_prompt
from core.agents.grisha import get_grisha_prompt, get_grisha_media_prompt
from core.vision_context import VisionContextManager
from providers.copilot import CopilotLLM

from core.mcp import MCPToolRegistry
from core.context7 import Context7
from core.verification import AdaptiveVerifier
from core.memory import get_memory
from core.self_healing import IssueSeverity
from core.vibe_assistant import VibeCLIAssistant
from dataclasses import dataclass
from tui.logger import get_logger, trace
from core.utils import extract_json_object
from core.constants import (
    DEV_KEYWORDS, GENERAL_KEYWORDS, MEDIA_KEYWORDS, 
    SUCCESS_MARKERS, FAILURE_MARKERS, UNCERTAIN_MARKERS,
    NEGATION_PATTERNS, VISION_FAILURE_KEYWORDS, MESSAGES,
    TERMINATION_MARKERS
)
import threading

@dataclass
class TrinityPermissions:
    """Permission flags for Trinity system actions."""
    allow_shell: bool = False
    allow_applescript: bool = False
    allow_file_write: bool = False
    allow_gui: bool = False
    allow_shortcuts: bool = False
    hyper_mode: bool = False # Automation without confirmation

# Define the state of the Trinity system
class TrinityState(TypedDict):
    messages: List[BaseMessage]
    current_agent: str
    task_status: str
    final_response: Optional[str]
    plan: Optional[List[Dict[str, Any]]]
    summary: Optional[str]
    step_count: int
    replan_count: int
    pause_info: Optional[Dict[str, Any]]  # Permission pause info
    gui_mode: Optional[str]  # off|on|auto
    execution_mode: Optional[str]  # native|gui
    gui_fallback_attempted: Optional[bool]
    task_type: Optional[str]  # DEV|GENERAL|UNKNOWN
    is_dev: Optional[bool]
    requires_windsurf: Optional[bool]
    dev_edit_mode: Optional[str]  # windsurf|cli
    intent_reason: Optional[str]
    last_step_status: Optional[str] # success|failed|uncertain
    uncertain_streak: Optional[int]  # Count of consecutive uncertain decisions (anti-loop)
    current_step_fail_count: Optional[int]  # Count of consecutive failures on the same step
    meta_config: Optional[Dict[str, Any]]  # Meta-planning: strategy, verification_rigor, recovery_mode, tool_preference, reasoning
    retrieved_context: Optional[str]  # Structured findings from RAG
    original_task: Optional[str]  # The original user request (Golden Goal)
    is_media: Optional[bool]  # Flag for media-related tasks (movie, video, audio)
    vibe_assistant_pause: Optional[Dict[str, Any]]  # Vibe CLI Assistant pause state
    vibe_assistant_context: Optional[str]  # Context for Vibe CLI Assistant
    vision_context: Optional[Dict[str, Any]] # Enhanced visual context
    learning_mode: Optional[bool]

class TrinityRuntime:
    MAX_REPLANS = 10
    MAX_STEPS = 50
    
    # Dev task keywords (allow execution)
    DEV_KEYWORDS = set(DEV_KEYWORDS)
    
    # Non-dev keywords (block execution)
    NON_DEV_KEYWORDS = set(GENERAL_KEYWORDS)
    
    def __init__(
        self,
        verbose: bool = True,
        permissions: TrinityPermissions = None,
        on_stream: Optional[Callable[[str, str], None]] = None,
        preferred_language: str = "en",
        enable_self_healing: bool = True,
        hyper_mode: bool = False,
        learning_mode: bool = False
    ):
        self.llm = CopilotLLM()
        self.verbose = verbose
        self.logger = get_logger("system_cli.trinity")
        self.registry = MCPToolRegistry()
        self.learning_mode = learning_mode
        
        # Integrate MCP tools with Trinity's registry
        try:
            from system_ai.tools.mcp_integration import register_mcp_tools_with_trinity
            register_mcp_tools_with_trinity(self.registry)
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"MCP integration with Trinity deferred: {e}")
        
        self.context_layer = Context7(verbose=verbose)
        self.verifier = AdaptiveVerifier(self.llm)
        self.memory = get_memory()
        self.permissions = permissions or TrinityPermissions()
        self.preferred_language = preferred_language
        # Callback for streaming deltas: (agent_name, text_delta)
        self.on_stream = on_stream
        # Thread lock to prevent duplicate streaming output
        self._stream_lock = threading.Lock()
        self._last_stream_content = {}  # Per-agent deduplication
        self.workflow = self._build_graph()
        
        # Hyper mode for unlimited permissions during testing
        self.hyper_mode = hyper_mode
        if self.hyper_mode:
            self.logger.info("🚀 HYPER MODE ACTIVATED: Unlimited permissions for Doctor Vibe")
            # Override permissions to allow everything
            self.permissions.allow_shell = True
            self.permissions.allow_applescript = True
            self.permissions.allow_file_write = True
            self.permissions.allow_gui = True
            self.permissions.allow_shortcuts = True
            self.permissions.hyper_mode = True
        
        # Initialize self-healing module
        self.self_healing_enabled = enable_self_healing
        self.self_healer = None
        if self.self_healing_enabled:
            self._initialize_self_healing()
        
        # Initialize Vision Context Manager
        self.vision_context_manager = VisionContextManager(max_history=10)
        
        # Initialize Vibe CLI Assistant
        self.vibe_assistant = VibeCLIAssistant(name="Doctor Vibe")
        
        # Register core tools including enhanced vision
        self._register_tools()

    def _deduplicated_stream(self, agent: str, content: str) -> None:
        """Thread-safe streaming with deduplication to prevent duplicate log entries."""
        if not self.on_stream or not content:
            return
        with self._stream_lock:
            # Check for duplicate content (exact match or prefix match)
            last = self._last_stream_content.get(agent, "")
            if content == last or (len(content) < len(last) and last.startswith(content)):
                return  # Skip duplicate
            self._last_stream_content[agent] = content
        self.on_stream(agent, content)

    def _register_tools(self) -> None:
        """Register all local tools and MCP tools."""
        from system_ai.tools.vision import EnhancedVisionTools
        from system_ai.tools.screenshot import get_frontmost_app, get_all_windows
        
        # Core Vision Tools
        self.registry.register_tool(
            "enhanced_vision_analysis",
            EnhancedVisionTools.capture_and_analyze,
            description="Capture screen and perform differential visual/OCR analysis. Args: app_name (optional), window_title (optional)"
        )
        
        self.registry.register_tool(
            "vision_analysis_with_context",
            lambda args: EnhancedVisionTools.analyze_with_context(
                args.get("image_path"),
                self.vision_context_manager
            ),
            description="Analyze image and update global visual context"
        )
        
        # Window detection utilities
        self.registry.register_tool(
            "get_frontmost_app",
            lambda args: get_frontmost_app(),
            description="Get the currently active (frontmost) application name and window title on macOS"
        )
        
        self.registry.register_tool(
            "get_all_windows",
            lambda args: get_all_windows(),
            description="Get list of all visible windows with their app names, titles, positions and sizes"
        )

    def _initialize_self_healing(self) -> None:
        """Initialize the self-healing module."""
        try:
            from core.self_healing import CodeSelfHealer
            self.self_healer = CodeSelfHealer(on_stream=self.on_stream)
            self.self_healer.integrate_with_trinity(self)
            
            # Start background monitoring
            self.self_healing_thread = self.self_healer.start_background_monitoring(interval=60.0)
            
            # Connect Vibe Assistant to Self-Healer for auto-repair
            if hasattr(self, 'vibe_assistant'):
                self.vibe_assistant.set_self_healer(
                    self.self_healer,
                    on_repair_complete=self._on_auto_repair_complete
                )
            
            if self.verbose:
                self.logger.info("Self-healing module initialized and monitoring started")
        except Exception as e:
            self.logger.error(f"Failed to initialize self-healing: {e}")
            self.self_healing_enabled = False
    
    def _on_auto_repair_complete(self, result: dict) -> None:
        """Callback when Doctor Vibe auto-repair completes."""
        if result.get("success"):
            self.logger.info(f"Auto-repair successful: {result.get('repairs_successful', 0)} fixes applied")
        else:
            self.logger.warning(f"Auto-repair failed: {result.get('message', 'unknown')}")
    
    def _classify_task_llm(self, task: str) -> Optional[Dict[str, Any]]:
        try:
            if os.getenv("PYTEST_CURRENT_TEST"):
                return None

            disable = str(os.getenv("TRINITY_DISABLE_INTENT_LLM", "")).strip().lower()
            if disable in {"1", "true", "yes", "on"}:
                return None

            sys = (
                "You are a task router for a macOS developer assistant. "
                "Classify the user request into one of: DEV, GENERAL. "
                "DEV means software development work or dev-support operations (debugging, code analysis, checking permissions/disk space/processes, git, tests, repo files, browser-based research for dev purposes). "
                "GENERAL means completely unrelated non-technical/personal tasks. "
                "Default to DEV if there is any technical context."
                "Also decide whether the task requires using Windsurf IDE for code generation/editing. "
                "Return STRICT JSON only with keys: task_type (DEV|GENERAL), requires_windsurf (bool), confidence (0..1), reason (string)."
            )
            msgs: List[BaseMessage] = [
                SystemMessage(content=sys),
                HumanMessage(content=str(task or "")),
            ]
            resp = self.llm.invoke(msgs)
            resp_content = getattr(resp, "content", "") if resp is not None else ""
            data = extract_json_object(resp_content)
            if not data:
                return None
            task_type = str(data.get("task_type") or "").strip().upper()
            if task_type not in {"DEV", "GENERAL"}:
                return None
            requires_windsurf = bool(data.get("requires_windsurf"))
            try:
                confidence = float(data.get("confidence"))
            except Exception:
                confidence = 0.0
            reason = str(data.get("reason") or "").strip()
            return {
                "task_type": task_type,
                "requires_windsurf": requires_windsurf,
                "confidence": confidence,
                "reason": reason,
            }
        except Exception:
            return None

    def _classify_task_fallback(self, task: str) -> Dict[str, Any]:
        task_lower = str(task or "").lower()

        for keyword in self.NON_DEV_KEYWORDS:
            if keyword in task_lower:
                return {"task_type": "GENERAL", "requires_windsurf": False, "confidence": 0.2, "reason": "keyword_fallback: non_dev"}

        for keyword in self.DEV_KEYWORDS:
            if keyword in task_lower:
                return {"task_type": "DEV", "requires_windsurf": True, "confidence": 0.2, "reason": "keyword_fallback: dev"}

        return {"task_type": "UNKNOWN", "requires_windsurf": True, "confidence": 0.1, "reason": "keyword_fallback: unknown"}

    def _classify_task(self, task: str) -> tuple[str, bool, bool]:
        """
        Classify task as DEV or GENERAL.
        Returns: (task_type, is_dev, is_media)
        """
        task_lower = str(task or "").lower()
        # Media keywords for specific logic
        media_keywords = set(MEDIA_KEYWORDS)
        is_media = any(k in task_lower for k in media_keywords)
        
        llm_res = self._classify_task_llm(task)
        if llm_res:
            task_type = str(llm_res.get("task_type") or "").strip().upper()
            return (task_type, task_type == "DEV", is_media)
        fb = self._classify_task_fallback(task)
        task_type = str(fb.get("task_type") or "").strip().upper()
        return (task_type, task_type != "GENERAL", is_media)
    
    def get_self_healing_status(self) -> Optional[Dict[str, Any]]:
        """
        Get the current status of the self-healing module.
        
        Returns:
            Dictionary with self-healing status or None if disabled
        """
        if not self.self_healing_enabled or not self.self_healer:
            return None
        
        return self.self_healer.get_status()
    
    def trigger_self_healing_scan(self) -> Optional[List[Dict[str, Any]]]:
        """
        Trigger an immediate scan for issues.
        
        Returns:
            List of detected issues or None if disabled
        """
        if not self.self_healing_enabled or not self.self_healer:
            return None
        
        issues = self.self_healer.trigger_immediate_scan()
        return [issue.to_dict() for issue in issues]
    
    def _check_for_vibe_assistant_intervention(self, state: TrinityState) -> Optional[Dict[str, Any]]:
        """
        Check if Doctor Vibe intervention is needed based on current state.
        This method integrates with Atlas meta-planning to create a seamless workflow.
        
        Args:
            state: Current Trinity state
            
        Returns:
            Dict with pause information if intervention needed, None otherwise
        """
        # Check if we already have an active pause
        if state.get("vibe_assistant_pause"):
            return state["vibe_assistant_pause"]
        
        # Check if self-healing detected critical issues that need human attention
        if self.self_healing_enabled and self.self_healer:
            issues = self.self_healer.detected_issues
            critical_issues = [issue for issue in issues if issue.severity in {IssueSeverity.CRITICAL, IssueSeverity.HIGH}]
            
            if critical_issues:
                # Create pause context for Doctor Vibe with Atlas integration
                pause_context = {
                    "reason": "critical_issues_detected",
                    "issues": [issue.to_dict() for issue in critical_issues[:5]],  # Top 5 most critical
                    "message": f"Doctor Vibe: Виявлено {len(critical_issues)} критичних помилок. Атлас призупинив виконання для вашого втручання.",
                    "timestamp": datetime.now().isoformat(),
                    "suggested_action": "Будь ласка, виправте помилки. Атлас автоматично продовжить після /continue",
                    "atlas_status": "paused_waiting_for_human",
                    "auto_resume_available": True
                }
                return pause_context
        
        # Check for repeated failures that might need human intervention
        current_step_fail_count = state.get("current_step_fail_count", 0)
        if current_step_fail_count >= 3:
            lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
            pause_context = {
                "reason": "repeated_failures",
                "message": "Doctor Vibe: Atlas detected repeating errors. System paused." if lang != "uk" else "Doctor Vibe: Атлас виявив повторювані помилки. Система призупинена для аналізу.",
                "timestamp": datetime.now().isoformat(),
                "suggested_action": "Please analyze the issue. Use /continue or /cancel" if lang != "uk" else "Будь ласка, проаналізуйте проблему. Використовуйте /continue або /cancel",
                "atlas_status": "paused_analyzing_failures",
                "auto_resume_available": True
            }
            return pause_context
        
        # Check for complex dev tasks that might need Doctor Vibe's attention
        task_type = state.get("task_type", "UNKNOWN")
        is_dev_task = state.get("is_dev", False)
        
        if task_type == "DEV" and is_dev_task:
            # For dev tasks, Doctor Vibe works in parallel thread for error correction
            # Check if there are any unresolved issues that need attention
            if self.self_healing_enabled and self.self_healer:
                unresolved_issues = [issue for issue in self.self_healer.detected_issues 
                                   if issue.severity in {IssueSeverity.MEDIUM, IssueSeverity.HIGH}]
                
                if unresolved_issues and len(unresolved_issues) > 2:
                    # Doctor Vibe works in background mode for dev tasks
                    lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
                    pause_context = {
                        "reason": "background_error_correction_needed",
                        "issues": [issue.to_dict() for issue in unresolved_issues[:3]],
                        "message": f"Doctor Vibe: Detected {len(unresolved_issues)} background errors. Atlas continues current task." if lang != "uk" else f"Doctor Vibe: Виявлено {len(unresolved_issues)} помилок в фоновому режимі. Атлас продовжує основне завдання.",
                        "timestamp": datetime.now().isoformat(),
                        "suggested_action": "Errors are being fixed automatically." if lang != "uk" else "Помилки виправляються автоматично. Ви можете продовжувати роботу",
                        "atlas_status": "running_with_background_fixes",
                        "auto_resume_available": False,  # No pause needed, just notification
                        "background_mode": True
                    }
                    return pause_context
        
        # Check for unknown stalls - when system is stuck without clear reason
        # This happens when last message contains uncertainty or system is waiting
        if state.get("vibe_assistant_pause"):
            # Already paused, no need to intervene again
            return None
        
        # Detect stall conditions
        messages = state.get("messages", [])
        last_message = getattr(messages[-1], "content", "") if messages and len(messages) > 0 and messages[-1] is not None else ""
        last_message_lower = last_message.lower()
        
        stall_conditions = [
            "план порожній",
            "empty plan",
            "no steps",
            "cannot",
            "не може",
            "не вдається",
            "failed to",
            "немає кроків"
        ]
        
        if any(condition in last_message_lower for condition in stall_conditions):
            lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
            # System is stalled with unclear reason - Doctor Vibe should intervene
            pause_context = {
                "reason": "unknown_stall_detected",
                "message": f"Doctor Vibe: Detected unknown stall. Last message: {last_message[:100]}..." if lang != "uk" else f"Doctor Vibe: Виявлено невідому зупинку системи. Останнє повідомлення: {last_message[:100]}...",
                "timestamp": datetime.now().isoformat(),
                "suggested_action": "Please clarify the task or restart the system." if lang != "uk" else "Будь ласка, уточніть завдання або перезапустіть систему",
                "atlas_status": "stalled_unknown_reason",
                "auto_resume_available": False,
                "last_message": last_message,
                "original_task": state.get("original_task")
            }
            return pause_context
        
        return None
    
    def _create_vibe_assistant_pause_state(self, state: TrinityState, pause_reason: str, message: str) -> TrinityState:
        """
        Create a pause state for Vibe CLI Assistant intervention.
        
        Args:
            state: Current Trinity state
            pause_reason: Reason for pause
            message: Message to display to user
            
        Returns:
            Updated state with pause information
        """
        pause_info = {
            "reason": pause_reason,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "initiated_by": "Vibe CLI Assistant",
            "status": "awaiting_human_input"
        }
        
        # Add context about current task
        if state.get("original_task"):
            pause_info["original_task"] = state["original_task"]
        
        if state.get("plan"):
            pause_info["current_step"] = state["plan"][0] if state["plan"] else None
        
        # If we have critical issues from self-healing, add them to the context
        if self.self_healing_enabled and self.self_healer:
            issues = self.self_healer.detected_issues
            critical_issues = [issue for issue in issues if issue.severity in {IssueSeverity.CRITICAL, IssueSeverity.HIGH}]
            if critical_issues:
                pause_info["issues"] = [issue.to_dict() for issue in critical_issues[:5]]  # Top 5 most critical
        
        # Notify Vibe CLI Assistant about the pause
        self.vibe_assistant.handle_pause_request(pause_info)
        
        return {
            **state,
            "vibe_assistant_pause": pause_info,
            "vibe_assistant_context": f"PAUSED: {message}"
        }
    
    def _resume_from_vibe_assistant_pause(self, state: TrinityState) -> TrinityState:
        """
        Resume execution from Vibe CLI Assistant pause.
        
        Args:
            state: Current Trinity state with pause information
            
        Returns:
            Updated state with pause cleared
        """
        # Clear pause state but keep context for logging
        pause_context = state.get("vibe_assistant_context", "")
        
        # Clear Vibe CLI Assistant pause state
        self.vibe_assistant.clear_pause_state()
        
        return {
            **state,
            "vibe_assistant_pause": None,
            "vibe_assistant_context": f"RESUMED: {pause_context}"
        }
    
    def handle_vibe_assistant_command(self, command: str) -> Dict[str, Any]:
        """
        Handle commands from Vibe CLI Assistant during pause state.
        
        Args:
            command: User command (e.g., /continue, /cancel, /help)
            
        Returns:
            Dict with action result
        """
        return self.vibe_assistant.handle_user_command(command)
    
    def get_vibe_assistant_status(self) -> Dict[str, Any]:
        """
        Get current status of Vibe CLI Assistant.
        
        Returns:
            Dict with status information
        """
        current_pause = self.vibe_assistant.get_current_pause_status()
        intervention_history = self.vibe_assistant.get_intervention_history()
        
        return {
            "name": self.vibe_assistant.name,
            "current_pause": current_pause,
            "interventions_total": len(intervention_history),
            "interventions_active": sum(1 for record in intervention_history if record["status"] == "active"),
            "interventions_resolved": sum(1 for record in intervention_history if record["status"] == "resolved"),
            "interventions_cancelled": sum(1 for record in intervention_history if record["status"] == "cancelled")
        }
    
    def start_eternal_engine_mode(self, task: str) -> None:
        """
        Start the system in eternal engine mode with Doctor Vibe.
        
        This mode:
        1. Automatically detects task type (DEV or GENERAL)
        2. For DEV tasks: Doctor Vibe works in background for error correction
        3. For GENERAL tasks: Doctor Vibe only intervenes on critical errors
        4. System continues until task is completed or manually cancelled
        
        Args:
            task: The task to execute in eternal engine mode
        """
        if self.verbose:
            self.logger.info("🚀 ETERNAL ENGINE MODE ACTIVATED with Doctor Vibe")
        
        # Classify the task
        task_type, is_dev, is_media = self._classify_task(task)
        
        if self.verbose:
            self.logger.info(f"📝 Task classified as: {task_type} (DEV: {is_dev}, MEDIA: {is_media})")
        
        # Set up initial state with Doctor Vibe context
        initial_state = {
            "messages": [HumanMessage(content=task)],
            "current_agent": "meta_planner",
            "task_status": "starting",
            "final_response": None,
            "plan": [],
            "summary": "",
            "step_count": 0,
            "replan_count": 0,
            "pause_info": None,
            "gui_mode": "auto",
            "execution_mode": "native",
            "gui_fallback_attempted": False,
            "task_type": task_type,
            "is_dev": is_dev,
            "requires_windsurf": is_dev,
            "dev_edit_mode": "cli",
            "intent_reason": "eternal_engine_mode",
            "last_step_status": "success",
            "uncertain_streak": 0,
            "current_step_fail_count": 0,
            "meta_config": {
                "strategy": "linear",
                "verification_rigor": "medium",
                "recovery_mode": "local_fix",
                "tool_preference": "hybrid",
                "doctor_vibe_mode": "background" if is_dev else "intervention"
            },
            "retrieved_context": "",
            "original_task": task,
            "vibe_assistant_pause": None,
            "is_media": is_media,
            "vibe_assistant_context": "eternal_engine_mode: Doctor Vibe monitoring activated",
            "learning_mode": self.learning_mode
        }
        
        if self.verbose:
            mode_desc = "background error correction" if is_dev else "critical error intervention"
            self.logger.info(f"🤖 Doctor Vibe mode: {mode_desc}")
        
        # Start background monitoring if in hyper mode
        if self.hyper_mode and self.self_healing_enabled:
            if self.verbose:
                self.logger.info("🔄 Starting self-healing background monitoring...")
            # Self-healing already started in __init__
        
        # Execute the workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            
            if self.verbose:
                self.logger.info("✅ Eternal engine mode completed successfully")
            
            return final_state
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"❌ Eternal engine mode failed: {e}")
            
            # Doctor Vibe handles the error
            error_context = {
                "reason": "eternal_engine_failure",
                "message": f"Doctor Vibe: Eternal engine encountered error: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "suggested_action": "Please check logs and restart with corrected parameters"
            }
            
            self.vibe_assistant.handle_pause_request(error_context)
            raise
    
    def _build_graph(self):
        builder = StateGraph(TrinityState)

        builder.add_node("meta_planner", self._meta_planner_node)
        builder.add_node("atlas", self._atlas_node)
        builder.add_node("tetyana", self._tetyana_node)
        builder.add_node("grisha", self._grisha_node)
        builder.add_node("knowledge", self._knowledge_node)

        builder.set_entry_point("meta_planner")
        
        builder.add_conditional_edges(
            "meta_planner",
            self._router,
            {"atlas": "atlas", "tetyana": "tetyana", "grisha": "grisha", "knowledge": "knowledge", "end": END}
        )
        builder.add_conditional_edges(
            "atlas", 
            self._router, 
            {"tetyana": "tetyana", "grisha": "grisha", "meta_planner": "meta_planner", "atlas": "atlas", "knowledge": "knowledge", "end": END}
        )
        builder.add_conditional_edges(
            "tetyana", 
            self._router, 
            {"grisha": "grisha", "meta_planner": "meta_planner", "tetyana": "tetyana", "atlas": "atlas", "knowledge": "knowledge", "end": END}
        )
        builder.add_conditional_edges(
            "grisha", 
            self._router, 
            {"meta_planner": "meta_planner", "knowledge": "knowledge", "atlas": "atlas", "end": END}
        )
        builder.add_conditional_edges(
            "knowledge",
            self._router,
            {"end": END}
        )

        return builder.compile()

    def _meta_planner_node(self, state: TrinityState):
        """The 'Controller Brain' that sets policies and manages replanning strategy."""
        if self.verbose: print("🧠 [Meta-Planner] Analyzing strategy...")
        context = state.get("messages", [])
        # Safe access to last message - check if context is not empty first
        last_msg = getattr(context[-1], "content", "Start") if context and len(context) > 0 and context[-1] is not None else "Start"
        original_task = state.get("original_task") or "Unknown"
        step_count = state.get("step_count", 0)
        replan_count = state.get("replan_count", 0)
        last_step_status = state.get("last_step_status", "success")
        plan = state.get("plan") or []
        meta_config = state.get("meta_config") or {}
        
        # Ensure meta_config has all required keys with safe defaults
        if isinstance(meta_config, dict):
            meta_config.setdefault("strategy", "hybrid")
            meta_config.setdefault("verification_rigor", "standard")
            meta_config.setdefault("recovery_mode", "local_fix")
            meta_config.setdefault("tool_preference", "hybrid")
            meta_config.setdefault("reasoning", "")
            meta_config.setdefault("retrieval_query", last_msg)
            meta_config.setdefault("n_results", 3)
        else:
            # If meta_config is not a dict for some reason, reset it
            meta_config = {
                "strategy": "hybrid",
                "verification_rigor": "standard",
                "recovery_mode": "local_fix",
                "tool_preference": "hybrid",
                "reasoning": "",
                "retrieval_query": last_msg,
                "n_results": 3
            }
        
        current_step_fail_count = int(state.get("current_step_fail_count") or 0)

        # 1. Update Summary Memory periodically
        summary = state.get("summary", "")
        if len(context) > 6 and step_count % 3 == 0:
             try:
                # Safe content extraction - handle objects without .content attribute
                recent_contents = []
                for m in (context[-4:] if len(context) >= 4 else context):
                    msg_content = getattr(m, "content", "") if m is not None else ""
                    if msg_content:
                        recent_contents.append(str(msg_content)[:4000])
                
                summary_prompt = [
                    SystemMessage(content=f"You are the Trinity archivist. Create a concise summary (2-3 sentences) of the current task state in {self.preferred_language}. What has been done? What remains?"),
                    HumanMessage(content=f"Current summary: {summary}\n\nRecent events:\n" + "\n".join(recent_contents))
                ]
                sum_resp = self.llm.invoke(summary_prompt)
                summary = getattr(sum_resp, "content", "")
                if self.verbose: print(f"🧠 [Meta-Planner] Summary update: {summary[:50] if summary else '(empty)'}...")
             except Exception:
                pass

        # 1b. Check Master Limits
        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
        if step_count >= self.MAX_STEPS:
            msg = MESSAGES[lang]["step_limit_reached"].format(limit=self.MAX_STEPS)
            return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"[VOICE] {msg}")]}
        if replan_count >= self.MAX_REPLANS:
            msg = MESSAGES[lang]["replan_limit_reached"].format(limit=self.MAX_REPLANS)
            return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"[VOICE] {msg}")]}

        # 2. Plan Maintenance (Consumption)
        if plan:
            if last_step_status == "success":
                # Success - record it in history and consume
                completed_step = plan.pop(0)
                hist = state.get("history_plan_execution") or []
                desc = completed_step.get('description', 'Unknown step')
                hist.append(f"SUCCESS: {desc}")
                state["history_plan_execution"] = hist
                current_step_fail_count = 0
                state["gui_fallback_attempted"] = False # Reset for next step
                if self.verbose: print(f"🧠 [Meta-Planner] Step succeeded: {desc}. Remaining: {len(plan)}")
                if not plan:
                    # Robust termination: Only end if the Global Goal is explicitly verified
                    has_verified = any(m.upper() in last_msg.upper() for m in TERMINATION_MARKERS) or "[ACHIEVEMENT_CONFIRMED]" in last_msg.upper()
                    if has_verified:
                        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
                        msg = MESSAGES[lang]["task_achieved"]
                        return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"[VOICE] {msg}")]}
                    else:
                        if self.verbose: print("🧠 [Meta-Planner] Plan exhausted but Global Goal NOT verified. Triggering replan for next steps.")
                        # Do not return 'end' here; let the decision logic below set action = 'replan'

            elif last_step_status == "failed":
                current_step_fail_count += 1
                if self.verbose: print(f"🧠 [Meta-Planner] Step failed ({current_step_fail_count}/3).")
                
                # Record failure
                hist = state.get("history_plan_execution") or []
                desc = plan[0].get('description', 'Unknown step') if plan else 'Unknown step'
                hist.append(f"FAILED: {desc} (Try #{current_step_fail_count})")
                state["history_plan_execution"] = hist
                
            elif last_step_status == "uncertain":
                # Treat uncertain as soft failure - increment count but don't replan immediately
                current_step_fail_count += 1
                if self.verbose: print(f"🧠 [Meta-Planner] Step uncertain ({current_step_fail_count}/4).")
                
                # Record uncertainty
                hist = state.get("history_plan_execution") or []
                desc = plan[0].get('description', 'Unknown step') if plan else 'Unknown step'
                hist.append(f"UNCERTAIN: {desc} (Check #{current_step_fail_count})")
                state["history_plan_execution"] = hist

                # Increase allowance for uncertainty to avoid premature failure
                if current_step_fail_count >= 4:
                    if self.verbose: print(f"🧠 [Meta-Planner] Uncertainty limit reached ({current_step_fail_count}). Marking step as FAILED to trigger recovery.")
                    last_step_status = "failed"
                    # Capture failed action for forbidden list (Manual Retry)
                    forbidden = state.get("forbidden_actions") or []
                    forbidden.append(f"FAILED ACTION: {desc}")
                    state["forbidden_actions"] = forbidden
                    # Do NOT pop the plan. Let the decision logic below handle 'failed' -> 'replan'.

        # 3. Decision Logic with Doctor Vibe integration
        action = "proceed" # Default: continue to tetyana with current plan
        
        if not meta_config:
            action = "initialize"
        elif not plan:
            # Check if this is a planning failure that needs Doctor Vibe intervention
            if step_count > 0 and last_step_status == "success":
                # Empty plan after successful step - just replan
                if self.verbose:
                    self.logger.info("Plan completed. Triggering replan for next steps.")
                action = "replan"
            else:
                action = "replan" # out of steps
        elif last_step_status == "failed":
            if current_step_fail_count >= 3:
                 action = "replan"
                 # Capture failed action for forbidden list
                 hist = state.get("history_plan_execution") or []
                 if hist:
                     forbidden = state.get("forbidden_actions") or []
                     forbidden.append(f"FAILED ACTION: {hist[-1]}")
                     state["forbidden_actions"] = forbidden
            else:
                 recovery_mode = meta_config.get("recovery_mode", "local_fix")
                 action = "replan" if recovery_mode == "full_replan" else "repair"
        
        # Doctor Vibe integration: Check if we're in background error correction mode
        vibe_assistant_context = state.get("vibe_assistant_context", "")
        if "background_mode" in vibe_assistant_context:

            # If Doctor Vibe is working in background, let him continue
            if self.verbose:
                self.logger.info("🧠 [Meta-Planner] Doctor Vibe working in background mode - continuing execution")
            action = "proceed"
        # NOTE: Removed the old "uncertain -> replan" logic. Uncertain is now handled above as a soft failure.
        
        # 4. Meta-Reasoning (LLM)
        if action in ["initialize", "replan", "repair"]:
            from core.agents.atlas import get_meta_planner_prompt
            
            task_context = f"Global Goal: {original_task}\nCurrent Request: {last_msg}\nStep: {step_count}\nStatus: {last_step_status}\nCurrent config: {meta_config}\nPlan (remaining): {len(plan)} steps."
            prompt = get_meta_planner_prompt(task_context, preferred_language=self.preferred_language)
            
            try:
                resp = self.llm.invoke(prompt.format_messages())
                resp_content = getattr(resp, "content", "") if resp is not None else ""
                data = self._extract_json_object(resp_content)
                if data and "meta_config" in data:
                    meta_config.update(data["meta_config"])
                    # Selective RAG: If Meta-Planner decides context is needed
                    if meta_config.get("strategy") == "rag_heavy" or action in ["initialize", "replan", "repair"]:
                        query = meta_config.get("retrieval_query", last_msg)
                        limit = int(meta_config.get("n_results", 3))
                        
                        if self.verbose: print(f"🧠 [Meta-Planner] Selective RAG lookup: '{query}' (top {limit})...")
                        mem_res = self.memory.query_memory("knowledge_base", query, n_results=limit)
                        
                        # Filter memories: Prioritize high confidence, be wary of 'failed' ones
                        relevant_context = []
                        for r in mem_res:
                            m = r.get("metadata", {})
                            status = m.get("status", "success")
                            conf = float(m.get("confidence", 1.0))
                            
                            if status == "success" and conf > 0.3:
                                relevant_context.append(f"[SUCCESS] {r.get('content')}")
                            elif status == "failed":
                                relevant_context.append(f"[WARNING: FAILED PREVIOUSLY] Avoid this: {r.get('content')}")
                        
                        if not relevant_context:
                            # fallback to strategies
                            mem_res = self.memory.query_memory("strategies", query, n_results=limit)
                            relevant_context = [r.get("content", "") for r in mem_res]
                        
                        state["retrieved_context"] = "\n".join(relevant_context)
                    
                    if self.verbose: print(f"🧠 [Meta-Planner] Reasoning: {meta_config.get('reasoning')}")
                    if self.verbose: print(f"🧠 [Meta-Planner] Updated policy: {meta_config.get('strategy')}, rigor={meta_config.get('verification_rigor')}")
            except Exception as e:
                if self.verbose: print(f"⚠️ [Meta-Planner] Error: {e}")

            # Signal Atlas if we need plan changes
            # REPAIR MODE: Keep remaining plan, only regenerate the FAILED step
            # REPLAN MODE: Regenerate entire plan from scratch
            if action == "repair" and plan:
                # Mark the current (failed) step for regeneration, keep the rest
                failed_step_desc = plan[0].get("description", "Unknown") if plan else ""
                meta_config["repair_mode"] = True
                meta_config["failed_step"] = failed_step_desc
                if self.verbose: print(f"🔧 [Meta-Planner] REPAIR MODE: Regenerating only step '{failed_step_desc[:50]}...'")
                # Remove the failed step, Atlas will generate a replacement
                plan_for_atlas = plan[1:] if len(plan) > 1 else []
            else:
                plan_for_atlas = None  # Full replan
                meta_config["repair_mode"] = False
                
            return {
                "current_agent": "atlas",
                "meta_config": meta_config,
                "plan": plan_for_atlas,
                "current_step_fail_count": current_step_fail_count,
                "gui_fallback_attempted": False if action == "replan" else state.get("gui_fallback_attempted"),
                "summary": summary,
                "retrieved_context": state.get("retrieved_context", "")
            }

        # 5. Default flow
        out = self._atlas_dispatch(state, plan)
        out["summary"] = summary
        return out

    def _atlas_node(self, state: TrinityState):
        """Generates the plan based on Meta-Planner policy."""
        if self.verbose: print("🌐 [Atlas] Generating steps...")
        context = state.get("messages", [])
        last_msg = getattr(context[-1], "content", "Start") if context and len(context) > 0 and context[-1] is not None else "Start"
        step_count = state.get("step_count", 0) + 1
        replan_count = state.get("replan_count", 0)
        plan = state.get("plan")
        meta_config = state.get("meta_config") or {}

        # ANTI-LOOP: If we already have a valid plan with steps, dispatch directly to execution
        if plan and len(plan) > 0:
            if self.verbose: print(f"🌐 [Atlas] Using existing plan ({len(plan)} steps). Dispatching to execution.")
            return self._atlas_dispatch(state, plan)

        # ANTI-LOOP: Check if we're stuck in replan loop (too many replans without progress)
        last_status = state.get("last_step_status", "success")
        if replan_count >= 3 and last_status != "success":
            if self.verbose: print(f"⚠️ [Atlas] Replan loop detected (#{replan_count}). Forcing simple execution.")
            # Create minimal fallback plan to break the loop
            fallback = [{"id": 1, "type": "execute", "description": last_msg, "agent": "tetyana", "tools": ["browser_open_url"]}]
            return self._atlas_dispatch(state, fallback, replan_count=replan_count)

        # Generate new plan
        replan_count += 1
        if self.verbose: print(f"🔄 [Atlas] Replan #{replan_count}")
        
        from core.agents.atlas import get_atlas_plan_prompt
        # Context is now provided by Context7 Layer (Explicit Context Management)
        rag_context = state.get("retrieved_context", "")
        structure_context = self._get_project_structure_context()
        
        # Determine last user message for Context7 prioritization if needed
        last_user_msg = last_msg # simplified, ideally specific user request
        
        # Prepare context via Context7
        final_context = self.context_layer.prepare(
            rag_context=rag_context,
            project_structure=structure_context,
            meta_config=meta_config,
            last_msg=last_user_msg
        )

        # Prepare history of execution for context
        execution_history = []
        hist = state.get("history_plan_execution") or []
        if hist:
            for h in hist:
                execution_history.append(f"- {h}")
        
        history_str = "\n".join(execution_history) if execution_history else "No steps executed yet. Starting fresh."
        
        prompt = get_atlas_plan_prompt(
            f"Global Goal: {state.get('original_task')}\nCurrent Request: {last_msg}\n\nEXECUTION HISTORY SO FAR (Status of steps):\n{history_str}",
            tools_desc=self.registry.list_tools(),
            context=final_context + ("\n\n[MEDIA_MODE] This is a media-related task. Use the Two-Phase Media Strategy." if state.get("is_media") else ""),
            preferred_language=self.preferred_language,
            forbidden_actions="\n".join(state.get("forbidden_actions") or []),
            vision_context=self.vision_context_manager.current_context
        )
        
        # Inject REPAIR or REPLAN mode instructions
        if meta_config.get("repair_mode"):
            failed_step = meta_config.get("failed_step", "Unknown")
            remaining_plan = plan if plan else []
            remaining_desc = ", ".join([s.get("description", "?")[:30] for s in remaining_plan[:3]]) if remaining_plan else "none"
            prompt.messages.append(HumanMessage(content=f"""🔧 REPAIR MODE: Generate ONLY ONE alternative step to replace the failed step.

FAILED STEP: {failed_step}

REMAINING PLAN (do NOT regenerate these): {remaining_desc}

Generate ONE step that achieves the same goal as the failed step but uses a DIFFERENT approach:
- If browser tool failed → try pyautogui or applescript
- If selector failed → try different selector or coordinate-based click
- If URL failed → try alternative URL or Google search

Return JSON with ONLY the replacement step. I will prepend it to the remaining plan."""))
        elif state.get("last_step_status") == "failed":
            prompt.messages.append(HumanMessage(content=f"PREVIOUS ATTEMPT FAILED. Current history shows what didn't work. AVOID REPEATING FAILED ACTIONS. Respecify the plan starting from the current state to achieve the goal. RESUME, DO NOT RESTART."))
        elif state.get("last_step_status") == "uncertain":
            prompt.messages.append(HumanMessage(content=f"PREVIOUS STEP WAS UNCERTAIN. Review the last action's output and verify if you need to retry it differently or try an alternative approach to confirm success."))

        try:
            def on_delta(chunk):
                self._deduplicated_stream("atlas", chunk)

            # Use Atlas-specific LLM
            atlas_model = os.getenv("ATLAS_MODEL") or os.getenv("COPILOT_MODEL") or "gpt-4.1"
            atlas_llm = CopilotLLM(model_name=atlas_model)

            plan_resp = atlas_llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
            plan_resp_content = getattr(plan_resp, "content", "") if plan_resp is not None else ""
            data = self._extract_json_object(plan_resp_content)
            
            raw_plan = []
            if isinstance(data, list): raw_plan = data
            elif isinstance(data, dict):
                if data.get("status") == "completed":
                    return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"[VOICE] {data.get('message', 'Done.')}")]}
                raw_plan = data.get("steps") or data.get("plan") or []
                if data.get("meta_config"):
                    meta_config.update(data["meta_config"])
                    if self.verbose: print(f"🌐 [Atlas] Strategy Justification: {meta_config.get('reasoning')}")
                    if self.verbose: print(f"🌐 [Atlas] Preferences: tool_pref={meta_config.get('tool_preference', 'hybrid')}")

            if not raw_plan: raise ValueError("No steps generated")

            # REPAIR MODE: Prepend the new step to remaining plan
            if meta_config.get("repair_mode") and plan:
                # Take only the first step from generated plan (repair step)
                repair_step = raw_plan[0] if raw_plan else None
                if repair_step:
                    optimized_plan = [repair_step] + list(plan)
                    if self.verbose: print(f"🔧 [Atlas] REPAIR: Prepended new step to {len(plan)} remaining steps")
                else:
                    optimized_plan = list(plan)
                meta_config["repair_mode"] = False  # Reset flag
            else:
                # Full replan: optimize entire new plan
                # Optimize with Grisha (Verifier) using GRISHA settings
                grisha_model = os.getenv("GRISHA_MODEL") or os.getenv("COPILOT_MODEL") or "gpt-4.1"
                grisha_llm = CopilotLLM(model_name=grisha_model)
                local_verifier = AdaptiveVerifier(grisha_llm)
                
                optimized_plan = local_verifier.optimize_plan(raw_plan, meta_config=meta_config)
            
            return self._atlas_dispatch(state, optimized_plan, replan_count=replan_count)

        except Exception as e:
            if self.verbose: print(f"⚠️ [Atlas] Error: {e}")
            
            # Check if this is a planning failure that Doctor Vibe should handle
            error_str = str(e).lower()
            if "no steps generated" in error_str or "empty plan" in error_str or "cannot" in error_str:
                if self.verbose:
                    print(f"🚨 [Atlas] Planning failure detected. Activating Doctor Vibe intervention.")
                
                # Create pause context for Doctor Vibe
                pause_context = {
                    "reason": "planning_failure",
                    "message": f"Doctor Vibe: Атлас не може створити план для завдання: {last_msg}",
                    "timestamp": datetime.now().isoformat(),
                    "suggested_action": "Будь ласка, уточніть завдання або розбийте його на простіші кроки",
                    "atlas_status": "planning_failed",
                    "auto_resume_available": False,
                    "original_task": state.get("original_task"),
                    "current_attempt": last_msg
                }
                    
                # Notify Doctor Vibe and create pause state
                self.vibe_assistant.handle_pause_request(pause_context)
                
                return {
                    **state,
                    "vibe_assistant_pause": pause_context,
                    "vibe_assistant_context": f"PAUSED: Planning failure for task: {last_msg}",
                    "current_agent": "meta_planner",  # Stay in meta_planner to handle pause
                    "messages": list(context) + [AIMessage(content=f"[VOICE] Doctor Vibe: Виникла проблема з плануванням. Будь ласка, уточніть завдання.")]
                }
            else:
                # Regular fallback for other errors
                if self.verbose:
                    print(f"🔄 [Atlas] Using fallback plan due to error: {e}")
                fallback = [{"id": 1, "type": "execute", "description": last_msg, "agent": "tetyana"}]
                return self._atlas_dispatch(state, fallback, replan_count=replan_count)

    def _atlas_dispatch(self, state, plan, replan_count=None):
        """Internal helper to format the dispatch message and return state."""
        context = state.get("messages", [])
        step_count = state.get("step_count", 0) + 1
        replan_count = replan_count or state.get("replan_count", 0)
        
        current_step = plan[0] if plan else None
        if not current_step:
            return {"current_agent": "end", "messages": list(context) + [AIMessage(content="[VOICE] План порожній.")]}

        desc = current_step.get('description', '')
        step_type = current_step.get("type", "execute")
        next_agent = "grisha" if step_type == "verify" else "tetyana"
        
        voice = f"[VOICE] {next_agent.capitalize()}, {desc}."
        content = f"{voice}\n\n[Atlas Debug] Step: {desc}. Next: {next_agent}"
        
        return {
            "current_agent": next_agent,
            "messages": list(context) + [AIMessage(content=content)],
            "plan": plan,
            "step_count": step_count,
            "replan_count": replan_count,
            "meta_config": state.get("meta_config"),
            "current_step_fail_count": state.get("current_step_fail_count"),
            "gui_mode": state.get("gui_mode"),
            "execution_mode": state.get("execution_mode"),
            "task_type": state.get("task_type"),
            "vision_context": self.vision_context_manager.get_context_for_api()
        }

    def _tetyana_node(self, state: TrinityState):
        if self.verbose: print("💻 [Tetyana] Developing...")
        context = state.get("messages", [])
        if not context:
            return {"current_agent": "end", "messages": [AIMessage(content="[VOICE] Немає контексту для виконання.")]}
        # Safe content extraction - check for None and missing attribute
        last_msg = getattr(context[-1], "content", "") if context and context[-1] is not None else ""
        original_task = state.get("original_task") or ""

        gui_mode = str(state.get("gui_mode") or "auto").strip().lower()
        execution_mode = str(state.get("execution_mode") or "native").strip().lower()
        gui_fallback_attempted = bool(state.get("gui_fallback_attempted") or False)
        task_type = str(state.get("task_type") or "").strip().upper()
        requires_windsurf = bool(state.get("requires_windsurf") or False)
        dev_edit_mode = str(state.get("dev_edit_mode") or ("windsurf" if requires_windsurf else "cli")).strip().lower()
        had_failure = False # Initialize for scope safety
        
        try:
            plan_preview = state.get("plan")
            trace(self.logger, "tetyana_enter", {
                "task_type": task_type,
                "requires_windsurf": requires_windsurf,
                "dev_edit_mode": dev_edit_mode,
                "execution_mode": execution_mode,
                "gui_mode": gui_mode,
                "gui_fallback_attempted": gui_fallback_attempted,
                "plan_len": len(plan_preview) if isinstance(plan_preview, list) else 0,
                "last_msg_preview": str(last_msg)[:200],
            })
        except Exception:
            pass
        
        routing_hint = ""
        try:
            routing_hint = f"\n\n[ROUTING] task_type={task_type} requires_windsurf={requires_windsurf} dev_edit_mode={dev_edit_mode}"
        except Exception:
            routing_hint = ""

        # Inject retry context if applicable
        current_step_fail_count = int(state.get("current_step_fail_count") or 0)
        retry_context = ""
        if current_step_fail_count > 0:
            retry_context = f"\n\n[SYSTEM NOTICE] This is retry #{current_step_fail_count} for this step. Previous attempts were uncertain or failed. Please adjust your approach (e.g., waiting longer, checking errors)."

        # Inject available tools into Tetyana's prompt.
        # If we are in GUI mode, we still list all tools, but the prompt instructs to prefer GUI primitives.
        tools_list = self.registry.list_tools()
        
        # Combined context: Goal + immediate request + hints + retry
        full_context = f"Global Goal: {original_task}\nRequest: {last_msg}{routing_hint}{retry_context}"
        prompt = get_tetyana_prompt(
            full_context, 
            tools_desc=tools_list, 
            preferred_language=self.preferred_language,
            vision_context=self.vision_context_manager.current_context
        )
        
        # Bind tools to LLM for structured tool_calls output.
        tool_defs = self.registry.get_all_tool_definitions()
        
        # Use Tetyana-specific LLM
        tetyana_model = os.getenv("TETYANA_MODEL") or os.getenv("COPILOT_MODEL") or "gpt-4o"
        tetyana_llm = CopilotLLM(model_name=tetyana_model)
        
        bound_llm = tetyana_llm.bind_tools(tool_defs)
        
        pause_info = None
        content = ""  # Initialize content variable
        
        try:
            # For tool-bound calls, use invoke_with_stream to capture deltas for the TUI
            def on_delta(chunk):
                self._deduplicated_stream("tetyana", chunk)
            
            # Use Tetyana's local bound LLM
            response = tetyana_llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
            content = getattr(response, "content", "") if response is not None else ""
            tool_calls = getattr(response, "tool_calls", []) if response is not None and hasattr(response, 'tool_calls') else []
            
            # Anti-acknowledgment check: if no tools and content looks like "I understand/will do"
            if not tool_calls and content:
                lower_content = content.lower()
                acknowledgment_patterns = ["зрозуміла", "зрозумів", "ок", "добре", "починаю", "буду використовувати"]
                if any(p in lower_content for p in acknowledgment_patterns) and len(lower_content) < 300:
                    if self.verbose: print("⚠️ [Tetyana] Acknowledgment loop detected. Forcing retry...")
                    new_msg = AIMessage(content=f"[VOICE] Error: No tool call provided. STOP TALKING, USE A TOOL. {content}")
                    return {
                        "messages": context + [new_msg],
                        "last_step_status": "failed" # This will trigger replan or retry
                    }

            try:
                trace(self.logger, "tetyana_llm", {
                    "tool_calls": len(tool_calls) if isinstance(tool_calls, list) else 0,
                    "content_preview": str(content)[:200],
                })
            except Exception:
                pass
            
            results = []
            gui_tools = {
                "move_mouse",
                "click_mouse",
                "click",
                "type_text",
                "press_key",
                "find_image_on_screen",
            }
            applescript_tools = {
                "run_applescript",
                "native_applescript",
                "native_click_ui",
                "native_type_text",
                "native_wait",
                "native_open_app",
                "native_activate_app",
                "send_to_windsurf",
            }
            shell_tools = {
                "run_shell",
                "open_file_in_windsurf",
                "open_project_in_windsurf",
                "is_windsurf_running",
                "get_windsurf_current_project_path",
            }
            file_write_tools = {
                "write_file",
                "copy_file",
            }
            windsurf_tools = {
                "send_to_windsurf",
                "open_file_in_windsurf",
                "open_project_in_windsurf",
                "is_windsurf_running",
                "get_windsurf_current_project_path",
            }
            if tool_calls:
                for tool in tool_calls:
                    name = tool.get("name")
                    args = tool.get("args") or {}

                    def _general_allows_file_write(tool_name: str, tool_args: Dict[str, Any]) -> bool:
                        try:
                            from system_ai.tools.filesystem import _normalize_special_paths  # type: ignore

                            git_root = self._get_git_root() or ""
                            home = os.path.expanduser("~")
                            allowed_roots = {
                                home,
                                os.path.join(os.sep, "tmp"),
                            }

                            def _is_allowed_path(p: str) -> bool:
                                p2 = _normalize_special_paths(str(p or ""))
                                ap = os.path.abspath(os.path.expanduser(str(p2 or "").strip()))
                                if not ap:
                                    return False
                                # Block any writes inside repo for GENERAL tasks.
                                if git_root and (ap == git_root or ap.startswith(git_root + os.sep)):
                                    return False
                                # Allow within home (or /tmp) only.
                                if ap == home or ap.startswith(home + os.sep):
                                    return True
                                if ap == os.path.join(os.sep, "tmp") or ap.startswith(os.path.join(os.sep, "tmp") + os.sep):
                                    return True
                                return False

                            if tool_name == "write_file":
                                return _is_allowed_path(tool_args.get("path"))
                            if tool_name == "copy_file":
                                return _is_allowed_path(tool_args.get("dst"))
                            return False
                        except Exception:
                            return False

                    if task_type == "GENERAL" and name in windsurf_tools:
                        results.append(f"[BLOCKED] {name}: GENERAL task must not use Windsurf dev subsystem")
                        continue
                    if task_type == "GENERAL" and name in file_write_tools:
                        if not _general_allows_file_write(name, args):
                            results.append(f"[BLOCKED] {name}: GENERAL write allowed only outside repo (home/tmp).")
                            continue

                    if (
                        name in file_write_tools
                        and task_type in {"DEV", "UNKNOWN"}
                        and requires_windsurf
                        and dev_edit_mode == "windsurf"
                    ):
                        results.append(
                            f"[BLOCKED] {name}: DEV task requires Windsurf-first. Use send_to_windsurf/open_file_in_windsurf, or switch to CLI fallback if Windsurf is unavailable."
                        )
                        continue

                    # Permission check for file writes
                    if name in file_write_tools and not (self.permissions.allow_file_write or self.permissions.hyper_mode):
                        pause_info = {
                            "permission": "file_write",
                            "message": "Потрібен дозвіл на запис у файли. Увімкніть Unsafe mode в TUI або перезапустіть задачу з allow_file_write.",
                            "blocked_tool": name,
                            "blocked_args": args,
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                    
                    # Permission check for dangerous tools
                    if name in shell_tools and not (self.permissions.allow_shell or self.permissions.hyper_mode):
                        pause_info = {
                            "permission": "shell",
                            "message": "Потрібен дозвіл на виконання shell команд. Увімкніть Unsafe mode або додайте CONFIRM_SHELL у запит.",
                            "blocked_tool": name,
                            "blocked_args": args
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue

                    if name == "run_shortcut" and not (self.permissions.allow_shortcuts or self.permissions.hyper_mode):
                        pause_info = {
                            "permission": "shortcuts",
                            "message": "Потрібен дозвіл на запуск Shortcuts. Увімкніть Unsafe mode (або дозвольте shortcuts у налаштуваннях).",
                            "blocked_tool": name,
                            "blocked_args": args,
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                        
                    if name in applescript_tools and not (self.permissions.allow_applescript or self.permissions.hyper_mode):
                        pause_info = {
                            "permission": "applescript",
                            "message": "Потрібен дозвіл на виконання AppleScript. Увімкніть Unsafe mode або додайте CONFIRM_APPLESCRIPT у запит.",
                            "blocked_tool": name,
                            "blocked_args": args
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                    if name in gui_tools and not (self.permissions.allow_gui or self.permissions.hyper_mode):
                        pause_info = {
                            "permission": "gui",
                            "message": "Потрібен дозвіл на GUI automation (mouse/keyboard). Увімкніть Unsafe mode або додайте CONFIRM_GUI у запит.",
                            "blocked_tool": name,
                            "blocked_args": args,
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                        
                    # Execute via MCP Registry
                    res_str = self.registry.execute(name, args)
                    results.append(f"Result for {name}: {res_str}")

                    windsurf_failed = False
                    if name in windsurf_tools:
                        try:
                            res_dict = json.loads(res_str)
                            if isinstance(res_dict, dict) and str(res_dict.get("status", "")).lower() == "error":
                                windsurf_failed = True
                        except Exception:
                            pass
                        if windsurf_failed and not pause_info and dev_edit_mode == "windsurf":
                            updated_messages = list(context) + [
                                AIMessage(content="[VOICE] Windsurf не відповідає. Перемикаюсь на CLI режим.")
                            ]
                            
                            try:
                                trace(self.logger, "tetyana_windsurf_fallback", {"tool": name, "dev_edit_mode": dev_edit_mode})
                            except Exception:
                                pass
                            return {
                                "current_agent": "atlas",
                                "messages": updated_messages,
                                "dev_edit_mode": "cli",
                                "execution_mode": execution_mode,
                                "gui_mode": gui_mode,
                                "gui_fallback_attempted": gui_fallback_attempted,
                                "last_step_status": "failed",
                            }

                    # Track failures and captchas for fallback decision
                    try:
                        res_dict = json.loads(res_str)
                        if isinstance(res_dict, dict):
                            status = str(res_dict.get("status", "")).lower()
                            if status == "error":
                                had_failure = True
                            if res_dict.get("has_captcha"):
                                had_failure = True
                                if self.verbose: print("⚠️ [Tetyana] Captcha detected. Marking as failure to trigger GUI mode.")
                    except Exception:
                        # If not JSON, check for error string pattern from MCP executor
                        if str(res_str).strip().startswith("Error"):
                            had_failure = True
                    
                    # Check for permission_required errors in result
                    try:
                        res_dict = json.loads(res_str)
                        if isinstance(res_dict, dict) and res_dict.get("error_type") == "permission_required":
                            pause_info = {
                                "permission": res_dict.get("permission", "unknown"),
                                "message": res_dict.get("error", "Permission required"),
                                "settings_url": res_dict.get("settings_url", "")
                            }
                    except (json.JSONDecodeError, TypeError):
                            pass
            
            # If we executed tools, append results to content
            if results:
                content += "\n\nTool Results:\n" + "\n".join(results)
                # Add explicit success marker if no errors occurred
                if not had_failure and not pause_info:
                    success_marker = "[STEP_COMPLETED]" if "[STEP_COMPLETED]" not in content else ""
                    if success_marker:
                        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
                        desc = "All actions completed, verification can begin." if lang != "uk" else "Всі дії виконано, верифікацію можна починати."
                        content += f"\n\n{success_marker} {desc}"

            # Save successful action to RAG memory (only if no pause and learning mode is ON)
            if not pause_info and state.get("learning_mode", True):
                try:
                    action_summary = f"Task: {last_msg[:100]}\nTools used: {[t.get('name') for t in tool_calls]}\nResult: Success"
                    self.memory.add_memory("strategies", action_summary, {"type": "tetyana_action"})
                except Exception:
                    pass
            
            # Hybrid fallback: if native attempt failed and GUI fallback is allowed, switch execution_mode
            if (
                (not pause_info)
                and had_failure
                and (execution_mode != "gui")
                and (gui_mode in {"auto", "on"})
                and (not gui_fallback_attempted)
            ):
                # Tell the graph to retry this step in GUI mode.
                lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
                msg = MESSAGES[lang]["native_failed_switching_gui"]
                updated_messages = list(context) + [AIMessage(content=msg)]
                
                try:
                    trace(self.logger, "tetyana_gui_fallback", {"from": execution_mode, "to": "gui"})
                except Exception:
                    pass
                return {
                    "current_agent": "tetyana",
                    "messages": updated_messages,
                    "execution_mode": "gui",
                    "gui_fallback_attempted": True,
                    "gui_mode": gui_mode,
                    "last_step_status": "failed", # Retrying in GUI mode counts as a fail for the native step
                }
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Tetyana] Exception: {e}")
            content = f"Error invoking Tetyana: {e}"
        
        # If paused, return to atlas with pause_info
        if pause_info:
            updated_messages = list(context) + [AIMessage(content=f"[ПАУЗОВАНО] {pause_info['message']}")]
            
            try:
                trace(self.logger, "tetyana_paused", {"pause_info": pause_info})
            except Exception:
                pass
            return {
                "current_agent": "meta_planner",
                "messages": updated_messages,
                "pause_info": pause_info,
                "last_step_status": "uncertain"
            }
        
        # Preserve existing messages and add new one
        updated_messages = list(context) + [AIMessage(content=content)]
        
        # Extract tool context for Grisha's vision verification
        used_tools = [t.get("name") for t in tool_calls] if tool_calls else []
        tool_args_context = {}
        for t in (tool_calls or []):
            name = t.get("name", "")
            args = t.get("args", {})
            # Extract app/window context from tool arguments
            if "app" in args or "app_name" in args:
                tool_args_context["app_name"] = args.get("app_name") or args.get("app")
            if "window" in args or "window_title" in args:
                tool_args_context["window_title"] = args.get("window_title") or args.get("window")
            if "url" in args:
                tool_args_context["url"] = args.get("url")
            # Playwright tools
            if name.startswith("playwright."):
                tool_args_context["browser_tool"] = True
            # PyAutoGUI tools
            if name.startswith("pyautogui."):
                tool_args_context["gui_tool"] = True
        
        try:
            trace(self.logger, "tetyana_exit", {
                "next_agent": "grisha",
                "last_step_status": "failed" if had_failure else "success",
                "execution_mode": execution_mode,
                "gui_mode": gui_mode,
                "dev_edit_mode": dev_edit_mode,
                "used_tools": used_tools,
            })
        except Exception:
            pass
        return {
            "current_agent": "grisha", 
            "messages": updated_messages,
            "execution_mode": execution_mode,
            "gui_mode": gui_mode,
            "gui_fallback_attempted": gui_fallback_attempted,
            "dev_edit_mode": dev_edit_mode,
            "last_step_status": "failed" if had_failure else "success",
            "tetyana_used_tools": used_tools,
            "tetyana_tool_context": tool_args_context,
        }

    def _grisha_node(self, state: TrinityState):
        if self.verbose: print("👁️ [Grisha] Verifying...")
        context = state.get("messages", [])
        if not context:
            return {"current_agent": "end", "messages": [AIMessage(content="[VOICE] Немає контексту для перевірки.")]}
        last_msg = getattr(context[-1], "content", "") if context and len(context) > 0 and context[-1] is not None else ""
        if isinstance(last_msg, str) and len(last_msg) > 50000:
            last_msg = last_msg[:45000] + "\n\n[... TRUNCATED DUE TO SIZE ...]\n\n" + last_msg[-5000:]
        tool_calls = [] # Initialize for scope safety
        
        gui_mode = str(state.get("gui_mode") or "auto").strip().lower()
        execution_mode = str(state.get("execution_mode") or "native").strip().lower()

        try:
            plan_preview = state.get("plan")
            trace(self.logger, "grisha_enter", {
                "step_count": state.get("step_count"),
                "replan_count": state.get("replan_count"),
                "plan_len": len(plan_preview) if isinstance(plan_preview, list) else 0,
                "task_type": state.get("task_type"),
                "gui_mode": gui_mode,
                "execution_mode": execution_mode,
                "last_msg_preview": str(last_msg)[:200],
            })
        except Exception:
            pass
        
        # Check for code changes in critical directories and run tests
        test_results = ""
        critical_dirs = ["core/", "system_ai/", "tui/", "providers/"]
        try:
            # Check if we should even verify tests based on task type
            task_type = str(state.get("task_type") or "").strip().upper()
            should_skip_tests = (task_type == "GENERAL")
            
            repo_changes = self._get_repo_changes()
            changed_files = []
            if isinstance(repo_changes, dict) and repo_changes.get("ok") is True:
                changed_files = list(repo_changes.get("changed_files") or [])
            
            has_critical_changes = any(
                any(f.startswith(d) for d in critical_dirs) 
                for f in changed_files
            )
            
            try:
                trace(self.logger, "grisha_verification_check", {
                    "task_type": task_type,
                    "critical_changes": has_critical_changes,
                    "changed_files": changed_files,
                    "skip": should_skip_tests
                })
            except Exception:
                pass
            
            if has_critical_changes and not should_skip_tests:
                if self.verbose:
                    print("👁️ [Grisha] Detected changes in critical directories. Running pytest...")
                # Run pytest
                test_cmd = "pytest -q --tb=short 2>&1"
                test_proc = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, cwd=self._get_git_root() or ".")
                test_output = test_proc.stdout + test_proc.stderr
                test_results = f"\n\n[TEST_VERIFICATION] pytest output:\n{test_output}"
                
                if self.verbose:
                    print(f"👁️ [Grisha] Test results:\n{test_output[:200]}...")
            else:
                 if self.verbose:
                    print("👁️ [Grisha] Skipping extensive tests (simple task or no critical changes).")
                    
        except Exception as e:
            if self.verbose:
                print(f"👁️ [Grisha] Test execution error: {e}")
        
        # Inject available tools (Vision priority)
        # RESTRICTED: Grisha only gets read-only tools
        all_tools = self.registry.list_tools()
        allowed_prefixes = ["capture_", "analyze_", "browser_screenshot", "browser_get_", "chrome_active_tab", "read_", "list_", "run_shell"]
        # Explicit allow-list for safety
        allowed_tools_list = []
        # We need a way to parse the tools_list string or object. 
        # Assuming list_tools returns a string description, we might need to filter at execution time mostly.
        # But `tools_list` variable is passed to prompt. Ideally we filter it.
        # Check if list_tools returns a raw list or string. 
        # Based on typical usage, it returns a string description. 
        # For prompt safety, we will append a STRICT WARNING instead of parsing the string complexly.
        
        tools_desc = self.registry.list_tools()
        
        plan = state.get("plan") or []
        current_step_desc = plan[0].get("description", "Unknown") if plan else "Final Verification"
        
        # Extract just Tetyana's tool results from last_msg for clearer context
        tetyana_result_summary = ""
        if "[STEP_COMPLETED]" in last_msg:
            tetyana_result_summary = "Tetyana reported: [STEP_COMPLETED] - action succeeded"
        elif "Tool Results:" in last_msg:
            # Extract just the tool results section
            try:
                tool_results_start = last_msg.find("Tool Results:")
                tool_results_end = last_msg.find("[STEP_COMPLETED]", tool_results_start)
                if tool_results_end == -1:
                    tool_results_end = len(last_msg)
                tetyana_result_summary = last_msg[tool_results_start:tool_results_end].strip()
            except Exception:
                tetyana_result_summary = last_msg[:500]
        else:
            tetyana_result_summary = last_msg[:500] if len(last_msg) > 500 else last_msg
        
        original_task = state.get("original_task") or ""
        
        # CRITICAL: Make the verification context very explicit about what to verify
        verify_context = f"""🎯 VERIFICATION TASK:

GLOBAL GOAL (for reference only): {original_task}

⚡ CURRENT STEP TO VERIFY: {current_step_desc}

📋 TETYANA'S REPORT:
{tetyana_result_summary}

❓ YOUR TASK: Did the CURRENT STEP "{current_step_desc}" complete successfully?
- If YES → respond with [STEP_COMPLETED]
- If there was an error → respond with [FAILED]
- If unsure → use vision tools first, then decide

⚠️ IMPORTANT: Do NOT evaluate the global goal yet! Only verify the current step."""
        
        if state.get("is_media"):
            prompt = get_grisha_media_prompt(verify_context, tools_desc=tools_desc, preferred_language=self.preferred_language)
        else:
            prompt = get_grisha_prompt(
                verify_context, 
                tools_desc=tools_desc, 
                preferred_language=self.preferred_language,
                vision_context=self.vision_context_manager.current_context
            )
        
        content = ""  # Initialize content variable
        executed_tools_results = [] # Keep track of results for verdict phase

        try:
            trace(self.logger, "grisha_llm_start", {"prompt_len": len(str(prompt.format_messages()))})
            # For tool-bound calls, use invoke_with_stream to capture deltas for the TUI
            def on_delta(chunk):
                self._deduplicated_stream("grisha", chunk)
            
            # Use Grisha-specific LLM
            grisha_model = os.getenv("GRISHA_MODEL") or os.getenv("COPILOT_MODEL") or "gpt-4.1"
            grisha_llm = CopilotLLM(model_name=grisha_model)
            
            response = grisha_llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
            content = getattr(response, "content", "") if response is not None else ""
            tool_calls = getattr(response, "tool_calls", []) if response is not None and hasattr(response, 'tool_calls') else []
            
            try:
                trace(self.logger, "grisha_llm", {
                    "tool_calls": len(tool_calls) if isinstance(tool_calls, list) else 0,
                    "content_preview": str(content)[:200],
                })
            except Exception:
                pass
            
            # Execute Tools
            if tool_calls:
                 for tool in tool_calls:
                     name = tool.get("name")
                     args = tool.get("args") or {}
                     
                     # ⛔️ RUNTIME BLOCK FOR GRISHA ⛔️
                     # She is NOT allowed to navigate or click.
                     forbidden_prefixes = ["browser_open", "browser_click", "browser_type", "write_", "create_", "delete_", "move_"]
                     if any(name.startswith(p) for p in forbidden_prefixes):
                         res_str = f"Result for {name}: [BLOCKED] Grisha is a read-only agent. Navigation/Modification blocked."
                         if self.verbose:
                             print(f"🛑 [Grisha] Blocked forbidden tool: {name}")
                         executed_tools_results.append(res_str)
                         continue

                     # Provide helpful default for capture_screen if args empty
                     if name == "capture_screen" and not args:
                         args = {"app_name": None}

                     # Execute via MCP Registry
                     res = self.registry.execute(name, args)
                     res_str = f"Result for {name}: {res}"
                     executed_tools_results.append(res_str)
            
            if executed_tools_results:
                content += "\n\nVerification Tools Results:\n" + "\n".join(executed_tools_results)
            
            # Append test results if any
            if test_results:
                content += test_results
                executed_tools_results.append(test_results)

            # --- SMART VISION VERIFICATION ---
            # Determine if and how to capture screen based on Tetyana's actions
            tetyana_tools = state.get("tetyana_used_tools") or []
            tetyana_context = state.get("tetyana_tool_context") or {}
            
            # Define tool categories for smart detection
            gui_visual_tools = {"click", "type_text", "move_mouse", "press_key", "find_image_on_screen"}
            browser_tools = {"browser_open_url", "browser_click", "browser_type", "browser_type_text", "browser_get_links", "browser_screenshot", "browser_navigate", "browser_press_key"}
            playwright_tools = {t for t in tetyana_tools if t.startswith("playwright.")}
            pyautogui_tools = {t for t in tetyana_tools if t.startswith("pyautogui.")}
            
            # Check if visual verification is needed
            used_gui_tools = bool(set(tetyana_tools) & gui_visual_tools) or bool(pyautogui_tools)
            used_browser_tools = bool(set(tetyana_tools) & browser_tools) or bool(playwright_tools)
            # Check last_msg (Tetyana's output) for browser indicators, not content (Grisha's LLM response)
            is_browser_task = "browser_" in last_msg.lower() or "браузер" in last_msg.lower() or tetyana_context.get("browser_tool")
            needs_visual_verification = used_gui_tools or used_browser_tools or is_browser_task
            
            if self.verbose:
                print(f"👁️ [Grisha] Visual check: tetyana_tools={tetyana_tools}, used_browser={used_browser_tools}, is_browser_task={is_browser_task}, needs_visual={needs_visual_verification}")
            
            # Determine the best screenshot method
            vision_args = {}
            vision_method = "full_screen"  # default
            
            if tetyana_context.get("app_name"):
                # Specific app was used - capture that app's window
                vision_args["app_name"] = tetyana_context["app_name"]
                vision_method = "app_window"
                if tetyana_context.get("window_title"):
                    vision_args["window_title"] = tetyana_context["window_title"]
                    vision_method = "specific_window"
            elif used_browser_tools or playwright_tools or is_browser_task:
                # Browser task - try to capture browser window
                # Do NOT default to Safari blindly, as Playwright might use Chromium/Firefox
                # vision_args["app_name"] = "Safari" 
                vision_method = "browser"
                
                # Try to detect actual browser from tool results
                detected_browser = None
                for browser in ["Chrome", "Safari", "Firefox", "Arc", "Brave", "Chromium"]:
                    if browser.lower() in content.lower():
                        detected_browser = browser
                        break
                
                if detected_browser:
                    vision_args["app_name"] = detected_browser
                else:
                    # If no specific browser detected, rely on full screen / multi-monitor capture
                    # This avoids capturing an empty Safari window when Chrome is used
                    vision_method = "full_screen_browser_context"
            elif pyautogui_tools or used_gui_tools:
                # GUI automation - need to detect active window
                vision_method = "active_window"
                # We'll use full screen but could enhance to get frontmost app
            
            forced_verification_run = False
            
            if needs_visual_verification or (gui_mode in {"auto", "on"} and execution_mode == "gui"):
                if self.verbose:
                    print(f"👁️ [Grisha] Vision verification: method={vision_method}, args={vision_args}")
                
                # CRITICAL: Wait for browser/GUI to settle after Tetyana's actions
                # Without this delay, Grisha captures stale screenshots before page updates
                browser_action_tools = {"browser_type_text", "browser_click", "browser_open_url", "browser_navigate"}
                used_browser_actions = bool(set(tetyana_tools or []) & browser_action_tools)
                
                if used_browser_actions:
                    import time
                    wait_time = 3.0  # seconds - allow page to load/update after actions
                    if self.verbose:
                        print(f"👁️ [Grisha] Waiting {wait_time}s for browser to settle...")
                    try:
                        trace(self.logger, "grisha_browser_wait", {"wait_time": wait_time, "reason": "browser_action_detected"})
                    except Exception:
                        pass
                    time.sleep(wait_time)
                
                # Use enhanced vision with smart context
                analysis = self.registry.execute("enhanced_vision_analysis", vision_args)
                
                # CRITICAL: Update vision context manager with fresh analysis data
                # This ensures Grisha's prompt has accurate, current visual context
                if isinstance(analysis, dict) and analysis.get("status") == "success":
                    try:
                        self.vision_context_manager.update_context(analysis)
                        if self.verbose:
                            print(f"👁️ [Grisha] Vision context updated successfully")
                    except Exception as ve:
                        if self.verbose:
                            print(f"👁️ [Grisha] Vision context update failed: {ve}")
                
                analysis_res = f"\n[GUI_BROWSER_VERIFY] enhanced_vision_analysis (method={vision_method}):\n{analysis}"
                content += analysis_res
                executed_tools_results.append(analysis_res)
                forced_verification_run = True

                try:
                    # Attempt to extract image path from analysis result for further analyze_screen if needed
                    # Note: enhanced_vision_analysis result structure is different
                    if isinstance(analysis, dict):
                        img_path = analysis.get("diff_image_path") or analysis.get("path")
                    else:
                        analysis_dict = json.loads(analysis)
                        img_path = analysis_dict.get("diff_image_path") or analysis_dict.get("path")
                except Exception:
                    img_path = None
                
                if img_path:
                    # Optional: still use LLM analysis on the diff image for high-level understanding
                    analysis_llm = self.registry.execute(
                        "analyze_screen",
                        {"image_path": img_path, "prompt": "Based on this (potentially highlighted diff) image and the goal, provide a final confirmation of success or failure. Focus on specific UI changes."},
                    )
                    analysis_res_llm = f"\n[GUI_VERIFY_LLM] analyze_screen:\n{analysis_llm}"
                    content += analysis_res_llm
                    executed_tools_results.append(analysis_res_llm)

        except Exception as e:
            content = f"Error invoking Grisha: {e}"
            executed_tools_results.append(f"Error: {e}")

        # --- VERDICT PHASE ---
        # If tools were executed (voluntarily or forced), we must ask Grisha to ANALYZE the results.
        # Otherwise, he often ignores them or assumes uncertainty.
        
        has_tools_run = bool(executed_tools_results)
        verdict_content = content
        
        if has_tools_run:
            if self.verbose: print(f"👁️ [Grisha] Analyzing {len(executed_tools_results)} tool results for Verdict...")
            
            verdict_prompt_txt = (
                "Here are the verification results obtained from the tools:\n" + 
                "\n".join(executed_tools_results) + 
                "\n\nBased on these results and history, provide your FINAL verdict.\n"
                "IMPORTANT: Distinguish between CURRENT STEP success and GLOBAL GOAL success.\n"
                "You MUST respond with exactly ONE of these markers at the VERY END of your message:\n"
                "- [VERIFIED] (if the Global Goal is fully achieved and no more actions are needed)\n"
                "- [STEP_COMPLETED] (if the current step succeeded and we should move to the next part of the plan, but the Global Goal is NOT yet reached)\n"
                "- [FAILED] (if the current step failed, an error occurred, or the goal is unachievable)\n"
                "- [UNCERTAIN] (if results are truly inconclusive)\n\n"
                "Explain your reasoning briefly before the marker."
            )
            
            verdict_msgs = [
                SystemMessage(content="You are Grisha, analyzing verification data."),
                HumanMessage(content=verdict_prompt_txt)
            ]
            
            # We don't stream the verdict, just get it
            try:
                verdict_resp = self.llm.invoke(verdict_msgs)
                verdict_content_to_add = getattr(verdict_resp, "content", "") if verdict_resp is not None else ""
                verdict_content += "\n\n[VERDICT ANALYSIS]\n" + verdict_content_to_add
            except Exception as e:
                verdict_content += f"\n\n[VERDICT ERROR] Could not get verdict: {e}"

        # If Grisha says "CONFIRMED" or "VERIFIED", we end. Else Atlas replans.
        # Sanitize verdict content to avoid meta-instructions (from other agents) causing false failures
        lower_content = verdict_content.lower()
        sanitized_lower_content = lower_content
        # Remove known meta-instruction noise that may appear in agent messages
        for noise in ["error: no tool call provided", "stop talking, use a tool"]:
            sanitized_lower_content = sanitized_lower_content.replace(noise, "")
        # Collapse whitespace for more robust keyword matching
        sanitized_lower_content = " ".join(sanitized_lower_content.split())
        step_status = "uncertain"
        next_agent = "meta_planner"

        # 1. Check for explicit FAILURE markers first (Priority)
        # Use sanitized content for failure/success detection to avoid false positives
        has_explicit_fail = any(f"[{m}]" in sanitized_lower_content or m in sanitized_lower_content for m in FAILURE_MARKERS)
        
        # 2. Check for explicit SUCCESS markers
        has_explicit_complete = any(f"[{m}]" in sanitized_lower_content or m in sanitized_lower_content for m in SUCCESS_MARKERS)
        # 3. Check for tool execution errors in context
        latest_tools_result = "\n".join(executed_tools_results).lower()
        has_tool_error_in_context = '"status": "error"' in latest_tools_result
        
        # 4. Check for test failures
        has_test_failure = "[test_verification]" in lower_content and ("failed" in lower_content or "error" in lower_content)
        
        # 5. Markers analysis (Failure takes precedence)
        if has_explicit_fail:
             step_status = "failed"
             next_agent = "meta_planner"
        elif has_test_failure:
            step_status = "failed"
            next_agent = "meta_planner"
        elif has_tool_error_in_context:
            # If the tool failed, we default to failed unless EXPLICITLY confirmed (safe default)
            # But even if [VERIFIED] is present, tool error is suspicious. 
            # We trust [VERIFIED] only if there are NO tool errors.
            if has_explicit_complete:
                 # Ambiguous: Tool error but LLM says verified. 
                 # Trust LLM only if it explained why the error is fine? 
                 # For safety, let's downgrade to UNCERTAIN or FAILED.
                 # Let's say FAILED to force replan/retry.
                 step_status = "failed"
            else:
                 step_status = "failed"
            next_agent = "meta_planner"
        elif "[captcha]" in lower_content or "captcha detected" in lower_content:
            step_status = "uncertain"
            next_agent = "meta_planner"
        elif has_explicit_complete:
            # CHECK FOR NEGATIONS: if 'not' or 'не' is near the marker
            is_negated = False
            lang_negations = NEGATION_PATTERNS.get(self.preferred_language, NEGATION_PATTERNS["en"])
            
            for kw in SUCCESS_MARKERS:
                if kw in lower_content:
                    for match in re.finditer(re.escape(kw), lower_content):
                        idx = match.start()
                        pre_text = lower_content[max(0, idx-25):idx]
                        if re.search(lang_negations, pre_text):
                            is_negated = True
                            break
                if is_negated: break
            
            if not is_negated:
                step_status = "success"
                next_agent = "meta_planner"
            else:
                step_status = "failed"
                next_agent = "meta_planner"

        # NEW: Anti-loop protection via uncertain_streak
        current_streak = int(state.get("uncertain_streak") or 0)
        
        # If still uncertain and no tools were run (and we haven't forced them yet)
        if step_status == "uncertain" and not has_tools_run:
             # Force verification if we haven't already
             pass # We can't easily force it here without recursion or complex logic. 
                  # Ideally the first prompt should have triggered tools. 
                  # If we are here, Grisha produced text without tools and without a verdict.
        
        if step_status in {"uncertain", "failed"}:
            current_streak += 1
        else:
            current_streak = 0  # Reset on definite decision (success)
        
        # If 3+ consecutive uncertain decisions, consider forcing completion
        vision_shows_failure = any(kw in sanitized_lower_content for kw in VISION_FAILURE_KEYWORDS)
        
        if step_status == "uncertain" and current_streak >= 3:
            if vision_shows_failure or "[failed]" in lower_content:
                if self.verbose:
                    print(f"⚠️ [Grisha] Uncertainty streak ({current_streak}) but failure detected → triggering REPLAN")
                step_status = "failed"
                # Add explainer
                verdict_content += "\n\n[SYSTEM] Uncertainty limit reached with negative evidence. Marking as FAILED."
                current_streak = 0
            else:
                # If ambiguous but no obvious failure, force FAIL to be safe (replan is safer than fake success)
                if self.verbose:
                    print(f"⚠️ [Grisha] Uncertainty streak ({current_streak}) reached limit → forcing FAILED (conclusive verification failed)")
                step_status = "failed"
                verdict_content += "\n\n[SYSTEM] Uncertainty limit reached. Consistency check failed. Marking as FAILED."
                current_streak = 0

        try:
            trace(self.logger, "grisha_decision", {"next_agent": next_agent, "last_step_status": step_status, "uncertain_streak": current_streak})
        except Exception:
            pass

        out = {
            "current_agent": next_agent, 
            "messages": list(context) + [AIMessage(content=verdict_content)],
            "last_step_status": step_status,
            "uncertain_streak": current_streak,
            "plan": state.get("plan"),  # Always preserve plan in state
        }
        
        return out

    def _router(self, state: TrinityState):
        current = state.get("current_agent", "meta_planner")  # Safe default to meta_planner
        
        # Check for Vibe CLI Assistant pause state
        if state.get("vibe_assistant_pause"):
            pause_info = state.get("vibe_assistant_pause")
            if pause_info is None:
                # Corrupted pause state, reset
                state["vibe_assistant_pause"] = None
                return current
            
            # Try auto-repair if enabled
            if self.vibe_assistant.should_attempt_auto_repair(pause_info):
                if self.verbose:
                    self.logger.info("🔧 Doctor Vibe: Attempting auto-repair...")
                
                repair_result = self.vibe_assistant.attempt_auto_repair(pause_info)
                
                if repair_result and repair_result.get("success"):
                    # Auto-repair succeeded - clear pause and continue
                    if self.verbose:
                        self.logger.info(f"✅ Doctor Vibe: Auto-repair successful! Resuming execution.")
                    
                    # Clear pause state in vibe_assistant (already done by attempt_auto_repair)
                    # Update state to remove pause
                    state["vibe_assistant_pause"] = None
                    state["vibe_assistant_context"] = f"AUTO-REPAIRED: {repair_result.get('message', 'Fixed') if repair_result else 'Fixed'}"
                    
                    # Reset failure counters to give system fresh start
                    state["current_step_fail_count"] = 0
                    state["uncertain_streak"] = 0
                    
                    # Return to meta_planner for fresh planning after repair
                    return "meta_planner"
                else:
                    # Auto-repair failed - keep paused, wait for human
                    if self.verbose:
                        self.logger.warning(f"⚠️ Doctor Vibe: Auto-repair failed. Waiting for human intervention.")
                    return current
            
            # No auto-repair - stay paused
            if self.verbose:
                self.logger.info(f"Vibe CLI Assistant PAUSE: {pause_info.get('message', 'No reason provided')}")
            return current
        
        # Check if Vibe CLI Assistant intervention is needed
        pause_context = self._check_for_vibe_assistant_intervention(state)
        if pause_context:
            # Check if we should try auto-repair first
            if pause_context.get("auto_resume_available", False) or pause_context.get("background_mode", False):
                if self.vibe_assistant.should_attempt_auto_repair(pause_context):
                    repair_result = self.vibe_assistant.attempt_auto_repair(pause_context)
                    if repair_result and repair_result.get("success"):
                        # Fixed before even creating pause - continue normally
                        if self.verbose:
                            self.logger.info("🔧 Doctor Vibe: Pre-emptive repair successful!")
                        return current  # Continue without pause
            
            # Create pause state and return to current agent
            new_state = self._create_vibe_assistant_pause_state(state, 
                                                               pause_context.get("reason", "unknown"), 
                                                               pause_context.get("message", "Unknown pause reason"))
            # Update the state in the workflow
            # We'll handle this in the node functions
            if self.verbose:
                self.logger.info(f"Vibe CLI Assistant INTERVENTION: {pause_context.get('message', 'Unknown reason')}")
            return current
        
        try:
            # Check for completion to trigger learning
            # If current is 'end', we check if we should go to 'knowledge' first
            if current == "end":
                # ANTI-LOOP: If we were already in knowledge, just end
                # We can check the messages or a specific state flag if we added one.
                # But simpler: if the last message was from Grisha/Meta and contains success, go to knowledge.
                # If the last message was from Knowledge, then it's really the end.
                
                # Check the message history to see who sent the last message
                messages = state.get("messages", [])
                if messages and isinstance(messages[-1], AIMessage):
                    content = getattr(messages[-1], "content", "").lower() if messages[-1] is not None else ""
                    # If it sounds like success AND it's not a message from the knowledge node itself
                    if any(x in content for x in ["завершена", "готово", "виконано", "completed", "success"]):
                        # Simple heuristic: if the message doesn't mention "experience stored" (which knowledge node does)
                        if "experience stored" not in content and "досвід збережено" not in content:
                            return "knowledge"

            trace(self.logger, "router_decision", {"current": current, "next": current})
        except Exception:
            pass
        return current

    # _extract_json_object was moved to the top of the class to avoid duplication.

    def _knowledge_node(self, state: TrinityState):
        """Final node to extract and store knowledge (success or failure) from completion."""
        if self.verbose: print("🧠 [Learning] Extracting structured experience...")
        context = state.get("messages", [])
        plan = state.get("plan") or []
        summary = state.get("summary", "")
        replan_count = state.get("replan_count", 0)
        last_status = state.get("last_step_status", "success")
        
        # Determine status: if we are here via 'success' tags, it's a win.
        # But we should also be able to learn from failures.
        actual_status = "success"
        if last_status == "failed":
            actual_status = "failed"
        elif context and len(context) > 0 and context[-1] is not None:
            last_content = getattr(context[-1], "content", "").lower()
            if "failed" in last_content:
                actual_status = "failed"
            
        # Self-evaluation of confidence
        if actual_status == "success":
            confidence = 1.0 - (min(replan_count, 5) * 0.1) - (min(len(plan), 10) * 0.02)
        else:
            confidence = 0.5 # Failures have neutral confidence (they are certain warnings)
            
        confidence = max(0.1, round(confidence, 2))
        
        try:
            # Create a structured memory entry
            experience = f"Task: {summary}\nStatus: {actual_status}\nSteps: {len(plan)}\n"
            if plan:
                experience += "Plan Summary:\n" + "\n".join([f"- {s.get('description')}" for s in plan])
            
            # Save to knowledge_base
            self.memory.add_memory(
                category="knowledge_base",
                content=experience,
                metadata={
                    "type": "experience_log",
                    "status": actual_status,
                    "source": "trinity_runtime",
                    "timestamp": int(time.time()),
                    "confidence": confidence,
                    "replan_count": replan_count
                }
            )
            
            if self.verbose: 
                stored_msg = f"🧠 [Learning] {actual_status.upper()} experience stored (conf: {confidence})"
                print(stored_msg)
            
            try:
                trace(self.logger, "knowledge_stored", {"status": actual_status, "confidence": confidence})
            except Exception:
                pass
                
        except Exception as e:
            if self.verbose: print(f"⚠️ [Learning] Error: {e}")
            
        final_msg = "[VOICE] Досвід збережено. Завдання завершено." if self.preferred_language == "uk" else "[VOICE] Experience stored. Task completed."
        return {
            "current_agent": "end",
            "messages": context + [AIMessage(content=final_msg)]
        }

    def _get_git_root(self) -> Optional[str]:
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                return None
            root = (proc.stdout or "").strip()
            return root or None
        except Exception:
            return None

    def _get_project_structure_context(self) -> str:
        """Read project_structure_final.txt for Atlas context."""
        try:
            git_root = self._get_git_root()
            if not git_root:
                return ""
            
            structure_file = os.path.join(git_root, "project_structure_final.txt")
            if not os.path.exists(structure_file):
                return ""
            
            # Read only first part of file to avoid memory issues with huge files
            # then process carefully
            with open(structure_file, 'r', encoding='utf-8') as f:
                # Read up to 100kb of the file
                content = f.read(100000)
            
            # Extract key sections for context (Metadata, Program Execution Logs, Project Structure)
            lines = content.split('\n')
            context_lines = []
            current_section = None
            section_count = 0
            
            for line in lines:
                # Each line limited to 500 chars to avoid prompt blowup
                line = line[:500]
                
                # Identify sections
                lstrip = line.strip()
                if lstrip.startswith('## Metadata'):
                    current_section = 'metadata'
                    section_count = 0
                elif '## Program Execution Logs' in lstrip:
                    current_section = 'logs'
                    section_count = 0
                elif '## Project Structure' in lstrip:
                    current_section = 'structure'
                    section_count = 0
                elif lstrip.startswith('## ') and current_section:
                    # If it's a new section we don't care about, stop capturing
                    if not any(x in lstrip for x in ['Metadata', 'Logs', 'Structure']):
                        current_section = None
                
                # Collect lines (limit per section to avoid bias)
                if current_section:
                    if section_count < 30: # Max 30 lines per section
                         if lstrip and not lstrip.startswith('```'):
                            context_lines.append(line)
                            section_count += 1
            
            # Final safety cut
            return '\n'.join(context_lines[:150]) 
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Trinity] Error reading project structure: {e}")
            return ""

    def _regenerate_project_structure(self, response_text: str) -> bool:
        """Regenerate project_structure_final.txt with last response."""
        try:
            git_root = self._get_git_root()
            if not git_root:
                if self.verbose:
                    print("⚠️ [Trinity] Not a git repo, skipping structure regeneration")
                return False
            
            # Save response to .last_response.txt
            response_file = os.path.join(git_root, ".last_response.txt")
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(response_text)
            
            # Run regenerate_structure.sh
            regenerate_script = os.path.join(git_root, "regenerate_structure.sh")
            if not os.path.exists(regenerate_script):
                if self.verbose:
                    print("⚠️ [Trinity] regenerate_structure.sh not found")
                return False
            
            result = subprocess.run(
                ["bash", regenerate_script],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                if self.verbose:
                    print("✓ [Trinity] Project structure regenerated")
                return True
            else:
                if self.verbose:
                    print(f"⚠️ [Trinity] Structure regeneration failed: {result.stderr}")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Trinity] Error regenerating structure: {e}")
            return False

    def _get_repo_changes(self) -> Dict[str, Any]:
        root = self._get_git_root()
        if not root:
            return {"ok": False, "error": "not_a_git_repo"}

        try:
            diff_name = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            diff_stat = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=root,
                capture_output=True,
                text=True,
            )

            changed_files: List[str] = []
            if diff_name.returncode == 0:
                changed_files.extend([l.strip() for l in (diff_name.stdout or "").splitlines() if l.strip()])

            if status.returncode == 0:
                for line in (status.stdout or "").splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    parts = s.split(maxsplit=1)
                    if len(parts) == 2:
                        changed_files.append(parts[1].strip())

            # de-dup while preserving order
            seen = set()
            deduped: List[str] = []
            for f in changed_files:
                if f in seen:
                    continue
                seen.add(f)
                deduped.append(f)

            return {
                "ok": True,
                "git_root": root,
                "changed_files": deduped,
                "diff_stat": (diff_stat.stdout or "").strip() if diff_stat.returncode == 0 else "",
                "status_porcelain": (status.stdout or "").strip() if status.returncode == 0 else "",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _short_task_for_commit(self, task: str, max_len: int = 72) -> str:
        t = re.sub(r"\s+", " ", str(task or "").strip())
        if not t:
            return "(no task)"
        if len(t) <= max_len:
            return t
        cut = t[: max_len - 1].rstrip()
        return cut + "…"

    def _auto_commit_on_success(self, *, task: str, report: str, repo_changes: Dict[str, Any]) -> Dict[str, Any]:
        root = self._get_git_root()
        if not root:
            return {"ok": False, "error": "not_a_git_repo"}

        try:
            env = os.environ.copy()
            env.setdefault("GIT_AUTHOR_NAME", "Trinity")
            env.setdefault("GIT_AUTHOR_EMAIL", "trinity@local")
            env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
            env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])

            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            if status.returncode != 0:
                return {"ok": False, "error": (status.stderr or "").strip() or "git status failed"}

            has_changes = bool((status.stdout or "").strip())

            short_task = self._short_task_for_commit(task)
            subject = f"Trinity task completed: {short_task}"

            diff_stat = str(repo_changes.get("diff_stat") or "").strip() if isinstance(repo_changes, dict) else ""
            body_lines: List[str] = []
            if diff_stat:
                body_lines.append("Diff stat:")
                body_lines.append(diff_stat)
            body = "\n".join(body_lines).strip()

            add = subprocess.run(
                ["git", "add", "."],
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            if add.returncode != 0:
                return {"ok": False, "error": (add.stderr or "").strip() or "git add failed"}

            commit_cmd: List[str] = [
                "git",
                "-c",
                "user.name=Trinity",
                "-c",
                "user.email=trinity@local",
                "commit",
                "--allow-empty",
                "-m",
                subject,
            ]
            if body:
                commit_cmd.extend(["-m", body])

            env_commit = env.copy()
            env_commit["TRINITY_POST_COMMIT_RUNNING"] = "1"
            commit = subprocess.run(
                commit_cmd,
                cwd=root,
                capture_output=True,
                text=True,
                env=env_commit,
            )
            if commit.returncode != 0:
                combined = (commit.stdout or "") + "\n" + (commit.stderr or "")
                if "nothing to commit" in combined.lower():
                    if not has_changes:
                        return {"ok": True, "skipped": True, "reason": "nothing_to_commit"}
                return {"ok": False, "error": (commit.stderr or "").strip() or "git commit failed"}

            structure_ok = self._regenerate_project_structure(report)
            amended = False
            response_path = os.path.join(root, ".last_response.txt")

            if os.path.exists(response_path):
                subprocess.run(
                    ["git", "add", ".last_response.txt"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    env=env,
                )

            if structure_ok and os.path.exists(os.path.join(root, "project_structure_final.txt")):
                subprocess.run(
                    ["git", "add", "-f", "project_structure_final.txt"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    env=env,
                )

            cached = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            if cached.returncode != 0:
                env_amend = env.copy()
                env_amend["TRINITY_POST_COMMIT_RUNNING"] = "1"
                amend = subprocess.run(
                    ["git", "commit", "--amend", "--no-edit"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    env=env_amend,
                )
                if amend.returncode == 0:
                    amended = True

            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            commit_hash = (head.stdout or "").strip() if head.returncode == 0 else ""
            return {
                "ok": True,
                "skipped": False,
                "commit": commit_hash,
                "structure_ok": bool(structure_ok),
                "amended": bool(amended),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _format_final_report(
        self,
        *,
        task: str,
        outcome: str,
        repo_changes: Dict[str, Any],
        last_agent: str,
        last_message: str,
        replan_count: int = 0,
        commit_hash: Optional[str] = None,
    ) -> str:
        lines: List[str] = []
        lines.append("[Atlas] Final report")
        lines.append("")
        lines.append(f"Task: {str(task or '').strip()}")
        lines.append(f"Outcome: {outcome}")
        lines.append(f"Replans: {replan_count}")
        if commit_hash:
            lines.append(f"Зміни закомічені: {commit_hash}")
        lines.append(f"Last agent: {last_agent}")
        if last_message:
            lines.append("")
            lines.append("Last message:")
            lines.append(str(last_message).strip())

        lines.append("")
        if repo_changes.get("ok") is True:
            files = repo_changes.get("changed_files") or []
            lines.append("Changed files:")
            if files:
                for f in files:
                    lines.append(f"- {f}")
            else:
                lines.append("- (no uncommitted changes detected)")

            stat = str(repo_changes.get("diff_stat") or "").strip()
            if stat:
                lines.append("")
                lines.append("Diff stat:")
                lines.append(stat)
        else:
            lines.append("Changed files:")
            lines.append(f"- (unavailable: {repo_changes.get('error')})")

        lines.append("")
        lines.append("Verification:")
        # Best-effort heuristic based on last message content.
        msg_l = (last_message or "").lower()
        if any(k in msg_l for k in SUCCESS_MARKERS):
            lines.append("- status: passed (heuristic)")
        elif any(k in msg_l for k in FAILURE_MARKERS):
            lines.append("- status: failed (heuristic)")
        else:
            lines.append("- status: unknown (no explicit signal)")

        lines.append("")
        lines.append("Tests:")
        lines.append("- not executed by Trinity (no deterministic test runner in pipeline)")
        return "\n".join(lines).strip() + "\n"

    def run(
        self,
        input_text: str,
        *,
        gui_mode: Optional[str] = None,
        execution_mode: Optional[str] = None,
        recursion_limit: Optional[int] = None,
    ):
        # Step 1: Classify task (LLM intent routing; keyword fallback)
        llm_res = self._classify_task_llm(input_text)
        if llm_res:
            task_type = str(llm_res.get("task_type") or "").strip().upper()
            requires_windsurf = bool(llm_res.get("requires_windsurf") or False)
            intent_reason = str(llm_res.get("reason") or "").strip()
        else:
            fb = self._classify_task_fallback(input_text)
            task_type = str(fb.get("task_type") or "").strip().upper()
            requires_windsurf = bool(fb.get("requires_windsurf") or False)
            intent_reason = str(fb.get("reason") or "").strip()

        is_dev = task_type != "GENERAL"

        routing_mode = str(os.getenv("TRINITY_ROUTING_MODE", "dev_only")).strip().lower() or "dev_only"
        allow_general = (
            routing_mode in {"hybrid", "all", "general"}
            or str(os.getenv("TRINITY_ALLOW_GENERAL", "")).strip().lower() in {"1", "true", "yes", "on"}
        )

        if not is_dev and not allow_general:
            blocked_message = (
                f"❌ **Trinity блокує це завдання**\n\n"
                f"Тип: {task_type}\n\n"
                f"Trinity працює **ТІЛЬКИ для dev-завдань** (код, рефакторинг, тести, git, архітектура).\n\n"
                f"Ваше завдання стосується: {input_text[:100]}...\n\n"
                f"Це **не dev-завдання**, тому Trinity не буде його виконувати.\n\n"
                f"💡 **Приклади dev-завдань, які Trinity МОЖЕ виконувати:**\n"
                f"- Напиши скрипт на Python\n"
                f"- Виправи баг у файлі core/trinity.py\n"
                f"- Додай нову функцію до API\n"
                f"- Запусти тести\n"
                f"- Зроби комміт з описом змін"
            )

            if self.verbose:
                print(blocked_message)

            final_messages = [HumanMessage(content=input_text), AIMessage(content=blocked_message)]
            yield {"atlas": {"messages": final_messages, "current_agent": "end", "task_status": "blocked"}}
            return

        if self.verbose:
            print(f"✅ [Trinity] Task classified as: {task_type} (is_dev={is_dev}, requires_windsurf={requires_windsurf})")
        
        gm = str(gui_mode or "auto").strip().lower() or "auto"
        if gm not in {"off", "on", "auto"}:
            gm = "auto"

        em = str(execution_mode or "native").strip().lower() or "native"
        if em not in {"native", "gui"}:
            em = "native"
        if recursion_limit is None:
            try:
                recursion_limit = int(os.getenv("TRINITY_RECURSION_LIMIT", "200"))
            except Exception:
                recursion_limit = 200
        try:
            recursion_limit = int(recursion_limit)
        except Exception:
            recursion_limit = 200
        if recursion_limit < 25:
            recursion_limit = 25

        initial_state = {
            "messages": [HumanMessage(content=input_text)],
            "current_agent": "meta_planner",  # Align with graph entry point
            "task_status": "started",
            "final_response": None,
            "plan": [],
            "summary": "",
            "step_count": 0,
            "replan_count": 0,
            "uncertain_streak": 0,
            "current_step_fail_count": 0,
            "history_plan_execution": [],
            "forbidden_actions": [],
            "pause_info": None,
            "gui_mode": gm,
            "execution_mode": em,
            "gui_fallback_attempted": False,
            "task_type": task_type,
            "is_dev": bool(is_dev),
            "requires_windsurf": bool(requires_windsurf),
            "dev_edit_mode": "cli",
            "intent_reason": intent_reason,
            "last_step_status": "success",
            "meta_config": {
                "strategy": "hybrid",
                "verification_rigor": "standard",
                "recovery_mode": "local_fix",
                "tool_preference": "hybrid",
                "reasoning": "",
                "retrieval_query": input_text[:100],
                "n_results": 3
            },
            "retrieved_context": "",
            "original_task": input_text,
            "is_media": any(kw in input_text.lower() for kw in MEDIA_KEYWORDS),
            "vibe_assistant_pause": None,
            "vibe_assistant_context": "",
            "vision_context": None,
            "learning_mode": self.learning_mode
        }

        # Initialize snapshot session
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            from system_ai.tools.screenshot import VisionDiffManager
            VisionDiffManager.get_instance().set_session_id(session_id)
            if self.verbose: 
                print(f"📸 [Trinity] Screenshot session initialized: {session_id}")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Trinity] Could not initialize screenshot session: {e}")

        last_node_name: str = ""
        last_state_update: Dict[str, Any] = {}
        last_agent_message: str = ""
        last_agent_label: str = ""
        last_replan_count: int = 0

        try:
            trace(self.logger, "trinity_run_start", {
                "task_type": task_type,
                "requires_windsurf": bool(requires_windsurf),
                "gui_mode": gm,
                "execution_mode": em,
                "recursion_limit": recursion_limit,
                "input_preview": str(input_text)[:200],
            })
        except Exception:
            pass
 
        for event in self.workflow.stream(initial_state, config={"recursion_limit": recursion_limit}):
            try:
                # Keep track of the last emitted node/message for the final report.
                for node_name, state_update in (event or {}).items():
                    last_node_name = str(node_name or "")
                    last_state_update = state_update if isinstance(state_update, dict) else {}
                    if isinstance(last_state_update, dict) and "replan_count" in last_state_update:
                        try:
                            last_replan_count = int(last_state_update.get("replan_count") or 0)
                        except Exception:
                            pass
                    msgs = last_state_update.get("messages", []) if isinstance(last_state_update, dict) else []
                    if msgs:
                        m = msgs[-1]
                        last_agent_message = str(getattr(m, "content", "") or "")
                    last_agent_label = str(node_name or "")

                    try:
                        trace(self.logger, "trinity_graph_event", {
                            "node": last_node_name,
                            "current_agent": last_state_update.get("current_agent") if isinstance(last_state_update, dict) else None,
                            "last_step_status": last_state_update.get("last_step_status") if isinstance(last_state_update, dict) else None,
                            "step_count": last_state_update.get("step_count") if isinstance(last_state_update, dict) else None,
                            "replan_count": last_replan_count,
                        })
                    except Exception:
                        pass
            except Exception:
                pass
            yield event

        # Emit final Atlas report as the last message.
        outcome = "completed"
        try:
            task_status = str((last_state_update or {}).get("task_status") or "").strip().lower()
            if task_status:
                outcome = task_status
            if "limit" in (last_agent_message or "").lower():
                outcome = "limit_reached"
            if "paused" in (last_agent_message or "").lower() or "пауза" in (last_agent_message or "").lower():
                outcome = "paused"
            # If the run ended with clarification/confirmation questions, don't treat it as completed.
            # This prevents misleading "Task completed" when agents are still waiting for input.
            lower_msg = (last_agent_message or "").lower()
            needs_input_markers = [
                "уточни",
                "уточнити",
                "підтверди",
                "підтвердження",
                "confirm",
                "confirmation",
                "clarify",
                "need уточ",
                "чи ",
            ]
            if outcome not in {"paused", "blocked", "limit_reached"}:
                if any(m in lower_msg for m in needs_input_markers) and ("[verified]" not in lower_msg and "[confirmed]" not in lower_msg):
                    outcome = "needs_input"

            # Task-specific artifact sanity check to avoid false "completed" outcomes.
            # (Used for macOS automation tasks that should produce concrete files.)
            task_l = str(input_text or "").lower()
            if outcome in {"completed", "success"} and "system_report_2025" in task_l:
                report_dir = os.path.expanduser("~/Desktop/System_Report_2025")
                zip_path = os.path.expanduser("~/Desktop/System_Report_2025.zip")
                required_files = [
                    os.path.join(report_dir, "desktop_screenshot.png"),
                    os.path.join(report_dir, "safari_apple.png"),
                    os.path.join(report_dir, "finder_downloads.png"),
                    os.path.join(report_dir, "chrome_search.png"),
                    os.path.join(report_dir, "system_info.txt"),
                    os.path.join(report_dir, "report_summary.md"),
                ]
                missing = []
                try:
                    if not os.path.isdir(report_dir):
                        missing.append(report_dir)
                    for p in required_files:
                        if not os.path.exists(p):
                            missing.append(p)
                    if not os.path.exists(zip_path):
                        missing.append(zip_path)
                except Exception:
                    missing = []

                if missing:
                    outcome = "failed_artifacts_missing"
                    last_agent_message = (
                        "System_Report_2025 artifacts missing. Expected files were not found on Desktop. "
                        + "Missing (first 6): "
                        + ", ".join(missing[:6])
                    )
        except Exception:
            pass

        repo_changes = self._get_repo_changes()
        commit_hash: Optional[str] = None
        base_report = self._format_final_report(
            task=input_text,
            outcome=outcome,
            repo_changes=repo_changes,
            last_agent=last_agent_label or last_node_name or "unknown",
            last_message=last_agent_message,
            replan_count=last_replan_count,
        )

        if outcome in {"completed", "success"}:
            commit_res = self._auto_commit_on_success(task=input_text, report=base_report, repo_changes=repo_changes)
            if commit_res.get("ok") is True and not commit_res.get("skipped"):
                commit_hash = str(commit_res.get("commit") or "").strip() or None
                repo_changes = self._get_repo_changes()

        report = self._format_final_report(
            task=input_text,
            outcome=outcome,
            repo_changes=repo_changes,
            last_agent=last_agent_label or last_node_name or "unknown",
            last_message=last_agent_message,
            replan_count=last_replan_count,
            commit_hash=commit_hash,
        )

        try:
            trace(self.logger, "trinity_run_end", {
                "outcome": outcome,
                "last_agent": last_agent_label or last_node_name or "unknown",
                "replan_count": last_replan_count,
            })
        except Exception:
            pass

        if commit_hash is None:
            try:
                existing_content = ""
                my_response_section = ""
                trinity_reports_section = ""

                try:
                    with open(".last_response.txt", "r", encoding="utf-8") as f:
                        existing_content = f.read().strip()
                except FileNotFoundError:
                    pass

                if existing_content:
                    if "## My Last Response" in existing_content:
                        parts = existing_content.split("## Trinity Report")
                        my_response_section = parts[0].strip()
                        if len(parts) > 1:
                            trinity_reports_section = "## Trinity Report" + "## Trinity Report".join(parts[1:])
                    else:
                        trinity_reports_section = existing_content

                new_content = ""
                if my_response_section:
                    new_content = my_response_section

                if trinity_reports_section:
                    new_content += "\n\n---\n\n" + trinity_reports_section

                new_content += "\n\n---\n\n## Trinity Report\n\n" + report

                with open(".last_response.txt", "w", encoding="utf-8") as f:
                    f.write(new_content)

                try:
                    subprocess.run(
                        ["python3", "generate_structure.py"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=self._get_git_root() or ".",
                    )
                except Exception:
                    pass

            except Exception:
                pass

        final_messages = [HumanMessage(content=input_text), AIMessage(content=report)]
        
        yield {"atlas": {"messages": final_messages, "current_agent": "end", "task_status": outcome}}
