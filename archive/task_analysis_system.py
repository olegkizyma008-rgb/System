#!/usr/bin/env python3

"""
Task Analysis System

This system helps execute tasks, capture logs, analyze screenshots,
and identify issues for code improvement.
"""

import os
import shutil
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('task_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TaskAnalyzer:
    """
    Task Analysis System
    
    Features:
    - Execute tasks with full logging
    - Capture screenshots at key points
    - Analyze execution logs
    - Identify error patterns
    - Generate improvement recommendations
    """
    
    def __init__(self):
        self.task_history = []
        self.current_task = None
        self.screenshot_dir = "task_screenshots"
        self.log_dir = "task_logs"
        
        # Create directories
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize MCP integration for advanced analysis
        try:
            from system_ai.tools.mcp_integration import get_mcp_tool
            self.mcp_tool = get_mcp_tool()
            self.mcp_available = self.mcp_tool.is_available()
        except Exception as e:
            logger.warning(f"MCP integration not available: {e}")
            self.mcp_tool = None
            self.mcp_available = False
    
    def start_task_analysis(self, task_name: str, task_description: str) -> Dict[str, Any]:
        """Start analyzing a new task"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_task = {
            "task_id": task_id,
            "name": task_name,
            "description": task_description,
            "start_time": datetime.now().isoformat(),
            "status": "started",
            "logs": [],
            "screenshots": [],
            "errors": [],
            "metrics": {}
        }
        
        # Create task-specific log file
        task_log_path = os.path.join(self.log_dir, f"{task_id}.log")
        self.current_task["log_file"] = task_log_path
        
        # Add file handler for this specific task
        file_handler = logging.FileHandler(task_log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        logger.info(f"🚀 Starting task analysis: {task_name}")
        logger.info(f"Task ID: {task_id}")
        logger.info(f"Description: {task_description}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Task analysis started"
        }
    
    def log_task_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log a task event"""
        if not self.current_task:
            logger.warning("No active task to log to")
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        
        self.current_task["logs"].append(event)
        
        # Log to both file and console
        log_message = f"[{event_type.upper()}] {data.get('message', 'No message')}"
        
        if event_type == "error":
            logger.error(log_message)
            self.current_task["errors"].append(event)
        elif event_type == "warning":
            logger.warning(log_message)
        elif event_type == "info":
            logger.info(log_message)
        else:
            logger.debug(log_message)
    
    def capture_screenshot(self, description: str = "") -> Dict[str, Any]:
        """Capture a screenshot during task execution"""
        if not self.current_task:
            return {"success": False, "error": "No active task"}
        
        try:
            from system_ai.tools.screenshot import take_screenshot
            
            screenshot_id = f"screenshot_{len(self.current_task['screenshots']) + 1}"

            # Take screenshot using the system tool which returns a dict with status/path
            screenshot_result = take_screenshot()

            if screenshot_result.get("status") == "success" and screenshot_result.get("path"):
                source_path = screenshot_result["path"]
                # Mirror into task_screenshots with task-based filename, preserving extension
                ext = os.path.splitext(source_path)[1] or ".png"
                dest_path = os.path.join(
                    self.screenshot_dir,
                    f"{self.current_task['task_id']}_{screenshot_id}{ext}"
                )
                try:
                    shutil.copyfile(source_path, dest_path)
                    screenshot_path = dest_path
                except Exception:
                    # Fallback to original source path if copy fails
                    screenshot_path = source_path
                screenshot_info = {
                    "screenshot_id": screenshot_id,
                    "path": screenshot_path,
                    "source_path": source_path,
                    "timestamp": datetime.now().isoformat(),
                    "description": description
                }

                self.current_task["screenshots"].append(screenshot_info)

                logger.info(f"📸 Captured screenshot: {description}")

                return {
                    "success": True,
                    "screenshot_id": screenshot_id,
                    "path": screenshot_path
                }
            else:
                err_msg = screenshot_result.get("error") or "Unknown screenshot error"
                tb = screenshot_result.get("traceback")
                # Log with exception context if available
                if tb:
                    logger.error(f"Failed to capture screenshot: {err_msg}\n{tb}")
                else:
                    logger.error(f"Failed to capture screenshot: {err_msg}")

                # Record the error in the current task for later analysis
                try:
                    self.log_task_event("error", {"message": err_msg, "traceback": tb})
                except Exception:
                    logger.exception("Failed to record screenshot error in task")

                return {"success": False, "error": err_msg, "traceback": tb}
                
        except Exception as e:
            logger.error(f"Screenshot capture error: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_task_execution(self) -> Dict[str, Any]:
        """Analyze the completed task execution"""
        if not self.current_task:
            return {"success": False, "error": "No task to analyze"}
        
        # Mark task end and dynamic status
        self.current_task["end_time"] = datetime.now().isoformat()
        error_count = len(self.current_task.get("errors", []))
        self.current_task["status"] = "failed" if error_count > 0 else "completed"
        
        # Calculate metrics
        start_time = datetime.fromisoformat(self.current_task["start_time"])
        end_time = datetime.fromisoformat(self.current_task["end_time"])
        duration = (end_time - start_time).total_seconds()
        
        self.current_task["metrics"] = {
            "duration_seconds": duration,
            "screenshot_count": len(self.current_task["screenshots"]),
            "error_count": len(self.current_task["errors"]),
            "log_count": len(self.current_task["logs"])
        }
        
        # Add to history
        self.task_history.append(self.current_task)
        
        # Generate analysis report
        report = self._generate_analysis_report()
        
        # Save task data
        self._save_task_data()
        
        # Save task_id before cleanup
        task_id = self.current_task["task_id"]

        # Clean up file handler for this task
        try:
            target_path = self.current_task.get("log_file")
            for h in logger.handlers[:]:
                try:
                    if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == target_path:
                        logger.removeHandler(h)
                        h.close()
                except Exception:
                    logger.exception("Failed to clean up task log handler")
        except Exception:
            logger.exception("Unexpected error during handler cleanup")

        # Clean up
        self.current_task = None
        
        return {
            "success": True,
            "report": report,
            "task_id": task_id
        }
    
    def _generate_analysis_report(self) -> Dict[str, Any]:
        """Generate a comprehensive analysis report"""
        task = self.current_task
        
        report = {
            "task_id": task["task_id"],
            "task_name": task["name"],
            "status": task["status"],
            "duration_seconds": task["metrics"]["duration_seconds"],
            "screenshot_count": task["metrics"]["screenshot_count"],
            "error_count": task["metrics"]["error_count"],
            "timeline": []
        }
        
        # Generate timeline from logs
        for log in task["logs"]:
            report["timeline"].append({
                "time": log["timestamp"],
                "type": log["type"],
                "message": log["data"].get("message", "")
            })
        
        # Add error analysis
        if task["errors"]:
            error_patterns = self._analyze_errors(task["errors"])
            report["error_analysis"] = error_patterns
        
        # Add recommendations
        recommendations = self._generate_recommendations(task)
        report["recommendations"] = recommendations
        
        return report
    
    def _analyze_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns"""
        analysis = {
            "total_errors": len(errors),
            "error_types": {},
            "common_patterns": []
        }
        
        for error in errors:
            error_type = error["data"].get("type", "unknown")
            error_message = error["data"].get("message", "").lower()
            
            # Count error types
            if error_type not in analysis["error_types"]:
                analysis["error_types"][error_type] = 0
            analysis["error_types"][error_type] += 1
            
            # Look for common patterns
            if "timeout" in error_message:
                analysis["common_patterns"].append("timeout_issue")
            elif "not found" in error_message:
                analysis["common_patterns"].append("element_not_found")
            elif "permission" in error_message:
                analysis["common_patterns"].append("permission_issue")
        
        # Remove duplicates from patterns
        analysis["common_patterns"] = list(set(analysis["common_patterns"]))
        
        return analysis
    
    def _generate_recommendations(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Analyze duration
        duration = task["metrics"]["duration_seconds"]
        if duration > 30:
            recommendations.append({
                "type": "performance",
                "suggestion": "Task took longer than expected. Consider optimizing steps or adding parallel execution.",
                "priority": "medium"
            })
        
        # Analyze errors
        error_count = task["metrics"]["error_count"]
        if error_count > 0:
            recommendations.append({
                "type": "error_handling",
                "suggestion": f"Task had {error_count} errors. Review error analysis and add specific handling.",
                "priority": "high"
            })
        
        # Analyze screenshots
        screenshot_count = task["metrics"]["screenshot_count"]
        if screenshot_count == 0:
            recommendations.append({
                "type": "monitoring",
                "suggestion": "No screenshots captured. Add screenshot capture at key steps for better debugging.",
                "priority": "low"
            })
        
        # MCP-specific recommendations if available
        if self.mcp_available and self.mcp_tool:
            try:
                # Run system diagnostics
                diagnostics = self.mcp_tool.diagnose_system()
                if diagnostics.get("success"):
                    mcp_diagnostics = diagnostics.get("diagnostics", {})
                    
                    # Check for system issues
                    if mcp_diagnostics.get("recommendations"):
                        for rec in mcp_diagnostics["recommendations"]:
                            recommendations.append({
                                "type": "system",
                                "suggestion": f"System issue detected: {rec['issue']}. Suggested: {rec['action']}",
                                "priority": rec.get("priority", "medium")
                            })
            except Exception as e:
                logger.warning(f"MCP diagnostics failed: {e}")
        
        return recommendations
    
    def _save_task_data(self) -> None:
        """Save task data to file"""
        if not self.current_task:
            return
        
        try:
            task_data_path = os.path.join(
                self.log_dir,
                f"{self.current_task['task_id']}_data.json"
            )
            
            with open(task_data_path, 'w') as f:
                json.dump(self.current_task, f, indent=2)
            
            logger.info(f"💾 Saved task data to {task_data_path}")
            
        except Exception as e:
            logger.error(f"Failed to save task data: {e}")
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """Get history of all analyzed tasks"""
        return self.task_history
    
    def get_task_report(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get report for a specific task"""
        for task in self.task_history:
            if task["task_id"] == task_id:
                return task
        return None


# Example Usage
if __name__ == "__main__":
    print("Task Analysis System - Example Usage")
    print("=" * 50)
    
    # Initialize the analyzer
    analyzer = TaskAnalyzer()
    
    # Start a task analysis
    analyzer.start_task_analysis(
        task_name="AI Movie Search",
        task_description="Find and play a modern AI movie in fullscreen"
    )
    
    # Simulate task execution with logging
    analyzer.log_task_event("info", {"message": "Starting Google search for AI movies"})
    analyzer.capture_screenshot("Google search results")
    
    analyzer.log_task_event("info", {"message": "Analyzing search results"})
    analyzer.capture_screenshot("Search results analysis")
    
    analyzer.log_task_event("info", {"message": "Opening movie page"})
    analyzer.capture_screenshot("Movie page loaded")
    
    analyzer.log_task_event("info", {"message": "Entering fullscreen mode"})
    analyzer.capture_screenshot("Fullscreen mode active")
    
    # Complete the analysis
    report = analyzer.analyze_task_execution()
    
    print(f"\n📊 Task Analysis Report:")
    print(f"Task: {report['task_name']}")
    print(f"Status: {report['status']}")
    print(f"Duration: {report['duration_seconds']:.1f} seconds")
    print(f"Screenshots: {report['screenshot_count']}")
    print(f"Errors: {report['error_count']}")
    
    print(f"\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"  - [{rec['priority'].upper()}] {rec['type']}: {rec['suggestion']}")
    
    print(f"\n🎉 Task analysis completed successfully!")