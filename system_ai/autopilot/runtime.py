import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from system_ai.graph.graph_chain import build_goal_graph
from system_ai.memory.summary_memory import SummaryMemory
from system_ai.rag.rag_pipeline import RagPipeline
from system_ai.tools import executor
from system_ai.tools.screenshot import take_screenshot
from system_ai.tools.vision import summarize_image_for_prompt

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except Exception:  # pragma: no cover
    HumanMessage = SystemMessage = None

try:
    from providers.copilot import CopilotLLM
except Exception:  # pragma: no cover
    CopilotLLM = None

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

def _load_env() -> None:
    if load_dotenv is None:
        return
    load_dotenv(os.path.join(REPO_ROOT, ".env"))

SYSTEM_PROMPT = """Ти — системний автопілот, що керує локальним macOS-комп'ютером користувача.

Ти працюєш ітеративно в циклі: PLAN -> ACT -> OBSERVE -> VERIFY -> NEXT.
Твоя мета — досягти КІНЦЕВОЇ ЦІЛІ користувача. Не проси користувача писати покрокові інструкції.

Доступні інструменти (першокласні канали виконання):
- open_app: args {"name": string} — відкрити macOS додаток
- open_url: args {"url": string} — відкрити URL у браузері
- run_shell: args {"command": string} — виконати shell команду
- run_applescript: args {"script": string} — виконати AppleScript (UI automation)
- run_shortcut: args {"name": string} — запустити macOS Shortcut (найнадійніше для UI)
- run_automator: args {"workflow_path": string} — запустити Automator workflow
- take_screenshot: args {"app_name": string|null} — зняти скрін (для VISION observation)

Пріоритет виконання (від найнадійнішого):
1. run_shortcut — для критичних дій (пошук, клік, fullscreen, медіа-керування)
2. run_automator — для legacy workflows
3. run_applescript — для гнучкої UI automation
4. run_shell — для системних команд
5. open_app / open_url — для базових дій

Правила:
- На кожному кроці ВІДПОВІДАЙ СТРОГО валідним JSON (без markdown/пояснень).
- Формат відповіді:
{
  "thought": "коротко що робиш",
  "summary": "оновлений підсумок стану (memory)",
  "preflight": [ {"type": "...", "details": "..."} ],
  "actions": [ {"tool": "...", "args": { ... }} ],
  "done": true|false,
  "result_message": "що сказати користувачу"
}

preflight — це список кроків підготовки (перевірка прав/контексту/готовності інструментів). Якщо плануєш UI automation (run_applescript/run_shortcut), включай preflight з вимогами Accessibility/Automation.

Після виконання actions, ти отримаєш tool_results і observation (VISION). Використай їх для корекції плану.
Якщо verify каже "off_track", будь готовий до переплануння (система автоматично перепланує).
"""

VERIFY_PROMPT = """Ти — модуль верифікації автопілоту.

Перевір, чи система рухається до КІНЦЕВОЇ ЦІЛІ користувача на основі:
- goal
- останнього плану (thought/result_message/done)
- tool_results
- observation (VISION)

Відповідай СТРОГО валідним JSON (без markdown/пояснень):
{
  "on_track": true|false,
  "done": true|false,
  "issues": "коротко що не так (якщо є)",
  "next_hint": "коротка підказка для наступного кроку"
}
"""

@dataclass
class ToolAction:
    tool: str
    args: Dict[str, Any]

@dataclass
class StepPlan:
    thought: str
    summary: str
    preflight: List[Dict[str, Any]]
    actions: List[ToolAction]
    done: bool
    result_message: str
    raw_response: str

@dataclass
class AutopilotPermissions:
    allow_autopilot: bool
    allow_shell: bool
    allow_applescript: bool

class AutopilotRuntime:
    def __init__(
        self,
        *,
        permissions: AutopilotPermissions,
        persist_dir: str = "~/.system_cli/chroma",
    ) -> None:
        if CopilotLLM is None or SystemMessage is None or HumanMessage is None:
            raise RuntimeError("LLM dependencies not available")

        _load_env()

        self.llm = CopilotLLM()
        self.permissions = permissions
        self.memory = SummaryMemory()
        self.rag = RagPipeline(persist_dir=persist_dir)

        self._run_state: Dict[str, Any] = {}
        self._replan_count = 0
        self._max_replans = 5

    def _plan_step(self, goal: str, *, step: int) -> StepPlan:
        retrieved = self.rag.retrieve(goal, k=5)
        last_results: List[Dict[str, Any]] = list(self._run_state.get("last_results") or [])
        history: List[str] = list(self._run_state.get("history") or [])
        last_observation = str(self._run_state.get("observation") or "")
        verify_hint = self._run_state.get("verify_hint")
        
        successful_examples = []
        if step == 1:
            try:
                successful_examples = self.rag.retrieve(f"успішний сценарій {goal}", k=3)
            except Exception:
                successful_examples = []

        user_payload: Dict[str, Any] = {
            "goal": goal,
            "step": int(step),
            "summary_memory": self.memory.summary,
            "history_tail": history[-5:],
            "rag_context": retrieved,
            "successful_examples": successful_examples,
            "last_results": last_results[-10:],
            "observation": last_observation,
            "permissions": {
                "allow_autopilot": bool(self.permissions.allow_autopilot),
                "allow_shell": bool(self.permissions.allow_shell),
                "allow_applescript": bool(self.permissions.allow_applescript),
            },
        }
        if verify_hint:
            user_payload["verify_hint"] = str(verify_hint)

        messages: List[Any] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
        ai_msg = self.llm.invoke(messages)
        plan = self._parse_plan(ai_msg)

        if plan.summary:
            self.memory.update(plan.summary)

        self._run_state["plan"] = plan
        history.append(f"Step {step}: {plan.thought} | {plan.result_message}")
        self._run_state["history"] = history
        return plan

    def _act_step(self, actions: List[ToolAction], *, step: int) -> List[Dict[str, Any]]:
        action_results = self._execute(actions)

        if not any(r.get("tool") == "take_screenshot" for r in action_results):
            try:
                action_results.append(take_screenshot(None))
            except Exception:
                pass

        self._run_state["last_results"] = list(action_results)
        return action_results

    def _observe_step(self, action_results: List[Dict[str, Any]], *, step: int) -> str:
        obs_shot = next(
            (
                r
                for r in reversed(action_results or [])
                if r.get("tool") == "take_screenshot" and r.get("status") == "success"
            ),
            None,
        )
        obs_text = ""
        if obs_shot:
            p = str(obs_shot.get("path") or "")
            if p:
                obs_text = summarize_image_for_prompt(p)
        self._run_state["observation"] = obs_text
        return obs_text

    def _verify_step(
        self,
        goal: str,
        plan: StepPlan,
        action_results: List[Dict[str, Any]],
        observation: str,
        *,
        step: int,
    ) -> Dict[str, Any]:
        pause_info = self._run_state.get("pause_info")
        if pause_info:
            return {
                "on_track": False,
                "done": True,
                "issues": str(pause_info.get("message") or "Permission required"),
                "next_hint": "",
                "replan": False,
                "paused": True,
                "pause_info": dict(pause_info),
            }

        verify_interval = int(self._run_state.get("verify_interval") or 3)
        should_verify = (step % verify_interval == 0) or bool(getattr(plan, "done", False))
        if not should_verify:
            return {"on_track": True, "done": bool(getattr(plan, "done", False)), "issues": "", "next_hint": "", "replan": False}

        payload = {
            "goal": goal,
            "step": int(step),
            "plan": {
                "thought": getattr(plan, "thought", ""),
                "result_message": getattr(plan, "result_message", ""),
                "done": bool(getattr(plan, "done", False)),
            },
            "tool_results": action_results[-10:],
            "observation": observation,
        }
        messages: List[Any] = [
            SystemMessage(content=VERIFY_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        ai_msg = self.llm.invoke(messages)
        raw = str(getattr(ai_msg, "content", "") or "")
        match = re.search(r"\{[\s\S]*\}", raw)
        json_str = match.group(0) if match else raw
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ValueError("verify not a dict")
        except Exception:
            parsed = {"on_track": True, "done": bool(getattr(plan, "done", False)), "issues": raw[:500], "next_hint": ""}

        on_track = bool(parsed.get("on_track", True))
        next_hint = str(parsed.get("next_hint") or "").strip()
        
        if not on_track and self._replan_count < self._max_replans:
            self._replan_count += 1
            self._run_state["verify_hint"] = f"REPLAN #{self._replan_count}: {next_hint}"
            self._run_state["should_replan"] = True
            adaptive_interval = min(int(verify_interval * 1.5), 10)
            self._run_state["verify_interval"] = adaptive_interval
            return {
                "on_track": False,
                "done": False,
                "issues": str(parsed.get("issues") or ""),
                "next_hint": self._run_state["verify_hint"],
                "replan": True,
            }
        
        self._run_state["verify_hint"] = next_hint
        return {
            "on_track": on_track,
            "done": bool(parsed.get("done", bool(getattr(plan, "done", False)))),
            "issues": str(parsed.get("issues") or ""),
            "next_hint": next_hint,
            "replan": False,
        }

    def _parse_plan(self, ai_message: Any) -> StepPlan:
        text = str(getattr(ai_message, "content", "") or "")
        match = re.search(r"\{[\s\S]*\}", text)
        json_str = match.group(0) if match else text
        try:
            data = json.loads(json_str)
        except Exception:
            return StepPlan(
                thought="Модель повернула не-JSON відповідь",
                summary=self.memory.summary,
                preflight=[],
                actions=[],
                done=True,
                result_message=text,
                raw_response=text,
            )

        actions_raw = data.get("actions") or []
        actions: List[ToolAction] = []
        if isinstance(actions_raw, list):
            for item in actions_raw:
                if not isinstance(item, dict):
                    continue
                tool = str(item.get("tool", ""))
                args = item.get("args") or {}
                if tool:
                    actions.append(ToolAction(tool=tool, args=dict(args) if isinstance(args, dict) else {}))

        preflight_raw = data.get("preflight") or []
        preflight: List[Dict[str, Any]] = []
        if isinstance(preflight_raw, list):
            for item in preflight_raw:
                if isinstance(item, dict):
                    preflight.append(dict(item))

        return StepPlan(
            thought=str(data.get("thought", "")),
            summary=str(data.get("summary", "")),
            preflight=preflight,
            actions=actions,
            done=bool(data.get("done", False)),
            result_message=str(data.get("result_message", "")) or text,
            raw_response=text,
        )

    def _execute(self, actions: List[ToolAction]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for a in actions:
            if a.tool == "open_app":
                results.append(executor.open_app(str(a.args.get("name", ""))))
            elif a.tool == "open_url":
                results.append(executor.open_url(str(a.args.get("url", ""))))
            elif a.tool == "run_shell":
                results.append(
                    executor.run_shell(
                        str(a.args.get("command", "")),
                        allow=self.permissions.allow_shell and self.permissions.allow_autopilot,
                        cwd=REPO_ROOT,
                    )
                )
            elif a.tool == "run_applescript":
                results.append(
                    executor.run_applescript(
                        str(a.args.get("script", "")),
                        allow=self.permissions.allow_applescript and self.permissions.allow_autopilot,
                    )
                )
                last = results[-1]
                if isinstance(last, dict) and last.get("error_type") == "permission_required":
                    perm = str(last.get("permission") or "")
                    try:
                        results.append(executor.open_system_settings_privacy(perm))
                    except Exception:
                        pass
                    self._run_state["pause_info"] = {
                        "permission": perm,
                        "settings_url": str(last.get("settings_url") or ""),
                        "message": str(last.get("error") or "Permission required"),
                    }
                    break
            elif a.tool == "run_shortcut":
                results.append(
                    executor.run_shortcut(
                        str(a.args.get("name", "")),
                        allow=self.permissions.allow_shell and self.permissions.allow_autopilot,
                    )
                )
            elif a.tool == "run_automator":
                results.append(
                    executor.run_automator(
                        str(a.args.get("workflow_path", "")),
                        allow=self.permissions.allow_shell and self.permissions.allow_autopilot,
                    )
                )
            elif a.tool == "take_screenshot":
                app_name = a.args.get("app_name")
                results.append(take_screenshot(str(app_name)) if app_name else take_screenshot(None))
            else:
                results.append({"tool": a.tool, "status": "error", "error": "Unknown tool"})
        return results

    def run_goal(self, goal: str, *, max_steps: int = 30) -> Generator[Dict[str, Any], None, None]:
        if not self.permissions.allow_autopilot:
            raise RuntimeError("Autopilot not confirmed")

        self._run_state = {
            "history": [],
            "last_results": [],
            "observation": "",
            "verify_hint": "",
            "verify_interval": 3,
            "pause_info": None,
        }

        graph = build_goal_graph(
            plan_step=self._plan_step,
            act_step=self._act_step,
            observe_step=self._observe_step,
            verify_step=self._verify_step,
        )

        for event in graph.run(goal, max_steps=int(max_steps)):
            step = int(event.get("step") or 0)
            plan = event.get("plan")
            action_results = event.get("actions_results") or []
            observation = str(event.get("observation") or "")
            verify = event.get("verify") or {}

            done_flag = bool(event.get("done"))

            try:
                self.rag.ingest_text(
                    json.dumps(
                        {
                            "step": step,
                            "goal": goal,
                            "thought": getattr(plan, "thought", "") if plan else "",
                            "result_message": getattr(plan, "result_message", "") if plan else "",
                            "preflight": getattr(plan, "preflight", []) if plan else [],
                            "actions": [a.__dict__ for a in getattr(plan, "actions", [])] if plan else [],
                            "tool_results": action_results,
                            "observation": observation,
                            "verify": verify,
                        },
                        ensure_ascii=False,
                    ),
                    metadata={"type": "autopilot_step", "step": step},
                )
            except Exception:
                pass

            yield {
                "step": step,
                "plan": plan,
                "actions_results": action_results,
                "observation": observation,
                "verify": verify,
                "done": done_flag,
            }

            if done_flag:
                break
