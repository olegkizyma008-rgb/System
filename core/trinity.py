from typing import Annotated, TypedDict, Literal, List, Dict, Any, Optional
import json
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from core.agents.atlas import get_atlas_prompt
from core.agents.tetyana import get_tetyana_prompt
from core.agents.grisha import get_grisha_prompt
from providers.copilot import CopilotLLM

from core.mcp import MCPToolRegistry
from core.verification import AdaptiveVerifier

# Define the state of the Trinity system
class TrinityState(TypedDict):
    messages: List[BaseMessage]
    current_agent: str
    task_status: str
    final_response: Optional[str]
    plan: Optional[List[Dict[str, Any]]] # List of steps including verification checkpoints

class TrinityRuntime:
    def __init__(self, verbose: bool = True):
        self.llm = CopilotLLM()
        self.verbose = verbose
        self.registry = MCPToolRegistry()
        self.verifier = AdaptiveVerifier(self.llm)
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
        
        # 1. Check if we have a plan. If not, generate one.
        plan = state.get("plan")
        if not plan:
            # TODO: Use LLM to generate structured plan. 
            # For now, we wrap the user request as a single execution step.
            raw_plan = [{
                "id": 1, 
                "type": "execute", 
                "description": last_msg,
                "agent": "tetyana"
            }]
            
            # 2. Optimize Plan (Adaptive Verification)
            # This inserts Grisha 'verify' steps at critical points
            plan = self.verifier.optimize_plan(raw_plan)
            
            if self.verbose:
                print(f"🌐 [Atlas] Plan Optimized: {len(plan)} steps.")
                for step in plan:
                    print(f"   - {step['type'].upper()}: {step['description']}")

        # 3. Dispatch Logic (Simple First-Step approach for now)
        # We look at the first incomplete step. 
        # Since we don't have a 'completed' flag tracker in this simple dict yet,
        # we assume for this iteration we just trigger the next agent based on the *first* step type.
        
        current_step = plan[0] if plan else None
        
        if not current_step:
            return {"current_agent": "end", "messages": [AIMessage(content="No plan generated.")]}

        # Invoke Atlas Persona to announce strategy
        # (We keep this specifically to maintain the chat persona)
        prompt = get_atlas_prompt(f"The plan is: {current_step['description']}. Announce it.")
        try:
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
            
        # Update state with the plan
        return {
            "current_agent": next_agent, 
            "messages": [AIMessage(content=content)],
            "plan": plan
        }

    def _tetyana_node(self, state: TrinityState):
        if self.verbose: print("💻 [Tetyana] Developing...")
        context = state.get("messages", [])
        last_msg = context[-1].content
        
        
        # Inject available tools into Tetyana's prompt
        tools_list = self.registry.list_tools()
        prompt = get_tetyana_prompt(last_msg, tools_desc=tools_list)
        
        # Bind tools to LLM for structured tool_calls output
        # We pass tool descriptions as simple dicts for the bind_tools method
        tool_defs = []
        for name, func in self.registry._tools.items():
            desc = self.registry._descriptions.get(name, "")
            tool_defs.append({"name": name, "description": desc})
        
        bound_llm = self.llm.bind_tools(tool_defs)
        
        try:
            response = bound_llm.invoke(prompt.format_messages())
            # For now, we assume direct text or basic JSON. 
            # In a full impl, we'd use tool usage parsing as seen in CopilotLLM.
            content = response.content
            tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
            
            # If no structured tool calls, try to parse JSON manually or via simple heuristics
            # (Assuming CopilotLLM returns tool_calls formatted)
            
            results = []
            if tool_calls:
                 for tool in tool_calls:
                     name = tool.get("name")
                     args = tool.get("args") or {}
                     
                     # Execute via MCP Registry
                     res = self.registry.execute(name, args)
                     results.append(f"Result for {name}: {res}")
            
            # If we executed tools, append results to content
            if results:
                content += "\n\nTool Results:\n" + "\n".join(results)
                
        except Exception as e:
            content = f"Error invoking Tetyana: {e}"
        
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
        
        try:
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
            "final_response": None
        }
        
        for event in self.workflow.stream(initial_state):
            yield event



