# Automatic Response Saving Workflow

## Overview
This system automatically saves Cascade responses and creates git commits with project structure updates.

## Workflow

### Step 1: Cascade Response
When Cascade (me) completes important work (code changes, analysis, debugging), I should:

```bash
./auto_commit.sh "My complete response text here"
```

### Step 2: Automatic Process
The `auto_commit.sh` script will:

1. **Save response** → `.last_response.txt`
   - Preserves format: `## My Last Response` + previous Trinity Reports
   
2. **Create commit** → `git commit -m "Update: Add latest response"`
   
3. **Post-commit hook** (automatic):
   - Reads `.last_response.txt`
   - Runs `generate_structure.py`
   - Generates `project_structure_final.txt`
   - Amends the commit to include structure

### Step 3: Result
Final commit contains:
- `.last_response.txt` - Latest response + history
- `project_structure_final.txt` - Full project snapshot with:
  - Last response
  - Git diff (recent changes)
  - Git log (commit history)
  - Directory tree
  - File contents

## Files Involved

| File | Purpose |
|------|---------|
| `auto_commit.sh` | Main script - saves response and creates commit |
| `save_response.sh` | Helper - handles response formatting and history |
| `generate_structure.py` | Generates full project structure |
| `.git/hooks/post-commit` | Automatic post-commit regeneration |

## When to Use

**Use `auto_commit.sh` after:**
- ✅ Code changes/implementations
- ✅ Analysis/debugging sessions
- ✅ File modifications
- ✅ Completed tasks

**Skip for:**
- ❌ Simple "ok", "done", "understood"
- ❌ Quick clarifications
- ❌ Questions without action

## Example Usage

```bash
# After implementing a feature
./auto_commit.sh "Implemented user authentication with JWT tokens. Added login/logout endpoints, password hashing with bcrypt, and token refresh mechanism. Tests passing."

# After debugging
./auto_commit.sh "Fixed memory leak in event listener. Issue was event handlers not being removed on component unmount. Added cleanup in useEffect."

# After analysis
./auto_commit.sh "Analyzed performance bottleneck. Root cause: N+1 queries in user profile endpoint. Implemented query batching, reduced response time from 2s to 200ms."
```

## Safety Features

1. **Infinite Loop Prevention**: Post-commit hook checks `TRINITY_POST_COMMIT_RUNNING` flag
2. **Error Handling**: Script continues even if structure generation fails
3. **Git Safety**: Only commits if there are actual changes
4. **History Preservation**: Previous responses are kept in file

## Troubleshooting

**Commit not created?**
- Check if `.last_response.txt` exists
- Verify git is initialized: `git status`

**Structure not regenerating?**
- Check post-commit hook is executable: `ls -la .git/hooks/post-commit`
- Verify `generate_structure.py` works: `python3 generate_structure.py`

**Too many commits?**
- This is expected - each response = one commit
- Provides detailed development history
- Can be squashed later if needed
