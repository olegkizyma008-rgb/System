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

    def get_diff_strategy(self, current_image_path: str, previous_image_path: str) -> float:
        """
        Calculates a 'diff score' (0.0 to 1.0) between two images to determine significant change.
        Returns 0.0 (identical) to 1.0 (completely different).
        Uses local Pillow-based optimization to save LLM tokens.
        """
        if not current_image_path or not previous_image_path:
            return 1.0 # Force check if missing images
            
        try:
            from PIL import Image, ImageChops
            import math
            import operator
            from functools import reduce

            img1 = Image.open(current_image_path).convert('RGB')
            img2 = Image.open(previous_image_path).convert('RGB')

            # Ensure same size for comparison
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)

            # 1. Fast Histogram Difference
            h1 = img1.histogram()
            h2 = img2.histogram()
            
            # RMS (Root Mean Square) difference of histograms
            diff = math.sqrt(reduce(operator.add,
                map(lambda a,b: (a-b)**2, h1, h2))/len(h1))
            
            # Normalize reasonably (assuming max diff is fairly large)
            # This is a heuristic. A score > 0.05 usually means visibility changed.
            # We map it to 0-1 range roughly.
            normalized_score = min(diff / 1000.0, 1.0)
            
            return normalized_score

        except Exception as e:
            # If local diff fails, assume change (safety fallback)
            print(f"[Verifier] Diff calculation error: {e}")
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
