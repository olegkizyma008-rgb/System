#!/bin/bash

# Generate project_structure_final.txt with all necessary data
# Includes: directory tree, last response, task logs, git info, editor integration info

OUTPUT_FILE="project_structure_final.txt"

# Generate using Python for better data integration
python3 << 'PYTHON_EOF'
import os
import subprocess
from pathlib import Path
from datetime import datetime
import sys

def get_last_response():
    """Отримати останню відповідь від агента"""
    try:
        if Path(".last_response.txt").exists():
            with open(".last_response.txt", 'r', encoding='utf-8') as f:
                content = f.read()
                # Обмежимо розмір до 500 символів
                if len(content) > 500:
                    return content[:500] + "\n[...скорочено...]"
                return content
    except Exception as e:
        return f"[Помилка читання: {e}]"
    return "[Немає збереженої відповіді]"

def get_task_logs():
    """Отримати останні логи завдань"""
    try:
        task_dir = Path("task_logs")
        if task_dir.exists():
            logs = sorted(task_dir.glob("task_*.log"), reverse=True)[:5]
            if logs:
                items = []
                for log in logs:
                    size = log.stat().st_size / 1024  # KB
                    items.append(f"  - {log.name} ({size:.1f} KB)")
                return "\n".join(items)
    except Exception as e:
        return f"[Помилка: {e}]"
    return "Немає логів"

def get_git_info():
    """Отримати git інформацію"""
    try:
        result = subprocess.run(["git", "log", "--oneline", "-10"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return "\n".join(f"  {line}" for line in lines if line)
        return "[Git недоступний]"
    except Exception as e:
        return f"[Помилка: {e}]"

def get_log_locations():
    """Інформація про розташування логів редакторів та Trinity"""
    return """
### Trinity Logs (Проект)
  - logs/trinity_state_*.log (State initialization & transitions)
  - task_logs/task_*.log (Task execution logs)
  - logs/cli.log (CLI operations)

### Editor Logs (VS Code, Windsurf, Copilot)
  - ~/Library/Application Support/Windsurf/logs/ (Windsurf)
  - ~/.vscode/extensions/github.copilot-*/logs/ (GitHub Copilot)
  - ~/Library/Application Support/Code/logs/ (VS Code)

### Last Response
  - .last_response.txt (Остання відповідь від редактора/агента)
"""

def count_project_stats():
    """Підрахувати статистику проєкту"""
    try:
        # Count Python files
        py_count = len(list(Path(".").rglob("*.py")))
        # Count test files
        test_count = len(list(Path("tests").rglob("test_*.py"))) if Path("tests").exists() else 0
        # Count documentation
        doc_count = len(list(Path("docs").rglob("*.md"))) if Path("docs").exists() else 0
        # Count configs
        config_count = len(list(Path("configs").glob("*/metadata.json"))) if Path("configs").exists() else 0
        
        return f"""
### Project Statistics
  - Python files: {py_count}
  - Test files: {test_count}
  - Documentation files: {doc_count}
  - Configuration sets: {config_count}
"""
    except Exception as e:
        return f"[Error: {e}]"

def generate_tree():
    """Генеруємо дерево структури"""
    try:
        result = subprocess.run(
            ["tree", "-I", "__pycache__|*.pyc|.git|.venv|.DS_Store|.agent|node_modules|dist|build|coverage|.pytest_cache|.cache"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    
    # Fallback: використовуємо find
    try:
        result = subprocess.run(
            ["find", ".", "-type", "d", "-name", "__pycache__", "-prune", "-o", "-type", "f", "-print"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            lines = sorted([l for l in result.stdout.strip().split('\n') if l and not any(ig in l for ig in ['__pycache__', '.git', '.venv', '.DS_Store'])])
            return "\n".join(lines[:300])  # Обмежимо до 300 рядків
    except Exception:
        pass
    
    return "[Помилка генерації структури]"

# Main generation
print("Generating project_structure_final.txt...", file=sys.stderr)

with open(os.getenv('OUTPUT_FILE', 'project_structure_final.txt'), 'w', encoding='utf-8') as f:
    f.write("## Metadata\n")
    f.write(f"Generated: {datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')}\n\n")
    
    f.write("## Program Execution Logs\n")
    f.write("(See logs/cli.log for details)\n")
    f.write(f"\nRecent Task Logs:\n{get_task_logs()}\n\n")
    
    f.write("## Останні відповіді редакторів\n")
    f.write("(Дивись atlas.md розділ 11 для інформації про інтеграцію)\n\n")
    f.write("### Last Agent Response from Trinity/Windsurf/Copilot\n")
    f.write("```\n")
    f.write(get_last_response())
    f.write("\n```\n\n")
    
    f.write("## Log Locations (Логи та Діагностика)\n")
    f.write(get_log_locations())
    f.write("\n")
    
    f.write(count_project_stats())
    f.write("\n")
    
    f.write("## Git History (Last 10 Commits)\n")
    f.write("```\n")
    f.write(get_git_info())
    f.write("\n```\n\n")
    
    f.write("## Project Structure\n")
    f.write("```\n")
    f.write(generate_tree())
    f.write("\n```\n")

print("✓ Project structure regenerated in project_structure_final.txt", file=sys.stderr)

PYTHON_EOF
