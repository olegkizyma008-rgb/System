#!/bin/zsh

echo "=================================================="
echo "🚀 ГЛИБОКЕ ВИДАЛЕННЯ WINDSURF ДЛЯ НОВОГО КЛІЄНТА"
echo "=================================================="

# Директорії для конфігурацій
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIGS_DIR="$SCRIPT_DIR/configs"
ORIGINAL_CONFIG="$CONFIGS_DIR/original"

# ПОПЕРЕДНЬО: Генерація унікального hostname з реальною назвою (без підозрілих цифр)
# Формат: <CommonName>-<RandomName> (наприклад: Alex-Studio, James-Desktop)
# Список реальних імен:
REAL_NAMES=("Alex" "James" "Michael" "David" "Robert" "John" "Richard" "Charles" "Daniel" "Matthew" "Anthony" "Mark" "Donald" "Steven" "Paul" "Andrew" "Joshua" "Kenneth" "Kevin" "Brian" "George" "Edward" "Ronald" "Timothy" "Jason" "Jeffrey" "Ryan" "Jacob" "Gary" "Nicholas" "Eric" "Jonathan" "Stephen" "Larry" "Justin" "Scott" "Brandon" "Benjamin" "Samuel" "Frank" "Gregory" "Alexander" "Patrick" "Dennis" "Jerry" "Tyler" "Aaron" "Jose" "Adam" "Henry")
PLACE_NAMES=("Studio" "Office" "Desktop" "Workspace" "Workstation" "Lab" "Server" "Machine" "System" "Device" "Node" "Box" "Computer" "Platform" "Station" "Terminal" "Host" "Client" "Instance" "Pod")

# Вибір випадкових імені та місця
RANDOM_NAME=${REAL_NAMES[$((RANDOM % ${#REAL_NAMES[@]}))]}
RANDOM_PLACE=${PLACE_NAMES[$((RANDOM % ${#PLACE_NAMES[@]}))]}
NEW_HOSTNAME="${RANDOM_NAME}-${RANDOM_PLACE}"

# Отримання оригінального hostname
ORIGINAL_HOSTNAME=$(scutil --get HostName 2>/dev/null || echo "DEVs-Mac-Studio")

# Створити директорії якщо не існують
mkdir -p "$CONFIGS_DIR"

# Функція для безпечного видалення
safe_remove() {
    if [ -e "$1" ]; then
        echo "🗑️  Видаляю: $1"
        rm -rf "$1" 2>/dev/null
    fi
}

# Функція для збереження поточної конфігурації як оригінал
save_as_original() {
    echo "\n💎 Збереження поточної конфігурації як ОРИГІНАЛ..."
    
    mkdir -p "$ORIGINAL_CONFIG/User/globalStorage"
    
    # Зберегти Machine-ID
    if [ -f ~/Library/Application\ Support/Windsurf/machineid ]; then
        cp ~/Library/Application\ Support/Windsurf/machineid "$ORIGINAL_CONFIG/machineid"
        echo "  ✓ Machine-ID збережено"
    fi
    
    # Зберегти Storage
    if [ -f ~/Library/Application\ Support/Windsurf/storage.json ]; then
        cp ~/Library/Application\ Support/Windsurf/storage.json "$ORIGINAL_CONFIG/storage.json"
        echo "  ✓ Storage збережено"
    fi
    
    # Зберегти Global Storage
    if [ -f ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json ]; then
        cp ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json "$ORIGINAL_CONFIG/User/globalStorage/storage.json"
        echo "  ✓ Global Storage збережено"
    fi
    
    # Зберегти hostname
    ORIGINAL_HOSTNAME=$(scutil --get HostName 2>/dev/null || echo "DEVs-Mac-Studio")
    echo "$ORIGINAL_HOSTNAME" > "$ORIGINAL_CONFIG/hostname.txt"
    echo "  ✓ Hostname збережено: $ORIGINAL_HOSTNAME"
    
    # Метадані
    cat > "$ORIGINAL_CONFIG/metadata.json" << EOF
{
  "name": "original",
  "created": "$(date +%Y-%m-%d\ %H:%M:%S)",
  "hostname": "$ORIGINAL_HOSTNAME",
  "description": "Original Windsurf configuration for auto-restore"
}
EOF
    
    echo "✅ Оригінальна конфігурація збережена!"
}

# Перевірити чи існує оригінальна конфігурація, якщо ні - зберегти
if [ ! -d "$ORIGINAL_CONFIG" ]; then
    echo "\n⚠️  Оригінальна конфігурація не знайдена!"
    echo "📦 Зберігаю поточний стан як ОРИГІНАЛ..."
    save_as_original
fi

# 1. ОСНОВНІ ПАПКИ WINDSURF (окрім Application Support - його очистимо пізніше)
echo "\n[1/10] Видалення основних папок..."
safe_remove ~/Library/Application\ Support/windsurf
safe_remove ~/Library/Preferences/Windsurf
safe_remove ~/Library/Logs/Windsurf
safe_remove ~/.windsurf
safe_remove ~/.windsurf-server
safe_remove ~/.config/Windsurf
safe_remove ~/Library/Saved\ Application\ State/Windsurf.savedState
safe_remove ~/Library/Saved\ Application\ State/com.windsurf.savedState

echo "ℹ️  Application Support/Windsurf буде очищено пізніше (після резервування)"

# 2. ВИДАЛЕННЯ ДОДАТКУ
echo "\n[2/10] Видалення додатку Windsurf..."
echo "⚠️  ВАЖЛИВО: Додаток Windsurf буде ВИДАЛЕНО!"
echo "💡 Після cleanup потрібно буде скачати та встановити Windsurf заново"
safe_remove /Applications/Windsurf.app
echo "✅ Додаток видалено з /Applications"

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

# ДОДАТКОВО: Очищення всіх баз даних та сховищ ДО резервування
echo "\n🗑️  Очищення баз даних та локальних сховищ (перед резервуванням)..."
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb.backup
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb-shm
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb-wal
safe_remove ~/Library/Application\ Support/Windsurf/Local\ Storage
safe_remove ~/Library/Application\ Support/Windsurf/Session\ Storage
safe_remove ~/Library/Application\ Support/Windsurf/IndexedDB
safe_remove ~/Library/Application\ Support/Windsurf/databases
echo "✅ Бази даних очищено"

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

# Зберегти НОВУ конфігурацію в configs/
echo "\n💾 Збереження нової конфігурації..."
NEW_CONFIG_NAME="$NEW_HOSTNAME"
NEW_CONFIG_PATH="$CONFIGS_DIR/$NEW_CONFIG_NAME"
mkdir -p "$NEW_CONFIG_PATH/User/globalStorage"

# Копіювати нові ідентифікатори
if [ -f ~/Library/Application\ Support/Windsurf/machineid ]; then
    cp ~/Library/Application\ Support/Windsurf/machineid "$NEW_CONFIG_PATH/machineid"
fi

if [ -f ~/Library/Application\ Support/Windsurf/storage.json ]; then
    cp ~/Library/Application\ Support/Windsurf/storage.json "$NEW_CONFIG_PATH/storage.json"
fi

if [ -f ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json ]; then
    cp ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json "$NEW_CONFIG_PATH/User/globalStorage/storage.json"
fi

# Зберегти новий hostname
echo "$NEW_HOSTNAME" > "$NEW_CONFIG_PATH/hostname.txt"

# Метадані
cat > "$NEW_CONFIG_PATH/metadata.json" << EOF
{
  "name": "$NEW_CONFIG_NAME",
  "created": "$(date +%Y-%m-%d\ %H:%M:%S)",
  "hostname": "$NEW_HOSTNAME",
  "description": "Auto-generated Windsurf profile"
}
EOF

echo "✅ Нову конфігурацію збережено: $NEW_CONFIG_NAME"
echo "📂 Локація: $NEW_CONFIG_PATH"

# 9. ОЧИЩЕННЯ ГЛОБАЛЬНИХ НАЛАШТУВАНЬ ТА РОЗШИРЕНЬ
echo "\n[9/10] Видалення розширень та глобальних налаштувань..."
safe_remove ~/.windsurf/extensions
safe_remove ~/.vscode-windsurf
safe_remove ~/Library/Application\ Support/Windsurf/extensions
safe_remove ~/Library/Application\ Support/Windsurf/User

# Видалення продуктових ідентифікаторів
safe_remove ~/Library/Application\ Support/Windsurf/product.json

# КРИТИЧНО: Видалення всіх файлів де може зберігатися API ключ Codeium
echo "🔐 Очищення всіх можливих місць зберігання API ключів..."
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb.backup
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb-shm
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb-wal
safe_remove ~/Library/Application\ Support/Windsurf/User/workspaceStorage
safe_remove ~/Library/Application\ Support/Windsurf/User/globalStorage
safe_remove ~/Library/Application\ Support/Windsurf/Local\ Storage
safe_remove ~/Library/Application\ Support/Windsurf/IndexedDB
safe_remove ~/Library/Application\ Support/Windsurf/Session\ Storage

# Видалення всіх можливих Codeium токенів з Keychain
echo "🔑 Видалення Codeium токенів з Keychain..."
for service in "Codeium" "codeium" "codeium.com" "api.codeium.com" "Codeium Windsurf" "codeium-windsurf"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
    security delete-generic-password -l "$service" 2>/dev/null
done

echo "✅ API ключі та токени очищено"

# 10. ЗМІНА СИСТЕМНИХ ІДЕНТИФІКАТОРІВ
echo "\n[10/10] Зміна системних ідентифікаторів..."

echo "🔄 Зміна hostname з $ORIGINAL_HOSTNAME на $NEW_HOSTNAME на 5 годин..."
echo "📝 Оригінальний hostname: $ORIGINAL_HOSTNAME"
echo "🎲 Новий унікальний hostname: $NEW_HOSTNAME"

sudo scutil --set HostName "$NEW_HOSTNAME"
sudo scutil --set LocalHostName "$NEW_HOSTNAME"
sudo scutil --set ComputerName "$NEW_HOSTNAME"

# Очищення DNS кешу
echo "🔄 Очищення DNS кешу..."
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder 2>/dev/null

# Повернення hostname у фоні через 5 годин (18000 секунд)
# Запуск у фоні з перенаправленням логів
{
    sleep 18000
    echo "\n⏰ 5 годин минуло. Відновлення оригінальних налаштувань..."
    
    # Отримання оригінального hostname
    if [ -f "$ORIGINAL_CONFIG/hostname.txt" ]; then
        SAVED_HOSTNAME=$(cat "$ORIGINAL_CONFIG/hostname.txt")
    else
        SAVED_HOSTNAME="$ORIGINAL_HOSTNAME"
    fi
    
    # Відновлення hostname
    echo "🔄 Повертаю оригінальний hostname: $SAVED_HOSTNAME"
    sudo scutil --set HostName "$SAVED_HOSTNAME"
    sudo scutil --set LocalHostName "$SAVED_HOSTNAME"
    sudo scutil --set ComputerName "$SAVED_HOSTNAME"
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder 2>/dev/null
    
    # Відновлення ОРИГІНАЛЬНОЇ конфігурації з configs/original
    if [ -d "$ORIGINAL_CONFIG" ]; then
        echo "🔄 Відновлення ОРИГІНАЛЬНОЇ конфігурації..."
        
        # Відновлення machineid
        if [ -f "$ORIGINAL_CONFIG/machineid" ]; then
            MACHINEID_PATH=~/Library/Application\ Support/Windsurf/machineid
            mkdir -p "$(dirname "$MACHINEID_PATH")"
            cp "$ORIGINAL_CONFIG/machineid" "$MACHINEID_PATH"
            echo "✅ Machine-ID відновлено з оригіналу"
        fi
        
        # Відновлення storage.json
        if [ -f "$ORIGINAL_CONFIG/storage.json" ]; then
            RESTORE_PATH=~/Library/Application\ Support/Windsurf/storage.json
            mkdir -p "$(dirname "$RESTORE_PATH")"
            cp "$ORIGINAL_CONFIG/storage.json" "$RESTORE_PATH"
            echo "✅ Storage відновлено з оригіналу"
        fi
        
        # Відновлення global storage
        if [ -f "$ORIGINAL_CONFIG/User/globalStorage/storage.json" ]; then
            RESTORE_PATH=~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json
            mkdir -p "$(dirname "$RESTORE_PATH")"
            cp "$ORIGINAL_CONFIG/User/globalStorage/storage.json" "$RESTORE_PATH"
            echo "✅ Global Storage відновлено з оригіналу"
        fi
        
        echo "✅ Оригінальна конфігурація повністю відновлена!"
    else
        echo "⚠️  Оригінальна конфігурація не знайдена в $ORIGINAL_CONFIG"
    fi
    
    # Відновлення з тимчасового бекапу (для сумісності)
    if [ -d "$BACKUP_DIR" ]; then
        echo "🔄 Видалення тимчасового бекапу..."
        rm -rf "$BACKUP_DIR"
        echo "✅ Бекап видалено"
    fi
    
    echo "\n🎉 Відновлення завершено! Система повернута до оригінального стану."
} > /tmp/windsurf_restore_$$.log 2>&1 &

RESTORE_PID=$!
echo ""
echo "✅ Hostname змінено на: $NEW_HOSTNAME"
echo "📋 Процес автовідновлення запущено (PID: $RESTORE_PID)"
echo "⏰ Оригінальні налаштування будуть відновлено за 5 годин"
echo ""

# ФІНАЛЬНЕ ОЧИЩЕННЯ
echo "\n🧹 Фінальне очищення залишкових файлів..."
find ~/Library -iname "*windsurf*" -maxdepth 3 -not -path "*/Trash/*" -exec rm -rf {} + 2>/dev/null
find ~/.config -iname "*windsurf*" -exec rm -rf {} + 2>/dev/null

# Очищення системних логів
sudo rm -rf /var/log/*windsurf* 2>/dev/null
sudo rm -rf /Library/Logs/*windsurf* 2>/dev/null

# КРИТИЧНО: Повне видалення Application Support/Windsurf (після збереження всіх бекапів)
echo "\n🔥 КРИТИЧНЕ ОЧИЩЕННЯ: Видалення всієї папки Application Support/Windsurf..."
echo "⚠️  Це видалить ВСІ дані включно з базами даних де зберігаються API ключі!"
safe_remove ~/Library/Application\ Support/Windsurf
echo "✅ Application Support/Windsurf повністю видалено"

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
echo "   • Тимчасовий бекап: $BACKUP_DIR"
echo "   • Machine-ID: $([ -f "$BACKUP_DIR/machineid.bak" ] && echo "✓ збережено" || echo "✗ не знайдено")"
echo "   • Storage файли: $(find "$BACKUP_DIR" -name "*.json.bak" 2>/dev/null | wc -l | xargs) шт."
echo ""
echo "🔧 СИСТЕМА КОНФІГУРАЦІЙ:"
echo "   • Оригінальна конфігурація: збережена в configs/original"
echo "   • Нова конфігурація: $NEW_CONFIG_NAME"
echo "   • Локація: $CONFIGS_DIR"
echo "   • Управління: ./manage_configs.sh"
echo ""
echo "⏰ АВТОМАТИЧНЕ ВІДНОВЛЕННЯ:"
echo "   • Через 5 годин буде відновлена ОРИГІНАЛЬНА конфігурація"
echo "   • Hostname повернеться до оригінального"
echo "   • Machine-ID та Device-ID повернуться до оригіналу"
echo "   • PID процесу відновлення: $RESTORE_PID"
echo ""
echo "💡 УПРАВЛІННЯ КОНФІГУРАЦІЯМИ:"
echo "   • Запустіть: ./manage_configs.sh"
echo "   • Перемикайтеся між будь-якими збереженими профілями"
echo "   • Зберігайте необмежену кількість конфігурацій"
echo ""
echo "⚠️  ВАЖЛИВО:"
echo "   • НЕ перезавантажуйте Mac якщо хочете автовідновлення!"
echo "   • Windsurf тепер сприйме систему як НОВОГО клієнта"
echo "   • Для ручного відновлення: cp $BACKUP_DIR/* до відповідних директорій"
echo ""
echo "� ІНСТАЛЯЦІЯ WINDSURF:"
echo "   • Windsurf можна встановлювати та запускати ОДРАЗУ (перезавантаження НЕ потрібне)"
echo "   • Скачайте з: https://codeium.com/windsurf"
echo "   • Або якщо вже встановлений: просто запустіть Windsurf.app"
echo "   • При першому запуску він побачить вас як НОВОГО користувача"
echo ""
echo "💡 РЕКОМЕНДАЦІЇ:"
echo "   • Якщо Windsurf вже запущений - закрийте його перед cleanup"
echo "   • Після cleanup - зачекайте 5-10 секунд перед запуском Windsurf"
echo "   • При першому запуску може попросити авторизацію - це нормально"
echo ""
echo "�🔄 Для перезавантаження (вимкне автовідновлення): sudo shutdown -r now"
echo "📊 Для перевірки процесу відновлення: ps -p $RESTORE_PID"
echo "=================================================="