from typing import List, Dict, Any, Optional
import json

class AdaptiveVerifier:
    """
    Handles the 'Smart Plan Optimization' and 'Dynamic Granularity' logic.
    """
    
    def __init__(self, llm):
        self.llm = llm

    def optimize_plan(self, raw_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes a raw execution plan (list of steps) and inserts 'VERIFY' steps
        at critical junctions ("Critical Path Analysis").
        """
        optimized_plan = []
        
        for i, step in enumerate(raw_plan):
            optimized_plan.append(step)
            
            # Simple heuristic for now - real logic would use LLM to analyze context
            action_type = step.get("type", "").lower()
            description = step.get("description", "").lower()
            
            needs_verification = False
            verify_type = "instrumental" # default
            
            # Heuristic Rules based on TZ 6.5
            if "browser" in action_type or "open url" in description:
                needs_verification = True
                verify_type = "visual" # Browser usually needs vision
            elif "click" in description or "select" in description:
                 # Interaction often needs check
                 needs_verification = True
                 verify_type = "visual"
            elif "write" in action_type or "save" in description:
                needs_verification = True
                verify_type = "instrumental" # File check
            elif "calc" in description or "math" in description:
                needs_verification = True
                verify_type = "visual_diff" # Check result change
                
            if needs_verification:
                optimized_plan.append({
                    "type": "verify",
                    "method": verify_type,
                    "target_step_id": step.get("id"),
                    "description": f"Verify success of: {description}"
                })
                
        return optimized_plan

    def get_diff_strategy(self, current_state: Any, previous_state: Any) -> float:
        """
        Calculates a 'diff score' to determine if a significant change happened.
        For vision, this would compare image hashes or use a VLM to say 'what changed?'.
        Returns 0.0 (no change) to 1.0 (major change).
        """
        # Placeholder for Vision Diff Logic
        return 1.0 

    def replan_on_failure(self, failed_step: Dict[str, Any], context: str) -> List[Dict[str, Any]]:
        """
        Generates a high-granularity recovery plan for a failed step.
        """
        # This would invoke the LLM (Atlas) to 'zoom in' on the problem
        # For now, return a retry stub
        return [
            {"type": "diagnose", "description": f"Check why {failed_step['description']} failed"},
            {"type": "retry", "description": f"Retry {failed_step['description']} with explicit dwell time"},
            {"type": "verify", "method": "visual", "description": "Verify retry success"}
        ]
