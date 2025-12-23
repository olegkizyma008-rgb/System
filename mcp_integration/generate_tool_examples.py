#!/usr/bin/env python3
"""
Tool Examples Generator
Generates 10,000+ tool examples for RAG-based tool selection.
"""

import json
import os
import random
from pathlib import Path
from typing import List, Dict, Any
import itertools


class ToolExamplesGenerator:
    """Generate comprehensive tool examples for MCP servers."""
    
    def __init__(self, output_dir: str = "core/tool_examples"):
        self.output_dir = Path(__file__).parent / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Base tool definitions
        self.tool_definitions = {
            "browser": self._get_browser_tools(),
            "system": self._get_system_tools(),
            "gui": self._get_gui_tools(),
            "ai": self._get_ai_tools(),
            "filesystem": self._get_filesystem_tools(),
            "code_analysis": self._get_code_analysis_tools()
        }
        
        # Variation templates
        self.variations = {
            "actions": ["perform", "execute", "run", "trigger", "initiate", "start", "begin", "launch"],
            "targets": ["element", "component", "widget", "control", "item", "object", "target"],
            "websites": ["google.com", "github.com", "stackoverflow.com", "reddit.com", "twitter.com", 
                        "linkedin.com", "youtube.com", "amazon.com", "wikipedia.org", "medium.com"],
            "file_types": [".py", ".js", ".ts", ".json", ".yaml", ".md", ".txt", ".html", ".css", ".sh"],
            "apps": ["Safari", "Chrome", "Firefox", "Terminal", "Finder", "Notes", "Calendar", 
                    "Mail", "Messages", "Slack", "Discord", "VSCode", "Xcode", "Spotify"],
            "search_terms": ["python tutorial", "machine learning", "web development", "api documentation",
                           "best practices", "code examples", "debugging tips", "performance optimization"],
            "ai_tasks": ["analyze", "summarize", "classify", "generate", "translate", "extract", 
                        "compare", "evaluate", "predict", "recommend"]
        }
    
    def _get_browser_tools(self) -> List[Dict]:
        """Browser automation tools."""
        return [
            {"tool": "browser_navigate", "base_desc": "Navigate to {url}", "server": "playwright", "params": ["url"]},
            {"tool": "browser_click", "base_desc": "Click on {selector}", "server": "playwright", "params": ["selector"]},
            {"tool": "browser_type", "base_desc": "Type {text} into {selector}", "server": "playwright", "params": ["selector", "text"]},
            {"tool": "browser_screenshot", "base_desc": "Take screenshot of {target}", "server": "playwright", "params": ["target"]},
            {"tool": "browser_scroll", "base_desc": "Scroll {direction} on page", "server": "playwright", "params": ["direction"]},
            {"tool": "browser_wait", "base_desc": "Wait for {selector} to be {state}", "server": "playwright", "params": ["selector", "state"]},
            {"tool": "browser_evaluate", "base_desc": "Evaluate JavaScript: {script}", "server": "playwright", "params": ["script"]},
            {"tool": "browser_select", "base_desc": "Select {option} from {selector}", "server": "playwright", "params": ["selector", "option"]},
            {"tool": "browser_hover", "base_desc": "Hover over {selector}", "server": "playwright", "params": ["selector"]},
            {"tool": "browser_fill_form", "base_desc": "Fill form with {data}", "server": "playwright", "params": ["data"]},
            {"tool": "browser_get_text", "base_desc": "Get text from {selector}", "server": "playwright", "params": ["selector"]},
            {"tool": "browser_get_attribute", "base_desc": "Get {attribute} from {selector}", "server": "playwright", "params": ["selector", "attribute"]},
            {"tool": "browser_new_tab", "base_desc": "Open new tab with {url}", "server": "playwright", "params": ["url"]},
            {"tool": "browser_close_tab", "base_desc": "Close current tab", "server": "playwright", "params": []},
            {"tool": "browser_back", "base_desc": "Navigate back in history", "server": "playwright", "params": []},
            {"tool": "browser_forward", "base_desc": "Navigate forward in history", "server": "playwright", "params": []},
            {"tool": "browser_refresh", "base_desc": "Refresh current page", "server": "playwright", "params": []},
            {"tool": "browser_get_url", "base_desc": "Get current page URL", "server": "playwright", "params": []},
            {"tool": "browser_get_title", "base_desc": "Get current page title", "server": "playwright", "params": []},
            {"tool": "browser_set_viewport", "base_desc": "Set viewport to {width}x{height}", "server": "playwright", "params": ["width", "height"]},
        ]
    
    def _get_system_tools(self) -> List[Dict]:
        """System command tools."""
        return [
            {"tool": "run_shell", "base_desc": "Execute shell command: {command}", "server": "local", "params": ["command"]},
            {"tool": "run_applescript", "base_desc": "Run AppleScript: {script}", "server": "applescript", "params": ["script"]},
            {"tool": "open_app", "base_desc": "Open application: {app_name}", "server": "applescript", "params": ["app_name"]},
            {"tool": "close_app", "base_desc": "Close application: {app_name}", "server": "applescript", "params": ["app_name"]},
            {"tool": "get_frontmost_app", "base_desc": "Get frontmost application", "server": "applescript", "params": []},
            {"tool": "activate_app", "base_desc": "Activate application: {app_name}", "server": "applescript", "params": ["app_name"]},
            {"tool": "hide_app", "base_desc": "Hide application: {app_name}", "server": "applescript", "params": ["app_name"]},
            {"tool": "quit_app", "base_desc": "Quit application: {app_name}", "server": "applescript", "params": ["app_name"]},
            {"tool": "run_shortcut", "base_desc": "Run Shortcuts workflow: {shortcut}", "server": "applescript", "params": ["shortcut"]},
            {"tool": "get_clipboard", "base_desc": "Get clipboard contents", "server": "applescript", "params": []},
            {"tool": "set_clipboard", "base_desc": "Set clipboard to: {text}", "server": "applescript", "params": ["text"]},
            {"tool": "speak_text", "base_desc": "Speak text: {text}", "server": "applescript", "params": ["text"]},
            {"tool": "display_notification", "base_desc": "Display notification: {message}", "server": "applescript", "params": ["message"]},
            {"tool": "display_dialog", "base_desc": "Display dialog: {message}", "server": "applescript", "params": ["message"]},
            {"tool": "get_volume", "base_desc": "Get system volume", "server": "applescript", "params": []},
            {"tool": "set_volume", "base_desc": "Set system volume to {level}", "server": "applescript", "params": ["level"]},
            {"tool": "get_brightness", "base_desc": "Get display brightness", "server": "applescript", "params": []},
            {"tool": "set_brightness", "base_desc": "Set display brightness to {level}", "server": "applescript", "params": ["level"]},
            {"tool": "lock_screen", "base_desc": "Lock the screen", "server": "applescript", "params": []},
            {"tool": "sleep_display", "base_desc": "Put display to sleep", "server": "applescript", "params": []},
        ]
    
    def _get_gui_tools(self) -> List[Dict]:
        """GUI interaction tools."""
        return [
            {"tool": "gui_click", "base_desc": "Click at ({x}, {y})", "server": "pyautogui", "params": ["x", "y"]},
            {"tool": "gui_double_click", "base_desc": "Double click at ({x}, {y})", "server": "pyautogui", "params": ["x", "y"]},
            {"tool": "gui_right_click", "base_desc": "Right click at ({x}, {y})", "server": "pyautogui", "params": ["x", "y"]},
            {"tool": "gui_type", "base_desc": "Type text: {text}", "server": "pyautogui", "params": ["text"]},
            {"tool": "gui_hotkey", "base_desc": "Press hotkey: {keys}", "server": "pyautogui", "params": ["keys"]},
            {"tool": "gui_press", "base_desc": "Press key: {key}", "server": "pyautogui", "params": ["key"]},
            {"tool": "gui_move", "base_desc": "Move mouse to ({x}, {y})", "server": "pyautogui", "params": ["x", "y"]},
            {"tool": "gui_drag", "base_desc": "Drag from ({x1}, {y1}) to ({x2}, {y2})", "server": "pyautogui", "params": ["x1", "y1", "x2", "y2"]},
            {"tool": "gui_scroll", "base_desc": "Scroll {direction} by {amount}", "server": "pyautogui", "params": ["direction", "amount"]},
            {"tool": "gui_screenshot", "base_desc": "Take screenshot of {region}", "server": "pyautogui", "params": ["region"]},
            {"tool": "gui_locate", "base_desc": "Locate image: {image_path}", "server": "pyautogui", "params": ["image_path"]},
            {"tool": "gui_locate_all", "base_desc": "Locate all instances of: {image_path}", "server": "pyautogui", "params": ["image_path"]},
            {"tool": "gui_get_position", "base_desc": "Get current mouse position", "server": "pyautogui", "params": []},
            {"tool": "gui_get_screen_size", "base_desc": "Get screen size", "server": "pyautogui", "params": []},
            {"tool": "gui_alert", "base_desc": "Show alert: {message}", "server": "pyautogui", "params": ["message"]},
            {"tool": "gui_confirm", "base_desc": "Show confirm dialog: {message}", "server": "pyautogui", "params": ["message"]},
            {"tool": "gui_prompt", "base_desc": "Show prompt: {message}", "server": "pyautogui", "params": ["message"]},
            {"tool": "gui_password", "base_desc": "Show password prompt: {message}", "server": "pyautogui", "params": ["message"]},
            {"tool": "gui_hold", "base_desc": "Hold key: {key}", "server": "pyautogui", "params": ["key"]},
            {"tool": "gui_release", "base_desc": "Release key: {key}", "server": "pyautogui", "params": ["key"]},
        ]
    
    def _get_ai_tools(self) -> List[Dict]:
        """AI analysis tools."""
        return [
            {"tool": "ai_analyze", "base_desc": "Analyze {data} for {purpose}", "server": "anthropic", "params": ["data", "purpose"]},
            {"tool": "ai_summarize", "base_desc": "Summarize {content}", "server": "anthropic", "params": ["content"]},
            {"tool": "ai_generate", "base_desc": "Generate {content_type} about {topic}", "server": "anthropic", "params": ["content_type", "topic"]},
            {"tool": "ai_translate", "base_desc": "Translate {text} to {language}", "server": "anthropic", "params": ["text", "language"]},
            {"tool": "ai_extract", "base_desc": "Extract {entities} from {text}", "server": "anthropic", "params": ["entities", "text"]},
            {"tool": "ai_classify", "base_desc": "Classify {content} into {categories}", "server": "anthropic", "params": ["content", "categories"]},
            {"tool": "ai_compare", "base_desc": "Compare {item1} with {item2}", "server": "anthropic", "params": ["item1", "item2"]},
            {"tool": "ai_evaluate", "base_desc": "Evaluate {content} against {criteria}", "server": "anthropic", "params": ["content", "criteria"]},
            {"tool": "ai_predict", "base_desc": "Predict {outcome} based on {data}", "server": "anthropic", "params": ["outcome", "data"]},
            {"tool": "ai_recommend", "base_desc": "Recommend {items} based on {preferences}", "server": "anthropic", "params": ["items", "preferences"]},
            {"tool": "ai_explain", "base_desc": "Explain {concept} in {style}", "server": "anthropic", "params": ["concept", "style"]},
            {"tool": "ai_rewrite", "base_desc": "Rewrite {text} in {style}", "server": "anthropic", "params": ["text", "style"]},
            {"tool": "ai_code_review", "base_desc": "Review code: {code}", "server": "anthropic", "params": ["code"]},
            {"tool": "ai_debug", "base_desc": "Debug {error} in {context}", "server": "anthropic", "params": ["error", "context"]},
            {"tool": "ai_optimize", "base_desc": "Optimize {content} for {goal}", "server": "anthropic", "params": ["content", "goal"]},
            {"tool": "ai_validate", "base_desc": "Validate {data} against {schema}", "server": "anthropic", "params": ["data", "schema"]},
            {"tool": "ai_convert", "base_desc": "Convert {data} from {format1} to {format2}", "server": "anthropic", "params": ["data", "format1", "format2"]},
            {"tool": "ai_sentiment", "base_desc": "Analyze sentiment of {text}", "server": "anthropic", "params": ["text"]},
            {"tool": "ai_keywords", "base_desc": "Extract keywords from {text}", "server": "anthropic", "params": ["text"]},
            {"tool": "ai_answer", "base_desc": "Answer question: {question}", "server": "anthropic", "params": ["question"]},
        ]
    
    def _get_filesystem_tools(self) -> List[Dict]:
        """Filesystem tools."""
        return [
            {"tool": "file_read", "base_desc": "Read file: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "file_write", "base_desc": "Write to file: {path}", "server": "filesystem", "params": ["path", "content"]},
            {"tool": "file_append", "base_desc": "Append to file: {path}", "server": "filesystem", "params": ["path", "content"]},
            {"tool": "file_delete", "base_desc": "Delete file: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "file_copy", "base_desc": "Copy {source} to {destination}", "server": "filesystem", "params": ["source", "destination"]},
            {"tool": "file_move", "base_desc": "Move {source} to {destination}", "server": "filesystem", "params": ["source", "destination"]},
            {"tool": "file_rename", "base_desc": "Rename {old_name} to {new_name}", "server": "filesystem", "params": ["old_name", "new_name"]},
            {"tool": "file_exists", "base_desc": "Check if file exists: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "file_info", "base_desc": "Get file info: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "file_list", "base_desc": "List files in: {directory}", "server": "filesystem", "params": ["directory"]},
            {"tool": "file_search", "base_desc": "Search for {pattern} in {directory}", "server": "filesystem", "params": ["pattern", "directory"]},
            {"tool": "file_grep", "base_desc": "Search for {text} in {files}", "server": "filesystem", "params": ["text", "files"]},
            {"tool": "dir_create", "base_desc": "Create directory: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "dir_delete", "base_desc": "Delete directory: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "dir_list", "base_desc": "List directory contents: {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "file_zip", "base_desc": "Zip {files} to {archive}", "server": "filesystem", "params": ["files", "archive"]},
            {"tool": "file_unzip", "base_desc": "Unzip {archive} to {destination}", "server": "filesystem", "params": ["archive", "destination"]},
            {"tool": "file_hash", "base_desc": "Calculate hash of {path}", "server": "filesystem", "params": ["path"]},
            {"tool": "file_permissions", "base_desc": "Set permissions {mode} on {path}", "server": "filesystem", "params": ["mode", "path"]},
            {"tool": "file_watch", "base_desc": "Watch for changes in {path}", "server": "filesystem", "params": ["path"]},
        ]
    
    def _get_code_analysis_tools(self) -> List[Dict]:
        """Code analysis tools."""
        return [
            {"tool": "code_analyze", "base_desc": "Analyze code quality of {file}", "server": "sonarqube", "params": ["file"]},
            {"tool": "code_lint", "base_desc": "Lint {file} for issues", "server": "sonarqube", "params": ["file"]},
            {"tool": "code_format", "base_desc": "Format code in {file}", "server": "sonarqube", "params": ["file"]},
            {"tool": "code_complexity", "base_desc": "Calculate complexity of {file}", "server": "sonarqube", "params": ["file"]},
            {"tool": "code_coverage", "base_desc": "Get test coverage for {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_duplicates", "base_desc": "Find duplicates in {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_security", "base_desc": "Scan {project} for security issues", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_smell", "base_desc": "Detect code smells in {file}", "server": "sonarqube", "params": ["file"]},
            {"tool": "code_metrics", "base_desc": "Get metrics for {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_hotspots", "base_desc": "Find security hotspots in {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_bugs", "base_desc": "Find bugs in {file}", "server": "sonarqube", "params": ["file"]},
            {"tool": "code_vulnerabilities", "base_desc": "Find vulnerabilities in {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_debt", "base_desc": "Calculate technical debt for {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_issues", "base_desc": "Get all issues for {project}", "server": "sonarqube", "params": ["project"]},
            {"tool": "code_quality_gate", "base_desc": "Check quality gate for {project}", "server": "sonarqube", "params": ["project"]},
        ]
    
    def _generate_variations(self, tool: Dict, category: str, count: int = 100) -> List[Dict]:
        """Generate variations for a single tool."""
        examples = []
        
        base_desc = tool["base_desc"]
        tool_name = tool["tool"]
        server = tool["server"]
        
        # Generate different description variations
        action_verbs = ["Use", "Execute", "Run", "Perform", "Invoke", "Call", "Trigger", "Apply"]
        contexts = [
            "for automation", "programmatically", "via MCP", "through the server",
            "for testing", "in production", "for development", "automatically"
        ]
        
        for i in range(count):
            action = random.choice(action_verbs)
            context = random.choice(contexts)
            desc = base_desc
            
            # Use a dictionary for cleaner replacement
            replacements = {
                "{url}": lambda: f"https://{random.choice(self.variations['websites'])}",
                "{selector}": lambda: random.choice([f"#btn-{i}", f".class-{i}", f"button[data-id='{i}']", f"//div[@id='{i}']"]),
                "{text}": lambda: f"Sample text variation {i}",
                "{app_name}": lambda: random.choice(self.variations['apps']),
                "{command}": lambda: random.choice([f"ls -la", f"echo 'test {i}'", f"cat file_{i}.txt", f"grep -r 'pattern' ."]),
                "{x}": lambda: str(random.randint(0, 1920)),
                "{y}": lambda: str(random.randint(0, 1080)),
                "{key}": lambda: random.choice(["enter", "tab", "escape", "space", "backspace", "delete"]),
                "{keys}": lambda: random.choice(["cmd+c", "cmd+v", "cmd+z", "cmd+s", "cmd+shift+p", "ctrl+alt+t"]),
                "{path}": lambda: random.choice([f"/Users/dev/file_{i}{random.choice(self.variations['file_types'])}" for _ in range(5)]),
                "{directory}": lambda: f"/Users/dev/project_{i}",
                "{data}": lambda: f"dataset_{i}",
                "{content}": lambda: f"content sample {i}",
                "{purpose}": lambda: random.choice(["pattern detection", "anomaly detection", "classification", "optimization"]),
                "{topic}": lambda: random.choice(["machine learning", "web development", "data science", "automation"]),
                "{language}": lambda: random.choice(["Spanish", "French", "German", "Japanese", "Chinese", "Ukrainian"]),
                "{file}": lambda: f"file_{i}{random.choice(self.variations['file_types'])}",
                "{project}": lambda: f"project_{i}"
            }

            for placeholder, func in replacements.items():
                if placeholder in desc:
                    desc = desc.replace(placeholder, func())
            
            # Replace remaining placeholders
            import re
            desc = re.sub(r'\{[^}]+\}', lambda m: f"value_{i}", desc)
            
            full_desc = f"{action} {tool_name}: {desc} {context}"
            
            example = {
                "tool": tool_name,
                "description": full_desc,
                "category": category,
                "server": server,
                "variation_id": i,
                "tags": [category, server, tool_name.split("_")[0]]
            }
            examples.append(example)
        
        return examples
    
    def generate_all_examples(self, variations_per_tool: int = 100) -> Dict[str, int]:
        """Generate all tool examples."""
        stats = {}
        
        for category, tools in self.tool_definitions.items():
            print(f"📦 Generating examples for category: {category}")
            
            all_examples = []
            for tool in tools:
                examples = self._generate_variations(tool, category, variations_per_tool)
                all_examples.extend(examples)
            
            # Save to file
            output_file = self.output_dir / f"{category}_examples.json"
            with open(output_file, 'w') as f:
                json.dump(all_examples, f, indent=2)
            
            stats[category] = len(all_examples)
            print(f"  ✅ Generated {len(all_examples)} examples for {category}")
        
        return stats
    
    def generate_combined_dataset(self) -> str:
        """Generate combined dataset for RAG."""
        all_examples = []
        
        for json_file in self.output_dir.glob("*_examples.json"):
            with open(json_file, 'r') as f:
                examples = json.load(f)
                all_examples.extend(examples)
        
        # Save combined dataset
        combined_file = self.output_dir / "all_examples_combined.json"
        with open(combined_file, 'w') as f:
            json.dump(all_examples, f, indent=2)
        
        return str(combined_file)


def main():
    """Main entry point."""
    print("🚀 Starting tool examples generation...")
    
    generator = ToolExamplesGenerator()
    
    # Generate 100 variations per tool = ~11,500 examples total
    # (20 browser + 20 system + 20 gui + 20 ai + 20 filesystem + 15 code_analysis) * 100
    stats = generator.generate_all_examples(variations_per_tool=100)
    
    # Generate combined dataset
    combined_path = generator.generate_combined_dataset()
    
    total = sum(stats.values())
    print(f"\n{'='*60}")
    print(f"GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total examples generated: {total:,}")
    print(f"\nBy category:")
    for category, count in stats.items():
        print(f"  - {category}: {count:,}")
    print(f"\nCombined dataset: {combined_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
