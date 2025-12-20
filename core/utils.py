import json
import re
from typing import Any, Optional

def extract_json_object(text: str) -> Any:
    """
    Helper to extract any JSON object or list from a string.
    Robustly handles markdown code blocks, trailing text, and malformed inputs.
    """
    if not text:
        return None
    s = str(text).strip()
    
    # Try direct JSON first.
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try cleaning markdown code blocks
    s_clean = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s_clean = re.sub(r"\s*```$", "", s_clean, flags=re.IGNORECASE | re.MULTILINE)
    s_clean = s_clean.strip()
    
    try:
        return json.loads(s_clean)
    except Exception:
        pass

    # Try handling Python dict syntax (single quotes) - common LLM mistake
    try: 
        import ast
        return ast.literal_eval(s_clean)
    except Exception: 
        pass

    # Search for first JSON object {} or list []
    # We search for the first occurrence of { or [
    start_brace = s.find('{')
    start_bracket = s.find('[')
    
    if start_brace == -1 and start_bracket == -1:
        return None
        
    start_idx = -1
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start_idx = start_brace
    else:
        start_idx = start_bracket
        
    candidate = s[start_idx:]
    
    # Optimization: Try full candidate first
    try:
        return json.loads(candidate)
    except Exception:
        pass
        
    # Optimization: Try regex to find the matching closing brace/bracket
    # This is heuristics based, not a full parser, but faster than iterative slicing
    try:
        if candidate.startswith('{'):
            # Simple balanced brace counter
            count = 0
            for i, char in enumerate(candidate):
                if char == '{': count += 1
                elif char == '}': count -= 1
                if count == 0:
                    return json.loads(candidate[:i+1])
        elif candidate.startswith('['):
            count = 0
            for i, char in enumerate(candidate):
                if char == '[': count += 1
                elif char == ']': count -= 1
                if count == 0:
                    return json.loads(candidate[:i+1])
    except Exception:
        pass

    # Fallback to iterative trimming from the end if regex failed
    for i in range(len(candidate), 0, -1):
        try:
            # Potential optimization: only try if candidate[i-1] is } or ]
            char = candidate[i-1]
            if char not in ['}', ']']:
                continue
            return json.loads(candidate[:i])
        except Exception:
            pass
            
    return None
