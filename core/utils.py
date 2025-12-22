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
    
    # Strategy 1: Direct JSON
    res = _try_direct_json(s)
    if res is not None: return res

    # Strategy 2: Clean Markdown
    s_clean = _clean_markdown_blocks(s)
    res = _try_direct_json(s_clean)
    if res is not None: return res

    # Strategy 3: Python literal eval (fallback for single quotes)
    res = _try_python_literal(s_clean)
    if res is not None: return res

    # Strategy 4: Find first brace/bracket and parse
    return _parse_first_json_match(s)


def _try_direct_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _clean_markdown_blocks(text: str) -> str:
    s = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"\s*```$", "", s, flags=re.IGNORECASE | re.MULTILINE)
    return s.strip()


def _try_python_literal(text: str) -> Any:
    try:
        import ast
        return ast.literal_eval(text)
    except Exception:
        return None


def _parse_first_json_match(s: str) -> Any:
    start_brace = s.find('{')
    start_bracket = s.find('[')
    
    if start_brace == -1 and start_bracket == -1:
        return None
        
    start_idx = start_brace if (start_bracket == -1 or (start_brace != -1 and start_brace < start_bracket)) else start_bracket
    candidate = s[start_idx:]
    
    # Try full candidate first
    res = _try_direct_json(candidate)
    if res is not None: return res
        
    # Balanced brace/bracket counting
    res = _try_balanced_parse(candidate)
    if res is not None: return res

    # Iterative end-trimming fallback
    return _try_iterative_trim(candidate)


def _try_balanced_parse(candidate: str) -> Any:
    try:
        char_start = candidate[0]
        char_end = '}' if char_start == '{' else ']' if char_start == '[' else None
        if not char_end: return None
        
        count = 0
        for i, char in enumerate(candidate):
            if char == char_start: count += 1
            elif char == char_end: count -= 1
            if count == 0:
                return json.loads(candidate[:i+1])
    except Exception:
        pass
    return None


def _try_iterative_trim(candidate: str) -> Any:
    for i in range(len(candidate), 0, -1):
        try:
            if candidate[i-1] not in ['}', ']']:
                continue
            return json.loads(candidate[:i])
        except Exception:
            pass
    return None
