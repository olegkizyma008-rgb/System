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

@dataclass
class TrinityPermissions:
    """Permission flags for Trinity system actions."""
    allow_shell: bool = False
    allow_applescript: bool = False
    allow_file_write: bool = False
    allow_gui: bool = False
    allow_shortcuts: bool = False

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

class TrinityRuntime:
    MAX_REPLANS = 5
    MAX_STEPS = 30
    
    def __init__(
        self,
        verbose: bool = True,
        permissions: TrinityPermissions = None,
        on_stream: Optional[Callable[[str, str], None]] = None,
    ):
        self.llm = CopilotLLM()
        self.verbose = verbose
        self.registry = MCPToolRegistry()
        self.verifier = AdaptiveVerifier(self.llm)
        self.memory = get_memory()
        self.permissions = permissions or TrinityPermissions()
        # Callback for streaming deltas: (agent_name, text_delta)
        self.on_stream = on_stream
        self.workflow = self._build_graph()

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
            {"grisha": "grisha", "atlas": "atlas", "end": END}
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
        
        if step_count > self.MAX_STEPS:
            return {"current_agent": "end", "messages": [AIMessage(content=f"[Atlas] Ліміт кроків ({self.MAX_STEPS}) досягнуто. Завершую.")]}
        
        if replan_count > self.MAX_REPLANS:
            return {"current_agent": "end", "messages": [AIMessage(content=f"[Atlas] Ліміт перепланувань ({self.MAX_REPLANS}) досягнуто. Потрібна допомога користувача.")]}
        
        # Check for pause (permission required)
        pause_info = state.get("pause_info")
        if pause_info:
            msg = pause_info.get("message", "Permission required")
            if self.verbose:
                print(f"⚠️ [Atlas] PAUSED: {msg}")
            return {
                "current_agent": "end",
                "task_status": "paused",
                "messages": [AIMessage(content=f"[ПАУЗА] {msg}")],
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
        if plan and step_count > 1:
            # We returned to Atlas inside the loop.
            # Remove the step we just attempted/completed.
            if len(plan) > 0:
                plan.pop(0)
                # If plan is now empty, we are done!
                if not plan:
                    return {"current_agent": "end", "messages": [AIMessage(content="[Atlas] Всі кроки плану виконано успішно.")]}

        # 3. Generate New Plan if empty
        if not plan:
            if self.verbose: print("🌐 [Atlas] Generating new plan...")
            
            # Use LLM to generate structured plan
            plan_resp = None
            try:
                plan_prompt = get_atlas_plan_prompt(last_msg, context=rag_context)
                plan_resp = self.llm.invoke(plan_prompt.format_messages())
                
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
                raw_plan = [{
                    "id": 1, 
                    "type": "execute", 
                    "description": last_msg,
                    "agent": "tetyana"
                }]
            
            # Optimize Plan (Adaptive Verification)
            plan = self.verifier.optimize_plan(raw_plan)
            
            if self.verbose:
                print(f"🌐 [Atlas] Plan Optimized: {len(plan)} steps.")
                for step in plan:
                    print(f"   - {step['type'].upper()}: {step['description']}")

        # 3. Dispatch Logic
        current_step = plan[0] if plan else None
        
        if not current_step:
            return {"current_agent": "end", "messages": [AIMessage(content="No plan generated.")]}

        # Invoke Atlas Persona with RAG context
        rag_hint = f"\n\n{rag_context}" if rag_context else ""
        prompt = get_atlas_prompt(f"The plan is: {current_step['description']}. Announce it.{rag_hint}")
        content = ""  # Initialize content variable
        try:
            if self.on_stream and hasattr(self.llm, "invoke_with_stream"):
                # Wrap on_stream so the consumer knows which agent is speaking
                def _delta(piece: str) -> None:
                    try:
                        self.on_stream("Atlas", piece)
                    except Exception:
                        # Streaming callback failures should not break the agent
                        pass

                response = self.llm.invoke_with_stream(prompt.format_messages(), on_delta=_delta)
            else:
                response = self.llm.invoke(prompt.format_messages())
            content = response.content
        except Exception as e:
            content = f"Error invoking Atlas: {e}"
            return {"current_agent": "end", "messages": [AIMessage(content=content)]}

        # Router Logic based on Plan Step Type
        step_type = current_step.get("type", "execute")
        if step_type == "verify":
            next_agent = "grisha"
        elif step_type == "bootstrap":
            # Bootstrap steps are executed by Tetyana with special handling
            next_agent = "tetyana"
        else:
            next_agent = "tetyana"
            
        # Update state with the plan and counters
        # Preserve existing messages and add new one
        updated_messages = list(context) + [AIMessage(content=content)]
        return {
            "current_agent": next_agent, 
            "messages": updated_messages,
            "plan": plan,
            "step_count": step_count,
            "replan_count": replan_count,
            "summary": summary
        }

    def _tetyana_node(self, state: TrinityState):
        if self.verbose: print("💻 [Tetyana] Developing...")
        context = state.get("messages", [])
        if not context:
            return {"current_agent": "end", "messages": [AIMessage(content="[Tetyana] No context available.")]}
        last_msg = context[-1].content

        gui_mode = str(state.get("gui_mode") or "auto").strip().lower()
        execution_mode = str(state.get("execution_mode") or "native").strip().lower()
        gui_fallback_attempted = bool(state.get("gui_fallback_attempted") or False)
        
        
        # Inject available tools into Tetyana's prompt.
        # If we are in GUI mode, we still list all tools, but the prompt instructs to prefer GUI primitives.
        tools_list = self.registry.list_tools()
        prompt = get_tetyana_prompt(last_msg, tools_desc=tools_list)
        
        # Bind tools to LLM for structured tool_calls output.
        tool_defs = []
        for name, func in self.registry._tools.items():
            desc = self.registry._descriptions.get(name, "")
            tool_defs.append({"name": name, "description": desc})
        
        bound_llm = self.llm.bind_tools(tool_defs)
        
        pause_info = None
        content = ""  # Initialize content variable
        
        try:
            # For tool-bound calls, don't stream (JSON protocol needs complete response)
            response = bound_llm.invoke(prompt.format_messages())
            content = response.content
            tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            
            results = []
            had_failure = False
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
            }
            if tool_calls:
                for tool in tool_calls:
                    name = tool.get("name")
                    args = tool.get("args") or {}
                    
                    # Permission check for dangerous tools
                    if name in shell_tools and not self.permissions.allow_shell:
                        pause_info = {
                            "permission": "shell",
                            "message": "Потрібен дозвіл на виконання shell команд. Введіть /allow shell",
                            "blocked_tool": name,
                            "blocked_args": args
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue

                    if name == "run_shortcut" and not self.permissions.allow_shortcuts:
                        pause_info = {
                            "permission": "shortcuts",
                            "message": "Потрібен дозвіл на запуск Shortcuts. Введіть /allow shortcuts",
                            "blocked_tool": name,
                            "blocked_args": args,
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                        
                    if name in applescript_tools and not self.permissions.allow_applescript:
                        pause_info = {
                            "permission": "applescript",
                            "message": "Потрібен дозвіл на виконання AppleScript. Введіть /allow applescript",
                            "blocked_tool": name,
                            "blocked_args": args
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                    if name in gui_tools and not self.permissions.allow_gui:
                        pause_info = {
                            "permission": "gui",
                            "message": "Потрібен дозвіл на GUI automation (mouse/keyboard). Увімкніть unsafe/gui mode.",
                            "blocked_tool": name,
                            "blocked_args": args,
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue

                    
                    # Execute via MCP Registry
                    res_str = self.registry.execute(name, args)
                    results.append(f"Result for {name}: {res_str}")

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
                updated_messages = list(context) + [AIMessage(content=f"[Tetyana] Native execution had failures. Switching to GUI fallback mode.")]
                return {
                    "current_agent": "tetyana",
                    "messages": updated_messages,
                    "execution_mode": "gui",
                    "gui_fallback_attempted": True,
                    "gui_mode": gui_mode,
                }
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ [Tetyana] Exception: {e}")
            content = f"Error invoking Tetyana: {e}"
        
        # If paused, return to atlas with pause_info
        if pause_info:
            updated_messages = list(context) + [AIMessage(content=f"[ПАУЗОВАНО] {pause_info['message']}")]
            return {
                "current_agent": "atlas",
                "messages": updated_messages,
                "pause_info": pause_info
            }
        
        # Preserve existing messages and add new one
        updated_messages = list(context) + [AIMessage(content=content)]
        return {
            "current_agent": "grisha", 
            "messages": updated_messages,
            "execution_mode": execution_mode,
            "gui_mode": gui_mode,
            "gui_fallback_attempted": gui_fallback_attempted,
        }

    def _grisha_node(self, state: TrinityState):
        if self.verbose: print("👁️ [Grisha] Verifying...")
        context = state.get("messages", [])
        if not context:
            return {"current_agent": "end", "messages": [AIMessage(content="[Grisha] No context available.")]}
        last_msg = context[-1].content

        gui_mode = str(state.get("gui_mode") or "auto").strip().lower()
        execution_mode = str(state.get("execution_mode") or "native").strip().lower()
        
        # Check for code changes in critical directories and run tests
        test_results = ""
        critical_dirs = ["core/", "system_ai/", "tui/", "providers/"]
        try:
            repo_changes = self._get_repo_changes()
            changed_files = []
            if isinstance(repo_changes, dict) and repo_changes.get("ok") is True:
                changed_files = list(repo_changes.get("changed_files") or [])
            has_critical_changes = any(
                any(f.startswith(d) for d in critical_dirs) 
                for f in changed_files
            )
            
            if has_critical_changes and self.verbose:
                print("👁️ [Grisha] Detected changes in critical directories. Running pytest...")
            
            if has_critical_changes:
                # Run pytest
                test_cmd = "pytest -q --tb=short 2>&1"
                test_proc = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, cwd=self._get_git_root() or ".")
                test_output = test_proc.stdout + test_proc.stderr
                test_results = f"\n\n[TEST_VERIFICATION] pytest output:\n{test_output}"
                
                if self.verbose:
                    print(f"👁️ [Grisha] Test results:\n{test_output[:200]}...")
        except Exception as e:
            if self.verbose:
                print(f"👁️ [Grisha] Test execution error: {e}")
        
        # Inject available tools (Vision priority)
        tools_list = self.registry.list_tools()
        prompt = get_grisha_prompt(last_msg, tools_desc=tools_list)
        
        content = ""  # Initialize content variable
        try:
            # For tool-bound calls, don't stream (JSON protocol needs complete response)
            response = self.llm.invoke(prompt.format_messages())
            content = response.content
            tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            
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
        # ------------------------------------------------------------------
        # FEEDBACK LOOP LOGIC (Phase 3)
        # ------------------------------------------------------------------
        
        lower_content = content.lower()

        has_question = ("?" in content) or lower_content.strip().startswith("чи ") or (" чи " in lower_content)
        uncertainty_keywords = [
            "уточн",
            "потрібно уточн",
            "маю уточн",
            "перед початком",
            "якщо ",
            "не впевнен",
            "потрібна допомога",
            "питання",
        ]
        has_uncertainty = any(k in lower_content for k in uncertainty_keywords)

        explicit_complete_markers = [
            "[verified]",
            "[confirmed]",
            "verification passed",
            "qa passed",
            "verdict: pass",
            "верифікація пройдена",
            "перевірку пройдено",
        ]
        has_explicit_complete = any(m in lower_content for m in explicit_complete_markers)
        
        # Check for test failures first (highest priority)
        has_test_failure = "[test_verification]" in lower_content and ("failed" in lower_content or "error" in lower_content)
        
        # Check for positive verification keywords
        positive_keywords = ["успішно", "verified", "confirmed", "success", "завершено", "готово", "працює", "відкрито"]
        has_positive = any(kw in lower_content for kw in positive_keywords)
        
        # Check for negative keywords
        negative_keywords = ["failed", "error", "rejected", "помилка", "не вдалося"]
        has_negative = any(kw in lower_content for kw in negative_keywords)
        
        if has_test_failure:
            # Case A: TESTS FAILED - block task and return to Atlas for replan
            if self.verbose:
                print("👁️ [Grisha] Tests failed - blocking task and requesting replan")
            next_agent = "atlas"
            
        elif "tools results" in lower_content and tool_calls:
            # Case B: Grisha used a tool (e.g. took a screenshot). 
            # Loop back to Atlas to analyze the screenshot.
            next_agent = "atlas"
            
        elif has_negative:
            # Case C: VERIFICATION FAILED.
            # Trigger "Dynamic Granularity" (Replan).
            next_agent = "atlas"
            
        elif (has_explicit_complete or (has_positive and (not has_uncertainty) and (not has_question))) and not tool_calls:
            # Case D: VERIFICATION PASSED and no new tools called.
            # TASK IS COMPLETE!
            next_agent = "end"
            
        else:
            # Default fallback - continue to atlas for more instructions
            next_agent = "atlas"

        # Preserve existing messages and add new one
        updated_messages = list(context) + [AIMessage(content=content)]
        return {
            "current_agent": next_agent, 
            "messages": updated_messages
        }

    def _router(self, state: TrinityState):
        return state["current_agent"]

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
        commit_hash: Optional[str] = None,
    ) -> str:
        lines: List[str] = []
        lines.append("[Atlas] Final report")
        lines.append("")
        lines.append(f"Task: {str(task or '').strip()}")
        lines.append(f"Outcome: {outcome}")
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
        }

        last_node_name: str = ""
        last_state_update: Dict[str, Any] = {}
        last_agent_message: str = ""
        last_agent_label: str = ""

        for event in self.workflow.stream(initial_state, config={"recursion_limit": recursion_limit}):
            try:
                # Keep track of the last emitted node/message for the final report.
                for node_name, state_update in (event or {}).items():
                    last_node_name = str(node_name or "")
                    last_state_update = state_update if isinstance(state_update, dict) else {}
                    msgs = last_state_update.get("messages", []) if isinstance(last_state_update, dict) else []
                    if msgs:
                        m = msgs[-1]
                        last_agent_message = str(getattr(m, "content", "") or "")
                    last_agent_label = str(node_name or "")
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
            commit_hash=commit_hash,
        )

        # Save report to .last_response.txt for generate_structure.py to pick up
        # Preserve previous response (my analysis) and append new Trinity report
        try:
            existing_content = ""
            try:
                with open(".last_response.txt", "r", encoding="utf-8") as f:
                    existing_content = f.read().strip()
            except FileNotFoundError:
                pass
            
            # Build new content: keep my analysis, add new Trinity report
            new_content = ""
            if existing_content:
                # If file exists, preserve it and add separator + new report
                new_content = existing_content + "\n\n---\n\n## Trinity Report\n\n" + report
            else:
                # First time: just the report
                new_content = report
            
            with open(".last_response.txt", "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            pass

        final_messages = [HumanMessage(content=input_text), AIMessage(content=report)]
        yield {"atlas": {"messages": final_messages, "current_agent": "end", "task_status": outcome}}
