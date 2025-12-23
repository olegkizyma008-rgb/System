#!/bin/zsh

setopt NULL_GLOB

# ═══════════════════════════════════════════════════════════════
#  🔄 DEEP WINDSURF CLEANUP - Глибоке видалення Windsurf
#  Для повної переінсталяції як новий клієнт
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
if [ ! -f "$REPO_ROOT/cleanup_modules.json" ] && [ -f "$SCRIPT_DIR/../cleanup_modules.json" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# Підключення common_functions.sh
COMMON_FUNCTIONS="$SCRIPT_DIR/common_functions.sh"
if [ -f "$COMMON_FUNCTIONS" ]; then
    source "$COMMON_FUNCTIONS"
else
    echo "❌ Не знайдено common_functions.sh"
    exit 1
fi

CONFIGS_DIR="$REPO_ROOT/configs"
ORIGINAL_CONFIG="$CONFIGS_DIR/original"

# Завантаження змінних середовища
load_env "$REPO_ROOT"

# SUDO_ASKPASS
setup_sudo_askpass "$REPO_ROOT"

print_header "ГЛИБОКЕ ВИДАЛЕННЯ WINDSURF"
print_info "Для нового клієнта"
echo ""

# Перевірка sudo доступу
check_sudo

# ПЕРЕВІРКА КОНФЛІКТІВ
print_info "Перевірка активних процесів..."
if pgrep -f "Visual Studio Code" > /dev/null 2>&1; then
    print_warning "Visual Studio Code активний! Рекомендую закрити для уникнення конфліктів"
    if ! confirm "Продовжити cleanup?"; then
        print_error "Cleanup скасовано"
        exit 1
    fi
fi

# Генерація нового hostname
NEW_HOSTNAME=$(generate_hostname)
ORIGINAL_HOSTNAME=$(scutil --get HostName 2>/dev/null || echo "DEVs-Mac-Studio")
mkdir -p "$CONFIGS_DIR"

TOTAL_STEPS=15

WINDSURF_PATH="${EDITOR_PATHS[windsurf]}"

# Функція для збереження поточної конфігурації як оригінал
save_as_original() {
    print_info "Збереження поточної конфігурації як ОРИГІНАЛ..."
    
    mkdir -p "$ORIGINAL_CONFIG/User/globalStorage"
    
    [ -f "$WINDSURF_PATH/machineid" ] && cp "$WINDSURF_PATH/machineid" "$ORIGINAL_CONFIG/machineid"
    [ -f "$WINDSURF_PATH/storage.json" ] && cp "$WINDSURF_PATH/storage.json" "$ORIGINAL_CONFIG/storage.json"
    [ -f "$WINDSURF_PATH/User/globalStorage/storage.json" ] && cp "$WINDSURF_PATH/User/globalStorage/storage.json" "$ORIGINAL_CONFIG/User/globalStorage/storage.json"
    
    echo "$ORIGINAL_HOSTNAME" > "$ORIGINAL_CONFIG/hostname.txt"
    
    cat > "$ORIGINAL_CONFIG/metadata.json" << EOF
{
  "name": "original",
  "created": "$(date +%Y-%m-%d\ %H:%M:%S)",
  "hostname": "$ORIGINAL_HOSTNAME",
  "description": "Original Windsurf configuration for auto-restore"
}
EOF
    
    print_success "Оригінальна конфігурація збережена!"
}

# Перевірити чи існує оригінальна конфігурація
if [ ! -d "$ORIGINAL_CONFIG" ]; then
    print_warning "Оригінальна конфігурація не знайдена! Зберігаю поточний стан..."
    save_as_original
fi

# 1. Зупинка процесів та видалення папок
print_step 1 $TOTAL_STEPS "Видалення основних папок..."
stop_editor "windsurf"
safe_remove ~/Library/Application\ Support/windsurf
safe_remove ~/Library/Preferences/Windsurf
safe_remove ~/Library/Logs/Windsurf
safe_remove ~/.windsurf
safe_remove ~/.windsurf-server
safe_remove ~/.config/Windsurf
safe_remove ~/Library/Saved\ Application\ State/Windsurf.savedState
safe_remove ~/Library/Saved\ Application\ State/com.windsurf.savedState

# 2. Аналіз бази даних моніторингу для пошуку динамічних слідів
print_step 2 $TOTAL_STEPS "Аналіз бази даних моніторингу..."
MONITOR_DB="${SYSTEM_MONITOR_EVENTS_DB_PATH:-$HOME/.system_cli/monitor_events.db}"
if [ -f "$MONITOR_DB" ]; then
    print_info "Пошук додаткових слідів у $MONITOR_DB"
    DYNAMIC_TRACES=$(sqlite3 "$MONITOR_DB" "SELECT DISTINCT src_path FROM events WHERE src_path LIKE '%windsurf%' OR process LIKE '%Windsurf%' LIMIT 500;" 2>/dev/null)
    if [ -n "$DYNAMIC_TRACES" ]; then
        echo "$DYNAMIC_TRACES" | while read -r trace; do
            if [[ "$trace" == /Users/* ]] || [[ "$trace" == /private/var/* ]] || [[ "$trace" == /tmp/* ]]; then
                if [ -e "$trace" ]; then
                   print_info "Видалення динамічного сліду: $trace"
                   safe_remove "$trace"
                fi
            fi
        done
    fi
    print_success "Динамічні сліди з моніторингу оброблено"
else
    print_warning "Базу даних моніторингу не знайдено, пропускаємо динамічний аналіз"
fi

# 3. ВИДАЛЕННЯ ДОДАТКУ
print_step 3 $TOTAL_STEPS "Видалення додатку Windsurf..."
safe_remove /Applications/Windsurf.app
print_success "Додаток видалено"

# 4. КЕШІ
print_step 4 $TOTAL_STEPS "Очищення кешів..."
safe_remove ~/Library/Caches/Windsurf
safe_remove ~/Library/Caches/windsurf
safe_remove_glob ~/Library/Caches/com.windsurf.*
find ~/Library/Caches -iname "*windsurf*" -maxdepth 2 -exec rm -rf {} + 2>/dev/null
print_success "Кеші очищено"

# 5. CONTAINERS
print_step 5 $TOTAL_STEPS "Видалення контейнерів..."
find ~/Library/Containers -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null
find ~/Library/Group\ Containers -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null
print_success "Контейнери видалено"

# 6. COOKIES
print_step 6 $TOTAL_STEPS "Очищення cookies та веб-даних..."
find ~/Library/Cookies -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null
safe_remove ~/Library/WebKit/Windsurf
print_success "Cookies очищено"

# 7. PLIST
print_step 7 $TOTAL_STEPS "Видалення plist-файлів..."
find ~/Library/Preferences -iname "*windsurf*.plist" -delete 2>/dev/null
safe_remove ~/Library/Preferences/com.windsurf.plist
safe_remove ~/Library/Preferences/com.windsurf.helper.plist
print_success "Plist файли видалено"

# 8. KEYCHAIN
print_step 8 $TOTAL_STEPS "Очищення Keychain..."
cleanup_editor_keychain "windsurf"
# Додаткові сервіси
for service in "codeium" "codeium.com" "api.codeium.com" "windsurf.com" "auth.windsurf.com" "codeium-windsurf" "Codeium Editor"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
done
print_success "Keychain очищено"

# Перевірка UNSAFE_MODE
if [ "${UNSAFE_MODE}" != "1" ]; then
    print_warning "SAFE_MODE: виконую лише деінсталяцію/очистку (без підміни ідентифікаторів)"
    safe_remove "$WINDSURF_PATH"
    xcrun --kill-cache 2>/dev/null
    print_success "SAFE_MODE cleanup завершено."
    exit 0
fi

# 9. Підміна ідентифікаторів
print_step 9 $TOTAL_STEPS "Резервування та підміна ідентифікаторів..."
BACKUP_DIR="/tmp/windsurf_backup_$(date +%s)"
mkdir -p "$BACKUP_DIR"
print_info "Директорія бекапів: $BACKUP_DIR"

# Очищення баз даних
cleanup_editor_caches "windsurf"

# Створення директорій якщо не існують
mkdir -p "$WINDSURF_PATH"
mkdir -p "$WINDSURF_PATH/User/globalStorage"

# Підміна Machine-ID та Storage через common_functions
cleanup_editor_machine_id "windsurf"
cleanup_editor_storage "windsurf"
print_success "Ідентифікатори підмінено"

# Зберегти НОВУ конфігурацію в configs/
NEW_CONFIG_PATH="$CONFIGS_DIR/$NEW_HOSTNAME"
mkdir -p "$NEW_CONFIG_PATH/User/globalStorage"

[ -f "$WINDSURF_PATH/machineid" ] && cp "$WINDSURF_PATH/machineid" "$NEW_CONFIG_PATH/machineid"
[ -f "$WINDSURF_PATH/storage.json" ] && cp "$WINDSURF_PATH/storage.json" "$NEW_CONFIG_PATH/storage.json"
[ -f "$WINDSURF_PATH/User/globalStorage/storage.json" ] && cp "$WINDSURF_PATH/User/globalStorage/storage.json" "$NEW_CONFIG_PATH/User/globalStorage/storage.json"

echo "$NEW_HOSTNAME" > "$NEW_CONFIG_PATH/hostname.txt"
cat > "$NEW_CONFIG_PATH/metadata.json" << EOF
{
  "name": "$NEW_HOSTNAME",
  "created": "$(date +%Y-%m-%d\ %H:%M:%S)",
  "hostname": "$NEW_HOSTNAME",
  "description": "Auto-generated Windsurf profile"
}
EOF
print_success "Нову конфігурацію збережено: $NEW_HOSTNAME"

# 10. РОЗШИРЕННЯ
print_step 10 $TOTAL_STEPS "Видалення розширень..."
safe_remove ~/.windsurf/extensions
safe_remove ~/.vscode-windsurf
safe_remove "$WINDSURF_PATH/extensions"
safe_remove "$WINDSURF_PATH/User"
safe_remove "$WINDSURF_PATH/product.json"
safe_remove "$WINDSURF_PATH/Local Storage"
safe_remove "$WINDSURF_PATH/IndexedDB"
safe_remove "$WINDSURF_PATH/Session Storage"
print_success "Розширення видалено"

# 11. HOSTNAME (видалено дублікат - використовуйте hostname_spoof.sh)
print_step 11 $TOTAL_STEPS "Hostname..."
print_info "Для зміни hostname використовуйте: ./hostname_spoof.sh"
print_info "Поточний hostname: $(scutil --get HostName 2>/dev/null || echo 'не встановлено')"

# 12. МЕРЕЖА
print_step 12 $TOTAL_STEPS "Мережеві ідентифікатори..."
sudo dscacheutil -flushcache 2>/dev/null
sudo killall -HUP mDNSResponder 2>/dev/null
sudo arp -a -d 2>/dev/null
print_success "Мережу оновлено"

# 13. ФІНАЛЬНЕ ОЧИЩЕННЯ
print_step 13 $TOTAL_STEPS "Фінальне очищення..."
find ~/Library -iname "*windsurf*" -maxdepth 3 -not -path "*/Trash/*" -exec rm -rf {} + 2>/dev/null
find ~/.config -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null
sudo rm -rf /var/log/*windsurf* 2>/dev/null
sudo rm -rf /Library/Logs/*windsurf* 2>/dev/null
safe_remove "$WINDSURF_PATH"
print_success "Фінальне очищення завершено"

# 14. КЕШІ ІНСТРУМЕНТІВ
print_step 14 $TOTAL_STEPS "Очищення кешів інструментів..."
xcrun --kill-cache 2>/dev/null
print_success "Кеші інструментів очищено"

# 15. ІНСТАЛЯЦІЯ WINDSURF
print_step 15 $TOTAL_STEPS "Інсталяція Windsurf..."
WINDSURF_DMG="$REPO_ROOT/Windsurf.dmg"
WINDSURF_APP="$REPO_ROOT/Windsurf.app"

if [ -f "$WINDSURF_DMG" ]; then
    print_info "Знайдено Windsurf DMG: $(basename $WINDSURF_DMG)"
    print_info "Монтування..."
    hdiutil attach "$WINDSURF_DMG" -nobrowse -quiet
    if [ -d "/Volumes/Windsurf/Windsurf.app" ]; then
        sudo cp -R "/Volumes/Windsurf/Windsurf.app" /Applications/
        hdiutil detach "/Volumes/Windsurf" -quiet
        print_success "Windsurf встановлено"
    fi
elif [ -d "$WINDSURF_APP" ]; then
    print_info "Знайдено Windsurf.app"
    sudo cp -R "$WINDSURF_APP" /Applications/
    print_success "Windsurf встановлено"
else
    print_warning "Windsurf не знайдено"
    print_info "Завантажте з: https://codeium.com/windsurf"
fi

# Додати запис в історію
if [ -f "$REPO_ROOT/history_tracker.sh" ]; then
    "$REPO_ROOT/history_tracker.sh" add "windsurf" "cleanup" "Full cleanup completed" 2>/dev/null
fi

# Фінальний звіт
echo ""
print_header "ОЧИЩЕННЯ WINDSURF ЗАВЕРШЕНО"
echo ""
print_info "📋 Виконані дії:"
print_success "Видалено всі файли Windsurf"
print_success "Очищено Keychain"
print_success "Підмінено machine-id та device-id"
print_success "Очищено кеші"
print_success "Мережу оновлено"
if [ -d "/Applications/Windsurf.app" ]; then
    print_success "Windsurf встановлено в /Applications/"
fi
echo ""
print_info "💾 Бекап: $BACKUP_DIR"
print_info "📂 Конфігурація: $NEW_CONFIG_PATH"
echo ""
print_info "💡 РЕКОМЕНДАЦІЇ:"
print_info "   Для зміни hostname: ./hostname_spoof.sh"
print_info "   Для зміни MAC: ./hardware_spoof.sh"
print_info "   При першому запуску Windsurf побачить вас як НОВОГО користувача"
echo ""
echo "📊 Для перевірки процесу відновлення: ps -p $RESTORE_PID"
echo "=================================================="
# Explicit exit with success code
exit 0
