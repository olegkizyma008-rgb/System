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
        Analyzes a raw execution plan using LLM to insert 'VERIFY' steps dynamically.
        """
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.messages import SystemMessage, HumanMessage
        import json
        import re

        VERIFIER_PROMPT = """Ти — Grisha, агент безпеки та верифікації.
Твоє завдання: Проаналізувати план дій та вставити кроки перевірки (VERIFY) там, де це критично необхідно.

Критерії для вставки VERIFY:
1. Зміна стану системи (створення файлу, відкриття додатку, зміна налаштувань).
2. Критичні дії (видалення, відправка повідомлення).
3. Дії, результат яких не очевидний (клік по кнопці, пошук на сторінці).
4. НЕ потрібна перевірка для пасивних дій (прочитати, подумати).

Формат виводу: JSON список, де між кроками можуть бути вставлені об'єкти:
{{"type": "verify", "agent": "grisha", "description": "Перевірити, чи файл створено"}}

Вхідний план:
{plan_json}

Поверни ТІЛЬКИ JSON.
"""

        content = ""
        
        try:
            plan_json = json.dumps(raw_plan, ensure_ascii=False)
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=VERIFIER_PROMPT.format(plan_json=plan_json)),
                HumanMessage(content="Оптимізуй план, додавши перевірки.")
            ])
            
            response = self.llm.invoke(prompt.format_messages())
            content = response.content
            
            # Simple JSON cleanup
            content = content.replace("```json", "").replace("```", "").strip()
            
            # Extract JSON list [ ... ]
            import re
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                content = match.group(0)
                
            optimized = json.loads(content)
            if isinstance(optimized, list):
                return optimized
                
        except Exception as e:
            print(f"[Verifier] LLM JSON parsing error: {e}")
            print(f"[Verifier] Raw response: {content[:200]}...") # Debug log
            
        return raw_plan

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
