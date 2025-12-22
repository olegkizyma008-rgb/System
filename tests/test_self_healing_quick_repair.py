import os
import subprocess
from core.self_healing import CodeSelfHealer


def test_quick_repair_name_error(tmp_path):
    proj = tmp_path / 'proj'
    proj.mkdir()
    file = proj / 'some_module.py'
    file.write_text('print(context)\n')

    # create a log that contains a NameError with file and line
    log = tmp_path / 'cli.log'
    log.write_text(f'Traceback (most recent call last):\n  File "{file}", line 1, in <module>\n    print(context)\nNameError: name "context" is not defined\n')

    sh = CodeSelfHealer(project_root=str(proj), log_path=str(log))
    issues = sh.detect_errors()
    assert len(issues) >= 1
    issue = issues[0]
    assert "context" in issue.message.lower() or "name 'context'" in issue.message.lower()

    ok = sh.quick_repair('name_error', issue.file_path, issue.message, issue.line_number)
    # quick_repair should try to replace 'context' with a safe expression
    assert ok is True
    content = file.read_text()
    assert 'state.get("messages"' in content or 'state.get(\"messages\"' in content
