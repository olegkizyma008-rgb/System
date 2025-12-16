#!/bin/bash

# Script to save last chat response and regenerate project structure
# Usage: ./save_response.sh "Your response text here"

RESPONSE="${1:-}"

if [ -z "$RESPONSE" ]; then
    echo "❌ Error: No response provided"
    echo "Usage: ./save_response.sh \"Your response text here\""
    exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

echo "💾 Saving response to .last_response.txt..."

# Read existing content
EXISTING=""
if [ -f ".last_response.txt" ]; then
    EXISTING=$(cat ".last_response.txt")
fi

# Parse to separate my response from Trinity reports
MY_RESPONSE=""
TRINITY_REPORTS=""

if [ -n "$EXISTING" ]; then
    if echo "$EXISTING" | grep -q "## My Last Response"; then
        # Extract my response (everything before first Trinity Report)
        MY_RESPONSE=$(echo "$EXISTING" | sed '/## Trinity Report/q' | sed '$ d')
        # Extract Trinity reports (everything from first Trinity Report onwards)
        TRINITY_REPORTS=$(echo "$EXISTING" | sed -n '/## Trinity Report/,$ p')
    else
        # Old format: treat as Trinity reports
        TRINITY_REPORTS="$EXISTING"
    fi
fi

# Build new content: my response first, then Trinity reports
NEW_CONTENT="## My Last Response

$RESPONSE"

if [ -n "$TRINITY_REPORTS" ]; then
    NEW_CONTENT="$NEW_CONTENT

---

$TRINITY_REPORTS"
fi

# Write to file
echo "$NEW_CONTENT" > ".last_response.txt"
echo "✅ Response saved to .last_response.txt"

# Regenerate project structure
echo "🔄 Regenerating project structure..."
python3 generate_structure.py > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Project structure regenerated"
else
    echo "⚠️  Warning: Failed to regenerate project structure"
fi

# Stage files for git
echo "📝 Staging files for git..."
git add .last_response.txt project_structure_final.txt 2>/dev/null

echo "✅ Done! Files are ready to commit."
echo ""
echo "Next step: git commit -m \"Update: Add latest response to project structure\""
