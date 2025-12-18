from typing import Annotated, TypedDict, Literal, List, Dict, Any, Optional, Callable
import json
import os
import subprocess
import re
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from core.agents.atlas import get_atlas_prompt, get_atlas_plan_prompt
from core.agents.tetyana import get_tetyana_prompt
from core.agents.grisha import get_grisha_prompt
from providers.copilot import CopilotLLM

from core.mcp import MCPToolRegistry
from core.verification import AdaptiveVerifier
from core.memory import get_memory
from dataclasses import dataclass
from tui.logger import get_logger, trace

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

class TrinityRuntime:
    MAX_REPLANS = 10
    MAX_STEPS = 50
    
    # Dev task keywords (allow execution)
    DEV_KEYWORDS = {
        "код", "code", "python", "javascript", "typescript", "script", "function",
        "рефакторинг", "refactor", "тест", "test", "git", "commit", "branch",
        "архітектура", "architecture", "api", "database", "db", "sql",
        "windsurf", "editor", "ide", "файл", "file", "write", "create",
        "bug", "fix", "error", "debug", "patch", "merge", "pull request",
        "deploy", "build", "compile", "run", "execute", "shell", "command",
        "npm", "pip", "package", "dependency", "import", "module", "library"
    }
    
    # Non-dev keywords (block execution)
    NON_DEV_KEYWORDS = {
        # Media & Entertainment
        "фільм", "movie", "video", "youtube", "netflix", "браузер", "browser",
        "музика", "music", "spotify", "apple music", "відкрий", "open",
        "переглянь", "watch", "слухай", "listen", "грай", "play",
        "скачай", "download", "завантаж", "upload", "фото", "photo",
        "картинка", "image", "розташування", "location", "карта", "map",
        "погода", "weather", "новини", "news", "соціальна мережа", "social",
        "facebook", "instagram", "twitter", "whatsapp", "telegram",
        "email", "mail", "повідомлення", "message", "чат", "chat",
        
        # Standard macOS folders (non-dev)
        "documents", "документи", "desktop", "робочий стіл", "downloads", "завантаження",
        "pictures", "фото", "movies", "фільми", "music", "музика",
        "applications", "програми", "library", "бібліотека",
        "~/", "$home", "~", "home", "users", "користувачі",
        "finder", "фіндер", "trash", "кошик", "recycle bin",
        
        # System operations (non-dev)
        "видалити", "delete", "видали", "remove", "очистити", "clean",
        "перейменувати", "rename", "скопіювати", "copy", "перемістити", "move",
        "архівувати", "archive", "zip", "unzip", "compress", "розпакувати"
    }
    
    def __init__(
        self,
        verbose: bool = True,
        permissions: TrinityPermissions = None,
        on_stream: Optional[Callable[[str, str], None]] = None,
    ):
        self.llm = CopilotLLM()
        self.verbose = verbose
        self.logger = get_logger("system_cli.trinity")
        self.registry = MCPToolRegistry()
        self.verifier = AdaptiveVerifier(self.llm)
        self.memory = get_memory()
        self.permissions = permissions or TrinityPermissions()
        # Callback for streaming deltas: (agent_name, text_delta)
        self.on_stream = on_stream
        self.workflow = self._build_graph()

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            s = str(text or "").strip()
            if not s:
                return None
            # Try direct JSON first.
            if s.startswith("{") and s.endswith("}"):
                obj = json.loads(s)
                return obj if isinstance(obj, dict) else None
            # Best-effort extraction of the first JSON object.
            match = re.search(r"\{.*\}", s, re.DOTALL)
            if not match:
                return None
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

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
                "DEV means software development work or dev-support operations (debugging, checking permissions/disk space/processes for dev tools, git, tests, repo files). "
                "GENERAL means unrelated household/media/personal tasks. "
                "Also decide whether the task requires using Windsurf IDE for code generation/editing. "
                "Return STRICT JSON only with keys: task_type (DEV|GENERAL), requires_windsurf (bool), confidence (0..1), reason (string)."
            )
            msgs: List[BaseMessage] = [
                SystemMessage(content=sys),
                HumanMessage(content=str(task or "")),
            ]
            resp = self.llm.invoke(msgs)
            data = self._extract_json_object(getattr(resp, "content", ""))
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

    def _classify_task(self, task: str) -> tuple[str, bool]:
        """
        Classify task as DEV or GENERAL.
        Returns: (task_type, is_dev)
        """
        llm_res = self._classify_task_llm(task)
        if llm_res:
            task_type = str(llm_res.get("task_type") or "").strip().upper()
            return (task_type, task_type == "DEV")
        fb = self._classify_task_fallback(task)
        task_type = str(fb.get("task_type") or "").strip().upper()
        return (task_type, task_type != "GENERAL")
    
    def _build_graph(self):
        builder = StateGraph(TrinityState)

        builder.add_node("atlas", self._atlas_node)
        builder.add_node("tetyana", self._tetyana_node)
        builder.add_node("grisha", self._grisha_node)

        builder.set_entry_point("atlas")
        
        builder.add_conditional_edges(
            "atlas", 
            self._router, 
            {"tetyana": "tetyana", "grisha": "grisha", "end": END}
        )
        builder.add_conditional_edges(
            "tetyana", 
            self._router, 
            {"grisha": "grisha", "atlas": "atlas", "tetyana": "tetyana", "end": END}
        )
        builder.add_conditional_edges(
            "grisha", 
            self._router, 
            {"atlas": "atlas", "end": END}
        )

        return builder.compile()

    def _atlas_node(self, state: TrinityState):
        if self.verbose: print("🌐 [Atlas] Strategizing...")
        context = state.get("messages", [])
        last_msg = context[-1].content if context else "Start"
         
        # Check step/replan limits
        step_count = state.get("step_count", 0) + 1
        replan_count = state.get("replan_count", 0)

        try:
            plan_preview = state.get("plan")
            trace(self.logger, "atlas_enter", {
                "step_count": step_count,
                "replan_count": replan_count,
                "last_step_status": state.get("last_step_status"),
                "plan_len": len(plan_preview) if isinstance(plan_preview, list) else 0,
                "task_type": state.get("task_type"),
                "execution_mode": state.get("execution_mode"),
                "gui_mode": state.get("gui_mode"),
                "dev_edit_mode": state.get("dev_edit_mode"),
                "last_msg_preview": str(last_msg)[:200],
            })
        except Exception:
            pass
         
        if step_count > self.MAX_STEPS:
            try:
                trace(self.logger, "atlas_limit_reached", {"step_count": step_count, "max_steps": self.MAX_STEPS})
            except Exception:
                pass
            return {"current_agent": "end", "messages": [AIMessage(content=f"[VOICE] Ліміт кроків ({self.MAX_STEPS}) досягнуто. Завершую.")]}
         
        if replan_count > self.MAX_REPLANS:
            try:
                trace(self.logger, "atlas_replan_limit_reached", {"replan_count": replan_count, "max_replans": self.MAX_REPLANS})
            except Exception:
                pass
            return {"current_agent": "end", "messages": [AIMessage(content=f"[VOICE] Ліміт перепланувань ({self.MAX_REPLANS}) досягнуто. Потрібна допомога.")]}
         
        # Check for pause (permission required)
        pause_info = state.get("pause_info")
        if pause_info:
            msg = pause_info.get("message", "Permission required")
            if self.verbose:
                print(f"⚠️ [Atlas] PAUSED: {msg}")
            try:
                trace(self.logger, "atlas_paused", {"message": str(msg)[:200], "pause_info": pause_info})
            except Exception:
                pass
            return {
                "current_agent": "end",
                "task_status": "paused",
                "messages": [AIMessage(content=f"[VOICE] ПАУЗА. {msg}")],
                "pause_info": pause_info
            }
        
        # 1. Query RAG for relevant past experiences
        rag_context = ""
        try:
            strategies = self.memory.query_memory("strategies", last_msg, n_results=2)
            if strategies:
                rag_context = "Relevante минулі стратегії:\n" + "\n".join([s["content"][:200] for s in strategies])
                if self.verbose: print(f"🌐 [Atlas] RAG found {len(strategies)} relevant strategies.")
        except Exception:
            pass
        
        # 1b. Read project structure context for continual development
        structure_context = self._get_project_structure_context()
        if structure_context:
            rag_context += f"\n\n## Контекст репозиторію (Last Response, Git Log, Recent Changes):\n{structure_context}"
            if self.verbose: print(f"🌐 [Atlas] Loaded project structure context ({len(structure_context)} chars)")

        # Update Summary Memory if context is getting long
        summary = state.get("summary", "")
        if len(context) > 6 and step_count % 3 == 0:
             try:
                # Simple summarization using LLM
                summary_prompt = [
                    SystemMessage(content="Ти — архіваріус. Створи стислий підсумок (2-3 речення) поточного стану виконання задачі на основі історії повідомлень. Збережи ключові деталі (що зроблено, що залишилось)."),
                    HumanMessage(content=f"Поточний підсумок: {summary}\n\nОстанні повідомлення:\n" + "\n".join([m.content[:500] for m in context[-4:]]))
                ]
                sum_resp = self.llm.invoke(summary_prompt)
                summary = sum_resp.content
                if self.verbose: print(f"🌐 [Atlas] Memory Updated: {summary[:50]}...")
             except Exception:
                pass
        
        # 2. Manage Plan State (Consumption)
        plan = state.get("plan")
        last_step_status = state.get("last_step_status", "success") # Default to success for first run
        current_step_fail_count = int(state.get("current_step_fail_count") or 0)

        if plan and step_count > 1:
            if last_step_status == "success":
                # Only pop if the previous agent explicitly succeeded
                if len(plan) > 0:
                    plan.pop(0)
                    current_step_fail_count = 0  # Reset fail count on success
                    if self.verbose: print(f"🌐 [Atlas] Step completed successfully. Remaining steps: {len(plan)}")
                    try:
                        trace(self.logger, "atlas_step_consumed", {"remaining_steps": len(plan), "step_count": step_count})
                    except Exception:
                        pass
                    # If plan is now empty, we are done!
                    if not plan:
                        try:
                            trace(self.logger, "atlas_plan_completed", {"step_count": step_count, "replan_count": replan_count})
                        except Exception:
                            pass
                        return {"current_agent": "end", "messages": [AIMessage(content="[VOICE] Всі кроки плану виконано успішно.")]}
            elif last_step_status == "failed":
                current_step_fail_count += 1
                if self.verbose: print(f"🌐 [Atlas] Step failed (attempt {current_step_fail_count}). Retrying...")
                try:
                    trace(self.logger, "atlas_step_failed", {"step_count": step_count, "replan_count": replan_count, "fail_count": current_step_fail_count})
                except Exception:
                    pass
                # If 3+ failures on the same step, force replan
                if current_step_fail_count >= 3:
                    if self.verbose: print(f"🌐 [Atlas] 3+ failures on same step. Forcing replan.")
                    plan = None  # Force new plan generation
                    current_step_fail_count = 0
            else:
                if self.verbose: print(f"🌐 [Atlas] Step status uncertain ({last_step_status}). Continuing current step...")
                try:
                    trace(self.logger, "atlas_step_uncertain", {"step_count": step_count, "replan_count": replan_count})
                except Exception:
                    pass

        # 3. Generate New Plan if empty
        if not plan:
            if self.verbose: print("🌐 [Atlas] Generating new plan...")
            try:
                trace(self.logger, "atlas_plan_generate_start", {"step_count": step_count, "replan_count": replan_count})
            except Exception:
                pass
            
            # Use LLM to generate structured plan
            plan_resp = None
            try:
                routing_hint = ""
                try:
                    tt = str(state.get("task_type") or "").strip()
                    rw = state.get("requires_windsurf")
                    dem = str(state.get("dev_edit_mode") or "").strip()
                    if tt or (rw is not None) or dem:
                        routing_hint = f"\n\n[ROUTING] task_type={tt} requires_windsurf={rw} dev_edit_mode={dem}"
                except Exception:
                    routing_hint = ""

                # Use specific planning prompt with HISTORY
                from core.agents.atlas import ATLAS_PLANNING_PROMPT
                
                # Construct messages: System Prompt + History + Context/Instruction
                planning_messages = [SystemMessage(content=ATLAS_PLANNING_PROMPT)]
                
                # Add history (excluding the very last one if it's identical to what we'd append, but usually safe)
                # We want the planner to see the whole conversation to know what was done and what was asked.
                planning_messages.extend(state.get("messages", []))
                
                # Add a strong reminder of the current objective based on context
                reminder_msg = f"Проаналізуй історію вище. Поточний стан/контекст: {rag_context + routing_hint}\nЗараз ми на кроці {step_count}. Які наступні кроки згідно з оригінальним запитом? Поверни JSON."
                planning_messages.append(HumanMessage(content=reminder_msg))

                plan_resp = self.llm.invoke(planning_messages)
                
                import re
                json_str = plan_resp.content
                match = re.search(r"\[.*\]", json_str, re.DOTALL)
                if match:
                    json_str = match.group(0)
                
                raw_plan = json.loads(json_str)
                if not isinstance(raw_plan, list):
                    raise ValueError("Plan is not a list")
            except Exception as e:
                if self.verbose: print(f"⚠️ [Atlas] Smart Planning failed ({e}). Fallback to 1-step.")
                try:
                    trace(self.logger, "atlas_plan_generate_error", {"error": str(e)[:200]})
                except Exception:
                    pass
                raw_plan = [{
                    "id": 1, 
                    "type": "execute", 
                    "description": last_msg,
                    "agent": "tetyana"
                }]
            
            # Optimize Plan (Adaptive Verification)
            plan = self.verifier.optimize_plan(raw_plan)

            try:
                trace(self.logger, "atlas_plan_generated", {"steps": len(plan) if isinstance(plan, list) else 0, "step_count": step_count, "replan_count": replan_count})
            except Exception:
                pass
            
            if self.verbose:
                print(f"🌐 [Atlas] Plan Optimized: {len(plan)} steps.")
                for step in plan:
                    print(f"   - {step['type'].upper()}: {step['description']}")

        # 3. Dispatch Logic
        current_step = plan[0] if plan else None
        
        if not current_step:
            return {"current_agent": "end", "messages": [AIMessage(content="[VOICE] Не вдалося створити план.")]}
        
        # Router Logic based on Plan Step Type
        step_type = current_step.get("type", "execute")
        if step_type == "verify":
            next_agent = "grisha"
        elif step_type == "bootstrap":
            # Bootstrap steps are executed by Tetyana with special handling
            next_agent = "tetyana"
        else:
            next_agent = "tetyana"

        try:
            trace(self.logger, "atlas_dispatch", {
                "next_agent": next_agent,
                "step_type": step_type,
                "step_count": step_count,
                "replan_count": replan_count,
                "description_preview": str(current_step.get("description", ""))[:200],
            })
        except Exception:
            pass
            
        # Update state with the plan and counters
        # Build content from plan result or current step description
        desc = current_step.get('description', '')
        if next_agent == "tetyana":
            voice = f"[VOICE] Тетяно, {desc}. Виконуй."
        elif next_agent == "grisha":
            voice = f"[VOICE] Гріша, перевір: {desc}."
        else:
            voice = f"[VOICE] Наступний крок: {desc}."

        content = f"{voice}\n\n[Atlas Debug] Plan: {len(plan)} steps. Current: {desc}. Next: {next_agent}"
        
        # Preserve existing messages and add new one
        updated_messages = list(context) + [AIMessage(content=content)]
        return {
            "current_agent": next_agent, 
            "messages": updated_messages,
            "plan": plan,
            "step_count": step_count,
            "replan_count": replan_count,
            "summary": summary,
            "current_step_fail_count": current_step_fail_count,
        }

    def _tetyana_node(self, state: TrinityState):
        if self.verbose: print("💻 [Tetyana] Developing...")
        context = state.get("messages", [])
        if not context:
            return {"current_agent": "end", "messages": [AIMessage(content="[VOICE] Немає контексту для виконання.")]}
        last_msg = context[-1].content

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

        # Inject available tools into Tetyana's prompt.
        # If we are in GUI mode, we still list all tools, but the prompt instructs to prefer GUI primitives.
        tools_list = self.registry.list_tools()
        prompt = get_tetyana_prompt(str(last_msg or "") + routing_hint, tools_desc=tools_list)
        
        # Bind tools to LLM for structured tool_calls output.
        tool_defs = []
        for name, func in self.registry._tools.items():
            desc = self.registry._descriptions.get(name, "")
            tool_defs.append({"name": name, "description": desc})
        
        bound_llm = self.llm.bind_tools(tool_defs)
        
        pause_info = None
        content = ""  # Initialize content variable
        
        try:
            # For tool-bound calls, use invoke_with_stream to capture deltas for the TUI
            def on_delta(chunk):
                if self.on_stream:
                    self.on_stream("tetyana", chunk)
            
            response = self.llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
            content = response.content
            tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            
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

                    # Track failures for fallback decision
                    try:
                        res_dict = json.loads(res_str)
                        if isinstance(res_dict, dict):
                            if str(res_dict.get("status", "")).lower() == "error":
                                had_failure = True
                    except Exception:
                        pass
                    
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
                    content += "\n\n[STEP_COMPLETED] Всі інструменти виконано успішно."

            # Save successful action to RAG memory (only if no pause)
            if not pause_info:
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
                updated_messages = list(context) + [AIMessage(content=f"[VOICE] Native не спрацював. Перемикаюся на GUI режим.")]
                
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
                "current_agent": "atlas",
                "messages": updated_messages,
                "pause_info": pause_info
            }
        
        # Preserve existing messages and add new one
        updated_messages = list(context) + [AIMessage(content=content)]
        
        try:
            trace(self.logger, "tetyana_exit", {
                "next_agent": "grisha",
                "last_step_status": "failed" if had_failure else "success",
                "execution_mode": execution_mode,
                "gui_mode": gui_mode,
                "dev_edit_mode": dev_edit_mode,
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
        }

    def _grisha_node(self, state: TrinityState):
        if self.verbose: print("👁️ [Grisha] Verifying...")
        context = state.get("messages", [])
        if not context:
            return {"current_agent": "end", "messages": [AIMessage(content="[VOICE] Немає контексту для перевірки.")]}
        last_msg = context[-1].content
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
        tools_list = self.registry.list_tools()
        prompt = get_grisha_prompt(last_msg, tools_desc=tools_list)
        
        content = ""  # Initialize content variable
        try:
            trace(self.logger, "grisha_llm_start", {"prompt_len": len(str(prompt.format_messages()))})
            # For tool-bound calls, use invoke_with_stream to capture deltas for the TUI
            def on_delta(chunk):
                if self.on_stream:
                    self.on_stream("grisha", chunk)
            
            response = self.llm.invoke_with_stream(prompt.format_messages(), on_delta=on_delta)
            content = response.content
            tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            
            try:
                trace(self.logger, "grisha_llm", {
                    "tool_calls": len(tool_calls) if isinstance(tool_calls, list) else 0,
                    "content_preview": str(content)[:200],
                })
            except Exception:
                pass
            
            # Execute Tools
            results = []
            if tool_calls:
                 for tool in tool_calls:
                     name = tool.get("name")
                     args = tool.get("args") or {}
                     
                     # Provide helpful default for capture_screen if args empty
                     if name == "capture_screen" and not args:
                         args = {"app_name": None}

                     # Execute via MCP Registry
                     res = self.registry.execute(name, args)
                     results.append(f"Result for {name}: {res}")
            
            if results:
                content += "\n\nVerification Tools Results:\n" + "\n".join(results)
            
            # Append test results if any
            if test_results:
                content += test_results

            # Deterministic verification hook for GUI mode: always capture + analyze.
            if gui_mode in {"auto", "on"} and execution_mode == "gui":
                snap = self.registry.execute("capture_screen", {"app_name": None})
                content += "\n\n[GUI_VERIFY] capture_screen:\n" + str(snap)
                try:
                    snap_dict = json.loads(snap)
                    img_path = snap_dict.get("path") if isinstance(snap_dict, dict) else None
                except Exception:
                    img_path = None
                if img_path:
                    analysis = self.registry.execute(
                        "analyze_screen",
                        {"image_path": img_path, "prompt": "Verify the UI state. Describe what changed and whether the goal seems achieved."},
                    )
                    content += "\n\n[GUI_VERIFY] analyze_screen:\n" + str(analysis)

        except Exception as e:
            content = f"Error invoking Grisha: {e}"


        # If Grisha says "CONFIRMED" or "VERIFIED", we end. Else Atlas replans.
        lower_content = content.lower()
        step_status = "uncertain"
        next_agent = "atlas"

        # 1. Check for explicit success markers (including Tetyana's [STEP_COMPLETED])
        explicit_complete_markers = [
            "[verified]", "[confirmed]", "[step_completed]", "[completed]",
            "verification passed", "qa passed", 
            "verdict: pass", "верифікація пройдена", "перевірку пройдено", "підтверджую"
        ]
        has_explicit_complete = any(m in lower_content for m in explicit_complete_markers)
        
        # 2. Check for tool execution errors in context (status: error = FAILED, not uncertain)
        has_tool_error_in_context = '"status": "error"' in content or '"status":"error"' in content
        
        # 3. Check for test failures
        has_test_failure = "[test_verification]" in lower_content and ("failed" in lower_content or "error" in lower_content)
        
        # 4. NEW: Check for successful tool results (tool returned data without error = SUCCESS)
        # This is the key fix: if Tetyana executed tools and got results, that's success!
        has_successful_tool_result = (
            "tool results:" in lower_content and 
            '"status": "success"' in content or
            '"status":"success"' in content or
            # Tool returned a JSON array or object with data (not an error)
            ("result for " in lower_content and not has_tool_error_in_context)
        )
        
        # 5. Success / Failure / Indecision (REORDERED for better priority)
        if has_test_failure:
            step_status = "failed"
            next_agent = "atlas"
        elif has_tool_error_in_context:
            # Tool execution error is a clear failure, not uncertain
            step_status = "failed"
            next_agent = "atlas"
            if self.verbose:
                print("👁️ [Grisha] Tool error detected in context → marking as FAILED")
        elif has_explicit_complete:
            step_status = "success"
            next_agent = "atlas"
            if self.verbose:
                print("👁️ [Grisha] Explicit completion marker found → SUCCESS")
        elif has_successful_tool_result:
            # NEW: Tool executed successfully with data = SUCCESS (not uncertain!)
            step_status = "success"
            next_agent = "atlas"
            if self.verbose:
                print("👁️ [Grisha] Tool executed with successful result → SUCCESS")
        elif any(kw in lower_content for kw in ["успішно", "verified", "працює", "готово", "виконано", "completed", "done"]):
            step_status = "success"
            next_agent = "atlas"
        elif any(kw in lower_content for kw in ["failed", "error", "помилка", "не вдалося", "неможливо", "blocked"]):
            step_status = "failed"
            next_agent = "atlas"
        else:
            # NEW: If no tools were used and status is uncertain, force verification
            if not tool_calls:
                if self.verbose:
                    print("👁️ [Grisha] No tools used and uncertain → forcing capture_screen verification")
                try:
                    trace(self.logger, "grisha_forcing_verification", {"reason": "no_tools_uncertain"})
                    snap = self.registry.execute("capture_screen", {"app_name": None})
                    content += "\n\n[FORCED_VERIFY] capture_screen:\n" + str(snap)
                    # Try to extract image path for analysis
                    try:
                        snap_dict = json.loads(snap)
                        img_path = snap_dict.get("path") if isinstance(snap_dict, dict) else None
                    except Exception:
                        img_path = None
                    if img_path:
                        analysis = self.registry.execute(
                            "analyze_screen",
                            {"image_path": img_path, "prompt": "Describe what you see. Is this a success state or an error state?"},
                        )
                        content += "\n\n[FORCED_VERIFY] analyze_screen:\n" + str(analysis)
                        # Check analysis result for success/failure indicators
                        analysis_lower = str(analysis).lower()
                        if any(kw in analysis_lower for kw in ["success", "done", "completed", "expected", "correct"]):
                            step_status = "success"
                        elif any(kw in analysis_lower for kw in ["error", "fail", "wrong", "unexpected"]):
                            step_status = "failed"
                except Exception as ve:
                    if self.verbose:
                        print(f"👁️ [Grisha] Forced verification failed: {ve}")
            
            # If still uncertain after forced verification
            if step_status == "uncertain":
                step_status = "uncertain"
                next_agent = "atlas"

        # Preserve existing messages and add new one (with potentially enriched content)
        updated_messages = list(context) + [AIMessage(content=content)]

        # NEW: Anti-loop protection via uncertain_streak
        current_streak = int(state.get("uncertain_streak") or 0)
        if step_status in {"uncertain", "failed"}:
            current_streak += 1
        else:
            current_streak = 0  # Reset on definite decision (success)
        
        # If 3+ consecutive uncertain decisions, force to success with warning
        if step_status == "uncertain" and current_streak >= 3:
            if self.verbose:
                print(f"⚠️ [Grisha] Uncertainty streak ({current_streak}) reached limit → forcing SUCCESS")
            try:
                trace(self.logger, "grisha_uncertainty_limit", {"streak": current_streak, "forced": "success"})
            except Exception:
                pass
            step_status = "success"
            updated_messages.append(AIMessage(content="[VOICE] Після кількох спроб перевірки, вважаю завдання виконаним. [VERIFIED]"))
            current_streak = 0

        try:
            trace(self.logger, "grisha_decision", {"next_agent": next_agent, "last_step_status": step_status, "uncertain_streak": current_streak})
        except Exception:
            pass

        out = {
            "current_agent": next_agent, 
            "messages": updated_messages,
            "last_step_status": step_status,
            "uncertain_streak": current_streak,
            "plan": state.get("plan"),  # Always preserve plan in state
        }
        
        # Determine if we need to increase replan_count
        if next_agent == "atlas" and step_status in {"failed", "uncertain"}:
            current_replan = int(state.get("replan_count") or 0)
            
            # Replan if:
            # - Failed twice in a row (current_streak >= 2)
            # - Still uncertain after 2 attempts (will force success on 3rd)
            should_replan = (
                (step_status == "failed" and current_streak >= 2) or
                (step_status == "uncertain" and current_streak >= 2)
            )
            
            if should_replan:
                out["replan_count"] = current_replan + 1
                out["plan"] = None  # Clear plan to trigger regeneration
                try:
                    trace(self.logger, "replan_triggered", {"replan_count": out["replan_count"], "status": step_status, "streak": current_streak})
                except Exception:
                    pass
            else:
                # Keep plan, Atlas will retry the current step
                try:
                    trace(self.logger, "retry_without_replan", {"status": step_status, "streak": current_streak})
                except Exception:
                    pass
        return out

    def _router(self, state: TrinityState):
        current = state["current_agent"]
        try:
            trace(self.logger, "router_decision", {"current": current, "next": current})  # Router typically just returns current agent for StateGraph? No, state graph edge logic uses this.
        except Exception:
            pass
        return current

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
            
            with open(structure_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract key sections for context (Last Response, Git Log, Recent Changes)
            lines = content.split('\n')
            context_lines = []
            current_section = None
            section_count = 0
            
            for line in lines:
                # Extract Last Response section
                if '## Last Response' in line:
                    current_section = 'last_response'
                    section_count = 0
                    continue
                elif '## Git Diff' in line:
                    current_section = 'git_diff'
                    section_count = 0
                    continue
                elif '## Git Log' in line:
                    current_section = 'git_log'
                    section_count = 0
                    continue
                elif line.startswith('## ') and current_section:
                    current_section = None
                
                # Collect lines from key sections (limit to 50 lines per section)
                if current_section and section_count < 50:
                    if line.strip() and not line.startswith('```'):
                        context_lines.append(line)
                        section_count += 1
            
            return '\n'.join(context_lines[:100])  # Limit to 100 lines total
            
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
        if any(k in msg_l for k in ["verified", "confirmed", "успішно", "готово", "success"]):
            lines.append("- status: passed (heuristic)")
        elif any(k in msg_l for k in ["failed", "error", "помилка", "не вдалося"]):
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
                recursion_limit = int(os.getenv("TRINITY_RECURSION_LIMIT", "100"))
            except Exception:
                recursion_limit = 100
        try:
            recursion_limit = int(recursion_limit)
        except Exception:
            recursion_limit = 100
        if recursion_limit < 25:
            recursion_limit = 25

        initial_state = {
            "messages": [HumanMessage(content=input_text)],
            "current_agent": "atlas",
            "task_status": "started",
            "final_response": None,
            "step_count": 0,
            "replan_count": 0,
            "summary": None,
            "pause_info": None,
            "gui_mode": gm,
            "execution_mode": em,
            "gui_fallback_attempted": False,
            "task_type": task_type,
            "is_dev": bool(is_dev),
            "requires_windsurf": bool(requires_windsurf),
            "dev_edit_mode": "windsurf" if bool(requires_windsurf) else "cli",
            "intent_reason": intent_reason,
        }

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
