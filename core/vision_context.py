"""Vision Context Manager for Project Atlas

Enhanced visual context management with:
- Trend detection across frames
- Change region tracking
- Smart summarization
- Multi-monitor aware context
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ChangeRegion:
    """Represents a region of visual change."""
    x: int
    y: int
    width: int
    height: int
    area: float
    monitor_index: int = 0
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y, 
            "width": self.width, "height": self.height,
            "area": self.area, "monitor": self.monitor_index,
            "center": self.center
        }


@dataclass
class FrameAnalysis:
    """Complete analysis of a single frame."""
    timestamp: str
    change_percentage: float
    has_significant_changes: bool
    changed_regions: List[ChangeRegion]
    ocr_text: str
    ocr_status: str
    context_summary: str
    monitor_count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "change_percentage": self.change_percentage,
            "has_significant_changes": self.has_significant_changes,
            "changed_regions": [r.to_dict() for r in self.changed_regions],
            "ocr_text_preview": self.ocr_text[:100] if self.ocr_text else "",
            "ocr_status": self.ocr_status,
            "summary": self.context_summary,
            "monitor_count": self.monitor_count
        }


class VisionContextManager:
    """Manages visual context across multiple operations for Project Atlas.
    
    Enhanced with:
    - Trend detection (increasing/decreasing activity)
    - Change region tracking across frames
    - Smart summarization with context
    - Multi-monitor awareness
    """

    def __init__(self, max_history: int = 10):
        self.history: List[FrameAnalysis] = []
        self.max_history = max_history
        self.current_context = "No visual context available"
        
        # Trend tracking
        self._change_trend: List[float] = []
        self._max_trend_samples = 5
        
        # Active region tracking (regions that change frequently)
        self._active_regions: Dict[str, int] = {}  # region_key -> frequency
        
        # Monitor info
        self._monitor_count = 1

    def update_context(self, new_data: Dict[str, Any]) -> None:
        """Update context with new visual data from DifferentialVisionAnalyzer."""
        
        # Parse new data into FrameAnalysis
        diff = new_data.get("diff", {})
        ocr = new_data.get("ocr", {})
        
        # Extract change regions
        regions = []
        for r in diff.get("changed_regions", []):
            bbox = r.get("bbox", {})
            if bbox:
                regions.append(ChangeRegion(
                    x=bbox.get("x", 0),
                    y=bbox.get("y", 0),
                    width=bbox.get("width", 0),
                    height=bbox.get("height", 0),
                    area=r.get("area", 0),
                    monitor_index=r.get("monitor", 0)
                ))
        
        # Create frame analysis
        frame = FrameAnalysis(
            timestamp=new_data.get("timestamp", datetime.now().isoformat()),
            change_percentage=diff.get("global_change_percentage", 0),
            has_significant_changes=diff.get("has_significant_changes", False),
            changed_regions=regions,
            ocr_text=ocr.get("full_text", ""),
            ocr_status=ocr.get("status", "unknown"),
            context_summary=new_data.get("context", ""),
            monitor_count=diff.get("monitor_count", 1)
        )
        
        self.history.append(frame)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Update trend
        self._update_change_trend(frame.change_percentage)
        
        # Track active regions
        self._track_active_regions(regions)
        
        # Generate new human-readable summary
        self.current_context = self._generate_summary()

    def _update_change_trend(self, change_pct: float) -> None:
        """Track change percentage trend."""
        self._change_trend.append(change_pct)
        if len(self._change_trend) > self._max_trend_samples:
            self._change_trend.pop(0)

    def _track_active_regions(self, regions: List[ChangeRegion]) -> None:
        """Track regions that change frequently."""
        for r in regions:
            # Create region key based on approximate location (grid-based)
            grid_x = r.x // 100
            grid_y = r.y // 100
            key = f"{grid_x}_{grid_y}"
            self._active_regions[key] = self._active_regions.get(key, 0) + 1
        
        # Decay old regions
        keys_to_remove = []
        for key in self._active_regions:
            self._active_regions[key] -= 0.1
            if self._active_regions[key] <= 0:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._active_regions[key]

    def get_trend(self) -> str:
        """Get the current change trend: 'increasing', 'decreasing', 'stable'."""
        if len(self._change_trend) < 2:
            return "unknown"
        
        avg_first = sum(self._change_trend[:len(self._change_trend)//2]) / max(1, len(self._change_trend)//2)
        avg_second = sum(self._change_trend[len(self._change_trend)//2:]) / max(1, len(self._change_trend) - len(self._change_trend)//2)
        
        diff = avg_second - avg_first
        if diff > 2:
            return "increasing"
        elif diff < -2:
            return "decreasing"
        return "stable"

    def get_most_active_regions(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get the most frequently changing regions."""
        sorted_regions = sorted(
            self._active_regions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"grid_location": k, "frequency_score": v}
            for k, v in sorted_regions
        ]

    def _generate_summary(self) -> str:
        """Generate a concise context summary with trend info."""
        if not self.history:
            return "No visual context available"

        recent = self.history[-1]
        summary_parts = []
        
        # Timestamp
        ts = datetime.fromisoformat(recent.timestamp).strftime("%H:%M:%S")
        summary_parts.append(f"[{ts}]")

        # Change info with trend
        trend = self.get_trend()
        if recent.has_significant_changes:
            regions = len(recent.changed_regions)
            summary_parts.append(f"Changes: {recent.change_percentage:.1f}% ({regions} regions, trend: {trend})")
        else:
            summary_parts.append(f"Stable: {recent.change_percentage:.1f}% (trend: {trend})")

        # Multi-monitor info
        if recent.monitor_count > 1:
            summary_parts.append(f"Monitors: {recent.monitor_count}")

        # OCR info
        if recent.ocr_status == "success" and recent.ocr_text:
            text_snippet = recent.ocr_text[:40].replace("\n", " ").strip()
            if text_snippet:
                summary_parts.append(f"Text: '{text_snippet}...'")

        # Active regions hint
        active = self.get_most_active_regions(1)
        if active:
            summary_parts.append(f"Hot zone: {active[0]['grid_location']}")

        return " | ".join(summary_parts)

    def get_context_for_api(self) -> Dict[str, Any]:
        """Get context data formatted for LLM API transmission."""
        return {
            "history_summary": [
                frame.to_dict() 
                for frame in self.history[-5:]
            ],
            "current_context": self.current_context,
            "analysis_count": len(self.history),
            "trend": self.get_trend(),
            "active_regions": self.get_most_active_regions(3),
            "monitor_count": self._monitor_count
        }

    def get_diff_summary_for_step(self, step_index: int = -1) -> str:
        """Get a diff summary formatted for a specific step verification."""
        if not self.history:
            return "No visual data available for verification."
        
        try:
            frame = self.history[step_index]
        except IndexError:
            frame = self.history[-1]
        
        parts = [f"Visual verification at {frame.timestamp}:"]
        
        if frame.has_significant_changes:
            parts.append(f"✓ Screen changed ({frame.change_percentage:.1f}%)")
            parts.append(f"  - {len(frame.changed_regions)} regions modified")
            if frame.changed_regions:
                largest = max(frame.changed_regions, key=lambda r: r.area)
                parts.append(f"  - Largest change at ({largest.x}, {largest.y})")
        else:
            parts.append(f"⚠ Minimal screen change ({frame.change_percentage:.1f}%)")
            parts.append("  - Action may not have had visible effect")
        
        if frame.ocr_text:
            parts.append(f"  - Visible text: \"{frame.ocr_text[:50]}...\"")
        
        return "\n".join(parts)

    def clear(self) -> None:
        """Reset the vision context."""
        self.history = []
        self.current_context = "No visual context available"
        self._change_trend = []
        self._active_regions = {}

    def set_monitor_count(self, count: int) -> None:
        """Update the known monitor count."""
        self._monitor_count = count

