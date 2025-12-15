from typing import Annotated, TypedDict, Literal, List, Dict, Any, Optional, Callable
import json
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
        else:
            next_agent = "tetyana"
            
        # Update state with the plan and counters
        return {
            "current_agent": next_agent, 
            "messages": [AIMessage(content=content)],
            "plan": plan,
            "step_count": step_count,
            "replan_count": replan_count,
            "summary": summary
        }

    def _tetyana_node(self, state: TrinityState):
        if self.verbose: print("💻 [Tetyana] Developing...")
        context = state.get("messages", [])
        last_msg = context[-1].content
        
        
        # Inject available tools into Tetyana's prompt
        tools_list = self.registry.list_tools()
        prompt = get_tetyana_prompt(last_msg, tools_desc=tools_list)
        
        # Bind tools to LLM for structured tool_calls output
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
            if tool_calls:
                for tool in tool_calls:
                    name = tool.get("name")
                    args = tool.get("args") or {}
                    
                    # Permission check for dangerous tools
                    if name == "run_shell" and not self.permissions.allow_shell:
                        pause_info = {
                            "permission": "shell",
                            "message": "Потрібен дозвіл на виконання shell команд. Введіть /allow shell",
                            "blocked_tool": name,
                            "blocked_args": args
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                        
                    if name == "run_applescript" and not self.permissions.allow_applescript:
                        pause_info = {
                            "permission": "applescript",
                            "message": "Потрібен дозвіл на виконання AppleScript. Введіть /allow applescript",
                            "blocked_tool": name,
                            "blocked_args": args
                        }
                        results.append(f"[BLOCKED] {name}: permission required")
                        continue
                    
                    # Execute via MCP Registry
                    res_str = self.registry.execute(name, args)
                    results.append(f"Result for {name}: {res_str}")
                    
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
                
        except Exception as e:
            content = f"Error invoking Tetyana: {e}"
        
        # If paused, return to atlas with pause_info
        if pause_info:
            return {
                "current_agent": "atlas",
                "messages": [AIMessage(content=f"[ПАУЗОВАНО] {pause_info['message']}")],
                "pause_info": pause_info
            }
        
        return {
            "current_agent": "grisha", 
            "messages": [AIMessage(content=content)]
        }

    def _grisha_node(self, state: TrinityState):
        if self.verbose: print("👁️ [Grisha] Verifying...")
        context = state.get("messages", [])
        last_msg = context[-1].content
        
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

        except Exception as e:
            content = f"Error invoking Grisha: {e}"

        # If Grisha says "CONFIRMED" or "VERIFIED", we end. Else Atlas replans.
        # ------------------------------------------------------------------
        # FEEDBACK LOOP LOGIC (Phase 3)
        # ------------------------------------------------------------------
        
        lower_content = content.lower()
        
        # Check for positive verification keywords first
        positive_keywords = ["успішно", "verified", "confirmed", "success", "завершено", "готово", "працює", "відкрито"]
        has_positive = any(kw in lower_content for kw in positive_keywords)
        
        # Check for negative keywords
        negative_keywords = ["failed", "error", "rejected", "помилка", "не вдалося"]
        has_negative = any(kw in lower_content for kw in negative_keywords)
        
        if "tools results" in lower_content and tool_calls:
            # Case A: Grisha used a tool (e.g. took a screenshot). 
            # Loop back to Atlas to analyze the screenshot.
            next_agent = "atlas"
            
        elif has_negative:
            # Case B: VERIFICATION FAILED.
            # Trigger "Dynamic Granularity" (Replan).
            next_agent = "atlas"
            
        elif has_positive and not tool_calls:
            # Case C: VERIFICATION PASSED and no new tools called.
            # TASK IS COMPLETE!
            next_agent = "end"
            
        else:
            # Default fallback - continue to atlas for more instructions
            next_agent = "atlas"

        return {
            "current_agent": next_agent, 
            "messages": [AIMessage(content=content)]
        }

    def _router(self, state: TrinityState):
        return state["current_agent"]

    def run(self, input_text: str):
        initial_state = {
            "messages": [HumanMessage(content=input_text)],
            "current_agent": "atlas",
            "task_status": "started",
            "final_response": None,
            "step_count": 0,
            "replan_count": 0,
            "summary": None,
            "pause_info": None
        }
        
        for event in self.workflow.stream(initial_state):
            yield event



