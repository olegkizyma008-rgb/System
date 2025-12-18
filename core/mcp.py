import json
import time
import asyncio
import threading
import os
import contextlib
from typing import Dict, Any, Callable, List, Optional, Union
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import all tools
from system_ai.tools.executor import run_shell, open_app, run_applescript, run_shortcut
from system_ai.tools.executor import open_system_settings_privacy
from system_ai.tools.screenshot import take_screenshot
from system_ai.tools.filesystem import read_file, write_file, list_files, copy_file
from system_ai.tools.windsurf import (
    send_to_windsurf,
    open_file_in_windsurf,
    is_windsurf_running,
    get_windsurf_current_project_path,
    open_project_in_windsurf,
)
from system_ai.tools.input import click, type_text, press_key, move_mouse, click_mouse
from system_ai.tools.screenshot import take_screenshot, capture_screen_region, take_burst_screenshot
from system_ai.tools.vision import analyze_with_copilot, ocr_region, find_image_on_screen, compare_images
from core.memory import save_memory_tool, query_memory_tool

from system_ai.tools.permissions_manager import create_permissions_manager
from system_ai.tools.macos_native_automation import create_automation_executor
from system_ai.tools.macos_commands import create_command_executor
from system_ai.tools.system import list_processes, kill_process, get_system_stats
from system_ai.tools.desktop import get_monitors_info, get_open_windows, get_clipboard, set_clipboard
from system_ai.tools.browser import (
    browser_open_url,
    browser_click_element,
    browser_type_text,
    browser_get_content,
    browser_execute_script,
    browser_ensure_ready,
    browser_press_key,
    browser_screenshot
)

class ExternalMCPProvider:
    """Handles connection to an external MCP server via stdio."""
    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        self._server_params = StdioServerParameters(command=command, args=args, env=os.environ.copy())
        self._tools: Dict[str, Any] = {}
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._connected = False
        
    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def connect(self):
        if self._connected:
            return
        future = asyncio.run_coroutine_threadsafe(self._async_connect(), self._loop)
        future.result(timeout=30)
        self._connected = True

    async def _async_connect(self):
        self._exit_stack = contextlib.AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(stdio_client(self._server_params))
        self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        
        # List tools
        tools_list = await self._session.list_tools()
        for tool in tools_list.tools:
            self._tools[tool.name] = tool
        
    def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if not self._connected:
            self.connect()
        future = asyncio.run_coroutine_threadsafe(self._async_execute(tool_name, args), self._loop)
        return future.result(timeout=60)

    async def _async_execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        try:
            result = await self._session.call_tool(tool_name, args)
            # Standardize output for Trinity (JSON string or dict)
            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    content.append(item.text)
                elif hasattr(item, "data"):
                    # Handle image/binary data if needed
                    content.append(f"[Binary Data: {len(item.data)} bytes]")
            
            return {
                "tool": tool_name,
                "status": "success" if not result.isError else "error",
                "output": "\n".join(content) if content else "",
                "raw": str(result)
            }
        except Exception as e:
            return {"tool": tool_name, "status": "error", "error": str(e)}

class MCPToolRegistry:
    """
    The strictly defined Tool Registry for Project Atlas.
    Only tools registered here can be executed by the LLM.
    """
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}
        self._external_providers: Dict[str, ExternalMCPProvider] = {}
        self._external_tools_map: Dict[str, str] = {} # tool_name -> provider_name
        self._register_defaults()
        self._register_external_mcp()
        
    def _register_defaults(self):
        # Foundation Tools
        self.register_tool("run_shell", run_shell, "Execute shell command. Args: command (str), allow=True")
        self.register_tool("open_app", open_app, "Open MacOS Application. Args: name (str)")
        self.register_tool("run_applescript", run_applescript, "Run AppleScript. Args: script (str)")
        self.register_tool("run_shortcut", run_shortcut, "Run Shortcuts automation. Args: name (str), allow=True")

        # Permissions / Privacy
        self.register_tool(
            "open_system_settings_privacy",
            open_system_settings_privacy,
            "Open macOS Privacy pane. Args: permission (accessibility|automation|screen_recording|full_disk_access|microphone|files_and_folders)",
        )

        pm = create_permissions_manager()
        self.register_tool("check_permissions", lambda: {"tool": "check_permissions", "status": "success", "permissions": {k: vars(v) for k, v in pm.check_all().items()}}, "Check macOS permissions (accessibility/screen_recording/automation). Args: none")
        self.register_tool("permission_help", lambda lang="en": {"tool": "permission_help", "status": "success", "text": pm.get_permission_help_text(lang=str(lang or 'en').strip().lower())}, "Get permissions help text. Args: lang (en|uk)")

        def _get_recorder_service() -> Any:
            # Optional integration with TUI recorder if running under that environment.
            # Keep this import local to avoid hard dependency from core -> tui.
            try:
                from tui.cli import _get_recorder_service as _tui_get_recorder_service  # type: ignore

                return _tui_get_recorder_service()
            except Exception:
                return None

        def _record_automation_event(tool: str, args: Dict[str, Any], result: Any) -> None:
            try:
                rec = _get_recorder_service()
                if rec is None:
                    return
                status = getattr(rec, "status", None)
                if not bool(getattr(status, "running", False)):
                    return
                if not hasattr(rec, "_enqueue"):
                    return

                safe_args: Dict[str, Any] = {}
                for k, v in (args or {}).items():
                    if k == "script" and isinstance(v, str):
                        safe_args[k] = v[:200]
                    elif isinstance(v, str):
                        safe_args[k] = v[:500]
                    else:
                        safe_args[k] = v

                ev = {
                    "type": "automation",
                    "ts": time.time(),
                    "tool": str(tool or ""),
                    "args": safe_args,
                    "result": result,
                }
                rec._enqueue(ev)
            except Exception:
                return

        def _open_app_wrapped(name: str, **kwargs) -> Any:
            res = open_app(name=name)
            # Record with full kwargs for debugging
            _record_automation_event("open_app", {"name": name, **kwargs}, res)
            return res

        def _run_applescript_wrapped(script: str, allow: bool = True, **kwargs) -> Any:
            res = run_applescript(script=script, allow=allow)
            _record_automation_event("run_applescript", {"script": script, "allow": allow, **kwargs}, res)
            return res

        def _run_shell_wrapped(command: str, allow: bool = True, **kwargs) -> Any:
            # Handle potential 'cwd' or other kwargs passed by LLM
            res = run_shell(command=command, allow=allow, **kwargs)
            _record_automation_event("run_shell", {"command": command, "allow": allow, **kwargs}, res)
            return res

        def _run_shortcut_wrapped(name: str, allow: bool = True, **kwargs) -> Any:
            res = run_shortcut(name=name, allow=allow)
            _record_automation_event("run_shortcut", {"name": name, "allow": allow, **kwargs}, res)
            return res

        # Overwrite foundation tools with recorder-aware wrappers.
        self.register_tool("run_shell", _run_shell_wrapped, "Execute shell command. Args: command (str), allow=True")
        self.register_tool("open_app", _open_app_wrapped, "Open MacOS Application. Args: name (str)")
        self.register_tool("run_applescript", _run_applescript_wrapped, "Run AppleScript. Args: script (str)")
        self.register_tool("run_shortcut", _run_shortcut_wrapped, "Run Shortcuts automation. Args: name (str), allow=True")

        def _native() -> Any:
            return create_automation_executor(recorder_service=_get_recorder_service())

        def _native_cmd() -> Any:
            return create_command_executor(_native())

        # Native macOS automation (AppleScript-based)
        self.register_tool(
            "native_applescript",
            lambda script: _native().execute_applescript(str(script or ""), record=True),
            "Execute AppleScript via native automation (recordable if recorder is active). Args: script (str)",
        )
        self.register_tool(
            "native_click_ui",
            lambda app_name, ui_path: _native().click_ui_element(str(app_name or ""), str(ui_path or ""), record=True),
            "Click UI element via AppleScript (recordable). Args: app_name (str), ui_path (str)",
        )
        self.register_tool(
            "native_type_text",
            lambda text: _native().type_text(str(text or ""), record=True),
            "Type text via AppleScript (recordable). Args: text (str)",
        )
        self.register_tool(
            "native_wait",
            lambda seconds=1.0: _native().wait(float(seconds or 0.0), record=True),
            "Sleep/wait (recordable). Args: seconds (float)",
        )
        self.register_tool(
            "native_front_app",
            lambda: _native().get_frontmost_app(),
            "Get frontmost application name. Args: none",
        )

        # High-level commands (wrappers)
        self.register_tool(
            "native_open_app",
            lambda name: _native_cmd().open_app(str(name or "")),
            "Open application (native). Args: name (str)",
        )
        self.register_tool(
            "native_activate_app",
            lambda name: _native_cmd().activate_app(str(name or "")),
            "Activate application (native). Args: name (str)",
        )
        
        # Filesystem
        self.register_tool("read_file", read_file, "Read file content. Args: path (str)")
        self.register_tool("write_file", write_file, "Write file content. Args: path (str), content (str)")
        self.register_tool("copy_file", copy_file, "Copy file (binary-safe). Args: src (str), dst (str), overwrite (bool)")
        self.register_tool("list_files", list_files, "List directory. Args: path (str)")
        
        # Dev Subsystem
        self.register_tool("send_to_windsurf", send_to_windsurf, "Send message to Windsurf Chat. Args: message (str)")
        self.register_tool("open_file_in_windsurf", open_file_in_windsurf, "Open file in Windsurf. Args: path (str), line (int)")
        self.register_tool("is_windsurf_running", is_windsurf_running, "Check if Windsurf is running. Args: none")
        self.register_tool(
            "get_windsurf_current_project_path",
            get_windsurf_current_project_path,
            "Get current/open project folder path from Windsurf state. Args: none",
        )
        self.register_tool(
            "open_project_in_windsurf",
            open_project_in_windsurf,
            "Open a project folder in Windsurf. Args: path (str), new_window (bool)",
        )
        
        # Vision/Input
        self.register_tool("capture_screen", take_screenshot, "Take screenshot of app or screen. Args: app_name (optional)")
        self.register_tool("take_screenshot", take_screenshot, "Take screenshot of app or screen. Args: app_name (optional)")
        self.register_tool("take_burst_screenshot", take_burst_screenshot, "Take multiple screenshots in a burst. Args: app_name (optional), count (int), interval (float)")
        self.register_tool("capture_screen_region", capture_screen_region, "Capture screenshot of screen region. Args: x,y,width,height")
        self.register_tool("analyze_screen", analyze_with_copilot, "Analyze screen image with AI. Args: image_path (str), prompt (str)")
        self.register_tool("ocr_region", ocr_region, "OCR a screen region using vision. Args: x,y,width,height")
        self.register_tool("find_image_on_screen", find_image_on_screen, "Find an image template on screen (may be unimplemented). Args: template_path (str), tolerance (float)")
        self.register_tool("compare_images", compare_images, "Compare two images (before/after) using vision. Args: path1 (str), path2 (str), prompt (str optional)")

        self.register_tool("move_mouse", move_mouse, "Move mouse to absolute coordinates. Args: x (int), y (int)")
        self.register_tool("click_mouse", click_mouse, "Click mouse (left/right/double) optionally at x,y. Args: button(str), x?(int), y?(int)")
        self.register_tool("click", click, "Mouse click. Args: x (int), y (int)")
        self.register_tool("type_text", type_text, "Type text. Args: text (str)")
        self.register_tool("press_key", press_key, "Press key. Args: key (str), command(bool), shift(bool)...")

        # RAG Memory
        self.register_tool("save_memory", save_memory_tool, "Save info to memory. Args: category (ui_patterns/strategies), content (str)")
        self.register_tool("rag_query", query_memory_tool, "Query memory. Args: category (str), query (str)")

        # System Tools
        self.register_tool("list_processes", list_processes, "List running processes. Args: limit (int), sort_by (cpu|memory|name)")
        self.register_tool("kill_process", kill_process, "Terminate a process. Args: pid (int)")
        self.register_tool("get_system_stats", get_system_stats, "Get system stats (CPU/Mem). Args: none")

        # Desktop Tools
        self.register_tool("get_monitors_info", get_monitors_info, "Get info about connected displays. Args: none")
        self.register_tool("get_open_windows", get_open_windows, "List open windows. Args: on_screen_only (bool)")
        self.register_tool("get_clipboard", get_clipboard, "Read clipboard content. Args: none")
        self.register_tool("set_clipboard", set_clipboard, "Write to clipboard. Args: text (str)")

        # Browser Tools (Local Playwright)
        self.register_tool("browser_open_url", browser_open_url, "Open URL in local browser. Args: url (str), headless (bool)")
        self.register_tool("browser_navigate", browser_navigate, "Navigate to URL. Args: url (str), headless (bool)")
        self.register_tool("browser_click_element", browser_click_element, "Click element in browser. Args: selector (str)")
        self.register_tool("browser_type_text", browser_type_text, "Type text in browser. Args: selector (str), text (str), press_enter (bool)")
        self.register_tool("browser_press_key", browser_press_key, "Press a key in browser. Args: key (str)")
        self.register_tool("browser_screenshot", browser_screenshot, "Take screenshot of browser. Args: path (optional str)")
        self.register_tool("browser_snapshot", browser_snapshot, "Accessibility tree snapshot (best for navigation). Args: none")
        self.register_tool("browser_get_content", browser_get_content, "Get page/element text. Args: none")
        self.register_tool("browser_execute_script", browser_execute_script, "Run JS in browser. Args: script (str)")
        self.register_tool("browser_ensure_ready", browser_ensure_ready, "Check if browser is ready. Args: none")
        self.register_tool("browser_close", browser_close, "Close browser. Args: none")


        # Project Structure
        def _save_last_response_and_regenerate(text: str) -> Dict[str, Any]:
            """Save response to .last_response.txt (preserving Trinity reports) and regenerate project_structure_final.txt"""
            try:
                # Read existing content (Trinity reports)
                existing_content = ""
                try:
                    with open(".last_response.txt", "r", encoding="utf-8") as f:
                        existing_content = f.read().strip()
                except FileNotFoundError:
                    pass
                
                # Build new content: my response first, then existing Trinity reports
                new_content = ""
                if existing_content:
                    # Prepend my response, keep Trinity reports below
                    new_content = f"## My Last Response\n\n{text}\n\n---\n\n{existing_content}"
                else:
                    # First time: just my response
                    new_content = f"## My Last Response\n\n{text}"
                
                with open(".last_response.txt", "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                # Regenerate project structure
                import subprocess
                result = subprocess.run(
                    ["python3", "generate_structure.py"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "status": "success",
                    "message": "Response saved (Trinity reports preserved) and project structure regenerated",
                    "output": result.stdout[:500] if result.stdout else ""
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to save response: {str(e)}"
                }

        self.register_tool(
            "save_last_response",
            _save_last_response_and_regenerate,
            "Save last response to .last_response.txt and regenerate project_structure_final.txt. Args: text (str)"
        )

    def _register_external_mcp(self):
        """Register external MCP servers (Playwright & PyAutoGUI)."""
        import platform
        playwright_args = ["@playwright/mcp@latest"]
        if platform.system() != "Darwin":
            playwright_args.append("--no-sandbox")

        providers = [
            ("playwright", "npx", playwright_args),
            ("pyautogui", "mcp-pyautogui-server", [])
        ]
        
        for name, cmd, args in providers:
            try:
                provider = ExternalMCPProvider(name, cmd, args)
                self._external_providers[name] = provider
                # Lazy loading: we don't connect yet, just register the intent
                # Note: list_tools() will trigger connection if needed to get descriptions
            except Exception as e:
                print(f"[MCP] Failed to initialize external provider {name}: {e}")

    def register_tool(self, name: str, func: Callable, description: str):
        self._tools[name] = func
        self._descriptions[name] = description

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def list_tools(self) -> str:
        """Returns a formatted list of tools for the System Prompt."""
        lines = []
        # Local tools
        for name, desc in self._descriptions.items():
            lines.append(f"- {name}: {desc}")
        
        # External tools
        for p_name, provider in self._external_providers.items():
            try:
                provider.connect()
                for t_name, tool in provider._tools.items():
                    # Prefix external tools to avoid collisions (e.g. playwright.browser_snapshot)
                    prefixed_name = f"{p_name}.{t_name}"
                    self._external_tools_map[prefixed_name] = p_name
                    lines.append(f"- {prefixed_name}: {tool.description}")
            except Exception as e:
                lines.append(f"- [Provider Offline] {p_name}: {e}")
                
        return "\n".join(lines)

    def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Executes a tool safely and returns a string result."""
        # Check external tools first
        provider_name = self._external_tools_map.get(tool_name)
        if provider_name and provider_name in self._external_providers:
            provider = self._external_providers[provider_name]
            try:
                # Strip prefix if present (e.g. "playwright.browser_navigate" -> "browser_navigate")
                actual_name = tool_name.split(".", 1)[-1] if "." in tool_name else tool_name
                res = provider.execute(actual_name, args)
                return json.dumps(res, indent=2, ensure_ascii=False)
            except Exception as e:
                return f"Error executing external tool '{tool_name}': {str(e)}"

        func = self._tools.get(tool_name)
        if not func:
            return f"Error: Tool '{tool_name}' not found."
        
        try:
            # Inspection of function signature to avoid TypeError: unexpected keyword argument
            import inspect
            sig = inspect.signature(func)
            
            # Special handling for 'allow' kwarg in executor tools if not present but needed
            if "allow" in sig.parameters and "allow" not in args:
                args["allow"] = True
            
            call_kwargs = {}
            
            # TUI Tool Convention: If the function explicitly requests 'args', pass the full dictionary
            if "args" in sig.parameters:
                call_kwargs["args"] = args
            elif "_args" in sig.parameters:
                call_kwargs["_args"] = args
            
            # Filter args to only those supported by the function, unless it has **kwargs
            has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            
            if has_varkw:
                # If function has **kwargs, pass everything
                for k, v in args.items():
                    # Avoid overwriting the injected 'args' parameter if it exists
                    if k == "args" and "args" in sig.parameters:
                        continue
                    call_kwargs[k] = v
            else:
                # Filter to supported params
                for k, v in args.items():
                    if k in sig.parameters:
                        call_kwargs[k] = v
            
            result = func(**call_kwargs)
                
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error executing '{tool_name}': {str(e)}"
