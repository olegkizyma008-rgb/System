# Trinity Continual Development Project

This project was bootstrapped with Trinity's automatic continual development setup.

## Quick Start

1. **Open in Windsurf or your IDE**
   ```bash
   cd <project_name>
   ```

2. **Install dependencies (if needed)**
   ```bash
   pip install -r requirements.txt  # if Python project
   npm install                       # if Node project
   ```

3. **Start development**
   - Make changes to your code
   - Commit your changes: `git commit -m "Your message"`
   - `project_structure_final.txt` will be automatically updated

## Automatic Features

### Project Structure Tracking
- `project_structure_final.txt` is automatically regenerated after each commit
- Contains:
  - Last response/summary
  - Git diff (recent changes)
  - Git log (commit history)
  - Directory tree
  - File contents

### Continual Development Context
- Each commit updates the project snapshot
- Full development history is preserved
- Easy to track what changed and why

### Git Hooks
- Post-commit hook automatically updates `project_structure_final.txt`
- Prevents infinite loops with safety checks
- Works seamlessly with Windsurf and other IDEs

## Helper Scripts

### `regenerate_structure.sh`
Manually regenerate project structure:
```bash
./regenerate_structure.sh "Your last response or summary"
```

### `save_response_and_commit.py`
Save a response and regenerate structure:
```bash
python3 save_response_and_commit.py "Your response text"
```

### `generate_structure.py`
Generate project structure from scratch:
```bash
python3 generate_structure.py
```

## Configuration

Edit `.env` file to customize:
- `TRINITY_RECURSION_LIMIT` - Max recursion depth
- `TRINITY_VERBOSE` - Enable verbose logging
- Project-specific settings

## Tips

1. **Keep commits atomic** - One feature per commit for better tracking
2. **Use meaningful commit messages** - They appear in the structure file
3. **Check `project_structure_final.txt`** - It's your project's living documentation
4. **Leverage git hooks** - They work automatically, no manual steps needed

## Troubleshooting

### Structure not updating?
- Check if `.last_response.txt` exists
- Verify post-commit hook is executable: `chmod +x .git/hooks/post-commit`
- Run manually: `./regenerate_structure.sh "Your message"`

### Git hook issues?
- Ensure you're in a git repository: `git status`
- Check hook permissions: `ls -la .git/hooks/post-commit`
- View hook output: `git commit -m "test" --verbose`

## Learn More

For Trinity documentation and advanced features, see the main System repository.
