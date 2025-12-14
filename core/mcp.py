from typing import Dict, Any, Callable, List, Optional
import json

# Import all tools
from system_ai.tools.executor import run_shell, open_app, run_applescript, run_shortcut
from system_ai.tools.screenshot import take_screenshot
from system_ai.tools.filesystem import read_file, write_file, list_files
from system_ai.tools.windsurf import send_to_windsurf, open_file_in_windsurf
from system_ai.tools.input import click, type_text, press_key

class MCPToolRegistry:
    """
    The strictly defined Tool Registry for Project Atlas.
    Only tools registered here can be executed by the LLM.
    """
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}
        self._register_defaults()
        
    def _register_defaults(self):
        # Foundation Tools
        self.register_tool("run_shell", run_shell, "Execute shell command. Args: command (str), allow=True")
        self.register_tool("open_app", open_app, "Open MacOS Application. Args: name (str)")
        self.register_tool("run_applescript", run_applescript, "Run AppleScript. Args: script (str)")
        
        # Filesystem
        self.register_tool("read_file", read_file, "Read file content. Args: path (str)")
        self.register_tool("write_file", write_file, "Write file content. Args: path (str), content (str)")
        self.register_tool("list_files", list_files, "List directory. Args: path (str)")
        
        # Dev Subsystem
        self.register_tool("send_to_windsurf", send_to_windsurf, "Send message to Windsurf Chat. Args: message (str)")
        self.register_tool("open_file_in_windsurf", open_file_in_windsurf, "Open file in Windsurf. Args: path (str), line (int)")
        
        # Vision/Input
        self.register_tool("capture_screen", take_screenshot, "Take screenshot. Args: app_name (optional)")
        self.register_tool("click", click, "Mouse click. Args: x (int), y (int)")
        self.register_tool("type_text", type_text, "Type text. Args: text (str)")
        self.register_tool("press_key", press_key, "Press key. Args: key (str), command(bool), shift(bool)...")

    def register_tool(self, name: str, func: Callable, description: str):
        self._tools[name] = func
        self._descriptions[name] = description

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def list_tools(self) -> str:
        """Returns a formatted list of tools for the System Prompt."""
        lines = []
        for name, desc in self._descriptions.items():
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Executes a tool safely and returns a string result."""
        func = self._tools.get(tool_name)
        if not func:
            return f"Error: Tool '{tool_name}' not found."
        
        try:
            # We strictly map args from the dict to the function
            # Note: This simple implementation assumes args match function signature
            # In a robust system, we'd inspect signature or use **args
            
            # Special handling for 'allow' kwarg in executor tools
            if "allow" in func.__code__.co_varnames and "allow" not in args:
                args["allow"] = True
                
            result = func(**args)
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error executing '{tool_name}': {str(e)}"
