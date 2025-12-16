#!/bin/bash

# Bootstrap script to create a new Trinity continual development project
# Usage: ./bootstrap_new_project.sh <project_name> [parent_directory]

set -e

PROJECT_NAME="${1:-}"
PARENT_DIR="${2:-.}"

if [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <project_name> [parent_directory]"
    echo "Example: $0 MyNewGame"
    echo "Example: $0 MyNewGame ~/Projects"
    exit 1
fi

# Resolve parent directory
PARENT_DIR="$(cd "$PARENT_DIR" && pwd)"
PROJECT_DIR="$PARENT_DIR/$PROJECT_NAME"

# Check if project already exists
if [ -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory already exists: $PROJECT_DIR"
    exit 1
fi

echo "🚀 Bootstrapping new Trinity project: $PROJECT_NAME"
echo "📁 Location: $PROJECT_DIR"

# Create project directory
mkdir -p "$PROJECT_DIR"
echo "✓ Created project directory"

# Get bootstrap template directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_DIR="$SCRIPT_DIR/bootstrap"

if [ ! -d "$BOOTSTRAP_DIR" ]; then
    echo "❌ Error: Bootstrap template directory not found: $BOOTSTRAP_DIR"
    rm -rf "$PROJECT_DIR"
    exit 1
fi

# Copy bootstrap files
echo "📋 Copying bootstrap files..."
cp "$BOOTSTRAP_DIR/generate_structure.py" "$PROJECT_DIR/"
cp "$BOOTSTRAP_DIR/regenerate_structure.sh" "$PROJECT_DIR/"
cp "$BOOTSTRAP_DIR/save_response_and_commit.py" "$PROJECT_DIR/"
cp "$BOOTSTRAP_DIR/.gitignore" "$PROJECT_DIR/"
cp "$BOOTSTRAP_DIR/.env.example" "$PROJECT_DIR/"
cp "$BOOTSTRAP_DIR/README.md" "$PROJECT_DIR/"
echo "✓ Copied bootstrap files"

# Make scripts executable
chmod +x "$PROJECT_DIR/regenerate_structure.sh"
chmod +x "$PROJECT_DIR/save_response_and_commit.py"
echo "✓ Made scripts executable"

# Initialize git repository
cd "$PROJECT_DIR"
git init
echo "✓ Initialized git repository"

# Create .git/hooks directory
mkdir -p .git/hooks
cp "$BOOTSTRAP_DIR/post-commit" .git/hooks/post-commit
chmod +x .git/hooks/post-commit
echo "✓ Installed post-commit hook"

# Create initial .last_response.txt
echo "Bootstrap initialization" > .last_response.txt
echo "✓ Created .last_response.txt"

# Generate initial project structure
echo "📊 Generating initial project structure..."
python3 generate_structure.py > /dev/null 2>&1 || true
echo "✓ Generated project_structure_final.txt"

# Create initial commit
git add .
git commit -m "Initial commit: Bootstrap Trinity continual development project" 2>/dev/null || true
echo "✓ Created initial commit"

OPENED_IN_WINDSURF=0
if command -v windsurf >/dev/null 2>&1; then
    windsurf --new-window "$PROJECT_DIR" >/dev/null 2>&1 && OPENED_IN_WINDSURF=1 || true
else
    open -a Windsurf "$PROJECT_DIR" >/dev/null 2>&1 && OPENED_IN_WINDSURF=1 || true
fi
if [ "$OPENED_IN_WINDSURF" -eq 1 ]; then
    echo "🪟 Opened in Windsurf: $PROJECT_DIR"
else
    echo "⚠️ Could not auto-open Windsurf. You can run: windsurf \"$PROJECT_DIR\""
fi

# Summary
echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "📖 Next steps:"
echo "1. cd $PROJECT_DIR"
echo "2. Open in Windsurf: windsurf ."
echo "3. Start developing - project_structure_final.txt will update automatically"
echo ""
echo "📚 For more info, see README.md in the project directory"
