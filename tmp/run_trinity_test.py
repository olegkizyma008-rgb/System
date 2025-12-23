from core.trinity import TrinityRuntime
from langchain_core.messages import AIMessage
import os, subprocess, pathlib, shutil

os.environ['COPILOT_API_KEY'] = 'dummy'

tmp = pathlib.Path('/tmp/trinity_test_repo')
if tmp.exists():
    shutil.rmtree(tmp)
tmp.mkdir()
subprocess.run(['git','init'], cwd=str(tmp), check=True)
(tmp/'regenerate_structure.sh').write_text("#!/bin/bash\nset -e\necho 'structure' > project_structure_final.txt\n", encoding='utf-8')
(tmp/'regenerate_structure.sh').chmod(0o755)
(tmp/'some_change.txt').write_text('x', encoding='utf-8')

os.chdir(str(tmp))
rt = TrinityRuntime(verbose=True)
class _DummyWorkflow:
    def stream(self, _initial_state, config=None):
        yield {"atlas": {"messages": [AIMessage(content="ok")], "current_agent": "end", "task_status": "completed"}}
rt.workflow = _DummyWorkflow()
for e in rt.run("Make change to some_change.txt"):
    print('EVENT: ', e)

print('GIT LOG:')
subprocess.run(['git','log','--name-status','--pretty=format:%H %s','-n','10'], cwd=str(tmp))
print('LAST COMMIT SHOW:')
subprocess.run(['git','show','--name-only','--pretty=format:','HEAD'], cwd=str(tmp))
print('GIT STATUS AFTER RUN:')
print(subprocess.run(['git','status','--porcelain'], cwd=str(tmp), capture_output=True, text=True).stdout)
