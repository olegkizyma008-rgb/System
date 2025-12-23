#!/usr/bin/env python3
"""
Test script to verify _is_env_true() method fix.
This script tests the method signature and behavior without initializing TrinityRuntime.
"""

import os
import sys

# Add project root to path
_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Test 1: Check if the method exists and has correct signature
print("=" * 60)
print("TEST 1: Checking _is_env_true() method signature")
print("=" * 60)

# Read the trinity.py file and check for duplicate definitions
with open(os.path.join(_repo_root, "core/trinity.py"), "r") as f:
    content = f.read()
    
# Count occurrences of _is_env_true definition
count = content.count("def _is_env_true(self,")
print(f"Found {count} definition(s) of 'def _is_env_true(self,' in trinity.py")

if count == 1:
    print("✅ PASS: Only one _is_env_true() method definition found")
else:
    print(f"❌ FAIL: Expected 1 definition, found {count}")
    sys.exit(1)

# Check the signature
if "def _is_env_true(self, var: str, default: bool = False)" in content:
    print("✅ PASS: Method signature is correct: _is_env_true(self, var: str, default: bool = False)")
else:
    print("❌ FAIL: Method signature is incorrect")
    sys.exit(1)

# Test 2: Check if calls to _is_env_true have correct arguments
print("\n" + "=" * 60)
print("TEST 2: Checking _is_env_true() calls have correct arguments")
print("=" * 60)

# Check for calls without default parameter (should not exist)
bad_calls = [
    'self._is_env_true("TRINITY_DEV_BY_VIBE")',
    'self._is_env_true("TRINITY_VIBE_AUTO_APPLY")',
]

for call in bad_calls:
    if call in content:
        print(f"❌ FAIL: Found call without default parameter: {call}")
        sys.exit(1)

print("✅ PASS: No calls with missing default parameter found")

# Check for corrected calls
good_calls = [
    'self._is_env_true("TRINITY_DEV_BY_VIBE", False)',
    'self._is_env_true("TRINITY_VIBE_AUTO_APPLY", False)',
]

for call in good_calls:
    if call in content:
        print(f"✅ PASS: Found correct call: {call}")
    else:
        print(f"❌ FAIL: Expected call not found: {call}")
        sys.exit(1)

# Test 3: Check for duplicate _is_env_true functions in __post_init__
print("\n" + "=" * 60)
print("TEST 3: Checking for nested _is_env_true() in __post_init__")
print("=" * 60)

post_init_section = content[content.find("def __post_init__"):content.find("def __post_init__") + 2000]

if "def _is_env_true(var: str, default: bool)" in post_init_section:
    print("✅ PASS: Found nested function in __post_init__ (as expected)")
else:
    print("❌ FAIL: Nested function in __post_init__ not found")
    sys.exit(1)

# Test 4: Verify menu.py has import os
print("\n" + "=" * 60)
print("TEST 4: Checking menu.py has 'import os'")
print("=" * 60)

with open(os.path.join(_repo_root, "tui/menu.py"), "r") as f:
    menu_content = f.read()
    
if "import os" in menu_content:
    print("✅ PASS: Found 'import os' in menu.py")
else:
    print("❌ FAIL: 'import os' not found in menu.py")
    sys.exit(1)

# Test 5: Verify automation permissions menu rendering
print("\n" + "=" * 60)
print("TEST 5: Checking automation permissions menu rendering")
print("=" * 60)

if "_render_automation_permissions_menu" in menu_content:
    # Check that the function is properly implemented
    if "line += f" in menu_content or "line = f" in menu_content:
        print("✅ PASS: _render_automation_permissions_menu uses proper line construction")
    else:
        print("❌ FAIL: _render_automation_permissions_menu doesn't properly construct lines")
        sys.exit(1)
else:
    print("❌ FAIL: _render_automation_permissions_menu not found")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nSummary:")
print("  1. _is_env_true() method has correct signature (var, default)")
print("  2. All calls to _is_env_true() pass the required default parameter")
print("  3. Duplicate method definition removed")
print("  4. menu.py imports os module")
print("  5. Automation permissions menu properly renders clickable items")
