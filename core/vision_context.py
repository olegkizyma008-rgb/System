import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class VisionContextManager:
    """Manages visual context across multiple operations for Project Atlas"""

    def __init__(self, max_history: int = 10):
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.current_context = "No visual context available"

    def update_context(self, new_data: Dict[str, Any]) -> None:
        """Update context with new visual data from DifferentialVisionAnalyzer"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "data": new_data
        }
        self.history.append(entry)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Generate new human-readable summary
        self.current_context = self._generate_summary()

    def _generate_summary(self) -> str:
        """Generate a concise context summary from history"""
        if not self.history:
            return "No visual context available"

        # Get most recent analysis
        recent = self.history[-1]["data"]
        
        summary_parts = []
        
        # Add timestamp info
        ts = datetime.fromisoformat(self.history[-1]["timestamp"]).strftime("%H:%M:%S")
        summary_parts.append(f"Last analysis at {ts}")

        # Add visual change info if available
        diff = recent.get("diff", {})
        if diff:
            change_pct = diff.get("global_change_percentage", 0)
            if diff.get("has_significant_changes"):
                regions = len(diff.get("changed_regions", []))
                summary_parts.append(f"Significant changes ({change_pct:.1f}%, {regions} regions)")
            else:
                summary_parts.append(f"Minimal changes ({change_pct:.1f}%)")

        # Add OCR info if available
        ocr = recent.get("ocr", {})
        if ocr.get("status") == "success":
            text_snippet = ocr.get("full_text", "")[:50].replace("\n", " ").strip()
            if text_snippet:
                summary_parts.append(f"Text detected: '{text_snippet}...'")

        return ". ".join(summary_parts) + "."

    def get_context_for_api(self) -> Dict[str, Any]:
        """Get context data formatted for LLM API transmission"""
        # We send a slice of history to the LLM to provide temporal context
        # without overwhelming the token limit.
        return {
            "history_summary": [
                {
                    "timestamp": h["timestamp"],
                    "summary": h["data"].get("context", "No summary available")
                } 
                for h in self.history[-5:]
            ],
            "current_context": self.current_context,
            "analysis_count": len(self.history)
        }

    def clear(self):
        """Reset the vision context"""
        self.history = []
        self.current_context = "No visual context available"
