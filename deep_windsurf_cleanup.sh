#!/bin/zsh

echo "=================================================="
echo "🚀 ГЛИБОКЕ ВИДАЛЕННЯ WINDSURF ДЛЯ НОВОГО КЛІЄНТА"
echo "=================================================="

# Функція для безпечного видалення
safe_remove() {
    if [ -e "$1" ]; then
        echo "🗑️  Видаляю: $1"
        rm -rf "$1" 2>/dev/null
    fi
}

# 1. ОСНОВНІ ПАПКИ WINDSURF
echo "\n[1/10] Видалення основних папок..."
safe_remove ~/Library/Application\ Support/Windsurf
safe_remove ~/Library/Application\ Support/windsurf
safe_remove ~/Library/Preferences/Windsurf
safe_remove ~/Library/Logs/Windsurf
safe_remove ~/.windsurf
safe_remove ~/.windsurf-server
safe_remove ~/.config/Windsurf
safe_remove ~/Library/Saved\ Application\ State/Windsurf.savedState
safe_remove ~/Library/Saved\ Application\ State/com.windsurf.savedState

# 2. ВИДАЛЕННЯ ДОДАТКУ
echo "\n[2/10] Видалення додатку Windsurf..."
safe_remove /Applications/Windsurf.app

# 3. КЕШІ ТА ТИМЧАСОВІ ФАЙЛИ
echo "\n[3/10] Очищення кешів і тимчасових файлів..."
safe_remove ~/Library/Caches/Windsurf
safe_remove ~/Library/Caches/windsurf
safe_remove ~/Library/Caches/com.windsurf.*
find ~/Library/Caches -iname "*windsurf*" -maxdepth 2 -exec rm -rf {} + 2>/dev/null

# 4. CONTAINERS І GROUP CONTAINERS
echo "\n[4/10] Видалення контейнерів..."
find ~/Library/Containers -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null
find ~/Library/Group\ Containers -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null

# 5. COOKIES ТА WEB DATA
echo "\n[5/10] Очищення cookies та веб-даних..."
find ~/Library/Cookies -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null
safe_remove ~/Library/WebKit/Windsurf

# 6. ВИДАЛЕННЯ PLIST-ФАЙЛІВ (НАЛАШТУВАННЯ)
echo "\n[6/10] Видалення plist-файлів налаштувань..."
find ~/Library/Preferences -iname "*windsurf*.plist" -delete 2>/dev/null
safe_remove ~/Library/Preferences/com.windsurf.plist
safe_remove ~/Library/Preferences/com.windsurf.helper.plist

# 7. ОЧИЩЕННЯ KEYCHAIN (КРИТИЧНО ДЛЯ ІДЕНТИФІКАЦІЇ!)
echo "\n[7/10] Очищення Keychain від записів Windsurf..."
echo "⚠️  Для видалення з Keychain потрібен пароль адміністратора"

# Видалення всіх записів Windsurf з keychain
security find-generic-password -l "Windsurf" 2>/dev/null | grep "keychain:" | while read -r line; do
    keychain=$(echo "$line" | sed 's/.*"\(.*\)".*/\1/')
    security delete-generic-password -l "Windsurf" "$keychain" 2>/dev/null
done

security find-generic-password -s "windsurf" 2>/dev/null | grep "keychain:" | while read -r line; do
    keychain=$(echo "$line" | sed 's/.*"\(.*\)".*/\1/')
    security delete-generic-password -s "windsurf" "$keychain" 2>/dev/null
done

# Видалення всіх інтернет-паролів Windsurf
security find-internet-password -s "windsurf" 2>/dev/null | grep "keychain:" | while read -r line; do
    keychain=$(echo "$line" | sed 's/.*"\(.*\)".*/\1/')
    security delete-internet-password -s "windsurf" "$keychain" 2>/dev/null
done

# Пошук і видалення за різними варіантами назв
for service in "Windsurf" "windsurf" "com.windsurf" "Windsurf Editor" "Codeium Windsurf"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
done

echo "✅ Keychain очищено"

# 8. РЕЗЕРВУВАННЯ ТА ПІДМІНА MACHINE-ID ТА DEVICE-ID
echo "\n[8/10] Резервування та підміна machine-id та device-id файлів..."

# Створення директорії для бекапів
BACKUP_DIR="/tmp/windsurf_backup_$(date +%s)"
mkdir -p "$BACKUP_DIR"
echo "📦 Директорія бекапів: $BACKUP_DIR"

# Функція для генерації випадкового UUID
generate_uuid() {
    uuidgen | tr '[:upper:]' '[:lower:]'
}

# Функція для генерації випадкового machine-id (hex формат)
generate_machine_id() {
    openssl rand -hex 32
}

# Резервування та підміна machineid
MACHINEID_PATH=~/Library/Application\ Support/Windsurf/machineid
if [ -f "$MACHINEID_PATH" ]; then
    echo "💾 Резервую machine-id..."
    cp "$MACHINEID_PATH" "$BACKUP_DIR/machineid.bak"
    NEW_MACHINE_ID=$(generate_machine_id)
    echo "$NEW_MACHINE_ID" > "$MACHINEID_PATH"
    echo "✅ Machine-ID підмінено на новий"
else
    echo "ℹ️  Machine-ID файл не знайдено"
fi

# Резервування та підміна storage.json
STORAGE_PATHS=(
    ~/Library/Application\ Support/Windsurf/storage.json
    ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json
)

for STORAGE_PATH in "${STORAGE_PATHS[@]}"; do
    if [ -f "$STORAGE_PATH" ]; then
        echo "💾 Резервую storage: $STORAGE_PATH"
        STORAGE_FILENAME=$(basename "$STORAGE_PATH")
        STORAGE_DIRNAME=$(dirname "$STORAGE_PATH" | sed 's/.*Windsurf\///')
        BACKUP_SUBDIR="$BACKUP_DIR/$(echo $STORAGE_DIRNAME | tr '/' '_')"
        mkdir -p "$BACKUP_SUBDIR"
        cp "$STORAGE_PATH" "$BACKUP_SUBDIR/${STORAGE_FILENAME}.bak"
        
        # Генерація нового storage.json з фейковими даними
        NEW_DEVICE_ID=$(generate_uuid)
        NEW_SESSION_ID=$(generate_uuid)
        cat > "$STORAGE_PATH" << EOF
{
  "telemetry.machineId": "$(generate_machine_id)",
  "telemetry.macMachineId": "$(generate_machine_id)",
  "telemetry.devDeviceId": "$NEW_DEVICE_ID",
  "telemetry.sqmId": "{$(generate_uuid)}",
  "install.time": "$(date +%s)000",
  "sessionId": "$NEW_SESSION_ID"
}
EOF
        echo "✅ Storage підмінено на новий: $STORAGE_PATH"
    fi
done

# Видалення кешів (їх не потрібно відновлювати)
safe_remove ~/Library/Application\ Support/Windsurf/User/workspaceStorage
safe_remove ~/Library/Application\ Support/Windsurf/GPUCache
safe_remove ~/Library/Application\ Support/Windsurf/CachedData
safe_remove ~/Library/Application\ Support/Windsurf/Code\ Cache

# Видалення всіх логів
find ~/Library/Application\ Support/Windsurf -name "*.log" -delete 2>/dev/null

echo "📁 Бекапи збережено в: $BACKUP_DIR"

# 9. ОЧИЩЕННЯ ГЛОБАЛЬНИХ НАЛАШТУВАНЬ ТА РОЗШИРЕНЬ
echo "\n[9/10] Видалення розширень та глобальних налаштувань..."
safe_remove ~/.windsurf/extensions
safe_remove ~/.vscode-windsurf
safe_remove ~/Library/Application\ Support/Windsurf/extensions
safe_remove ~/Library/Application\ Support/Windsurf/User

# Видалення продуктових ідентифікаторів
safe_remove ~/Library/Application\ Support/Windsurf/product.json

# 10. ЗМІНА СИСТЕМНИХ ІДЕНТИФІКАТОРІВ
echo "\n[10/10] Зміна системних ідентифікаторів..."

# Зміна hostname (тимчасово на 5 годин)
NEW_HOSTNAME="And-MAC"
ORIGINAL_HOSTNAME=$(scutil --get HostName 2>/dev/null || echo "DEVs-Mac-Studio")

echo "🔄 Зміна hostname на $NEW_HOSTNAME на 5 годин..."
echo "📝 Оригінальний hostname: $ORIGINAL_HOSTNAME"

sudo scutil --set HostName "$NEW_HOSTNAME"
sudo scutil --set LocalHostName "$NEW_HOSTNAME"
sudo scutil --set ComputerName "$NEW_HOSTNAME"

# Очищення DNS кешу
echo "🔄 Очищення DNS кешу..."
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Повернення hostname у фоні через 5 годин (18000 секунд)
(
    sleep 18000
    echo "\n⏰ 5 годин минуло. Відновлення оригінальних налаштувань..."
    
    # Відновлення hostname
    echo "🔄 Повертаю оригінальний hostname: $ORIGINAL_HOSTNAME"
    sudo scutil --set HostName "$ORIGINAL_HOSTNAME"
    sudo scutil --set LocalHostName "$ORIGINAL_HOSTNAME"
    sudo scutil --set ComputerName "$ORIGINAL_HOSTNAME"
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder
    
    # Відновлення machine-id та storage файлів
    if [ -d "$BACKUP_DIR" ]; then
        echo "🔄 Відновлення machine-id та storage файлів з бекапу..."
        
        # Відновлення machineid
        if [ -f "$BACKUP_DIR/machineid.bak" ]; then
            MACHINEID_PATH=~/Library/Application\ Support/Windsurf/machineid
            mkdir -p "$(dirname "$MACHINEID_PATH")"
            cp "$BACKUP_DIR/machineid.bak" "$MACHINEID_PATH"
            echo "✅ Machine-ID відновлено"
        fi
        
        # Відновлення storage.json файлів
        find "$BACKUP_DIR" -name "*.json.bak" | while read -r backup_file; do
            # Визначення оригінального шляху
            if [[ "$backup_file" == *"User_globalStorage"* ]]; then
                RESTORE_PATH=~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json
            else
                RESTORE_PATH=~/Library/Application\ Support/Windsurf/storage.json
            fi
            
            mkdir -p "$(dirname "$RESTORE_PATH")"
            cp "$backup_file" "$RESTORE_PATH"
            echo "✅ Storage відновлено: $RESTORE_PATH"
        done
        
        echo "🧹 Видалення директорії бекапів..."
        rm -rf "$BACKUP_DIR"
        echo "✅ Всі оригінальні налаштування відновлено!"
    else
        echo "⚠️  Директорія бекапів не знайдена: $BACKUP_DIR"
    fi
    
    echo "\n🎉 Відновлення завершено! Система повернута до оригінального стану."
) &

RESTORE_PID=$!
echo "✅ Hostname змінено. Процес відновлення (PID: $RESTORE_PID) запущено у фоні"
echo "📁 Бекапи буде видалено після відновлення через 5 годин"

# ФІНАЛЬНЕ ОЧИЩЕННЯ
echo "\n🧹 Фінальне очищення залишкових файлів..."
find ~/Library -iname "*windsurf*" -maxdepth 3 -not -path "*/Trash/*" -exec rm -rf {} + 2>/dev/null
find ~/.config -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null

# Очищення системних логів
sudo rm -rf /var/log/*windsurf* 2>/dev/null
sudo rm -rf /Library/Logs/*windsurf* 2>/dev/null

echo "\n=================================================="
echo "✅ ОЧИЩЕННЯ ЗАВЕРШЕНО УСПІШНО!"
echo "=================================================="
echo ""
echo "📋 Виконані дії:"
echo "   ✓ Видалено всі файли Windsurf"
echo "   ✓ Очищено Keychain від записів Windsurf"
echo "   ✓ Створено бекап та підмінено machine-id на новий"
echo "   ✓ Створено бекап та підмінено device-id на новий"
echo "   ✓ Очищено всі кеші та тимчасові файли"
echo "   ✓ Видалено розширення та налаштування"
echo "   ✓ Змінено hostname на $NEW_HOSTNAME"
echo "   ✓ Очищено DNS кеш"
echo ""
echo "💾 Інформація про бекапи:"
echo "   • Директорія: $BACKUP_DIR"
echo "   • Machine-ID: $([ -f "$BACKUP_DIR/machineid.bak" ] && echo "✓ збережено" || echo "✗ не знайдено")"
echo "   • Storage файли: $(find "$BACKUP_DIR" -name "*.json.bak" 2>/dev/null | wc -l | xargs) шт."
echo ""
echo "⏰ АВТОМАТИЧНЕ ВІДНОВЛЕННЯ:"
echo "   • Через 5 годин всі оригінальні ідентифікатори буде відновлено"
echo "   • Hostname повернеться до: '$ORIGINAL_HOSTNAME'"
echo "   • Бекапи буде автоматично видалено після відновлення"
echo "   • PID процесу відновлення: $RESTORE_PID"
echo ""
echo "⚠️  ВАЖЛИВО:"
echo "   • НЕ перезавантажуйте Mac якщо хочете автовідновлення!"
echo "   • Windsurf тепер сприйме систему як НОВОГО клієнта"
echo "   • Для ручного відновлення: cp $BACKUP_DIR/* до відповідних директорій"
echo ""
echo "🔄 Для перезавантаження (вимкне автовідновлення): sudo shutdown -r now"
echo "📊 Для перевірки процесу відновлення: ps -p $RESTORE_PID"
echo "=================================================="