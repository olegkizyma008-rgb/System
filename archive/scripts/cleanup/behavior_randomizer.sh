#!/bin/zsh
# Behavioral pattern randomization for Windsurf

# Random typing delays
export WINDSURF_TYPING_DELAY=$((50 + RANDOM % 200))

# Random cursor movements
export WINDSURF_CURSOR_RANDOMIZE=1

# Random pause intervals
export WINDSURF_PAUSE_INTERVAL=$((5 + RANDOM % 15))

# Random code completion delays
export WINDSURF_COMPLETION_DELAY=$((100 + RANDOM % 300))
