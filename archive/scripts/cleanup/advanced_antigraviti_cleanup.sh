#!/bin/zsh

setopt NULL_GLOB

# Забезпечуємо базовий PATH для системних утиліт
PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

# ═══════════════════════════════════════════════════════════════
#  🛰  ADVANCED ANTIGRAVITY CLEANUP - Розширене очищення
#  Використовує спільні функції з common_functions.sh
#  Включає: браузерні дані, cookies, кеш, spotlight
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common_functions.sh"

print_header "🛰  ADVANCED ANTIGRAVITY CLEANUP" "$CYAN"
print_info "Розширене очищення всіх ідентифікаторів Antigravity"
echo ""

# Загальна кількість кроків: 12
TOTAL_STEPS=12

# 1. Зупинка всіх процесів та відмонтування DMG
print_step 1 $TOTAL_STEPS "Зупинка всіх пов'язаних процесів..."
pkill -f antigravity 2>/dev/null
pkill -f Antigravity 2>/dev/null
sleep 2

# Unmount any mounted Antigravity DMG volumes
for vol in /Volumes/Antigravity*; do
    if [ -d "$vol" ]; then
        print_info "Відмонтування: $vol"
        hdiutil detach "$vol" -force 2>/dev/null || diskutil unmount force "$vol" 2>/dev/null
        sleep 1
    fi
done

if [ -d "/Volumes/Antigravity" ]; then
    print_info "Відмонтування: /Volumes/Antigravity"
    hdiutil detach "/Volumes/Antigravity" -force 2>/dev/null || diskutil unmount force "/Volumes/Antigravity" 2>/dev/null
    sleep 1
fi

print_success "Процеси зупинено та DMG відмонтовано"

# 2. Базове очищення Antigravity директорій
print_step 2 $TOTAL_STEPS "Базове очищення Antigravity..."

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

ANTIGRAVITY_PATHS=(
    "$HOME/Library/Application Support/Antigravity"
    "$HOME/Library/Application Support/Google/Antigravity"
    "$HOME/Library/Caches/Antigravity"
    "$HOME/Library/Caches/Google/Antigravity"
    "$HOME/Library/Preferences/com.google.antigravity.plist"
    "$HOME/Library/Saved Application State/com.google.antigravity.savedState"
)

for path in "${ANTIGRAVITY_PATHS[@]}"; do
    safe_remove "$path"
done

safe_remove_glob "$HOME/Library/Preferences/ByHost/*antigravity*"
safe_remove_glob "$HOME/Library/Containers/*antigravity*"
safe_remove_glob "$HOME/Library/Group Containers/*antigravity*"
safe_remove_glob "$HOME/Library/Application Scripts/*antigravity*"
safe_remove_glob "$HOME/Library/HTTPStorages/*antigravity*"
safe_remove_glob "$HOME/Library/WebKit/*antigravity*"
print_success "Базові директорії очищено"

# 3. Видалення Chrome IndexedDB даних
print_step 3 $TOTAL_STEPS "Очищення Chrome IndexedDB даних..."
CHROME_DIR="$HOME/Library/Application Support/Google/Chrome"
if [ -d "$CHROME_DIR" ]; then
    find "$CHROME_DIR" -iname "*antigravity*" -type d -exec rm -rf {} + 2>/dev/null
    find "$CHROME_DIR" -path "*/IndexedDB/*antigravity*" -exec rm -rf {} + 2>/dev/null
    find "$CHROME_DIR" -path "*/Local Storage/*antigravity*" -exec rm -rf {} + 2>/dev/null
    find "$CHROME_DIR" -path "*/Session Storage/*antigravity*" -exec rm -rf {} + 2>/dev/null
    print_success "Chrome IndexedDB дані видалено"
else
    print_info "Chrome не встановлено"
fi

# 4. Очищення браузерних даних Safari та Firefox
print_step 4 $TOTAL_STEPS "Очищення браузерних даних Safari/Firefox..."
safe_remove_glob "$HOME/Library/Safari/Databases/*antigravity*"
safe_remove_glob "$HOME/Library/Safari/LocalStorage/*antigravity*"
find "$HOME/Library/Application Support/Firefox" -iname "*antigravity*" -exec rm -rf {} + 2>/dev/null
print_success "Браузерні дані очищено"

# 5. Очищення Keychain
print_step 5 $TOTAL_STEPS "Видалення токенів з Keychain..."
ANTIGRAVITY_KEYCHAIN_SERVICES=(
    "Antigravity" "antigravity" "Google Antigravity"
    "antigravity.google.com" "api.antigravity.google.com"
    "com.google.antigravity"
)

for service in "${ANTIGRAVITY_KEYCHAIN_SERVICES[@]}"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
    security delete-generic-password -l "$service" 2>/dev/null
done
print_success "Keychain очищено"

# 6. Очищення системних логів та історії
print_step 6 $TOTAL_STEPS "Очищення логів та історії..."
safe_remove_glob "$HOME/Library/Logs/Antigravity*"
safe_remove_glob "$HOME/Library/Logs/Google/Antigravity*"
sed -i '' '/antigravity/Id' ~/.bash_history 2>/dev/null
sed -i '' '/antigravity/Id' ~/.zsh_history 2>/dev/null
print_success "Логи та історія очищено"

# 7. Очищення тимчасових файлів та crash reports
print_step 7 $TOTAL_STEPS "Очищення тимчасових файлів..."
safe_remove_glob "/tmp/*antigravity*"
safe_remove_glob "/var/tmp/*antigravity*"
safe_remove_glob "$HOME/Library/Application Support/CrashReporter/*antigravity*"
safe_remove_glob "$HOME/Library/Application Support/CrashReporter/*Antigravity*"
print_success "Тимчасові файли очищено"

# 8. Очищення Gemini-пов'язаних даних
print_step 8 $TOTAL_STEPS "Очищення Gemini-пов'язаних даних..."
safe_remove_glob "$HOME/Library/Application Support/Gemini/Antigravity"
safe_remove_glob "$HOME/Library/Application Support/Google/Gemini/Antigravity"
safe_remove_glob "$HOME/Library/Caches/Gemini/Antigravity"
safe_remove_glob "$HOME/Library/Caches/Google/Gemini/Antigravity"
print_success "Gemini-дані очищено"

# 9. Очищення пошукових індексів Spotlight
print_step 9 $TOTAL_STEPS "Очищення пошукових індексів..."
mdimport -r "$HOME/Library/Application Support/Antigravity" 2>/dev/null
mdimport -r "$HOME/Library/Application Support/Google/Antigravity" 2>/dev/null
print_success "Пошукові індекси оновлено"

# 10. Очищення системних preferences та defaults
print_step 10 $TOTAL_STEPS "Очищення системних preferences..."
defaults delete com.google.antigravity 2>/dev/null
defaults delete com.google.Antigravity 2>/dev/null
print_success "System preferences очищено"

# 11. Очищення Gatekeeper quarantine атрибутів
print_step 11 $TOTAL_STEPS "Очищення Gatekeeper quarantine..."
xattr -d com.apple.quarantine "/Applications/Antigravity.app" 2>/dev/null
xattr -d com.apple.quarantine "$HOME/Applications/Antigravity.app" 2>/dev/null
print_success "Gatekeeper атрибути очищено"

# 12. Фінальне очищення залишків
print_step 12 $TOTAL_STEPS "Фінальне очищення залишків..."
REMAINING_PATHS=$(find "$HOME/Library" -iname "*antigravity*" 2>/dev/null | /usr/bin/head -n 100)
if [ -n "$REMAINING_PATHS" ]; then
    echo "$REMAINING_PATHS" | while read -r path; do
        [ -n "$path" ] && safe_remove "$path"
    done
fi
print_success "Залишки очищено"

# Перевірка та звіт
echo ""
print_header "ЗВІТ РОЗШИРЕНОГО ОЧИЩЕННЯ ANTIGRAVITY"

REMAINING_ANTIGRAVITY_PATHS=$(find ~/Library -name "*antigravity*" -o -name "*Antigravity*" 2>/dev/null)

if [ -n "$REMAINING_ANTIGRAVITY_PATHS" ]; then
    print_warning "Знайдено залишкові файли/папки Antigravity у ~/Library. Видаляю:"
    echo "$REMAINING_ANTIGRAVITY_PATHS"
    echo "$REMAINING_ANTIGRAVITY_PATHS" | while read -r path; do
        [ -n "$path" ] && safe_remove "$path"
    done
fi

REMAINING_ANTIGRAVITY=$(find ~/Library -name "*antigravity*" -o -name "*Antigravity*" 2>/dev/null | /usr/bin/wc -l)
REMAINING_GOOGLE=$(find ~/Library/Application\ Support -name "*Google*" 2>/dev/null | /usr/bin/wc -l)
REMAINING_CACHES=$(find ~/Library/Caches -name "*antigravity*" -o -name "*Antigravity*" 2>/dev/null | /usr/bin/wc -l)

if [ "$REMAINING_ANTIGRAVITY" -eq 0 ]; then
    print_success "Antigravity ідентифікатори: ОЧИЩЕНО"
else
    print_warning "Antigravity ідентифікатори: Знайдено $REMAINING_ANTIGRAVITY залишків"
fi

if [ "$REMAINING_GOOGLE" -lt 5 ]; then
    print_success "Google-дані: ОЧИЩЕНО"
else
    print_warning "Google-дані: Знайдено $REMAINING_GOOGLE залишків"
fi

if [ "$REMAINING_CACHES" -eq 0 ]; then
    print_success "Кеш-дані: ОЧИЩЕНО"
else
    print_warning "Кеш-дані: Знайдено $REMAINING_CACHES залишків"
fi

# Перевірка Keychain
KEYCHAIN_ANTIGRAVITY=$(security find-generic-password -s "Antigravity" 2>/dev/null | /usr/bin/wc -l)
if [ "$KEYCHAIN_ANTIGRAVITY" -eq 0 ]; then
    print_success "Keychain: ОЧИЩЕНО"
else
    print_warning "Keychain: Знайдено записи"
fi

echo ""
print_success "Розширене очищення Antigravity Editor завершено!"
echo ""
