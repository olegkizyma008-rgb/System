import sys
import os
import re

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.constants import SUCCESS_MARKERS, FAILURE_MARKERS, NEGATION_PATTERNS

def check_verdict(content, lang="en"):
    """Logic captured from trinity.py for testing."""
    lower_content = content.lower()
    
    # 1. Explicit Fail
    if any(f"[{m}]" in lower_content or m in lower_content for m in FAILURE_MARKERS):
        return "failed"
        
    # 2. Explicit Complete
    if any(f"[{m}]" in lower_content or m in lower_content for m in SUCCESS_MARKERS):
        is_negated = _check_for_negation(lower_content, lang)
        return "success" if not is_negated else "failed"
        
    return "uncertain"


def _check_for_negation(lower_content: str, lang: str) -> bool:
    """Check if success markers are preceded by negation patterns."""
    lang_negations = NEGATION_PATTERNS.get(lang, NEGATION_PATTERNS["en"])
    
    for kw in SUCCESS_MARKERS:
        if kw not in lower_content:
            continue
            
        for match in re.finditer(re.escape(kw), lower_content):
            idx = match.start()
            pre_text = lower_content[max(0, idx-25):idx]
            if re.search(lang_negations, pre_text):
                return True
    return False


def run_test_case(content, lang, expected):
    """Run a single test case and return success."""
    actual = check_verdict(content, lang)
    if actual == expected:
        print(f"✅ PASSED: '{content}' ({lang}) -> {actual}")
        return True
    
    print(f"❌ FAILED: '{content}' ({lang}) -> Expected {expected}, got {actual}")
    return False


def test_negation_logic():
    print("🧪 Testing Negation Logic...")
    
    test_cases = [
        # English
        ("The task is [VERIFIED]", "en", "success"),
        ("The task is NOT [VERIFIED]", "en", "failed"),
        ("I was unable to reach the [SUCCESS] state", "en", "failed"),
        ("The goal is [FAILED]", "en", "failed"),
        
        # Ukrainian
        ("Завдання [ВИКОНАНО]", "uk", "success"),
        ("Завдання НЕ [ВИКОНАНО]", "uk", "failed"),
        ("На жаль, робота не [ГОТОВА]", "uk", "failed"),
        ("Сталася [ПОМИЛКА]", "uk", "failed"),
        
        # Edge cases
        ("It is done, but not quite [VERIFIED] yet", "en", "failed"),
        ("I [CONFIRMED] that it failed", "en", "failed"),
    ]
    
    passed_count = sum(1 for c, l, e in test_cases if run_test_case(c, l, e))
    
    print(f"\n📊 Result: {passed_count}/{len(test_cases)} passed.")
    return passed_count == len(test_cases)

if __name__ == "__main__":
    test_negation_logic()
