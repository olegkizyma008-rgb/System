from typing import Any, Dict, Optional


class GoalGraph:
    def __init__(
        self,
        *,
        plan_step: Any,
        act_step: Any,
        observe_step: Any,
        verify_step: Any,
    ) -> None:
        self._plan_step = plan_step
        self._act_step = act_step
        self._observe_step = observe_step
        self._verify_step = verify_step

    def run(self, goal: str, *, max_steps: int) -> Any:
        step = 0
        last_plan = None
        last_results = None
        last_observation = ""
        done = False

        while step < int(max_steps) and not done:
            next_step = step + 1
            try:
                last_plan = self._plan_step(goal, step=next_step)
            except TypeError:
                last_plan = self._plan_step(goal)

            try:
                last_results = self._act_step(getattr(last_plan, "actions", []) if last_plan else [], step=next_step)
            except TypeError:
                last_results = self._act_step(getattr(last_plan, "actions", []) if last_plan else [])

            try:
                last_observation = self._observe_step(last_results, step=next_step)
            except TypeError:
                last_observation = self._observe_step(last_results)

            try:
                verify = self._verify_step(goal, last_plan, last_results, last_observation, step=next_step)
            except TypeError:
                verify = self._verify_step(goal, last_plan, last_results, last_observation)

            step = next_step
            done = bool(getattr(last_plan, "done", False))
            if isinstance(verify, dict) and "done" in verify:
                done = bool(verify.get("done"))

            yield {
                "step": step,
                "plan": last_plan,
                "actions_results": last_results,
                "observation": last_observation,
                "verify": verify,
                "done": done,
            }


class LangGoalGraph:
    def __init__(
        self,
        *,
        plan_step: Any,
        act_step: Any,
        observe_step: Any,
        verify_step: Any,
    ) -> None:
        self._plan_step = plan_step
        self._act_step = act_step
        self._observe_step = observe_step
        self._verify_step = verify_step
        self._graph = self._build_langgraph()

    def _build_langgraph(self) -> Any:
        from langgraph.graph import END, StateGraph  # type: ignore

        def _plan(state: Dict[str, Any]) -> Dict[str, Any]:
            step = int(state.get("step") or 0) + 1
            goal = str(state.get("goal") or "")
            try:
                plan = self._plan_step(goal, step=step)
            except TypeError:
                plan = self._plan_step(goal)
            return {"step": step, "plan": plan}

        def _act(state: Dict[str, Any]) -> Dict[str, Any]:
            step = int(state.get("step") or 0)
            plan = state.get("plan")
            actions = getattr(plan, "actions", []) if plan else []
            try:
                results = self._act_step(actions, step=step)
            except TypeError:
                results = self._act_step(actions)
            return {"actions_results": results}

        def _observe(state: Dict[str, Any]) -> Dict[str, Any]:
            step = int(state.get("step") or 0)
            results = state.get("actions_results")
            try:
                obs = self._observe_step(results, step=step)
            except TypeError:
                obs = self._observe_step(results)
            return {"observation": obs}

        def _verify(state: Dict[str, Any]) -> Dict[str, Any]:
            step = int(state.get("step") or 0)
            goal = str(state.get("goal") or "")
            plan = state.get("plan")
            results = state.get("actions_results")
            obs = str(state.get("observation") or "")
            try:
                verify = self._verify_step(goal, plan, results, obs, step=step)
            except TypeError:
                verify = self._verify_step(goal, plan, results, obs)

            done = bool(getattr(plan, "done", False))
            if isinstance(verify, dict) and "done" in verify:
                done = bool(verify.get("done"))
            return {"verify": verify, "done": done}

        def _should_continue(state: Dict[str, Any]) -> str:
            done = bool(state.get("done"))
            step = int(state.get("step") or 0)
            max_steps = int(state.get("max_steps") or 0)
            if done or (max_steps and step >= max_steps):
                return END
            return "plan"

        sg: Any = StateGraph(Dict[str, Any])
        sg.add_node("plan", _plan)
        sg.add_node("act", _act)
        sg.add_node("observe", _observe)
        sg.add_node("verify", _verify)

        sg.set_entry_point("plan")
        sg.add_edge("plan", "act")
        sg.add_edge("act", "observe")
        sg.add_edge("observe", "verify")
        sg.add_conditional_edges("verify", _should_continue)
        return sg.compile()

    def run(self, goal: str, *, max_steps: int) -> Any:
        state: Dict[str, Any] = {"goal": goal, "step": 0, "max_steps": int(max_steps)}

        for update in self._graph.stream(state):
            if isinstance(update, dict):
                state.update(update)

            step = int(state.get("step") or 0)
            yield {
                "step": step,
                "plan": state.get("plan"),
                "actions_results": state.get("actions_results"),
                "observation": state.get("observation") or "",
                "verify": state.get("verify") or {},
                "done": bool(state.get("done")),
            }

            if bool(state.get("done")):
                break


def is_langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401

        return True
    except Exception:
        return False


def build_placeholder_graph() -> Dict[str, Any]:
    """Placeholder to keep folder structure stable.

    Later we will replace with a real LangGraph state machine.
    """
    return {"ok": True, "type": "placeholder", "langgraph": is_langgraph_available()}


def build_goal_graph(*, plan_step: Any, act_step: Any, observe_step: Any, verify_step: Any) -> GoalGraph:
    if is_langgraph_available():
        try:
            return LangGoalGraph(plan_step=plan_step, act_step=act_step, observe_step=observe_step, verify_step=verify_step)  # type: ignore[return-value]
        except Exception:
            return GoalGraph(plan_step=plan_step, act_step=act_step, observe_step=observe_step, verify_step=verify_step)
    return GoalGraph(plan_step=plan_step, act_step=act_step, observe_step=observe_step, verify_step=verify_step)
