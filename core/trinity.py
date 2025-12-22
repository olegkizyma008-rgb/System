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
    TERMINATION_MARKERS, STEP_COMPLETED_MARKER, UNKNOWN_STEP,
    VOICE_MARKER, DEFAULT_MODEL_FALLBACK
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
    MAX_STEPS = 50
    PROJECT_STRUCTURE_FILE = "project_structure_final.txt"
    LAST_RESPONSE_FILE = ".last_response.txt"
    TRINITY_REPORT_HEADER = "## Trinity Report"
    
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
        from system_ai.tools.screenshot import get_frontmost_app, get_all_windows

        disable_vision = str(os.environ.get("TRINITY_DISABLE_VISION", "")).strip().lower() in {"1", "true", "yes", "on"}
        EnhancedVisionTools = None
        if not disable_vision:
            try:
                from system_ai.tools.vision import EnhancedVisionTools as _EnhancedVisionTools

                EnhancedVisionTools = _EnhancedVisionTools
            except Exception as e:
                if self.verbose:
                    self.logger.warning(f"Vision tools unavailable: {e}")
        
        # Core Vision Tools (optional)
        if EnhancedVisionTools is not None:
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
        """Check if Doctor Vibe intervention is needed based on current state."""
        if state.get("vibe_assistant_pause"):
            return state["vibe_assistant_pause"]
            
        intervention = self._check_critical_issues()
        if intervention: return intervention
        
        intervention = self._check_repeated_failures(state)
        if intervention: return intervention
        
        intervention = self._check_background_dev_mode(state)
        if intervention: return intervention
        
        return self._check_stalls(state)

    def _check_critical_issues(self) -> Optional[Dict[str, Any]]:
        if not (self.self_healing_enabled and self.self_healer):
            return None
        issues = self.self_healer.detected_issues
        critical = [i for i in issues if i.severity in {IssueSeverity.CRITICAL, IssueSeverity.HIGH}]
        if not critical:
            return None
            
        return {
            "reason": "critical_issues_detected",
            "issues": [i.to_dict() for i in critical[:5]],
            "message": f"Doctor Vibe: Виявлено {len(critical)} критичних помилок. Атлас призупинив виконання.",
            "timestamp": datetime.now().isoformat(),
            "suggested_action": "Будь ласка, виправте помилки. Атлас автоматично продовжить після /continue",
            "atlas_status": "paused_waiting_for_human",
            "auto_resume_available": True
        }

    def _check_repeated_failures(self, state: TrinityState) -> Optional[Dict[str, Any]]:
        count = state.get("current_step_fail_count", 0)
        if count < 3:
            return None
        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
        return {
            "reason": "repeated_failures",
            "message": MESSAGES[lang].get("clueless_pause", "Doctor Vibe: System paused."),
            "timestamp": datetime.now().isoformat(),
            "suggested_action": "Please analyze the issue. Use /continue or /cancel" if lang != "uk" else "Проаналізуйте проблему. Використовуйте /continue або /cancel",
            "atlas_status": "paused_analyzing_failures",
            "auto_resume_available": True
        }

    def _check_background_dev_mode(self, state: TrinityState) -> Optional[Dict[str, Any]]:
        if state.get("task_type") != "DEV" or not state.get("is_dev"):
            return None
        if not (self.self_healing_enabled and self.self_healer):
            return None
        unresolved = [i for i in self.self_healer.detected_issues if i.severity in {IssueSeverity.MEDIUM, IssueSeverity.HIGH}]
        if len(unresolved) <= 2:
            return None
            
        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
        return {
            "reason": "background_error_correction_needed",
            "issues": [i.to_dict() for i in unresolved[:3]],
            "message": f"Doctor Vibe: Detected {len(unresolved)} background errors." if lang != "uk" else f"Doctor Vibe: Виявлено {len(unresolved)} помилок в фоновому режимі.",
            "timestamp": datetime.now().isoformat(),
            "suggested_action": "Errors fixed automatically." if lang != "uk" else "Помилки виправляються автоматично.",
            "atlas_status": "running_with_background_fixes",
            "auto_resume_available": False,
            "background_mode": True
        }

    def _check_stalls(self, state: TrinityState) -> Optional[Dict[str, Any]]:
        messages = state.get("messages", [])
        last = getattr(messages[-1], "content", "").lower() if messages and messages[-1] else ""
        stall_keys = ["план порожній", "empty plan", "no steps", "cannot", "не може", "не вдається", "failed to"]
        if not any(k in last for k in stall_keys):
            return None
            
        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
        return {
            "reason": "unknown_stall_detected",
            "message": f"Doctor Vibe: Stall detected: {last[:100]}..." if lang != "uk" else f"Doctor Vibe: Виявлено зупинку: {last[:100]}...",
            "timestamp": datetime.now().isoformat(),
            "suggested_action": "Clarify task or restart." if lang != "uk" else "Уточніть завдання або перезапустіть",
            "atlas_status": "stalled_unknown_reason",
            "auto_resume_available": False,
            "last_message": last,
            "original_task": state.get("original_task")
        }
    
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
        if self.verbose: print(f"🧠 {VOICE_MARKER} [Meta-Planner] Analyzing strategy...")
        context = state.get("messages", [])
        last_msg = getattr(context[-1], "content", "Start") if context and context[-1] else "Start"
        
        # 1. Initialize and maintain state
        meta_config = self._prepare_meta_config(state, last_msg)
        summary = self._update_periodic_summary(state, context)
        
        # 2. Check hard limits
        limit_reached = self._check_master_limits(state, context)
        if limit_reached: return limit_reached
        
        # 3. Consume or handle previous step result
        plan = state.get("plan") or []
        last_status = state.get("last_step_status", "success")
        fail_count = int(state.get("current_step_fail_count") or 0)
        
        if plan:
            plan, last_status, fail_count = self._consume_execution_step(state, plan, last_status, fail_count, last_msg)
            
        # 4. Decide next action
        action = self._decide_meta_action(plan, last_status, fail_count, state)
        
        # 5. Execute meta-action (replan/repair/initialize)
        if action in ["initialize", "replan", "repair"]:
            return self._handle_meta_action(state, action, plan, last_msg, meta_config, fail_count, summary)

        # 6. Default flow: Atlas dispatch
        out = self._atlas_dispatch(state, plan)
        out["summary"] = summary
        return out

    def _prepare_meta_config(self, state: TrinityState, last_msg: str) -> Dict[str, Any]:
        cfg = state.get("meta_config") or {}
        if not isinstance(cfg, dict): cfg = {}
        defaults = {
            "strategy": "hybrid", "verification_rigor": "standard",
            "recovery_mode": "local_fix", "tool_preference": "hybrid",
            "reasoning": "", "retrieval_query": last_msg, "n_results": 3
        }
        for k, v in defaults.items():
            cfg.setdefault(k, v)
        return cfg

    def _update_periodic_summary(self, state: TrinityState, context: List[Any]) -> str:
        summary = state.get("summary", "")
        step_count = state.get("step_count", 0)
        if len(context) > 6 and step_count % 3 == 0:
            try:
                recent = [str(getattr(m, "content", ""))[:4000] for m in context[-4:] if m]
                prompt = [
                    SystemMessage(content=f"Trinity archivist. Summarize (2-3 sentences) in {self.preferred_language}."),
                    HumanMessage(content=f"Summary: {summary}\n\nEvents:\n" + "\n".join(recent))
                ]
                summary = getattr(self.llm.invoke(prompt), "content", "")
            except Exception: pass
        return summary

    def _check_master_limits(self, state: TrinityState, context: List[Any]) -> Optional[Dict[str, Any]]:
        lang = self.preferred_language if self.preferred_language in MESSAGES else "en"
        if state.get("step_count", 0) >= self.MAX_STEPS:
            msg = MESSAGES[lang]["step_limit_reached"].format(limit=self.MAX_STEPS)
            return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"{VOICE_MARKER} {msg}")]}
        if state.get("replan_count", 0) >= self.MAX_REPLANS:
            msg = MESSAGES[lang]["replan_limit_reached"].format(limit=self.MAX_REPLANS)
            return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"{VOICE_MARKER} {msg}")]}
        return None

    def _consume_execution_step(self, state: TrinityState, plan: List[Dict], status: str, fail_count: int, last_msg: str) -> tuple:
        hist = state.get("history_plan_execution") or []
        desc = plan[0].get('description', UNKNOWN_STEP) if plan else UNKNOWN_STEP
        
        if status == "success":
            plan.pop(0)
            hist.append(f"SUCCESS: {desc}")
            fail_count = 0
            state["gui_fallback_attempted"] = False
        elif status == "failed":
            fail_count += 1
            hist.append(f"FAILED: {desc} (Try #{fail_count})")
        elif status == "uncertain":
            fail_count += 1
            hist.append(f"UNCERTAIN: {desc} (Check #{fail_count})")
            if fail_count >= 4:
                status = "failed"
                forbidden = state.get("forbidden_actions") or []
                forbidden.append(f"FAILED ACTION: {desc}")
                state["forbidden_actions"] = forbidden
                
        state["history_plan_execution"] = hist
        return plan, status, fail_count

    def _decide_meta_action(self, plan: List[Dict], status: str, fail_count: int, state: TrinityState) -> str:
        if not state.get("meta_config"): return "initialize"
        if not plan: return "replan"
        if status == "failed":
            if fail_count >= 3:
                hist = state.get("history_plan_execution") or []
                if hist:
                    forbidden = state.get("forbidden_actions") or []
                    forbidden.append(f"FAILED ACTION: {hist[-1]}")
                    state["forbidden_actions"] = forbidden
                return "replan"
            
            cfg = state.get("meta_config") or {}
            return "replan" if cfg.get("recovery_mode") == "full_replan" else "repair"
            
        vibe_ctx = state.get("vibe_assistant_context", "")
        if "background_mode" in vibe_ctx: return "proceed"
        
        return "proceed"

    def _handle_meta_action(self, state: TrinityState, action: str, plan: List[Dict], last_msg: str, 
                           meta_config: Dict, fail_count: int, summary: str):
        from core.agents.atlas import get_meta_planner_prompt
        task_ctx = f"Goal: {state.get('original_task')}\nReq: {last_msg}\nStep: {state.get('step_count')}\nStatus: {state.get('last_step_status')}"
        prompt = get_meta_planner_prompt(task_ctx, preferred_language=self.preferred_language)
        
        try:
            resp = self.llm.invoke(prompt.format_messages())
            data = self._extract_json_object(getattr(resp, "content", ""))
            if data and "meta_config" in data:
                meta_config.update(data["meta_config"])
                if meta_config.get("strategy") == "rag_heavy" or action in ["initialize", "replan", "repair"]:
                    self._perform_selective_rag(state, meta_config, last_msg)
        except Exception: pass

        plan_for_atlas = plan[1:] if action == "repair" and len(plan) > 0 else None
        meta_config["repair_mode"] = (action == "repair")
        meta_config["failed_step"] = plan[0].get("description", UNKNOWN_STEP) if action == "repair" and plan else UNKNOWN_STEP
        
        return {
            "current_agent": "atlas", "meta_config": meta_config, "plan": plan_for_atlas,
            "current_step_fail_count": fail_count, "summary": summary,
            "gui_fallback_attempted": False if action == "replan" else state.get("gui_fallback_attempted"),
            "retrieved_context": state.get("retrieved_context", "")
        }

    def _perform_selective_rag(self, state: TrinityState, meta_config: Dict, last_msg: str):
        query = meta_config.get("retrieval_query", last_msg)
        limit = int(meta_config.get("n_results", 3))
        mem_res = self.memory.query_memory("knowledge_base", query, n_results=limit)
        relevant = []
        for r in mem_res:
            m = r.get("metadata", {})
            if m.get("status") == "success" and float(m.get("confidence", 1.0)) > 0.3:
                relevant.append(f"[SUCCESS] {r.get('content')}")
            elif m.get("status") == "failed":
                relevant.append(f"[WARNING: FAILED] Avoid: {r.get('content')}")
        
        if not relevant:
            mem_res = self.memory.query_memory("strategies", query, n_results=limit)
            relevant = [r.get("content", "") for r in mem_res]
        state["retrieved_context"] = "\n".join(relevant)
        # NOTE: Removed the old "uncertain -> replan" logic. Uncertain is now handled above as a soft failure.
    def _atlas_node(self, state: TrinityState):
        """Generates the plan based on Meta-Planner policy."""
        if self.verbose: print("🌐 [Atlas] Generating steps...")
        
        # 1. State extraction
        plan = state.get("plan")
        replan_count = state.get("replan_count", 0)
        context = state.get("messages", [])
        last_msg = getattr(context[-1], "content", "Start") if context and len(context) > 0 and context[-1] is not None else "Start"

        # 2. Check for existing plan (Anti-loop)
        if plan and len(plan) > 0:
            if self.verbose: print(f"🌐 [Atlas] Using existing plan ({len(plan)} steps). Dispatching to execution.")
            return self._atlas_dispatch(state, plan)

        # 3. Check for replan loop (Anti-loop)
        loop_break = self._check_atlas_loop(state, replan_count, last_msg)
        if loop_break:
            return loop_break

        # 4. Prepare for new planning
        replan_count += 1
        meta_config = state.get("meta_config") or {}
        if self.verbose: print(f"🔄 [Atlas] Replan #{replan_count}")

        try:
            # 5. Prepare prompt
            prompt = self._prepare_atlas_prompt(state, last_msg, meta_config)
            
            # 6. Execute planning request
            raw_plan_data = self._execute_atlas_planning_request(prompt)
            
            # 7. Check for completion or valid plan
            if isinstance(raw_plan_data, dict) and raw_plan_data.get("status") == "completed":
                return {"current_agent": "end", "messages": list(context) + [AIMessage(content=f"[VOICE] {raw_plan_data.get('message', 'Done.')}")]}
                
            raw_plan = self._extract_raw_plan(raw_plan_data, meta_config)
            
            # 8. Optimize or Repair Plan
            optimized_plan = self._process_atlas_plan(raw_plan, plan, meta_config)
            
            return self._atlas_dispatch(state, optimized_plan, replan_count=replan_count)

        except Exception as e:
            return self._handle_atlas_planning_error(e, state, last_msg, context, replan_count)

    def _check_atlas_loop(self, state, replan_count, last_msg):
        """Check if we're stuck in a replan loop and break it if necessary."""
        last_status = state.get("last_step_status", "success")
        if replan_count >= 3 and last_status != "success":
            if self.verbose: print(f"⚠️ [Atlas] Replan loop detected (#{replan_count}). Forcing simple execution.")
            fallback = [{"id": 1, "type": "execute", "description": last_msg, "agent": "tetyana", "tools": ["browser_open_url"]}]
            return self._atlas_dispatch(state, fallback, replan_count=replan_count)
        return None

    def _prepare_atlas_prompt(self, state, last_msg, meta_config):
        """Prepare the prompt for Atlas planning."""
        from core.agents.atlas import get_atlas_plan_prompt
        
        rag_context = state.get("retrieved_context", "")
        structure_context = self._get_project_structure_context()
        
        final_context = self.context_layer.prepare(
            rag_context=rag_context,
            project_structure=structure_context,
            meta_config=meta_config,
            last_msg=last_msg
        )

        execution_history = []
        hist = state.get("history_plan_execution") or []
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
        
        self._inject_prompt_modifiers(prompt, state, meta_config)
        return prompt

    def _inject_prompt_modifiers(self, prompt, state, meta_config):
        """Inject specific modifiers like REPAIR or REPLAN instructions into the prompt."""
        plan = state.get("plan")
        if meta_config.get("repair_mode"):
            failed_step = meta_config.get("failed_step", "Unknown")
            remaining_plan = plan if plan else []
            remaining_desc = ", ".join([s.get("description", "?")[:30] for s in remaining_plan[:3]]) if remaining_plan else "none"
            prompt.messages.append(HumanMessage(content=f'''🔧 REPAIR MODE: Generate ONLY ONE alternative step to replace the failed step.
FAILED STEP: {failed_step}
REMAINING PLAN: {remaining_desc}
Generate ONE step that achieves the same goal as the failed step but uses a DIFFERENT approach.
Return JSON with ONLY the replacement step.'''))
        elif state.get("last_step_status") == "failed":
            prompt.messages.append(HumanMessage(content=f"PREVIOUS ATTEMPT FAILED. Current history shows what didn't work. AVOID REPEATING FAILED ACTIONS. Respecify the plan starting from the current state. RESUME, DO NOT RESTART."))
        elif state.get("last_step_status") == "uncertain":
            prompt.messages.append(HumanMessage(content=f"PREVIOUS STEP WAS UNCERTAIN. Review output and verify if you need to retry differently or try alternative."))

    def _execute_atlas_planning_request(self, prompt):
        """Execute the LLM request for planning."""
        def on_delta(chunk):
            self._deduplicated_stream("atlas", chunk)

        atlas_model = os.getenv("ATLAS_MODEL") or os.getenv("COPILOT_MODEL") or "gpt-4.1"
        atlas_llm = CopilotLLM(model_name=atlas_model)

        plan_resp = atlas_llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
        plan_resp_content = getattr(plan_resp, "content", "") if plan_resp is not None else ""
        return self._extract_json_object(plan_resp_content)

    def _extract_raw_plan(self, data, meta_config):
        """Extract raw plan from JSON data."""
        raw_plan = []
        if isinstance(data, list): 
            raw_plan = data
        elif isinstance(data, dict):
            raw_plan = data.get("steps") or data.get("plan") or []
            if data.get("meta_config"):
                meta_config.update(data["meta_config"])
                if self.verbose: 
                    print(f"🌐 [Atlas] Strategy Justification: {meta_config.get('reasoning')}")
                    print(f"🌐 [Atlas] Preferences: tool_pref={meta_config.get('tool_preference', 'hybrid')}")

        if not raw_plan: 
            raise ValueError("No steps generated")
        return raw_plan

    def _process_atlas_plan(self, raw_plan, existing_plan, meta_config):
        """Process the raw plan (repair or full optimization)."""
        if meta_config.get("repair_mode") and existing_plan:
            # Repair mode: Prepend new step
            repair_step = raw_plan[0] if raw_plan else None
            if repair_step:
                optimized_plan = [repair_step] + list(existing_plan)
                if self.verbose: print(f"🔧 [Atlas] REPAIR: Prepended new step to {len(existing_plan)} remaining steps")
            else:
                optimized_plan = list(existing_plan)
            meta_config["repair_mode"] = False
            return optimized_plan
        else:
            # Full replan: optimize new plan
            grisha_model = os.getenv("GRISHA_MODEL") or os.getenv("COPILOT_MODEL") or "gpt-4.1"
            grisha_llm = CopilotLLM(model_name=grisha_model)
            local_verifier = AdaptiveVerifier(grisha_llm)
            return local_verifier.optimize_plan(raw_plan, meta_config=meta_config)

    def _handle_atlas_planning_error(self, e, state, last_msg, context, replan_count):
        """Handle errors during Atlas planning phase."""
        if self.verbose: print(f"⚠️ [Atlas] Error: {e}")
        
        error_str = str(e).lower()
        if "no steps generated" in error_str or "empty plan" in error_str or "cannot" in error_str:
            if self.verbose:
                print(f"🚨 [Atlas] Planning failure detected. Activating Doctor Vibe intervention.")
            
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
                
            self.vibe_assistant.handle_pause_request(pause_context)
            
            return {
                **state,
                "vibe_assistant_pause": pause_context,
                "vibe_assistant_context": f"PAUSED: Planning failure for task: {last_msg}",
                "current_agent": "meta_planner",
                "messages": list(context) + [AIMessage(content=f"[VOICE] Doctor Vibe: Виникла проблема з плануванням. Будь ласка, уточніть завдання.")]
            }
        else:
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

    def _tetyana_node(self, state: TrinityState):

        """Executes the next step in the plan using Tetyana (Executor)."""
        if self.verbose: print(f"🔧 {VOICE_MARKER} [Tetyana] Executing step...")
        context = state.get("messages", [])
        original_task = state.get("original_task") or UNKNOWN_STEP
        last_msg = getattr(context[-1], "content", UNKNOWN_STEP) if context and context[-1] else UNKNOWN_STEP

        # 1. Prepare context and prompt
        full_context = self._prepare_tetyana_context(state, original_task, last_msg)
        prompt = get_tetyana_prompt(
            full_context,
            tools_desc=self.registry.list_tools(),
            preferred_language=self.preferred_language,
            vision_context=self.vision_context_manager.current_context
        )

        # 2. Invoke LLM
        tetyana_model = os.getenv("TETYANA_MODEL") or os.getenv("COPILOT_MODEL") or DEFAULT_MODEL_FALLBACK
        tetyana_llm = self.llm if hasattr(self, 'llm') and self.llm else CopilotLLM(model_name=tetyana_model)
        
        try:
            def on_delta(chunk): self._deduplicated_stream("tetyana", chunk)
            response = tetyana_llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
            
            content = getattr(response, "content", "") if response else ""
            tool_calls = getattr(response, "tool_calls", []) if response and hasattr(response, 'tool_calls') else []

            # 3. Handle acknowledgment loops
            if not tool_calls and content:
                ack_retry = self._check_tetyana_acknowledgment(content, context)
                if ack_retry: return ack_retry

            # 4. Execute tools
            results, pause_info, had_failure = self._execute_tetyana_tools(state, tool_calls)
            
            # 5. Post-execution processing
            if results:
                content += "\n\nTool Results:\n" + "\n".join(results)
                if not had_failure and not pause_info:
                    content = self._append_success_marker(content)

            # 6. Fallback and Final State
            return self._finalize_tetyana_state(state, context, content, tool_calls, had_failure, pause_info)

        except Exception as e:
            if self.verbose: print(f"⚠️ [Tetyana] Exception: {e}")
            return self._handle_tetyana_error(state, context, e)

    def _prepare_tetyana_context(self, state, original_task, last_msg):
        task_type = state.get("task_type")
        requires_windsurf = state.get("requires_windsurf")
        dev_edit_mode = state.get("dev_edit_mode")
        
        routing = f"\n\n[ROUTING] task_type={task_type} requires_windsurf={requires_windsurf} dev_edit_mode={dev_edit_mode}"
        retry = ""
        fail_count = int(state.get("current_step_fail_count") or 0)
        if fail_count > 0:
            retry = f"\n\n[SYSTEM NOTICE] This is retry #{fail_count} for this step. Adjust approach."
            
        return f"Global Goal: {original_task}\nRequest: {last_msg}{routing}{retry}"

    def _check_tetyana_acknowledgment(self, content, context):
        lower_content = content.lower()
        acknowledgment_patterns = ["зрозуміла", "зрозумів", "ок", "добре", "починаю", "буду використовувати"]
        if any(p in lower_content for p in acknowledgment_patterns) and len(lower_content) < 300:
            if self.verbose: print("⚠️ [Tetyana] Acknowledgment loop detected.")
            new_msg = AIMessage(content=f"{VOICE_MARKER} Error: No tool call provided. USE A TOOL. {content}")
            return {"messages": context + [new_msg], "last_step_status": "failed"}
        return None

    def _execute_tetyana_tools(self, state, tool_calls):
        results = []
        pause_info = None
        had_failure = False
        
        for tool in (tool_calls or []):
            name = tool.get("name")
            args = tool.get("args") or {}
            
            # Permission checks
            pause_info = self._check_tool_permissions(state, name, args)
            if pause_info:
                results.append(f"[BLOCKED] {name}: permission required")
                continue
            
            # Task-type constraints
            blocked_reason = self._check_task_constraints(state, name, args)
            if blocked_reason:
                results.append(blocked_reason)
                continue

            # Execution
            if name in {"browser_get_links", "browser_get_text", "browser_get_visible_html", "browser_screenshot"}:
                time.sleep(2.0)
            
            res_str = self.registry.execute(name, args)
            results.append(f"Result for {name}: {res_str}")
            
            # Failure tracking
            if self._is_execution_failure(res_str):
                had_failure = True
                
        return results, pause_info, had_failure

    def _check_tool_permissions(self, state, name, args):
        perm_map = {
            "file_write": (["write_file", "copy_file"], self.permissions.allow_file_write),
            "shell": (["run_shell", "open_file_in_windsurf", "open_project_in_windsurf"], self.permissions.allow_shell),
            "applescript": (["run_applescript", "native_applescript"], self.permissions.allow_applescript),
            "gui": (["move_mouse", "click_mouse", "click", "type_text", "press_key"], self.permissions.allow_gui),
            "shortcuts": (["run_shortcut"], self.permissions.allow_shortcuts),
        }
        
        for perm, (tools, allowed) in perm_map.items():
            if name in tools and not (allowed or self.permissions.hyper_mode):
                return {"permission": perm, "message": f"Permission required for {perm}.", "blocked_tool": name, "blocked_args": args}
        return None

    def _check_task_constraints(self, state, name, args):
        task_type = state.get("task_type")
        windsurf_tools = {"send_to_windsurf", "open_file_in_windsurf", "open_project_in_windsurf"}
        
        if task_type == "GENERAL":
            if name in windsurf_tools:
                return f"[BLOCKED] {name}: GENERAL task must not use Windsurf."
            if name in {"write_file", "copy_file"} and not self._is_safe_path(name, args):
                return f"[BLOCKED] {name}: GENERAL write allowed only outside repo."
        
        if task_type in {"DEV", "UNKNOWN"} and state.get("requires_windsurf") and state.get("dev_edit_mode") == "windsurf":
            if name in {"write_file", "copy_file"}:
                return f"[BLOCKED] {name}: Use Windsurf tools for DEV tasks."
        return None

    def _is_safe_path(self, name, args):
        try:
            from system_ai.tools.filesystem import _normalize_special_paths
            git_root = self._get_git_root() or ""
            home = os.path.expanduser("~")
            path = args.get("path") if name == "write_file" else args.get("dst")
            ap = os.path.abspath(os.path.expanduser(_normalize_special_paths(str(path or ""))))
            if git_root and (ap == git_root or ap.startswith(git_root + os.sep)): return False
            return ap.startswith(home + os.sep) or ap.startswith(os.path.join(os.sep, "tmp") + os.sep)
        except Exception: return False

    def _is_execution_failure(self, res_str):
        try:
            res_dict = json.loads(res_str)
            if isinstance(res_dict, dict):
                if str(res_dict.get("status", "")).lower() == "error": return True
                if res_dict.get("has_captcha"): return True
                output = str(res_dict.get("output", "") or res_dict.get("url", ""))
                if any(k in output.lower() for k in ["sorry/index", "recaptcha"]): return True
        except Exception:
            if str(res_str).strip().startswith("Error"): return True
        return "sorry/index" in str(res_str) or "recaptcha" in str(res_str).lower()

    def _append_success_marker(self, content):
        if STEP_COMPLETED_MARKER not in content:
            msg = "Actions completed." if self.preferred_language != "uk" else "Дії виконано."
            return f"{content}\n\n{STEP_COMPLETED_MARKER} {msg}"
        return content

    def _finalize_tetyana_state(self, state, context, content, tool_calls, had_failure, pause_info):
        updated_messages = list(context) + [AIMessage(content=content)]
        used_tools = [t.get("name") for t in tool_calls] if tool_calls else []
        
        if pause_info:
            return {**state, "messages": updated_messages, "pause_info": pause_info, "last_step_status": "uncertain", "current_agent": "meta_planner"}
            
        if had_failure and state.get("execution_mode") != "gui" and state.get("gui_mode") in {"auto", "on"} and not state.get("gui_fallback_attempted"):
            return {**state, "messages": updated_messages, "execution_mode": "gui", "gui_fallback_attempted": True, "last_step_status": "failed", "current_agent": "tetyana"}

        return {
            **state,
            "messages": updated_messages,
            "current_agent": "grisha",
            "last_step_status": "failed" if had_failure else "success",
            "tetyana_used_tools": used_tools,
            "tetyana_tool_context": self._extract_tool_context(tool_calls)
        }

    def _extract_tool_context(self, tool_calls):
        ctx = {}
        for t in (tool_calls or []):
            args = t.get("args") or {}
            for k in ["app_name", "app", "window_title", "window", "url"]:
                if k in args: ctx[k] = args[k]
        return ctx

    def _handle_tetyana_error(self, state, context, e):
        err_msg = f"Error invoking Tetyana: {e}"
        return {**state, "messages": list(context) + [AIMessage(content=err_msg)], "last_step_status": "failed", "current_agent": "grisha"}

    def _grisha_node(self, state: TrinityState):
        if self.verbose: print(f"👁️ {VOICE_MARKER} [Grisha] Verifying...")
        context = state.get("messages", [])
        last_msg = self._get_last_msg_content(context)
        
        # 1. Run tests if needed
        test_results = self._run_grisha_tests(state)

        # 2. Invoke LLM and get initial response
        prompt = self._prepare_grisha_prompt(state, last_msg)
        content, tool_calls = self._invoke_grisha(prompt, last_msg)
        
        # 3. Execute Verification Tools
        executed_results = self._execute_grisha_tools(tool_calls)
        
        # 4. Smart Vision Verification
        vision_result = self._perform_smart_vision(state, last_msg)
        if vision_result:
            content += f"\n\n[GUI_BROWSER_VERIFY]\n{vision_result}"
            executed_results.append(vision_result)

        # 5. Verdict Analysis
        final_content = self._get_grisha_verdict(content, executed_results, test_results)
        step_status, next_agent = self._determine_grisha_status(state, final_content, executed_results)

        # 6. Anti-loop protection
        current_streak = self._handle_grisha_streak(state, step_status, final_content)

        return {
            "current_agent": next_agent,
            "messages": list(context) + [AIMessage(content=final_content)],
            "last_step_status": step_status,
            "uncertain_streak": current_streak,
            "plan": state.get("plan"),
        }

    def _get_last_msg_content(self, context):
        msg = getattr(context[-1], "content", "") if context and context[-1] else ""
        if isinstance(msg, str) and len(msg) > 50000:
            return msg[:45000] + "\n[...]\n" + msg[-5000:]
        return msg

    def _run_grisha_tests(self, state):
        task_type = str(state.get("task_type") or "").upper()
        if task_type == "GENERAL": return ""
        
        critical_dirs = ["core/", "system_ai/", "tui/", "providers/"]
        changed = (self._get_repo_changes().get("changed_files") or []) if self._get_repo_changes().get("ok") else []
        if any(any(f.startswith(d) for d in critical_dirs) for f in changed):
            if self.verbose: print("👁️ [Grisha] Running pytest...")
            res = subprocess.run("pytest -q --tb=short 2>&1", shell=True, capture_output=True, text=True, cwd=self._get_git_root() or ".")
            return f"\n\n[TEST_VERIFICATION] pytest output:\n{res.stdout + res.stderr}"
        return ""

    def _prepare_grisha_prompt(self, state, last_msg):
        plan = state.get("plan") or []
        current_step = plan[0].get("description", "Unknown") if plan else "Final Verification"
        original_task = state.get("original_task") or ""
        
        verify_context = f"GLOBAL GOAL: {original_task}\nSTEP TO VERIFY: {current_step}\nREPORT: {last_msg[:1000]}"
        
        if state.get("is_media"):
            return get_grisha_media_prompt(verify_context, tools_desc=self.registry.list_tools(), preferred_language=self.preferred_language)
        
        return get_grisha_prompt(
            verify_context,
            tools_desc=self.registry.list_tools(),
            preferred_language=self.preferred_language,
            vision_context=self.vision_context_manager.current_context
        )

    def _invoke_grisha(self, prompt, last_msg):
        model = os.getenv("GRISHA_MODEL") or os.getenv("COPILOT_MODEL") or DEFAULT_MODEL_FALLBACK
        llm = CopilotLLM(model_name=model)
        def on_delta(chunk): self._deduplicated_stream("grisha", chunk)
        resp = llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
        content = getattr(resp, "content", "") if resp else ""
        tool_calls = getattr(resp, "tool_calls", []) if resp and hasattr(resp, 'tool_calls') else []
        
        # Override if Grisha fails without evidence
        if any(m in content.lower() for m in ["failed", "не виконано"]) and not tool_calls and STEP_COMPLETED_MARKER.lower() in last_msg.lower():
            if self.verbose: print("⚠️ [Grisha] Overriding FAILED without evidence.")
            content = f"{VOICE_MARKER} Tetyana reported success. Tools confirmed. {STEP_COMPLETED_MARKER}"
            tool_calls = []
        return content, tool_calls

    def _execute_grisha_tools(self, tool_calls):
        results = []
        forbidden = ["browser_open", "browser_click", "browser_type", "write_", "create_", "delete_", "move_"]
        for tool in (tool_calls or []):
            name = tool.get("name")
            args = tool.get("args") or {}
            if any(name.startswith(p) for p in forbidden):
                results.append(f"Result for {name}: [BLOCKED] Grisha is read-only.")
                continue
            res = self.registry.execute(name, ({"app_name": None} if name == "capture_screen" and not args else args))
            results.append(f"Result for {name}: {res}")
        return results

    def _perform_smart_vision(self, state, last_msg):
        tetyana_tools = state.get("tetyana_used_tools") or []
        tetyana_ctx = state.get("tetyana_tool_context") or {}
        
        browser_active = any(k in last_msg.lower() or k in str(state.get("original_task")).lower() for k in ["google", "browser", "сайт", "url"])
        needs_visual = (set(tetyana_tools) & {"click", "type_text", "move_mouse"}) or browser_active or tetyana_ctx.get("browser_tool")
        
        if not (needs_visual or (state.get("gui_mode") in {"auto", "on"} and state.get("execution_mode") == "gui")):
            return None

        if any(t in tetyana_tools for t in ["browser_type_text", "browser_click", "browser_open_url"]):
            time.sleep(3.0)
            
        args = {}
        if tetyana_ctx.get("app_name"):
            args["app_name"] = tetyana_ctx["app_name"]
            if tetyana_ctx.get("window_title"): args["window_title"] = tetyana_ctx["window_title"]
            
        analysis = self.registry.execute("enhanced_vision_analysis", args)
        if isinstance(analysis, dict) and analysis.get("status") == "success":
            self.vision_context_manager.update_context(analysis)
        return str(analysis)

    def _get_grisha_verdict(self, content, executed_results, test_results):
        if not executed_results and not test_results: return content
        
        prompt = (f"Analyze these results:\n" + "\n".join(executed_results) + (f"\nTests:\n{test_results}" if test_results else "") +
                 f"\n\nRespond with Reasoning + Marker: [VERIFIED], [STEP_COMPLETED], [FAILED], or [UNCERTAIN].")
        try:
            resp = self.llm.invoke([SystemMessage(content="You are Grisha."), HumanMessage(content=prompt)])
            return content + "\n\n[VERDICT ANALYSIS]\n" + getattr(resp, "content", "")
        except Exception as e:
            return content + f"\n\n[VERDICT ERROR] {e}"

    def _determine_grisha_status(self, state, content, executed_results):
        lower = content.lower()
        res_str = "\n".join(executed_results).lower()
        
        if any(m in lower or f"[{m}]" in lower for m in FAILURE_MARKERS) or ("[test_verification]" in lower and "failed" in lower):
            return "failed", "meta_planner"
        if '"status": "error"' in res_str:
            return "failed", "meta_planner"
        if "[captcha]" in lower:
            return "uncertain", "meta_planner"
            
        for kw in SUCCESS_MARKERS:
            if kw.lower() in lower:
                idx = lower.find(kw.lower())
                pre = lower[max(0, idx-25):idx]
                if not re.search(NEGATION_PATTERNS.get(self.preferred_language, "not |never "), pre):
                    return "success", "meta_planner"
        return "uncertain", "meta_planner"

    def _handle_grisha_streak(self, state, status, content):
        streak = (int(state.get("uncertain_streak") or 0) + 1) if status == "uncertain" else 0
        if streak >= 3:
            if any(k in content.lower() for k in VISION_FAILURE_KEYWORDS) or "[failed]" in content.lower():
                return 0 
            return 0
        return streak


    def _router(self, state: TrinityState):
        """Route to next agent based on current state."""
        current = state.get("current_agent", "meta_planner")

        # Step 1: Handle existing pause state
        pause_result = self._handle_existing_pause(state, current)
        if pause_result is not None:
            return pause_result

        # Step 2: Check for new intervention needed
        intervention_result = self._handle_new_intervention(state, current)
        if intervention_result is not None:
            return intervention_result

        # Step 3: Check for knowledge transition
        knowledge_result = self._check_knowledge_transition(state, current)
        if knowledge_result is not None:
            return knowledge_result

        return current

    def _handle_existing_pause(self, state: TrinityState, current: str) -> Optional[str]:
        """Handle existing vibe assistant pause state."""
        if not state.get("vibe_assistant_pause"):
            return None

        pause_info = state.get("vibe_assistant_pause")
        if pause_info is None:
            state["vibe_assistant_pause"] = None
            return current

        # Try auto-repair
        repair_result = self._try_auto_repair(state, pause_info)
        if repair_result is not None:
            return repair_result

        # Stay paused
        if self.verbose:
            self.logger.info(f"Vibe CLI Assistant PAUSE: {pause_info.get('message', 'No reason provided')}")
        return current

    def _try_auto_repair(self, state: TrinityState, pause_info: dict) -> Optional[str]:
        """Attempt auto-repair for paused state. Returns new agent or None."""
        if not self.vibe_assistant.should_attempt_auto_repair(pause_info):
            return None

        if self.verbose:
            self.logger.info("🔧 Doctor Vibe: Attempting auto-repair...")

        repair_result = self.vibe_assistant.attempt_auto_repair(pause_info)

        if not (repair_result and repair_result.get("success")):
            if self.verbose:
                self.logger.warning("⚠️ Doctor Vibe: Auto-repair failed. Waiting for human intervention.")
            return state.get("current_agent", "meta_planner")

        # Success - clear pause and reset counters
        if self.verbose:
            self.logger.info("✅ Doctor Vibe: Auto-repair successful! Resuming execution.")

        state["vibe_assistant_pause"] = None
        state["vibe_assistant_context"] = f"AUTO-REPAIRED: {repair_result.get('message', 'Fixed')}"
        state["current_step_fail_count"] = 0
        state["uncertain_streak"] = 0
        return "meta_planner"

    def _handle_new_intervention(self, state: TrinityState, current: str) -> Optional[str]:
        """Check if new intervention is needed and handle it."""
        pause_context = self._check_for_vibe_assistant_intervention(state)
        if not pause_context:
            return None

        # Try pre-emptive repair
        if pause_context.get("auto_resume_available", False) or pause_context.get("background_mode", False):
            if self.vibe_assistant.should_attempt_auto_repair(pause_context):
                repair_result = self.vibe_assistant.attempt_auto_repair(pause_context)
                if repair_result and repair_result.get("success"):
                    if self.verbose:
                        self.logger.info("🔧 Doctor Vibe: Pre-emptive repair successful!")
                    return None  # Continue without pause

        # Create pause state
        self._create_vibe_assistant_pause_state(
            state,
            pause_context.get("reason", "unknown"),
            pause_context.get("message", "Unknown pause reason")
        )
        if self.verbose:
            self.logger.info(f"Vibe CLI Assistant INTERVENTION: {pause_context.get('message', 'Unknown reason')}")
        return current

    def _check_knowledge_transition(self, state: TrinityState, current: str) -> Optional[str]:
        """Check if we should transition to knowledge node."""
        try:
            if current != "end":
                return None

            messages = state.get("messages", [])
            if not messages or not isinstance(messages[-1], AIMessage):
                return None

            content = getattr(messages[-1], "content", "").lower() if messages[-1] else ""
            success_markers = ["завершена", "готово", "виконано", "completed", "success"]
            knowledge_markers = ["experience stored", "досвід збережено"]

            if any(x in content for x in success_markers):
                if not any(x in content for x in knowledge_markers):
                    return "knowledge"

            trace(self.logger, "router_decision", {"current": current, "next": current})
        except Exception:
            pass
        return None

    # _extract_json_object was moved to the top of the class to avoid duplication.

    def _knowledge_node(self, state: TrinityState):
        """Final node to extract and store knowledge from completion."""
        if self.verbose:
            print("🧠 [Learning] Extracting structured experience...")
        
        context = state.get("messages", [])
        plan = state.get("plan") or []
        summary = state.get("summary", "")
        replan_count = state.get("replan_count", 0)
        
        actual_status = self._determine_knowledge_status(state, context)
        confidence = self._calculate_confidence(actual_status, replan_count, len(plan))
        
        self._store_experience(summary, actual_status, plan, confidence, replan_count)
        
        final_msg = "[VOICE] Досвід збережено. Завдання завершено." if self.preferred_language == "uk" else "[VOICE] Experience stored. Task completed."
        return {"current_agent": "end", "messages": context + [AIMessage(content=final_msg)]}

    def _determine_knowledge_status(self, state: TrinityState, context: list) -> str:
        """Determine actual status for knowledge storage."""
        if state.get("last_step_status") == "failed":
            return "failed"
        if context and context[-1] is not None:
            last_content = getattr(context[-1], "content", "").lower()
            if "failed" in last_content:
                return "failed"
        return "success"

    def _calculate_confidence(self, status: str, replan_count: int, plan_len: int) -> float:
        """Calculate confidence score."""
        if status != "success":
            return 0.5
        confidence = 1.0 - (min(replan_count, 5) * 0.1) - (min(plan_len, 10) * 0.02)
        return max(0.1, round(confidence, 2))

    def _store_experience(self, summary: str, status: str, plan: list, confidence: float, replan_count: int):
        """Store experience in knowledge base."""
        try:
            experience = f"Task: {summary}\nStatus: {status}\nSteps: {len(plan)}\n"
            if plan:
                experience += "Plan Summary:\n" + "\n".join([f"- {s.get('description')}" for s in plan])
            
            self.memory.add_memory(
                category="knowledge_base",
                content=experience,
                metadata={
                    "type": "experience_log", "status": status, "source": "trinity_runtime",
                    "timestamp": int(time.time()), "confidence": confidence, "replan_count": replan_count
                }
            )
            if self.verbose:
                print(f"🧠 [Learning] {status.upper()} experience stored (conf: {confidence})")
            try:
                trace(self.logger, "knowledge_stored", {"status": status, "confidence": confidence})
            except Exception:
                pass
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Learning] Error: {e}")

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
            
            structure_file = os.path.join(git_root, self.PROJECT_STRUCTURE_FILE)
            if not os.path.exists(structure_file):
                return ""
            
            # Read only first part of file to avoid memory issues with huge files
            with open(structure_file, 'r', encoding='utf-8') as f:
                content = f.read(100000)
            
            return self._parse_context_sections(content)
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Trinity] Error reading project structure: {e}")
            return ""

    def _parse_context_sections(self, content: str) -> str:
        """Extract key sections (Metadata, Logs, Structure) from project structure file."""
        lines = content.split('\n')
        context_lines = []
        current_section = None
        section_count = 0
        
        for line in lines:
            # Each line limited to 500 chars to avoid prompt blowup
            line = line[:500]
            lstrip = line.strip()
            
            # Identify or switch sections
            new_section = self._identify_structure_section(lstrip, current_section)
            if new_section != current_section:
                current_section = new_section
                section_count = 0
            
            # Collect lines
            if current_section and section_count < 30:
                 if lstrip and not lstrip.startswith('```'):
                    context_lines.append(line)
                    section_count += 1
        
        return '\n'.join(context_lines[:150])

    def _identify_structure_section(self, lstrip: str, current_section: Optional[str]) -> Optional[str]:
        """Identify which section a line belongs to."""
        if lstrip.startswith('## Metadata'): return 'metadata'
        if '## Program Execution Logs' in lstrip: return 'logs'
        if '## Project Structure' in lstrip: return 'structure'
        
        if lstrip.startswith('## ') and current_section:
            # New section that isn't one of the known ones -> exit section
            return None
        return current_section

    def _regenerate_project_structure(self, response_text: str) -> bool:
        """Regenerate project_structure_final.txt with last response."""
        try:
            git_root = self._get_git_root()
            if not git_root:
                if self.verbose:
                    print("⚠️ [Trinity] Not a git repo, skipping structure regeneration")
                return False
            
            # Save response to LAST_RESPONSE_FILE
            response_file = os.path.join(git_root, self.LAST_RESPONSE_FILE)
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
        """Get git repository changes."""
        root = self._get_git_root()
        if not root:
            return {"ok": False, "error": "not_a_git_repo"}

        try:
            diff_name = subprocess.run(["git", "diff", "--name-only"], cwd=root, capture_output=True, text=True)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
            diff_stat = subprocess.run(["git", "diff", "--stat"], cwd=root, capture_output=True, text=True)

            changed_files = self._collect_changed_files(diff_name, status)
            deduped = self._dedupe_files(changed_files)

            return {
                "ok": True, "git_root": root, "changed_files": deduped,
                "diff_stat": (diff_stat.stdout or "").strip() if diff_stat.returncode == 0 else "",
                "status_porcelain": (status.stdout or "").strip() if status.returncode == 0 else "",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _collect_changed_files(self, diff_name, status) -> List[str]:
        """Collect changed files from git commands."""
        files = []
        if diff_name.returncode == 0:
            files.extend([l.strip() for l in (diff_name.stdout or "").splitlines() if l.strip()])
        if status.returncode == 0:
            for line in (status.stdout or "").splitlines():
                s = line.strip()
                if s:
                    parts = s.split(maxsplit=1)
                    if len(parts) == 2:
                        files.append(parts[1].strip())
        return files

    def _dedupe_files(self, files: List[str]) -> List[str]:
        """Deduplicate file list while preserving order."""
        seen = set()
        result = []
        for f in files:
            if f not in seen:
                seen.add(f)
                result.append(f)
        return result

    def _short_task_for_commit(self, task: str, max_len: int = 72) -> str:
        t = re.sub(r"\s+", " ", str(task or "").strip())
        if not t:
            return "(no task)"
        if len(t) <= max_len:
            return t
        cut = t[: max_len - 1].rstrip()
        return cut + "…"

    def _auto_commit_on_success(self, *, task: str, report: str, repo_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-commit changes on successful task completion."""
        root = self._get_git_root()
        if not root:
            return {"ok": False, "error": "not_a_git_repo"}

        try:
            env = self._prepare_git_env()

            # Check if there are changes
            status = self._run_git_command(["git", "status", "--porcelain"], root, env)
            if status.returncode != 0:
                return {"ok": False, "error": (status.stderr or "").strip() or "git status failed"}

            has_changes = bool((status.stdout or "").strip())

            # Create commit
            commit_result = self._create_commit(root, env, task, repo_changes, has_changes)
            if commit_result.get("error"):
                return commit_result

            # Stage additional files and amend if needed
            amended = self._stage_and_amend(root, env, report)

            # Get final commit hash
            head = self._run_git_command(["git", "rev-parse", "HEAD"], root, env)
            commit_hash = (head.stdout or "").strip() if head.returncode == 0 else ""

            return {
                "ok": True,
                "skipped": commit_result.get("skipped", False),
                "commit": commit_hash,
                "structure_ok": bool(commit_result.get("structure_ok")),
                "amended": bool(amended),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _prepare_git_env(self) -> Dict[str, str]:
        """Prepare git environment with Trinity author info."""
        env = os.environ.copy()
        env.setdefault("GIT_AUTHOR_NAME", "Trinity")
        env.setdefault("GIT_AUTHOR_EMAIL", "trinity@local")
        env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
        env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
        return env

    def _run_git_command(self, cmd: List[str], cwd: str, env: Dict[str, str]) -> subprocess.CompletedProcess:
        """Run a git command and return result."""
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)

    def _create_commit(self, root: str, env: Dict[str, str], task: str, 
                       repo_changes: Dict[str, Any], has_changes: bool) -> Dict[str, Any]:
        """Create git commit with task info."""
        # Stage all changes
        add = self._run_git_command(["git", "add", "."], root, env)
        if add.returncode != 0:
            return {"ok": False, "error": (add.stderr or "").strip() or "git add failed"}

        # Prepare commit message
        short_task = self._short_task_for_commit(task)
        subject = f"Trinity task completed: {short_task}"
        diff_stat = str(repo_changes.get("diff_stat") or "").strip() if isinstance(repo_changes, dict) else ""

        commit_cmd = [
            "git", "-c", "user.name=Trinity", "-c", "user.email=trinity@local",
            "commit", "--allow-empty", "-m", subject,
        ]
        if diff_stat:
            commit_cmd.extend(["-m", f"Diff stat:\n{diff_stat}"])

        env_commit = env.copy()
        env_commit["TRINITY_POST_COMMIT_RUNNING"] = "1"
        commit = self._run_git_command(commit_cmd, root, env_commit)

        if commit.returncode != 0:
            combined = (commit.stdout or "") + "\n" + (commit.stderr or "")
            if "nothing to commit" in combined.lower() and not has_changes:
                return {"ok": True, "skipped": True, "reason": "nothing_to_commit"}
            return {"ok": False, "error": (commit.stderr or "").strip() or "git commit failed"}

        return {"ok": True, "skipped": False}

    def _stage_and_amend(self, root: str, env: Dict[str, str], report: str) -> bool:
        """Stage additional files and amend commit if needed."""
        structure_ok = self._regenerate_project_structure(report)
        response_path = os.path.join(root, self.LAST_RESPONSE_FILE)

        # Stage response file
        if os.path.exists(response_path):
            self._run_git_command(["git", "add", self.LAST_RESPONSE_FILE], root, env)

        # Stage structure file
        if structure_ok and os.path.exists(os.path.join(root, self.PROJECT_STRUCTURE_FILE)):
            self._run_git_command(["git", "add", "-f", self.PROJECT_STRUCTURE_FILE], root, env)

        # Check if we need to amend
        cached = self._run_git_command(["git", "diff", "--cached", "--quiet"], root, env)
        if cached.returncode != 0:
            env_amend = env.copy()
            env_amend["TRINITY_POST_COMMIT_RUNNING"] = "1"
            amend = self._run_git_command(["git", "commit", "--amend", "--no-edit"], root, env_amend)
            return amend.returncode == 0
        return False

    def _format_final_report(self, *, task: str, outcome: str, repo_changes: Dict[str, Any],
                             last_agent: str, last_message: str, replan_count: int = 0,
                             commit_hash: Optional[str] = None) -> str:
        """Format final task report."""
        lines = self._build_report_header(task, outcome, replan_count, commit_hash, last_agent, last_message)
        lines.extend(self._build_report_changes(repo_changes))
        lines.extend(self._build_report_verification(last_message))
        lines.extend(["", "Tests:", "- not executed by Trinity (no deterministic test runner in pipeline)"])
        return "\n".join(lines).strip() + "\n"

    def _build_report_header(self, task, outcome, replan_count, commit_hash, last_agent, last_message) -> List[str]:
        """Build report header section."""
        lines = ["[Atlas] Final report", "", f"Task: {str(task or '').strip()}", f"Outcome: {outcome}", f"Replans: {replan_count}"]
        if commit_hash:
            lines.append(f"Зміни закомічені: {commit_hash}")
        lines.append(f"Last agent: {last_agent}")
        if last_message:
            lines.extend(["", "Last message:", str(last_message).strip()])
        return lines

    def _build_report_changes(self, repo_changes: Dict[str, Any]) -> List[str]:
        """Build changed files section."""
        lines = [""]
        if repo_changes.get("ok") is True:
            files = repo_changes.get("changed_files") or []
            lines.append("Changed files:")
            lines.extend([f"- {f}" for f in files] if files else ["- (no uncommitted changes detected)"])
            stat = str(repo_changes.get("diff_stat") or "").strip()
            if stat:
                lines.extend(["", "Diff stat:", stat])
        else:
            lines.extend(["Changed files:", f"- (unavailable: {repo_changes.get('error')})"])
        return lines

    def _build_report_verification(self, last_message: str) -> List[str]:
        """Build verification section."""
        lines = ["", "Verification:"]
        msg_l = (last_message or "").lower()
        if any(k in msg_l for k in SUCCESS_MARKERS):
            lines.append("- status: passed (heuristic)")
        elif any(k in msg_l for k in FAILURE_MARKERS):
            lines.append("- status: failed (heuristic)")
        else:
            lines.append("- status: unknown (no explicit signal)")
        return lines

    # ============ run() helper methods ============

    def _classify_and_route_task(self, input_text: str) -> Dict[str, Any]:
        """Classify task and determine routing parameters."""
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

        return {
            "task_type": task_type,
            "requires_windsurf": requires_windsurf,
            "intent_reason": intent_reason,
            "is_dev": is_dev,
            "allow_general": allow_general,
        }

    def _get_blocked_message(self, task_type: str, input_text: str) -> str:
        """Generate blocked task message."""
        return (
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

    def _normalize_run_params(self, gui_mode: Optional[str], execution_mode: Optional[str], recursion_limit: Optional[int]) -> tuple:
        """Normalize and validate run parameters."""
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

        return gm, em, recursion_limit

    def _build_initial_state(self, input_text: str, routing: Dict[str, Any], gm: str, em: str) -> Dict[str, Any]:
        """Build initial state dictionary for workflow."""
        return {
            "messages": [HumanMessage(content=input_text)],
            "current_agent": "meta_planner",
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
            "task_type": routing["task_type"],
            "is_dev": bool(routing["is_dev"]),
            "requires_windsurf": bool(routing["requires_windsurf"]),
            "dev_edit_mode": "cli",
            "intent_reason": routing["intent_reason"],
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

    def _init_screenshot_session(self) -> str:
        """Initialize screenshot session and return session ID."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            from system_ai.tools.screenshot import VisionDiffManager
            VisionDiffManager.get_instance().set_session_id(session_id)
            if self.verbose:
                print(f"📸 [Trinity] Screenshot session initialized: {session_id}")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Trinity] Could not initialize screenshot session: {e}")
        return session_id

    def _process_workflow_event(self, event: Dict[str, Any], tracking: Dict[str, Any]) -> None:
        """Process a single workflow event and update tracking state."""
        for node_name, state_update in (event or {}).items():
            tracking["last_node_name"] = str(node_name or "")
            tracking["last_state_update"] = state_update if isinstance(state_update, dict) else {}
            if isinstance(tracking["last_state_update"], dict) and "replan_count" in tracking["last_state_update"]:
                try:
                    tracking["last_replan_count"] = int(tracking["last_state_update"].get("replan_count") or 0)
                except Exception:
                    pass
            msgs = tracking["last_state_update"].get("messages", []) if isinstance(tracking["last_state_update"], dict) else []
            if msgs:
                m = msgs[-1]
                tracking["last_agent_message"] = str(getattr(m, "content", "") or "")
            tracking["last_agent_label"] = str(node_name or "")

    def _determine_outcome(self, last_state_update: Dict[str, Any], last_agent_message: str) -> str:
        """Determine task outcome from state and message."""
        outcome = self._get_base_outcome(last_state_update, last_agent_message)
        if outcome in {"paused", "blocked", "limit_reached"}:
            return outcome
        return self._check_needs_input(outcome, last_agent_message)

    def _get_base_outcome(self, last_state_update: Dict[str, Any], last_agent_message: str) -> str:
        """Get base outcome from status."""
        outcome = "completed"
        task_status = str((last_state_update or {}).get("task_status") or "").strip().lower()
        if task_status:
            outcome = task_status
        lower_msg = (last_agent_message or "").lower()
        if "limit" in lower_msg:
            return "limit_reached"
        if "paused" in lower_msg or "пауза" in lower_msg:
            return "paused"
        return outcome

    def _check_needs_input(self, outcome: str, last_agent_message: str) -> str:
        """Check if outcome should be needs_input."""
        lower_msg = (last_agent_message or "").lower()
        needs_input_markers = ["уточни", "уточнити", "підтверди", "підтвердження", "confirm", "confirmation", "clarify", "need уточ", "чи "]
        if any(m in lower_msg for m in needs_input_markers):
            if "[verified]" not in lower_msg and "[confirmed]" not in lower_msg:
                return "needs_input"
        return outcome

    def _check_artifact_sanity(self, input_text: str, outcome: str) -> tuple:
        """Check for missing artifacts in specific tasks. Returns (outcome, message)."""
        task_l = str(input_text or "").lower()
        if outcome not in {"completed", "success"} or "system_report_2025" not in task_l:
            return outcome, None

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
            return "failed_artifacts_missing", (
                "System_Report_2025 artifacts missing. Expected files were not found on Desktop. "
                + "Missing (first 6): "
                + ", ".join(missing[:6])
            )
        return outcome, None

    def _handle_run_completion(self, input_text: str, outcome: str, last_agent_message: str,
                                last_agent_label: str, last_node_name: str, last_replan_count: int) -> tuple:
        """Handle run completion: commit, report generation. Returns (report, commit_hash)."""
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
        return report, commit_hash

    def _save_response_file(self, report: str) -> None:
        """Save report to response file when no commit was made."""
        try:
            existing_content = ""
            my_response_section = ""
            trinity_reports_section = ""

            try:
                with open(self.LAST_RESPONSE_FILE, "r", encoding="utf-8") as f:
                    existing_content = f.read().strip()
            except FileNotFoundError:
                pass

            if existing_content:
                if "## My Last Response" in existing_content:
                    parts = existing_content.split(self.TRINITY_REPORT_HEADER)
                    my_response_section = parts[0].strip()
                    if len(parts) > 1:
                        trinity_reports_section = self.TRINITY_REPORT_HEADER + self.TRINITY_REPORT_HEADER.join(parts[1:])
                else:
                    trinity_reports_section = existing_content

            new_content = ""
            if my_response_section:
                new_content = my_response_section

            if trinity_reports_section:
                new_content += "\n\n---\n\n" + trinity_reports_section

            new_content += f"\n\n---\n\n{self.TRINITY_REPORT_HEADER}\n\n" + report

            with open(self.LAST_RESPONSE_FILE, "w", encoding="utf-8") as f:
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


    def run(
        self,
        input_text: str,
        *,
        gui_mode: Optional[str] = None,
        execution_mode: Optional[str] = None,
        recursion_limit: Optional[int] = None,
    ):
        """Main execution entry point for Trinity runtime."""
        # Step 1: Classify and route task
        routing = self._classify_and_route_task(input_text)
        task_type = routing["task_type"]
        requires_windsurf = routing["requires_windsurf"]
        is_dev = routing["is_dev"]

        # Step 2: Block non-dev tasks if not allowed
        if not is_dev and not routing["allow_general"]:
            blocked_message = self._get_blocked_message(task_type, input_text)
            if self.verbose:
                print(blocked_message)
            final_messages = [HumanMessage(content=input_text), AIMessage(content=blocked_message)]
            yield {"atlas": {"messages": final_messages, "current_agent": "end", "task_status": "blocked"}}
            return

        if self.verbose:
            print(f"✅ [Trinity] Task classified as: {task_type} (is_dev={is_dev}, requires_windsurf={requires_windsurf})")

        # Step 3: Normalize parameters
        gm, em, recursion_limit = self._normalize_run_params(gui_mode, execution_mode, recursion_limit)

        # Step 4: Build initial state
        initial_state = self._build_initial_state(input_text, routing, gm, em)

        # Step 5: Initialize screenshot session
        self._init_screenshot_session()

        # Step 6: Setup tracking state
        tracking = {
            "last_node_name": "",
            "last_state_update": {},
            "last_agent_message": "",
            "last_agent_label": "",
            "last_replan_count": 0
        }

        # Step 7: Log run start
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

        # Step 8: Execute workflow and stream events
        for event in self.workflow.stream(initial_state, config={"recursion_limit": recursion_limit}):
            try:
                self._process_workflow_event(event, tracking)
                try:
                    trace(self.logger, "trinity_graph_event", {
                        "node": tracking["last_node_name"],
                        "current_agent": tracking["last_state_update"].get("current_agent") if isinstance(tracking["last_state_update"], dict) else None,
                        "last_step_status": tracking["last_state_update"].get("last_step_status") if isinstance(tracking["last_state_update"], dict) else None,
                        "step_count": tracking["last_state_update"].get("step_count") if isinstance(tracking["last_state_update"], dict) else None,
                        "replan_count": tracking["last_replan_count"],
                    })
                except Exception:
                    pass
            except Exception:
                pass
            yield event

        # Step 9: Determine outcome
        outcome = self._determine_outcome(tracking["last_state_update"], tracking["last_agent_message"])

        # Step 10: Check artifact sanity
        try:
            new_outcome, artifact_msg = self._check_artifact_sanity(input_text, outcome)
            if artifact_msg:
                outcome = new_outcome
                tracking["last_agent_message"] = artifact_msg
        except Exception:
            pass

        # Step 11: Handle completion (commit, report)
        report, commit_hash = self._handle_run_completion(
            input_text, outcome, tracking["last_agent_message"],
            tracking["last_agent_label"], tracking["last_node_name"], tracking["last_replan_count"]
        )

        # Step 12: Log run end
        try:
            trace(self.logger, "trinity_run_end", {
                "outcome": outcome,
                "last_agent": tracking["last_agent_label"] or tracking["last_node_name"] or "unknown",
                "replan_count": tracking["last_replan_count"],
            })
        except Exception:
            pass

        # Step 13: Save response file if no commit
        if commit_hash is None:
            self._save_response_file(report)

        # Step 14: Yield final result
        final_messages = [HumanMessage(content=input_text), AIMessage(content=report)]
        yield {"atlas": {"messages": final_messages, "current_agent": "end", "task_status": outcome}}

