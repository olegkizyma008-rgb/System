import io
import sys
import io
import sys
import pytest
from core.vibe_assistant import VibeCLIAssistant


def test_display_pause_with_diagnostics(capsys):
    v = VibeCLIAssistant()
    diag = {
        'files': ['cleanup_scripts/advanced_antigraviti_cleanup.sh'],
        'diffs': [
            {'file': 'cleanup_scripts/advanced_antigraviti_cleanup.sh', 'diff': "@@ -1,3 +1,4 @@\n-OLD\n+NEW\n+ADDED\n"}
        ],
        'stack_trace': 'Traceback (most recent call last):\n  File "foo.py", line 10, in <module>\nNameError: name "context" is not defined'
    }

    pause_context = {
        'reason': 'doctor_vibe_dev',
        'message': 'Manual dev intervention required',
        'diagnostics': diag
    }

    v.handle_pause_request(pause_context)
    captured = capsys.readouterr()
    out = captured.out
    assert '🚨 Doctor Vibe' in out
    assert 'Діагностика' in out
    assert 'cleanup_scripts/advanced_antigraviti_cleanup.sh' in out
    assert 'Diff preview' in out
    assert 'Stack trace' in out