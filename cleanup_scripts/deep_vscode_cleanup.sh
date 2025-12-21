#!/bin/zsh

setopt NULL_GLOB

# ═══════════════════════════════════════════════════════════════
#  🔄 DEEP VSCODE CLEANUP - Глибоке видалення VS Code
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

# Конфігурації
CONFIGS_DIR="$REPO_ROOT/configs_vscode"
ORIGINAL_CONFIG="$CONFIGS_DIR/original"

# Завантаження змінних середовища
load_env "$REPO_ROOT"

# SUDO_ASKPASS
setup_sudo_askpass "$REPO_ROOT"

print_header "ГЛИБОКЕ ВИДАЛЕННЯ VS CODE"
print_info "Для нового клієнта"
echo ""

# Перевірка sudo доступу
check_sudo

# ПЕРЕВІРКА КОНФЛІКТІВ
print_info "Перевірка активних процесів..."
if pgrep -f "Windsurf" > /dev/null 2>&1; then
    print_warning "Windsurf активний! Рекомендую закрити для уникнення конфліктів"
    if ! confirm "Продовжити cleanup?"; then
        print_error "Cleanup скасовано"
        exit 1
    fi
fi

# Генерація нового hostname
NEW_HOSTNAME=$(generate_hostname)
ORIGINAL_HOSTNAME=$(scutil --get HostName 2>/dev/null || echo "DEVs-Mac-Studio")
mkdir -p "$CONFIGS_DIR"

TOTAL_STEPS=13

# Збереження оригіналу якщо не існує
if [ ! -d "$ORIGINAL_CONFIG" ]; then
    print_info "Збереження ОРИГІНАЛЬНОЇ конфігурації..."
    VSCODE_PATH="${EDITOR_PATHS[vscode]}"
    mkdir -p "$ORIGINAL_CONFIG/User/globalStorage"
    [ -f "$VSCODE_PATH/machineid" ] && cp "$VSCODE_PATH/machineid" "$ORIGINAL_CONFIG/machineid"
    [ -f "$VSCODE_PATH/storage.json" ] && cp "$VSCODE_PATH/storage.json" "$ORIGINAL_CONFIG/storage.json"
    [ -f "$VSCODE_PATH/User/globalStorage/storage.json" ] && cp "$VSCODE_PATH/User/globalStorage/storage.json" "$ORIGINAL_CONFIG/User/globalStorage/storage.json"
    echo "$ORIGINAL_HOSTNAME" > "$ORIGINAL_CONFIG/hostname.txt"
    echo '{"name":"original","created":"'$(date +%Y-%m-%d\ %H:%M:%S)'","hostname":"'$ORIGINAL_HOSTNAME'"}' > "$ORIGINAL_CONFIG/metadata.json"
    print_success "Оригінал збережено"
fi

VSCODE_PATH="${EDITOR_PATHS[vscode]}"

# 1. Зупинка процесів та видалення папок
print_step 1 $TOTAL_STEPS "Видалення VS Code папок..."
stop_editor "vscode"
safe_remove "$VSCODE_PATH"
safe_remove ~/Library/Preferences/Code
safe_remove ~/Library/Logs/Code
safe_remove ~/.vscode
safe_remove ~/.vscode-server
safe_remove ~/.config/Code
safe_remove ~/Library/Saved\ Application\ State/com.microsoft.VSCode.savedState

# 2. Видалення додатку
print_step 2 $TOTAL_STEPS "Видалення додатку..."
safe_remove /Applications/Visual\ Studio\ Code.app
print_success "Додаток видалено"

# 3. Очищення кешів
print_step 3 $TOTAL_STEPS "Очищення кешів..."
safe_remove ~/Library/Caches/Code
safe_remove ~/Library/Caches/com.microsoft.VSCode
find ~/Library/Caches -iname "*vscode*" -maxdepth 2 -exec rm -rf {} + 2>/dev/null
print_success "Кеші очищено"

# 4. Видалення контейнерів
print_step 4 $TOTAL_STEPS "Видалення контейнерів..."
find ~/Library/Containers -iname "*vscode*" -exec rm -rf {} + 2>/dev/null
find ~/Library/Group\ Containers -iname "*vscode*" -exec rm -rf {} + 2>/dev/null
print_success "Контейнери видалено"

# 5. Cookies
print_step 5 $TOTAL_STEPS "Видалення Cookies..."
find ~/Library/Cookies -iname "*vscode*" -exec rm -rf {} + 2>/dev/null
print_success "Cookies видалено"

# 6. Plist файли
print_step 6 $TOTAL_STEPS "Видалення Plist файлів..."
find ~/Library/Preferences -iname "*vscode*.plist" -delete 2>/dev/null
find ~/Library/Preferences -iname "*code*.plist" -delete 2>/dev/null
print_success "Plist файли видалено"

# 7. Keychain
print_step 7 $TOTAL_STEPS "Очищення Keychain..."
cleanup_editor_keychain "vscode"
print_success "Keychain очищено"

# Перевірка UNSAFE_MODE для розширених дій
if [ "${UNSAFE_MODE}" != "1" ]; then
    print_warning "SAFE_MODE: виконую лише деінсталяцію/очистку (без підміни ідентифікаторів)"
    print_success "SAFE_MODE cleanup завершено."
    exit 0
fi

# 8. Резервування та підміна ID
print_step 8 $TOTAL_STEPS "Резервування та підміна ідентифікаторів..."
BACKUP_DIR="/tmp/vscode_backup_$(date +%s)"
mkdir -p "$BACKUP_DIR"
print_info "Бекап: $BACKUP_DIR"

# Machine-ID та Storage через common_functions
mkdir -p "$VSCODE_PATH"
mkdir -p "$VSCODE_PATH/User/globalStorage"
cleanup_editor_machine_id "vscode"
cleanup_editor_storage "vscode"
print_success "Ідентифікатори підмінено"

# Видалення кешів
cleanup_editor_caches "vscode"

# Збереження нової конфігурації
NEW_CONFIG_PATH="$CONFIGS_DIR/$NEW_HOSTNAME"
mkdir -p "$NEW_CONFIG_PATH/User/globalStorage"
[ -f "$VSCODE_PATH/machineid" ] && cp "$VSCODE_PATH/machineid" "$NEW_CONFIG_PATH/machineid"
[ -f "$VSCODE_PATH/storage.json" ] && cp "$VSCODE_PATH/storage.json" "$NEW_CONFIG_PATH/storage.json"
[ -f "$VSCODE_PATH/User/globalStorage/storage.json" ] && cp "$VSCODE_PATH/User/globalStorage/storage.json" "$NEW_CONFIG_PATH/User/globalStorage/storage.json"
echo "$NEW_HOSTNAME" > "$NEW_CONFIG_PATH/hostname.txt"
echo '{"name":"'$NEW_HOSTNAME'","created":"'$(date +%Y-%m-%d\ %H:%M:%S)'","hostname":"'$NEW_HOSTNAME'"}' > "$NEW_CONFIG_PATH/metadata.json"
print_success "Нову конфігурацію збережено: $NEW_HOSTNAME"

# 9. Розширення
print_step 9 $TOTAL_STEPS "Видалення розширень та даних..."
safe_remove ~/.vscode/extensions
safe_remove "$VSCODE_PATH/extensions"
safe_remove "$VSCODE_PATH/User"
safe_remove "$VSCODE_PATH/product.json"
safe_remove "$VSCODE_PATH/Local Storage"
safe_remove "$VSCODE_PATH/IndexedDB"
safe_remove "$VSCODE_PATH/Session Storage"
print_success "Розширення видалено"

# 10. Hostname (видалено - використовуйте hostname_spoof.sh)
print_step 10 $TOTAL_STEPS "Hostname..."
print_info "Для зміни hostname використовуйте: ./hostname_spoof.sh"
print_info "Поточний hostname: $(scutil --get HostName 2>/dev/null || echo 'не встановлено')"

# 11. Мережа
print_step 11 $TOTAL_STEPS "Мережеві ідентифікатори..."
sudo dscacheutil -flushcache 2>/dev/null
sudo killall -HUP mDNSResponder 2>/dev/null
sudo arp -a -d 2>/dev/null
print_success "Мережу оновлено"

# 12. Фінальне очищення
print_step 12 $TOTAL_STEPS "Фінальне очищення..."
find ~/Library -iname "*vscode*" -maxdepth 3 -not -path "*/Trash/*" -print0 2>/dev/null | xargs -0 rm -rf 2>/dev/null
find ~/.config -iname "*vscode*" -print0 2>/dev/null | xargs -0 rm -rf 2>/dev/null
sudo find /var/log -iname "*vscode*" -print0 2>/dev/null | sudo xargs -0 rm -rf 2>/dev/null
print_success "Фінальне очищення завершено"

# 13. АВТОМАТИЧНА ІНСТАЛЯЦІЯ VS CODE
print_step 13 $TOTAL_STEPS "Автоматична інсталяція VS Code..."
VSCODE_ZIP="$REPO_ROOT/VSCode-darwin-universal.zip"
VSCODE_APP_SOURCE="$REPO_ROOT/Visual Studio Code.app"

# Перевірка ZIP файлу
if [ -f "$VSCODE_ZIP" ]; then
    print_info "Знайдено VS Code ZIP: $(basename $VSCODE_ZIP)"
    print_info "Розпакування..."
    
    cd "$REPO_ROOT"
    unzip -o "$VSCODE_ZIP" > /dev/null
    
    if [ $? -eq 0 ] && [ -d "Visual Studio Code.app" ]; then
        print_success "ZIP розпаковано успішно"
        VSCODE_APP_SOURCE="$REPO_ROOT/Visual Studio Code.app"
    else
        print_error "Помилка розпакування ZIP"
    fi
fi

# Встановлення з .app
if [ -d "$VSCODE_APP_SOURCE" ]; then
    print_info "Знайдено VS Code додаток: $(basename "$VSCODE_APP_SOURCE")"
    print_info "Копіювання в /Applications..."
    
    # Видалити старий якщо існує
    [ -d "/Applications/Visual Studio Code.app" ] && sudo rm -rf "/Applications/Visual Studio Code.app"
    
    # Копіювання в Applications
    sudo cp -R "$VSCODE_APP_SOURCE" /Applications/
    
    if [ $? -eq 0 ]; then
        print_success "VS Code успішно встановлено в /Applications/"
        sleep 2
        
        # Очищення тимчасових файлів
        if [ -f "$VSCODE_ZIP" ] && [ -d "$REPO_ROOT/Visual Studio Code.app" ]; then
            rm -rf "$REPO_ROOT/Visual Studio Code.app"
            print_info "Тимчасові файли очищено"
        fi
    else
        print_error "Помилка копіювання додатку"
    fi
else
    print_warning "VS Code не знайдено"
    print_info "Переконайтесь що файл VSCode-darwin-universal.zip знаходиться в: $REPO_ROOT"
    print_info "Або скачайте VS Code вручну з: https://code.visualstudio.com/"
fi

# Додати запис в історію
if [ -f "$REPO_ROOT/history_tracker.sh" ]; then
    "$REPO_ROOT/history_tracker.sh" add "vscode" "cleanup" "Full cleanup completed" 2>/dev/null
fi

# Фінальний звіт
echo ""
print_header "ОЧИЩЕННЯ ТА ІНСТАЛЯЦІЯ ЗАВЕРШЕНО"
echo ""
print_info "📋 Виконано:"
print_success "Видалено всі файли VS Code"
print_success "Очищено Keychain"
print_success "Підмінено machine-id та device-id"
print_success "Оновлено мережу"
if [ -d "/Applications/Visual Studio Code.app" ]; then
    print_success "VS Code встановлено в /Applications/"
fi
echo ""
print_info "💾 Бекап: $BACKUP_DIR"
print_info "📂 Конфігурація: $NEW_CONFIG_PATH"
echo ""
print_info "🚀 ЗАПУСК VS CODE:"
print_info "   VS Code можна запускати ОДРАЗУ (перезавантаження НЕ потрібне)"
print_info "   Просто запустіть Visual Studio Code.app"
print_info "   При першому запуску він побачить вас як НОВОГО користувача"
echo ""

