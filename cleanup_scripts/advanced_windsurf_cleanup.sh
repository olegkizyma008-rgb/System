#!/bin/zsh

# ═══════════════════════════════════════════════════════════════
#  🔄 ADVANCED WINDSURF CLEANUP - Розширене очищення ідентифікаторів
#  Видаляє ВСІ можливі ідентифікатори включаючи browser data та hardware fingerprinting
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

# Завантаження змінних середовища
load_env "$REPO_ROOT"

# SUDO_ASKPASS
setup_sudo_askpass "$REPO_ROOT"

# Перевірка безпечного режиму
check_safe_mode "advanced_windsurf_cleanup"

# Перевірка sudo доступу
check_sudo

print_header "ADVANCED WINDSURF CLEANUP"
print_info "Розширене очищення всіх ідентифікаторів"
echo ""

TOTAL_STEPS=11

# Зупинка всіх процесів
stop_editor "windsurf"

# 1. Базове очищення Windsurf (з попереднього скрипту)
print_step 1 $TOTAL_STEPS "Базове очищення Windsurf..."
cleanup_editor_machine_id "windsurf"
cleanup_editor_storage "windsurf"
print_success "Базове очищення завершено"

# 2. Видалення всіх Chrome IndexedDB даних Windsurf
print_step 2 $TOTAL_STEPS "Очищення Chrome IndexedDB даних..."
setopt NULL_GLOB
find ~/Library/Application\ Support/Google/Chrome -name "*windsurf*" -type d -exec rm -rf {} + 2>/dev/null
find ~/Library/Application\ Support/Google/Chrome -path "*/IndexedDB/https_windsurf.com_*" -exec rm -rf {} + 2>/dev/null
print_success "Chrome IndexedDB дані видалено"

# 3. Очищення всіх браузерних даних
print_step 3 $TOTAL_STEPS "Очищення браузерних даних..."
# Chrome
safe_remove_glob ~/Library/Application\ Support/Google/Chrome/*/Local\ Storage/leveldb/*windsurf*
safe_remove_glob ~/Library/Application\ Support/Google/Chrome/*/Session\ Storage/*windsurf*
# Safari
safe_remove_glob ~/Library/Safari/Databases/*windsurf*
safe_remove_glob ~/Library/Safari/LocalStorage/*windsurf*
# Firefox
find ~/Library/Application\ Support/Firefox -name "*windsurf*" -exec rm -rf {} + 2>/dev/null
print_success "Браузерні дані очищено"

# 4. Видалення системних списків та історії
print_step 4 $TOTAL_STEPS "Очищення системних списків..."
safe_remove_glob ~/Library/Application\ Support/com.apple.sharedfilelist/*windsurf*
safe_remove_glob ~/Library/Application\ Support/com.apple.sharedfilelist/*Windsurf*
safe_remove ~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure.plist
print_success "Системні списки очищено"

# 5. Повне видалення кешів та баз даних
print_step 5 $TOTAL_STEPS "Повне видалення кешів..."
WINDSURF_PATH="${EDITOR_PATHS[windsurf]}"
safe_remove "$WINDSURF_PATH/User/globalStorage/state.vscdb"
safe_remove "$WINDSURF_PATH/User/globalStorage/state.vscdb.backup"
safe_remove "$WINDSURF_PATH/Local Storage"
safe_remove "$WINDSURF_PATH/Session Storage"
safe_remove "$WINDSURF_PATH/IndexedDB"
safe_remove "$WINDSURF_PATH/databases"
safe_remove "$WINDSURF_PATH/GPUCache"
safe_remove "$WINDSURF_PATH/CachedData"
safe_remove "$WINDSURF_PATH/Code Cache"
safe_remove "$WINDSURF_PATH/User/workspaceStorage"
safe_remove "$WINDSURF_PATH/logs"
print_success "Кеші повністю видалено"

# 6. Розширене очищення Keychain
print_step 6 $TOTAL_STEPS "Розширене очищення Keychain..."
cleanup_editor_keychain "windsurf"
# Додаткові сервіси специфічні для Windsurf/Codeium
for service in "codeium" "codeium.com" "api.codeium.com" "windsurf.com" "auth.windsurf.com"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
done
print_success "Keychain повністю очищено"

# 7. Видалення всіх веб-даних та cookies
print_step 7 $TOTAL_STEPS "Видалення всіх веб-даних..."
safe_remove_glob "$WINDSURF_PATH/Cookies*"
safe_remove "$WINDSURF_PATH/Network Persistent State"
safe_remove "$WINDSURF_PATH/TransportSecurity"
safe_remove_glob "$WINDSURF_PATH/Trust Tokens*"
safe_remove_glob "$WINDSURF_PATH/SharedStorage*"
safe_remove "$WINDSURF_PATH/WebStorage"
print_success "Веб-дані повністю видалено"

# 8. Очищення Codeium даних
print_step 8 $TOTAL_STEPS "Очищення Codeium даних..."
safe_remove ~/Library/Application\ Support/com.intii.CopilotForXcode/Codeium
safe_remove ~/.codeium
safe_remove_glob ~/Library/Caches/com.codeium*
print_success "Codeium дані видалено"

# 9. Очищення DNS та мережевого кешу
print_step 9 $TOTAL_STEPS "Очищення мережевого кешу..."
sudo dscacheutil -flushcache 2>/dev/null
sudo killall -HUP mDNSResponder 2>/dev/null
sudo arp -a -d 2>/dev/null
print_success "Мережевий кеш очищено"

# 10. Очищення системних логів
print_step 10 $TOTAL_STEPS "Очищення системних логів..."
sudo rm -rf /var/log/*windsurf* 2>/dev/null
sudo rm -rf /tmp/*windsurf* 2>/dev/null
safe_remove_glob ~/Library/Logs/*windsurf*
safe_remove_glob ~/Library/Logs/*Windsurf*
print_success "Системні логи очищено"

# 11. Очищення Launch Services кешу
print_step 11 $TOTAL_STEPS "Очищення Launch Services кешу..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null
print_success "Launch Services кеш очищено"

# Фінальний звіт
echo ""
print_header "РОЗШИРЕНЕ ОЧИЩЕННЯ WINDSURF ЗАВЕРШЕНО"
echo ""
print_info "📋 Виконані дії:"
print_success "Базове очищення Windsurf"
print_success "Chrome IndexedDB дані видалено"
print_success "Всі браузерні дані очищено"
print_success "Системні списки очищено"
print_success "Кеші повністю видалено"
print_success "Keychain повністю очищено"
print_success "Веб-дані повністю видалено"
print_success "Codeium дані видалено"
print_success "Мережевий кеш очищено"
print_success "Системні логи очищено"
print_success "Launch Services кеш очищено"
echo ""
print_warning "⚠️  Для зміни MAC/hostname використовуйте окремі скрипти:"
print_info "   ./hardware_spoof.sh - для MAC адреси"
print_info "   ./hostname_spoof.sh - для hostname"
echo ""
print_warning "ВАЖЛИВО: Перезавантажте систему для повного ефекту"
print_info "Після перезавантаження запустіть Windsurf"
echo ""
