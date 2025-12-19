from typing import List, Dict, Any, Optional
import json
import logging

class AdaptiveVerifier:
    """
    Handles the 'Smart Plan Optimization' and 'Dynamic Granularity' logic.
    """
    
    def __init__(self, llm):
        self.llm = llm
        self.logger = logging.getLogger("system_cli.verifier")

    def optimize_plan(self, raw_plan: List[Dict[str, Any]], meta_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Analyzes a raw execution plan using LLM to insert 'VERIFY' steps dynamically.
        Ensures mandatory verification after critical steps, respecting the 'verification_rigor' policy.
        """
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.messages import SystemMessage, HumanMessage
        import json
        import re

        rigor = (meta_config or {}).get("verification_rigor", "medium")
        
        VERIFIER_PROMPT = f"""Ти — Grisha, агент безпеки та верифікації.
Твоє завдання: Проаналізувати план дій та вставити кроки перевірки (VERIFY).

ПОЛІТИКА ВЕРИФІКАЦІЇ (Rigor: {rigor}):
- Якщо rigor="high": Вставляй VERIFY після КОЖНОГО кроку без винятку.
- Якщо rigor="medium": Вставляй VERIFY після критичних кроків (файли, shell, GUI, git).
- Якщо rigor="low": Вставляй VERIFY тільки один раз у самому кінці плану.

Формат VERIFY кроку:
{{"type": "verify", "description": "Перевірити, що [результат дії]"}}

Вхідний план:
{{plan_json}}

Поверни повний оновлений JSON список кроків (оригінальні кроки + вставлені VERIFY кроки).
"""

        content = ""
        
        try:
            plan_json = json.dumps(raw_plan, ensure_ascii=False)
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=VERIFIER_PROMPT.format(plan_json=plan_json)),
                HumanMessage(content=f"Оптимізуй план згідно з політикою Rigor: {rigor}")
            ])
            
            response = self.llm.invoke(prompt.format_messages())
            content = response.content
            
            # Use improved extraction logic
            def extract_json(text):
                if not text: return None
                s = text.strip()
                try: return json.loads(s)
                except: pass
                
                # Match balanced or largest block
                # First try the whole thing without markdown
                s_clean = s.replace("```json", "").replace("```", "").strip()
                try: return json.loads(s_clean)
                except: pass
                
                # Regex fallback
                match = re.search(r"(\{.*\}|\[.*\])", s_clean, re.DOTALL)
                if match:
                    try: return json.loads(match.group(0))
                    except: pass
                    
                match = re.search(r"(\{.*?\}|\[.*?\])", s_clean, re.DOTALL)
                if match:
                    try: return json.loads(match.group(0))
                    except: pass
                return None

            optimized_raw = extract_json(content)
            
            if optimized_raw is None:
                self.logger.warning(f"[Verifier] No valid JSON found in response.")
                raise ValueError("No JSON found")
                
            # Handle if LLM returned an object instead of a list
            optimized = []
            if isinstance(optimized_raw, list):
                optimized = optimized_raw
            elif isinstance(optimized_raw, dict):
                optimized = optimized_raw.get("steps") or optimized_raw.get("plan") or []
            else:
                raise ValueError(f"Unexpected optimized plan type: {type(optimized_raw)}")

            # Safety check: ensure it's a list of dicts
            clean_optimized = []
            for item in optimized:
                if isinstance(item, dict):
                    clean_optimized.append(item)
                elif isinstance(item, str):
                    # Convert string step to dict step
                    clean_optimized.append({"type": "execute", "description": item})
                else:
                    self.logger.warning(f"[Verifier] Skipping invalid item in optimized plan: {item}")

            # If the optimizer removed steps or returned empty (and raw wasn't), treat as failure
            if len(clean_optimized) < len(raw_plan) and len(raw_plan) > 0:
                 self.logger.warning(f"[Verifier] Optimization reduced step count ({len(raw_plan)} -> {len(clean_optimized)}). Use raw plan fallback.")
                 raise ValueError("Optimized plan unexpectedly shorter than raw plan")

            # Fallback: if LLM didn't add verify steps, add them manually
            enhanced = self._ensure_verify_steps(clean_optimized, rigor=rigor)
            self.logger.debug(
                f"[Verifier] Plan optimized (Rigor: {rigor}): {len(raw_plan)} → {len(enhanced)} steps"
            )
            return enhanced
                
        except Exception as e:
            self.logger.warning(f"[Verifier] LLM JSON parsing/optimization error: {e}")
            self.logger.debug(f"[Verifier] Raw response snippet: {str(content)[:200]}...")
            # Fallback: ensure verify steps manually
            enhanced = self._ensure_verify_steps(raw_plan, rigor=rigor)
            self.logger.debug(
                f"[Verifier] Plan fallback: {len(raw_plan)} → {len(enhanced)} steps (added {len(enhanced) - len(raw_plan)} verify steps)"
            )
            return enhanced
    
    def _ensure_verify_steps(self, plan: List[Dict[str, Any]], rigor: str = "medium") -> List[Dict[str, Any]]:
        """
        Fallback: manually ensure verify steps according to rigor.
        """
        if rigor == "low":
            # Only ensure one verify at the very end
            if not plan:
                return []
            if plan[-1].get("type") == "verify":
                return plan
            return plan + [{"type": "verify", "description": "Фінальна перевірка результату задачі"}]

        critical_keywords = [
            "create", "delete", "remove", "git", "commit", "push", "pull",
            "shell", "run", "execute", "sudo", "write", "copy", "click", "type", "press"
        ]
        
        enhanced_plan = []
        for i, step in enumerate(plan):
            enhanced_plan.append(step)
            
            step_type = step.get("type", "execute").lower()
            description = step.get("description", "").lower()
            
            if step_type != "execute":
                continue
                
            is_critical = any(kw in description for kw in critical_keywords)
            
            # Decide if we need to add verify
            need_verify = (rigor == "high") or (rigor == "medium" and is_critical)
            
            if need_verify:
                # Check if next step is already verify
                next_is_verify = False
                if i + 1 < len(plan):
                    next_is_verify = plan[i+1].get("type") == "verify"
                
                if not next_is_verify:
                    verify_step = {
                        "type": "verify",
                        "description": f"Перевірити результат: {step.get('description', 'дії')}"
                    }
                    enhanced_plan.append(verify_step)
        
        return enhanced_plan

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
            self.logger.warning(f"[Verifier] Diff calculation error: {e}")
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
