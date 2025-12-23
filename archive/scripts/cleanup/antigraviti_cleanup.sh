#!/bin/zsh

setopt NULL_GLOB

# Забезпечуємо базовий PATH для системних утиліт (включаючи homebrew для timeout)
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

# ═══════════════════════════════════════════════════════════════
#  🛰  ANTIGRAVITY CLEANUP - Очищення ідентифікаторів Antigravity
#  Використовує спільні функції з common_functions.sh
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common_functions.sh"

print_header "🛰  ANTIGRAVITY CLEANUP" "$CYAN"
print_info "Очищення ідентифікаторів Google Antigravity Editor"
echo ""

# ─────────────────────────────────────────────────────────────────
# ANTIGRAVITY-СПЕЦИФІЧНІ ШЛЯХИ
# ─────────────────────────────────────────────────────────────────
ANTIGRAVITY_BASE="$HOME/Library/Application Support/Antigravity"
ANTIGRAVITY_GOOGLE="$HOME/Library/Application Support/Google/Antigravity"
ANTIGRAVITY_CACHES="$HOME/Library/Caches/Antigravity"
ANTIGRAVITY_GOOGLE_CACHES="$HOME/Library/Caches/Google/Antigravity"

# 1. Зупинка процесів Antigravity
print_step 1 11 "Зупинка Antigravity..."
pkill -f "Antigravity" 2>/dev/null
pkill -f "antigravity" 2>/dev/null
sleep 2
print_success "Antigravity зупинено"

# 2. Відмонтування DMG та видалення додатків
print_step 2 11 "Відмонтування DMG та видалення додатків..."

# Unmount any mounted Antigravity DMG volumes
for vol in /Volumes/Antigravity*; do
    if [ -d "$vol" ]; then
        print_info "Відмонтування: $vol"
        hdiutil detach "$vol" -force 2>/dev/null || diskutil unmount force "$vol" 2>/dev/null
        sleep 1
    fi
done

# Also check for generic "Antigravity" mount without wildcard
if [ -d "/Volumes/Antigravity" ]; then
    print_info "Відмонтування: /Volumes/Antigravity"
    hdiutil detach "/Volumes/Antigravity" -force 2>/dev/null || diskutil unmount force "/Volumes/Antigravity" 2>/dev/null
    sleep 1
fi

ANTIGRAVITY_APPS=(
    "/Applications/Antigravity.app"
    "/Applications/Google Antigravity.app"
    "$HOME/Applications/Antigravity.app"
    "/Applications/Utilities/Antigravity.app"
)

for app in "${ANTIGRAVITY_APPS[@]}"; do
    if [ -e "$app" ]; then
        print_info "Видалення додатку: $app"
        safe_remove "$app"
    fi
done

# Force remove any remaining Antigravity apps
find /Applications -maxdepth 2 -iname "*antigravity*.app" -exec rm -rf {} + 2>/dev/null
find "$HOME/Applications" -maxdepth 2 -iname "*antigravity*.app" -exec rm -rf {} + 2>/dev/null

print_success "Додатки видалено"

# 3. Очищення основних директорій
print_step 3 11 "Очищення основних директорій..."

ANTIGRAVITY_PATHS=(
    "$ANTIGRAVITY_BASE"
    "$ANTIGRAVITY_GOOGLE"
    "$ANTIGRAVITY_CACHES"
    "$ANTIGRAVITY_GOOGLE_CACHES"
    "$HOME/Library/Preferences/com.google.antigravity.plist"
    "$HOME/Library/Saved Application State/com.google.antigravity.savedState"
)

for path in "${ANTIGRAVITY_PATHS[@]}"; do
    safe_remove "$path"
done

safe_remove_glob "$HOME/Library/Preferences/ByHost/*antigravity*"
safe_remove_glob "$HOME/Library/HTTPStorages/*antigravity*"
safe_remove_glob "$HOME/Library/WebKit/*antigravity*"
safe_remove_glob "$HOME/Library/Containers/*antigravity*"
safe_remove_glob "$HOME/Library/Group Containers/*antigravity*"
safe_remove_glob "$HOME/Library/Application Scripts/*antigravity*"
print_success "Основні директорії очищено"

# 4. Очищення Chrome IndexedDB даних
print_step 4 11 "Очищення Chrome IndexedDB даних..."
CHROME_DIR="$HOME/Library/Application Support/Google/Chrome"
if [ -d "$CHROME_DIR" ]; then
    find "$CHROME_DIR" -path "*/IndexedDB/*antigravity*" -exec rm -rf {} + 2>/dev/null
    find "$CHROME_DIR" -path "*/IndexedDB/*google*" -name "*antigravity*" -exec rm -rf {} + 2>/dev/null
    find "$CHROME_DIR" -path "*/Local Storage/*antigravity*" -exec rm -rf {} + 2>/dev/null
    find "$CHROME_DIR" -path "*/Session Storage/*antigravity*" -exec rm -rf {} + 2>/dev/null
    print_success "Chrome IndexedDB дані видалено"
else
    print_info "Chrome не встановлено, пропускаємо"
fi

# 5. Очищення браузерних даних Safari та Firefox
print_step 5 11 "Очищення браузерних даних..."
safe_remove_glob "$HOME/Library/Safari/Databases/*antigravity*"
safe_remove_glob "$HOME/Library/Safari/LocalStorage/*antigravity*"
find "$HOME/Library/Application Support/Firefox" -name "*antigravity*" -exec rm -rf {} + 2>/dev/null
print_success "Браузерні дані очищено"

# 6. Очищення Keychain
print_step 6 11 "Очищення Keychain..."
ANTIGRAVITY_KEYCHAIN_SERVICES=(
    "Antigravity"
    "antigravity"
    "Google Antigravity"
    "google-antigravity"
    "antigravity.google.com"
    "api.antigravity.google.com"
    "com.google.antigravity"
)

for service in "${ANTIGRAVITY_KEYCHAIN_SERVICES[@]}"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
    security delete-generic-password -l "$service" 2>/dev/null
done
print_success "Keychain очищено"

# 7. Очищення Gemini-пов'язаних даних
print_step 7 11 "Очищення Gemini-пов'язаних даних..."
safe_remove_glob "$HOME/Library/Application Support/Gemini/Antigravity"
safe_remove_glob "$HOME/Library/Application Support/Google/Gemini/Antigravity"
safe_remove_glob "$HOME/Library/Caches/Gemini/Antigravity"
safe_remove_glob "$HOME/Library/Caches/Google/Gemini/Antigravity"
print_success "Gemini-дані очищено"

# 8. Очищення системних логів та історії
print_step 8 11 "Очищення логів та історії..."
safe_remove_glob "$HOME/Library/Logs/Antigravity*"
safe_remove_glob "$HOME/Library/Logs/Google/Antigravity*"
sed -i '' '/antigravity/Id' ~/.bash_history 2>/dev/null
sed -i '' '/antigravity/Id' ~/.zsh_history 2>/dev/null
print_success "Логи та історія очищено"

# 9. Очищення тимчасових файлів
print_step 9 11 "Очищення тимчасових файлів..."
safe_remove_glob "/tmp/*antigravity*"
safe_remove_glob "/var/tmp/*antigravity*"
safe_remove_glob "$HOME/Library/Application Support/CrashReporter/*antigravity*"
print_success "Тимчасові файли очищено"

# 10. Очищення системних defaults
print_step 10 11 "Очищення системних defaults..."
defaults delete com.google.antigravity 2>/dev/null
defaults delete com.google.Antigravity 2>/dev/null
print_success "System defaults очищено"

# ─────────────────────────────────────────────────────────────────
# ФІНАЛЬНЕ ОЧИЩЕННЯ
# ─────────────────────────────────────────────────────────────────
echo ""
print_info "Пошук та видалення залишків..."

REMAINING_PATHS=$(find "$HOME/Library" -iname "*antigravity*" 2>/dev/null | /usr/bin/head -n 100)
if [ -n "$REMAINING_PATHS" ]; then
    echo "$REMAINING_PATHS" | while read -r path; do
        [ -n "$path" ] && safe_remove "$path"
    done
fi

# ─────────────────────────────────────────────────────────────────
# ЗВІТ
# ─────────────────────────────────────────────────────────────────
echo ""
echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo "${WHITE}📊 ЗВІТ ОЧИЩЕННЯ ANTIGRAVITY:${NC}"
echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

REMAINING=$(find "$HOME/Library" -iname "*antigravity*" 2>/dev/null | /usr/bin/wc -l | /usr/bin/tr -d ' ')

if [ "$REMAINING" -eq 0 ]; then
    print_success "Antigravity ідентифікатори: ОЧИЩЕНО"
else
    print_warning "Знайдено $REMAINING залишкових файлів"
fi

# Use timeout to prevent keychain dialog from blocking
KEYCHAIN_CHECK=$(timeout 5 security find-generic-password -s "Antigravity" 2>/dev/null | /usr/bin/wc -l || echo "0")
if [ "$KEYCHAIN_CHECK" -eq 0 ] || [ -z "$KEYCHAIN_CHECK" ]; then
    print_success "Keychain: ОЧИЩЕНО"
else
    print_warning "Keychain: Знайдено записи"
fi

echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
print_success "Очищення Antigravity завершено!"
print_info "Тепер можна запускати Antigravity як новий користувач"
echo ""
