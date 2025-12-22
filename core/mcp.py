import json
import time
import asyncio
import threading
import os
import contextlib
from typing import Dict, Any, Callable, List, Optional, Union, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import RAG integration for intelligent tool selection
try:
    from mcp_integration.rag_integration import (
        select_tool_for_task,
        get_best_tool_for_task,
        classify_task,
        tool_selector
    )
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    tool_selector = None

# Import all tools
from system_ai.tools.automation import (
    run_shell, open_app, run_applescript, run_shortcut,
    click, type_text, press_key, move_mouse, click_mouse, activate_app
)
from system_ai.tools.permissions_manager import create_permissions_manager, open_system_settings_privacy
from system_ai.tools.screenshot import take_screenshot, capture_screen_region, take_burst_screenshot
from system_ai.tools.filesystem import read_file, write_file, list_files, copy_file
from system_ai.tools.windsurf import (
    send_to_windsurf,
    open_file_in_windsurf,
    is_windsurf_running,
    get_windsurf_current_project_path,
    open_project_in_windsurf,
)
analyze_with_copilot = None
ocr_region = None
find_image_on_screen = None
compare_images = None
from core.memory import save_memory_tool, query_memory_tool
from system_ai.tools.macos_native_automation import create_automation_executor
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
    browser_screenshot,
    browser_snapshot,
    browser_navigate,
    browser_get_links,
    browser_close,
    browser_search_duckduckgo
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
        self._exit_stack = None
        self._session = None
        
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
            result_content = getattr(result, "content", []) if result is not None else []
            for item in result_content if result_content else []:
                if item is not None and hasattr(item, "text"):
                    content.append(item.text)
                elif item is not None and hasattr(item, "data"):
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
    
    def disconnect(self):
        """Properly disconnect from the MCP server and cleanup resources."""
        if not self._connected:
            return
        
        try:
            future = asyncio.run_coroutine_threadsafe(self._async_disconnect(), self._loop)
            future.result(timeout=10)
        except Exception as e:
            print(f"Warning: Error during disconnect: {e}")
        finally:
            self._connected = False
    
    async def _async_disconnect(self):
        """Async cleanup of MCP connection."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                print(f"Warning: Error closing exit stack: {e}")
            finally:
                self._exit_stack = None
                self._session = None
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        if self._connected:
            self.disconnect()
        
        # Stop the event loop if it's running
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

class MCPToolRegistry:
    """
    The strictly defined Tool Registry for Project Atlas.
    Only tools registered here can be executed by the LLM.
    """
    
    VISION_DISABLED_ERROR = "Vision tools disabled (TRINITY_DISABLE_VISION=1)"
    LAST_RESPONSE_FILE = ".last_response.txt"
    YT_SEARCH_SELECTOR = '[name="search_query"]'

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}
        self._external_providers: Dict[str, ExternalMCPProvider] = {}
        self._external_tools_map: Dict[str, str] = {} # tool_name -> provider_name
        self._register_foundation_tools()
        self._register_filesystem_tools()
        self._register_dev_tools()
        self._register_vision_tools()
        self._register_system_and_desktop_tools()
        self._register_memory_tools()
        self._register_browser_tools()
        self._register_recorder_tools()
        self._register_response_tools()
        self._register_external_mcp()

    def _register_foundation_tools(self):
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

        # Log confirmation of low-level tool availability (User Request)
        print("✅ [MCP] Low-level tools available: run_shell, run_applescript, open_app, run_shortcut")

        self.register_tool("run_shell", self._run_shell_wrapped, "Execute shell command. Args: command (str), allow=True")
        self.register_tool("open_app", self._open_app_wrapped, "Open MacOS Application. Args: name (str)")
        self.register_tool("run_applescript", lambda script, allow=True: run_applescript(script=script, allow=allow), "Run AppleScript. Args: script (str)")
        self.register_tool("run_shortcut", self._run_shortcut_wrapped, "Run Shortcuts automation. Args: name (str), allow=True")

        self.register_tool(
            "native_applescript",
            lambda script: self._native_executor().execute_applescript(str(script or ""), record=True),
            "Execute AppleScript via native automation (recordable if recorder is active). Args: script (str)",
        )
        self.register_tool(
            "native_click_ui",
            lambda app_name, ui_path: self._native_executor().click_ui_element(str(app_name or ""), str(ui_path or ""), record=True),
            "Click UI element via AppleScript (recordable). Args: app_name (str), ui_path (str)",
        )
        self.register_tool(
            "native_type_text",
            lambda text: self._native_executor().type_text(str(text or ""), record=True),
            "Type text via AppleScript (recordable). Args: text (str)",
        )
        self.register_tool(
            "native_wait",
            lambda seconds=1.0: self._native_executor().wait(float(seconds or 0.0), record=True),
            "Sleep/wait (recordable). Args: seconds (float)",
        )
        self.register_tool(
            "native_front_app",
            lambda: self._native_executor().get_frontmost_app(),
            "Get frontmost application name. Args: none",
        )
        self.register_tool(
            "native_open_app",
            lambda name: open_app(str(name or "")),
            "Open application (native). Args: name (str)",
        )
        self.register_tool(
            "native_activate_app",
            lambda name: activate_app(str(name or "")),
            "Activate application (native). Args: name (str)",
        )

    def _get_recorder_service(self) -> Any:
        try:
            from tui.cli import _get_recorder_service as _tui_get_recorder_service
            return _tui_get_recorder_service()
        except Exception:
            return None

    def _record_automation_event(self, tool: str, args: Dict[str, Any], result: Any) -> None:
        try:
            rec = self._get_recorder_service()
            if rec is None or not bool(getattr(rec.status, "running", False)) or not hasattr(rec, "_enqueue"):
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

    def _open_app_wrapped(self, name: str, **kwargs) -> Any:
        res = open_app(name=name)
        self._record_automation_event("open_app", {"name": name, **kwargs}, res)
        return res

    def _run_shell_wrapped(self, command: str, allow: bool = True, **kwargs) -> Any:
        res = run_shell(command=command, allow=allow, **kwargs)
        self._record_automation_event("run_shell", {"command": command, "allow": allow, **kwargs}, res)
        return res

    def _run_shortcut_wrapped(self, name: str, allow: bool = True, **kwargs) -> Any:
        res = run_shortcut(name=name, allow=allow)
        self._record_automation_event("run_shortcut", {"name": name, "allow": allow, **kwargs}, res)
        return res

    def _native_executor(self) -> Any:
        return create_automation_executor(recorder_service=self._get_recorder_service())

    def _register_filesystem_tools(self):
        self.register_tool("read_file", read_file, "Read file content. Args: path (str)")
        self.register_tool("write_file", write_file, "Write file content. Args: path (str), content (str)")
        self.register_tool("copy_file", copy_file, "Copy file (binary-safe). Args: src (str), dst (str), overwrite (bool)")
        self.register_tool("list_files", list_files, "List directory. Args: path (str)")

    def _register_dev_tools(self):
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

    def _register_vision_tools(self):
        self.register_tool("take_screenshot", take_screenshot, "Take screenshot of app or screen. Args: app_name (optional)")
        self.register_tool("capture_screen", take_screenshot, "Capture current screen state for verification. Args: app_name (optional)")
        self.register_tool("take_burst_screenshot", take_burst_screenshot, "Take multiple screenshots in a burst. Args: app_name (optional), count (int), interval (float)")
        self.register_tool("capture_screen_region", capture_screen_region, "Capture screenshot of screen region. Args: x,y,width,height")

        disable_vision = str(os.environ.get("TRINITY_DISABLE_VISION", "")).strip().lower() in {"1", "true", "yes", "on"}
        if not disable_vision:
            try:
                from system_ai.tools.vision import (
                    analyze_with_copilot as _analyze_with_copilot,
                    ocr_region as _ocr_region,
                    find_image_on_screen as _find_image_on_screen,
                    compare_images as _compare_images,
                )
                global analyze_with_copilot, ocr_region, find_image_on_screen, compare_images
                analyze_with_copilot, ocr_region = _analyze_with_copilot, _ocr_region
                find_image_on_screen, compare_images = _find_image_on_screen, _compare_images

                self.register_tool("vision_analyze", analyze_with_copilot, "Analyze screen with AI to get coordinates and text. Args: image_path (optional), prompt (str)")
                self.register_tool("analyze_screen", analyze_with_copilot, "Analyze screen with AI to verify state, find elements, or solve tasks. Args: image_path (optional), prompt (str)")
                self.register_tool("ocr_region", ocr_region, "OCR a screen region using vision. Args: x,y,width,height")
                self.register_tool("find_image_on_screen", find_image_on_screen, "Find an image template on screen. Args: template_path (str), tolerance (float)")
                self.register_tool("compare_images", compare_images, "Compare two images (before/after) using vision. Args: path1 (str), path2 (str), prompt (str optional)")
            except Exception as e:
                err_func = lambda *_, **__: {"status": "error", "error": f"Vision tools unavailable: {e}"}
                self.register_tool("vision_analyze", err_func, "Analyze screen with AI (unavailable)")
                self.register_tool("analyze_screen", err_func, "Analyze screen with AI (unavailable)")
                self.register_tool("ocr_region", err_func, "OCR a screen region (unavailable)")
                self.register_tool("find_image_on_screen", err_func, "Find image on screen (unavailable)")
                self.register_tool("compare_images", err_func, "Compare images (unavailable)")
        else:
            err_func = lambda *_, **__: {"status": "error", "error": self.VISION_DISABLED_ERROR}
            self.register_tool("vision_analyze", err_func, "Analyze screen with AI (disabled)")
            self.register_tool("analyze_screen", err_func, "Analyze screen with AI (disabled)")
            self.register_tool("ocr_region", err_func, "OCR a screen region (disabled)")
            self.register_tool("find_image_on_screen", err_func, "Find image on screen (disabled)")
            self.register_tool("compare_images", err_func, "Compare images (disabled)")

    def _register_system_and_desktop_tools(self):
        self.register_tool("move_mouse", move_mouse, "Move mouse to absolute coordinates. Args: x (int), y (int)")
        self.register_tool("click_mouse", click_mouse, "Click mouse (left/right/double) optionally at x,y. Args: button(str), x?(int), y?(int)")
        self.register_tool("click", click, "Mouse click. Args: x (int), y (int)")
        self.register_tool("type_text", type_text, "Type text. Args: text (str)")
        self.register_tool("press_key", press_key, "Press key. Args: key (str), command(bool), shift(bool)...")
        self.register_tool("list_processes", list_processes, "List running processes. Args: limit (int), sort_by (cpu|memory|name)")
        self.register_tool("kill_process", kill_process, "Terminate a process. Args: pid (int)")
        self.register_tool("get_system_stats", get_system_stats, "Get system stats (CPU/Mem). Args: none")
        self.register_tool("get_monitors_info", get_monitors_info, "Get info about connected displays. Args: none")
        self.register_tool("get_open_windows", get_open_windows, "List open windows. Args: on_screen_only (bool)")
        self.register_tool("get_clipboard", get_clipboard, "Read clipboard content. Args: none")
        self.register_tool("set_clipboard", set_clipboard, "Write to clipboard. Args: text (str)")

        from system_ai.tools.cleanup import (
            system_cleanup_stealth, system_cleanup_windsurf,
            system_spoof_hardware, system_check_identifiers
        )
        self.register_tool("system_cleanup_stealth", system_cleanup_stealth, "Run stealth cleanup (logs, caches). Args: allow=True")
        self.register_tool("system_cleanup_windsurf", system_cleanup_windsurf, "Run deep Windsurf cleanup. Args: allow=True")
        self.register_tool("system_spoof_hardware", system_spoof_hardware, "Spoof MAC/Hostname. Args: allow=True")
        self.register_tool("system_check_identifiers", system_check_identifiers, "Check system identifiers. Args: none")

    def _register_memory_tools(self):
        self.register_tool("save_memory", save_memory_tool, "Save info to memory. Args: category (ui_patterns/strategies), content (str)")
        self.register_tool("rag_query", query_memory_tool, "Query memory. Args: category (str), query (str)")

    def _register_browser_tools(self):
        self.register_tool("browser_open_url", browser_open_url, "Open URL in browser. Args: url (str), headless (bool=False). Wait 3-5s after for page load.")
        self.register_tool("browser_navigate", browser_navigate, "Navigate to URL. Args: url (str), headless (bool=False)")
        self.register_tool("browser_click_element", browser_click_element, "Click element. Args: selector (CSS selector str). Use playwright.playwright_get_visible_html to find selectors first!")
        self.register_tool("browser_type_text", browser_type_text, "Type text in input. Args: selector (str), text (str), press_enter (bool). YouTube: [name='search_query'], Google: textarea[name='q']")
        self.register_tool("browser_press_key", browser_press_key, "Press a key in browser. Args: key (str)")
        self.register_tool("browser_screenshot", browser_screenshot, "Take screenshot of browser. Args: path (optional str)")
        self.register_tool("browser_snapshot", browser_snapshot, "Get visible text from page for verification. Args: none")
        self.register_tool("browser_get_content", browser_get_content, "Get page/element text. Args: none")
        self.register_tool("browser_get_links", browser_get_links, "Extract all clickable links from the current page. Args: none")
        self.register_tool("browser_execute_script", browser_execute_script, "Run JS in browser. Args: script (str)")
        self.register_tool("browser_ensure_ready", browser_ensure_ready, "Check if browser is ready. Args: none")
        self.register_tool("browser_close", browser_close, "Close browser. Args: none")
        self.register_tool("browser_search_duckduckgo", browser_search_duckduckgo, "Search using DuckDuckGo (CAPTCHA-resistant, use when Google blocked). Args: query (str), headless (bool=False). Returns search result links.")

    def _register_recorder_tools(self):
        def _recorder_action(action: str) -> Any:
            from core.mcp import _get_recorder_service as get_rec
            svc = get_rec()
            if not svc: return {"status": "error", "error": "Recorder service not available"}
            if action == "start":
                success, msg = svc.start()
                return {"status": "success" if success else "error", "message": msg}
            if action == "stop":
                success, msg, path = svc.stop()
                return {"status": "success" if success else "error", "message": msg, "path": path}
            if action == "status":
                st = svc.get_status()
                return {"status": "success", "running": st.running, "session_id": st.session_id, "events": st.events_count}
            return {"status": "error", "error": "Unknown action"}

        self.register_tool("recorder_start", lambda: _recorder_action("start"), "Start screen/event recording. Args: none")
        self.register_tool("recorder_stop", lambda: _recorder_action("stop"), "Stop recording and save. Args: none")
        self.register_tool("recorder_status", lambda: _recorder_action("status"), "Get recorder status. Args: none")

    def _register_response_tools(self):
        def _save_last_response_and_regenerate(text: str) -> Dict[str, Any]:
            try:
                existing_content = ""
                if os.path.exists(self.LAST_RESPONSE_FILE):
                    with open(self.LAST_RESPONSE_FILE, "r", encoding="utf-8") as f:
                        existing_content = f.read().strip()
                new_content = f"## My Last Response\n\n{text}\n\n---\n\n{existing_content}" if existing_content else f"## My Last Response\n\n{text}"
                with open(self.LAST_RESPONSE_FILE, "w", encoding="utf-8") as f:
                    f.write(new_content)
                import subprocess
                result = subprocess.run(["python3", "generate_structure.py"], capture_output=True, text=True, timeout=30)
                return {"status": "success", "message": "Response saved and project structure regenerated", "output": result.stdout[:500] if result.stdout else ""}
            except Exception as e:
                return {"status": "error", "message": f"Failed to save response: {str(e)}"}

        self.register_tool("save_last_response", _save_last_response_and_regenerate, f"Save last response to {self.LAST_RESPONSE_FILE} and regenerate project_structure_final.txt. Args: text (str)")

    def _register_external_mcp(self):
        """Register external MCP servers (Playwright, AppleScript, PyAutoGUI) - PRIORITY over local implementations."""
        import os
        import platform
        
        # Use the installed executeautomation playwright-mcp-server
        # -y flag auto-confirms installation if needed
        playwright_args = ["-y", "@executeautomation/playwright-mcp-server"]
        
        # AppleScript MCP server for native macOS automation
        # NOTE: @mseep/applescript-mcp has no bin file, use @iflow-mcp/applescript-mcp instead
        applescript_args = ["-y", "@iflow-mcp/applescript-mcp"]
        
        # PyAutoGUI MCP server for GUI automation
        pyautogui_args = []

        providers = [
            ("playwright", "npx", playwright_args),  # MCP server for browser automation (PRIORITY 1)
            ("applescript", "npx", applescript_args),  # MCP server for macOS automation (PRIORITY 2)
            ("pyautogui", "mcp-pyautogui-server", pyautogui_args),  # MCP server for GUI automation (PRIORITY 3)
        ]

        for name, cmd, args in providers:
            try:
                provider = ExternalMCPProvider(name, cmd, args)
                self._external_providers[name] = provider
                # Lazy loading: we don't connect yet, just register the intent
                # Note: list_tools() will trigger connection if needed to get descriptions
                print(f"[MCP] Registered external provider: {name}")
            except Exception as e:
                print(f"[MCP] Failed to initialize external provider {name}: {e}")

    def _adapt_args_for_mcp(self, local_name: str, mcp_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt local tool arguments to MCP server format."""
        
        # Adaptation handlers for specific tool categories
        handlers = {
            "browser_open_url": self._adapt_browser_nav,
            "browser_navigate": self._adapt_browser_nav,
            "browser_click_element": self._adapt_browser_click,
            "browser_type_text": self._adapt_browser_type,
            "browser_screenshot": self._adapt_browser_screenshot,
            "browser_press_key": self._adapt_browser_key,
            "browser_hover": lambda a: {"selector": a.get("selector", "")},
            "browser_select": lambda a: {"selector": a.get("selector", ""), "value": a.get("value", "")},
            "browser_get_content": lambda a: {"selector": a.get("selector", ""), "cleanHtml": True},
            "run_applescript": lambda a: {"script": a.get("script", "")}
        }
        
        handler = handlers.get(local_name)
        if handler:
            return handler(args)
            
        return args

    def _adapt_browser_nav(self, args):
        mcp_args = {"url": args.get("url", ""), "browserType": "chromium"}
        if "headless" in args:
            mcp_args["headless"] = args["headless"]
        return mcp_args

    def _adapt_browser_click(self, args):
        return {"selector": self._smart_selector(args.get("selector", ""))}

    def _adapt_browser_type(self, args):
        return {
            "selector": self._smart_selector(args.get("selector", "")),
            "value": args.get("text", "")
        }

    def _adapt_browser_screenshot(self, args):
        path = args.get("path", "screenshot")
        import os
        return {
            "name": os.path.basename(path).replace(".png", ""),
            "savePng": True,
            "downloadsDir": os.path.dirname(path) or ".",
            "fullPage": args.get("full_page", False)
        }

    def _adapt_browser_key(self, args):
        mcp_args = {"key": args.get("key", "")}
        if args.get("selector"):
            mcp_args["selector"] = args["selector"]
        return mcp_args

    def _smart_selector(self, selector: str) -> str:
        """Auto-correct common selector mistakes for popular sites."""
        selector_fixes = {
            # YouTube
            "input#search": self.YT_SEARCH_SELECTOR,
            "#search": self.YT_SEARCH_SELECTOR,
            "input[name='q']": self.YT_SEARCH_SELECTOR,  # Google-style won't work on YT
            
            # Google (fix textarea vs input)
            'input[name="q"]': 'textarea[name="q"], input[name="q"]',
        }
        
        # Return fixed selector if we have a mapping
        return selector_fixes.get(selector, selector)

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

    def get_all_tool_definitions(self) -> List[Dict[str, str]]:
        """Returns a list of tool definitions for LLM binding."""
        defs = []
        
        # Local tools
        for name, desc in self._descriptions.items():
            defs.append({"name": name, "description": desc})
            
        # External tools
        for p_name, provider in self._external_providers.items():
            try:
                # Ensure connected to get tools
                if not provider._connected:
                    provider.connect()
                
                for t_name, tool in provider._tools.items():
                    prefixed_name = f"{p_name}.{t_name}"
                    # Use schema if available, otherwise just description
                    defs.append({
                        "name": prefixed_name,
                        "description": tool.description
                    })
            except Exception as e:
                print(f"[MCP] Failed to get tools from provider {p_name}: {e}")
                
        return defs

    def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Executes a tool safely and returns a string result."""
        
        # 1. Routing to MCP Priotity
        mcp_res = self._try_mcp_routing(tool_name, args)
        if mcp_res is not None:
            return mcp_res

        # 2. Direct External Tool Call
        ext_res = self._try_external_direct_call(tool_name, args)
        if ext_res is not None:
            return ext_res

        # 3. Local Tool Call
        return self._execute_local_tool(tool_name, args)

    def _try_mcp_routing(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        mcp_routing = {
            "browser_open_url": ("playwright", "playwright_navigate"),
            "browser_navigate": ("playwright", "playwright_navigate"),
            "browser_click_element": ("playwright", "playwright_click"),
            "browser_type_text": ("playwright", "playwright_fill"),
            "browser_screenshot": ("playwright", "playwright_screenshot"),
            "browser_snapshot": ("playwright", "playwright_get_visible_text"),
            "browser_get_content": ("playwright", "playwright_get_visible_html"),
            "browser_close": ("playwright", "playwright_close"),
            "browser_press_key": ("playwright", "playwright_press_key"),
            "browser_hover": ("playwright", "playwright_hover"),
            "browser_select": ("playwright", "playwright_select"),
            "browser_go_back": ("playwright", "playwright_go_back"),
            "browser_go_forward": ("playwright", "playwright_go_forward"),
            "run_applescript": ("applescript", "run_applescript"),
        }
        
        if tool_name not in mcp_routing:
            return None
            
        provider_name, mcp_tool = mcp_routing[tool_name]
        if provider_name not in self._external_providers:
            return None
            
        provider = self._external_providers[provider_name]
        try:
            if not provider._connected:
                provider.connect()
            
            mcp_args = self._adapt_args_for_mcp(tool_name, mcp_tool, args)
            res = provider.execute(mcp_tool, mcp_args)
            
            if tool_name == "browser_type_text" and args.get("press_enter"):
                self._mcp_press_enter_fallback(provider, mcp_args)
            
            return json.dumps(res, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MCP] Failed {provider_name}.{mcp_tool}, falling back to local: {e}")
            return None

    def _mcp_press_enter_fallback(self, provider, mcp_args):
        try:
            time.sleep(0.5)
            key_args = {"key": "Enter"}
            if mcp_args.get("selector"):
                key_args["selector"] = mcp_args["selector"]
            provider.execute("playwright_press_key", key_args)
        except Exception:
            pass

    def _try_external_direct_call(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        provider_name = self._external_tools_map.get(tool_name)
        if not (provider_name and provider_name in self._external_providers):
            return None
            
        provider = self._external_providers[provider_name]
        try:
            actual_name = tool_name.split(".", 1)[-1] if "." in tool_name else tool_name
            res = provider.execute(actual_name, args)
            return json.dumps(res, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error executing external tool '{tool_name}': {str(e)}"

    def _execute_local_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        func = self._tools.get(tool_name)
        if not func:
            return f"Error: Tool '{tool_name}' not found."
            
        try:
            import inspect
            sig = inspect.signature(func)
            call_kwargs = self._prepare_call_kwargs(sig, args)
            result = func(**call_kwargs)
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error executing '{tool_name}': {str(e)}"

    def _prepare_call_kwargs(self, sig: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        if "allow" in sig.parameters and "allow" not in args:
            args["allow"] = True
            
        call_kwargs = {}
        if "args" in sig.parameters:
            call_kwargs["args"] = args
        elif "_args" in sig.parameters:
            call_kwargs["_args"] = args
            
        has_varkw = any(p.kind == 3 for p in sig.parameters.values()) # 3 = VAR_KEYWORD
        
        for k, v in args.items():
            if has_varkw:
                if not (k == "args" and "args" in sig.parameters):
                    call_kwargs[k] = v
            elif k in sig.parameters:
                call_kwargs[k] = v
        return call_kwargs

    # ===== RAG-based Intelligent Tool Selection =====
    
    def select_tool_for_task(self, task_description: str, n_candidates: int = 5) -> List[Dict[str, Any]]:
        """
        Use RAG to intelligently select the best tools for a given task.
        
        Args:
            task_description: Natural language description of what to do
            n_candidates: Number of tool candidates to return
            
        Returns:
            List of tool candidates with scores
        """
        if RAG_AVAILABLE and tool_selector:
            return tool_selector.select_tool(task_description, n_candidates)
        
        # Fallback: simple keyword matching
        return self._fallback_tool_selection(task_description, n_candidates)
    
    def get_best_tool(self, task_description: str) -> Optional[Dict[str, Any]]:
        """Get the single best tool for a task."""
        candidates = self.select_tool_for_task(task_description, n_candidates=1)
        return candidates[0] if candidates else None
    
    def classify_task(self, task_description: str) -> tuple:
        """
        Classify a task into a category (browser, system, gui, ai, etc.)
        
        Returns:
            Tuple of (category, confidence)
        """
        if RAG_AVAILABLE and tool_selector:
            return tool_selector.classify_task(task_description)
        
        # Fallback classification
        task_lower = task_description.lower()
        
        if any(kw in task_lower for kw in ["browser", "web", "url", "google", "search", "navigate"]):
            return ("browser", 0.8)
        elif any(kw in task_lower for kw in ["click", "mouse", "keyboard", "type", "gui"]):
            return ("gui", 0.8)
        elif any(kw in task_lower for kw in ["file", "read", "write", "copy", "delete"]):
            return ("filesystem", 0.8)
        elif any(kw in task_lower for kw in ["analyze", "ai", "summarize", "generate"]):
            return ("ai", 0.8)
        elif any(kw in task_lower for kw in ["shell", "terminal", "command", "applescript"]):
            return ("system", 0.8)
        
        return ("general", 0.5)
    
    def _fallback_tool_selection(self, task: str, n: int) -> List[Dict[str, Any]]:
        """Simple keyword-based tool selection as fallback."""
        task_lower = task.lower()
        scores = []
        
        for name, desc in self._descriptions.items():
            # Simple scoring based on keyword overlap
            desc_lower = desc.lower()
            score = 0
            
            for word in task_lower.split():
                if len(word) > 3 and word in desc_lower:
                    score += 1
                if word in name.lower():
                    score += 2
            
            if score > 0:
                scores.append({
                    "tool": name,
                    "description": desc,
                    "score": score / 10.0,
                    "server": "local"
                })
        
        # Sort by score and return top n
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:n]
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        if RAG_AVAILABLE and tool_selector:
            return tool_selector.get_stats()
        return {
            "rag_available": False,
            "fallback_mode": True,
            "local_tools": len(self._tools)
        }

