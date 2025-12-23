#!/bin/bash

# Script to save last chat response
# Post-commit hook will automatically regenerate structure and amend commit
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
TRINITY_REPORTS=""

if [ -n "$EXISTING" ]; then
    if echo "$EXISTING" | grep -q "## My Last Response"; then
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

echo ""
echo "📝 Next steps:"
echo "   1. git add .last_response.txt"
echo "   2. git commit -m \"Update: Add latest response\""
echo "   3. Post-commit hook will automatically regenerate structure and amend"
