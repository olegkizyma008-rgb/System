#!/bin/zsh

setopt NULL_GLOB

pkill -f antigravity 2>/dev/null
pkill -f Antigravity 2>/dev/null
sleep 2

safe_remove() {
  local p="$1"
  if [ -e "$p" ]; then
    echo "🗑️  Remove: $p"
    rm -rf "$p" 2>/dev/null
  fi
}

remove_glob() {
  local pat="$1"
  local matched=0
  for p in $~pat; do
    matched=1
    safe_remove "$p"
  done
  if [ "$matched" -eq 0 ]; then
    return 0
  fi
}

echo "=================================================="
echo "🧼 ANTIGRAVITY FRESH INSTALL RESET"
echo "=================================================="
echo "This module removes local Antigravity state so next launch behaves like first install."
echo ""

echo "[1/5] App Support / Caches / Preferences"
remove_glob "$HOME/Library/Application Support/Antigravity"
remove_glob "$HOME/Library/Application Support/Google/Antigravity"
remove_glob "$HOME/Library/Application Support/Gemini/Antigravity"
remove_glob "$HOME/Library/Application Support/Google/Gemini/Antigravity"
remove_glob "$HOME/Library/Caches/Antigravity"
remove_glob "$HOME/Library/Caches/Google/Antigravity"
remove_glob "$HOME/Library/Caches/Gemini/Antigravity"
remove_glob "$HOME/Library/Caches/Google/Gemini/Antigravity"
remove_glob "$HOME/Library/Preferences/com.google.antigravity*"
remove_glob "$HOME/Library/Saved Application State/com.google.antigravity*"
remove_glob "$HOME/Library/Preferences/ByHost/*antigravity*"
remove_glob "$HOME/Library/HTTPStorages/*antigravity*"
remove_glob "$HOME/Library/WebKit/*antigravity*"
remove_glob "$HOME/Library/Containers/*antigravity*"
remove_glob "$HOME/Library/Group Containers/*antigravity*"
remove_glob "$HOME/Library/Application Scripts/*antigravity*"
remove_glob "$HOME/Library/Logs/Antigravity*"
remove_glob "$HOME/Library/Logs/Google/Antigravity*"

echo "[1/5] Scan for Gemini + Antigravity paths (targeted)"
GEMINI_ANTIGRAVITY_MATCHES=$(find "$HOME/Library" -maxdepth 8 -iname "*gemini*" 2>/dev/null | grep -i "antigravity" | head -n 200)
if [ -n "$GEMINI_ANTIGRAVITY_MATCHES" ]; then
  echo "$GEMINI_ANTIGRAVITY_MATCHES" | while read -r p; do
    [ -n "$p" ] && safe_remove "$p"
  done
fi

echo "[2/5] Defaults"
defaults delete com.google.antigravity 2>/dev/null
defaults delete com.google.Antigravity 2>/dev/null

echo "[3/5] Keychain"
for service in \
  "Antigravity" \
  "antigravity" \
  "Google Antigravity" \
  "com.google.antigravity" \
  "antigravity.google.com" \
  "api.antigravity.google.com"; do
  security delete-generic-password -s "$service" 2>/dev/null
  security delete-internet-password -s "$service" 2>/dev/null
  security delete-generic-password -l "$service" 2>/dev/null
done

echo "[4/5] Browser site storage (targeted)"
CHROME_DIR="$HOME/Library/Application Support/Google/Chrome"
if [ -d "$CHROME_DIR" ]; then
  find "$CHROME_DIR" -path "*/IndexedDB/*antigravity*" -exec rm -rf {} + 2>/dev/null
  find "$CHROME_DIR" -path "*/Local Storage/*antigravity*" -exec rm -rf {} + 2>/dev/null
  find "$CHROME_DIR" -path "*/Local Storage/leveldb/*antigravity*" -exec rm -rf {} + 2>/dev/null
  find "$CHROME_DIR" -path "*/Session Storage/*antigravity*" -exec rm -rf {} + 2>/dev/null
  find "$CHROME_DIR" -path "*/Service Worker/*antigravity*" -exec rm -rf {} + 2>/dev/null
fi

echo "[5/5] Summary"
REMAINING=$(find "$HOME/Library" -name "*antigravity*" -o -name "*Antigravity*" 2>/dev/null | wc -l | tr -d ' ')
echo "Remaining matches under ~/Library: $REMAINING"

echo "=================================================="
echo "✅ Antigravity fresh-install reset completed."
echo "=================================================="
