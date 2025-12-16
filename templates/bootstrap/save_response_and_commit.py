#!/usr/bin/env python3
"""
Helper script to save last response and trigger regeneration.
Usage: python3 save_response_and_commit.py "Your response text here"
"""

import sys
import subprocess
import os
from pathlib import Path

def save_response(response_text: str):
    """Save response to .last_response.txt"""
    response_file = Path(".last_response.txt")
    response_file.write_text(response_text, encoding='utf-8')
    print(f"✓ Saved response to {response_file}")

def regenerate_structure():
    """Run regenerate_structure.sh"""
    try:
        result = subprocess.run(
            ["./regenerate_structure.sh"],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"⚠ Warning: regenerate_structure.sh returned {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"⚠ Error regenerating structure: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 save_response_and_commit.py 'Your response text'")
        sys.exit(1)
    
    response_text = sys.argv[1]
    
    # Save response
    save_response(response_text)
    
    # Regenerate structure
    regenerate_structure()
    
    print("✓ Done!")

if __name__ == "__main__":
    main()
