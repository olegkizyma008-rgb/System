---
description: The Core Architecture and Workflow of Project Atlas (Trinity Runtime).
---

# Project Atlas: Runtime & Workflow (Actual)

This document describes the **current, real** runtime of the project.

Important: there are *two* execution engines in the repo:

1. **Chat Agent Engine (default in TUI/CLI)**
   - Implemented in `tui/cli.py`.
   - Streams assistant output into the TUI log and can execute tool calls.

2. **Trinity Graph Runtime (LangGraph)**
   - Implemented in `core/trinity.py`.
   - Provides a multi-agent loop (Atlas/Tetyana/Grisha) with plan->act->verify behaviour.
   - Intended for complex tasks / autopilot-like runs.

---

## 1. Entry Points

### 1.1 Shell entry

- `./cli.sh`
  - Activates `.venv` if present.
  - Loads `.env` (if present).
  - Runs `cli.py`.

### 1.2 Python entry

- `cli.py` is a compatibility wrapper and delegates to `tui.cli.main()`.
- Main CLI/TUI implementation lives in `tui/cli.py`.

---

## 2. TUI Layer (UI, state, logging)

### 2.1 UI state

- State lives in `system_cli/state.py` (`AppState`).
- Key flags used by runtime:
  - `ui_streaming`
  - `ui_unsafe_mode`
  - `agent_processing`
  - `agent_paused` + pause metadata

### 2.2 Log rendering & streaming rules

- Logs are stored in `state.logs`.
- The UI supports streaming by reserving a line and updating it.
- Invariants:
  - **Never** update logs by “replace last line” in streaming mode.
  - Always reserve a specific line and update it by index.
  - All mutations of `state.logs` must be guarded by a lock.

---

## 3. Chat Agent Engine (default)

### 3.1 Where it runs

- TUI input handler (`_handle_input`) routes plain text into agent chat.
- CLI subcommand `agent-chat --message "..."` also uses the same agent entry.

### 3.2 Behaviour

- `_agent_send()` is the unified entry.
  - **Greeting fast-path:** for `Привіт/Hello/Hi/...` returns a stable short response.
  - Otherwise routes to `_agent_send_with_stream()` when `ui_streaming` is ON.

- `_agent_send_with_stream()`:
  - Streams assistant output into a reserved log line.
  - If the LLM returns tool calls, it executes them sequentially.
  - After tool execution, it requests a final response and streams it into a new reserved line.

---

## 4. Trinity Graph Runtime (LangGraph)

### 4.1 Agents

Trinity runtime (`core/trinity.py`) is a LangGraph state machine with nodes:

- **Atlas** (`_atlas_node`)
  - Decomposes tasks into steps.
  - Maintains a rolling summary (optional).
  - Queries memory for similar “strategies”.

- **Tetyana** (`_tetyana_node`)
  - Executes steps via tool registry (`core/mcp.py`).
  - Uses permissions (`TrinityPermissions`) to block dangerous tools.

- **Grisha** (`_grisha_node`)
  - Verifies results and decides whether to end or return control to Atlas.
  - Can use visual tools like `capture_screen`.

### 4.2 Streaming integration into TUI

- `tui/cli.py:_run_graph_agent_task()` wires `TrinityRuntime(on_stream=...)`.
- Each agent can stream deltas; the TUI reserves **separate** lines per agent name and updates them by index.

### 4.3 Current state

- Trinity is present and runnable, but the **default user experience** is the Chat Agent Engine.
- The long-term direction is to make runtime selection explicit and consistent (see Roadmap).

---

## 5. Safety & Permissions

There are two permission layers:

### 5.1 TUI “Unsafe mode”

- `ui_unsafe_mode=OFF`:
  - Dangerous tools require explicit confirmation markers (e.g. CONFIRM_*).
  - Permission-related errors can pause the agent.

- `ui_unsafe_mode=ON`:
  - Confirmations are bypassed (dangerous).

### 5.2 TrinityPermissions (Graph runtime)

- Blocks `run_shell` and `run_applescript` unless explicitly allowed.
- Supports a pause mechanism via `pause_info`.

---

## 6. Memory & storage

- Trinity uses a memory subsystem (Chroma/strategies) under `.atlas_memory/`.
- Treat `.atlas_memory/` as **runtime state** (usually not committed unless you intentionally want to version it).

---

## 7. Roadmap ("заходячи наперед")

### 7.1 Unify runtimes

- Define a single “routing policy”:
  - greeting -> fast-path
  - simple chat -> chat engine
  - multi-step/system actions -> Trinity graph

### 7.2 Make Trinity user-facing

- Add an explicit `final_response` field in Trinity state and ensure it is rendered to the user.
- Ensure the UI shows a clear final assistant message, not only internal plan/status lines.

### 7.3 Add regression protection

- Add smoke tests for:
  - streaming output stability (no log erasures)
  - greeting response
  - permission pause/resume

---

## 8. Test Plan (manual smoke)

- `./cli.sh agent-chat --message "Привіт"`
  - Expected: human greeting response.

- TUI:
  - Send a long message and verify that streaming does not erase previous logs.
  - Toggle streaming (`ui_streaming`) and verify output is still correct.

- Permissions:
  - With Unsafe mode OFF, attempt a request that would call `run_shell` and verify it is blocked/paused with a clear message.

---

## 9. File Structure (authoritative)

- `cli.sh` - shell entry wrapper
- `cli.py` - Python compatibility wrapper into `tui.cli`
- `tui/cli.py` - main CLI + TUI + chat agent engine + Trinity integration
- `system_cli/state.py` - AppState
- `core/trinity.py` - Trinity graph runtime
- `core/agents/*` - prompts
- `core/verification.py` - AdaptiveVerifier
- `core/mcp.py` - tool registry
