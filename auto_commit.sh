#!/bin/bash

# Script to automatically save response and create commit
# Usage: ./auto_commit.sh "Your response text here"
# This script:
# 1. Saves response to .last_response.txt
# 2. Adds it to git staging
# 3. Creates commit
# 4. Post-commit hook regenerates structure and amends commit

RESPONSE="${1:-}"

if [ -z "$RESPONSE" ]; then
    echo "❌ Error: No response provided"
    echo "Usage: ./auto_commit.sh \"Your response text here\""
    exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Use save_response.sh to handle the response saving logic
./save_response.sh "$RESPONSE"

if [ $? -ne 0 ]; then
    echo "❌ Failed to save response"
    exit 1
fi

# Add to git
echo "📝 Creating commit..."
git add .last_response.txt 2>/dev/null

# Create commit
git commit -m "Update: Add latest response" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Commit created successfully"
    echo "🔄 Post-commit hook will regenerate structure and amend commit"
else
    echo "⚠️  Warning: Commit creation failed (might be nothing to commit)"
fi
