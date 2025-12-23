#!/bin/zsh

echo "=================================================="
echo "📊 ІНФОРМАЦІЯ ПРО VS CODE БЕКАПИ"
echo "=================================================="

# Пошук всіх бекапів
BACKUPS=($(ls -td /tmp/vscode_backup_* 2>/dev/null))

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo "❌ Бекапи не знайдено в /tmp"
    echo "💡 Можливі причини:"
    echo "   • Система була перезавантажена"
    echo "   • Cleanup ще не запускався"
    echo "   • Бекапи були видалені"
else
    echo "📁 Знайдено бекапів: ${#BACKUPS[@]}"
    echo ""
    
    for backup in "${BACKUPS[@]}"; do
        TIMESTAMP=$(echo $backup | grep -o '[0-9]*$')
        BACKUP_DATE=$(date -r $TIMESTAMP +%d.%m.%Y\ %H:%M:%S 2>/dev/null || echo "Невідома дата")
        BACKUP_SIZE=$(du -sh "$backup" 2>/dev/null | awk '{print $1}')
        BACKUP_NAME=$(basename $backup)
        
        echo "📦 Бекап: $BACKUP_NAME"
        echo "📅 Дата створення: $BACKUP_DATE"
        echo "💾 Розмір: $BACKUP_SIZE"
        
        # Перевірка вмісту
        if [ -f "$backup/machineid.bak" ]; then
            MACHINEID_SIZE=$(wc -c < "$backup/machineid.bak" | xargs)
            echo "   ✓ machineid.bak (${MACHINEID_SIZE}B)"
        fi
        
        STORAGE_COUNT=$(find "$backup" -name "storage.json.bak" 2>/dev/null | wc -l | xargs)
        if [ $STORAGE_COUNT -gt 0 ]; then
            echo "   ✓ storage файлів: $STORAGE_COUNT шт."
        fi
        
        echo ""
    done
fi

# Перевірка процесу автовідновлення
echo "⏰ Процес автовідновлення:"
RESTORE_PROCESS=$(ps aux | grep "sleep 18000" | grep "vscode_restore" | grep -v grep)
if [ -n "$RESTORE_PROCESS" ]; then
    RESTORE_PID=$(echo "$RESTORE_PROCESS" | awk '{print $2}')
    echo "✓ Процес активний"
    echo "   PID: $RESTORE_PID"
    
    # Спроба отримати час запуску
    START_TIME=$(ps -p $RESTORE_PID -o lstart= 2>/dev/null)
    if [ -n "$START_TIME" ]; then
        echo "   Запущено: $START_TIME"
    fi
else
    echo "✗ Процес не знайдено"
    echo "   Можливо відновлення вже відбулось або було зупинено"
fi

# Перевірка збережених конфігурацій
echo "\n📂 Збережені конфігурації:"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
if [ ! -f "$REPO_ROOT/cleanup_modules.json" ] && [ -f "$SCRIPT_DIR/../cleanup_modules.json" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
CONFIGS_DIR="$REPO_ROOT/configs_vscode"

if [ -d "$CONFIGS_DIR" ]; then
    CONFIG_COUNT=$(ls -1 "$CONFIGS_DIR" 2>/dev/null | wc -l | xargs)
    echo "📁 Знайдено конфігурацій: $CONFIG_COUNT"
    
    for config_dir in "$CONFIGS_DIR"/*; do
        if [ -d "$config_dir" ]; then
            CONFIG_NAME=$(basename "$config_dir")
            if [ -f "$config_dir/metadata.json" ]; then
                CONFIG_CREATED=$(grep created "$config_dir/metadata.json" | cut -d'"' -f4)
                CONFIG_HOSTNAME=$(grep hostname "$config_dir/metadata.json" | cut -d'"' -f4)
                echo "   • $CONFIG_NAME"
                echo "     Hostname: $CONFIG_HOSTNAME"
                echo "     Створено: $CONFIG_CREATED"
            else
                echo "   • $CONFIG_NAME (без метаданих)"
            fi
        fi
    done
else
    echo "❌ Папка конфігурацій не знайдена"
fi

# Поточний стан системи
echo "\n🖥️  Поточний стан системи:"
CURRENT_HOSTNAME=$(scutil --get HostName 2>/dev/null || echo "Не встановлено")
echo "   Hostname: $CURRENT_HOSTNAME"

if [ -f ~/Library/Application\ Support/Code/machineid ]; then
    MACHINEID_SIZE=$(wc -c < ~/Library/Application\ Support/Code/machineid | xargs)
    echo "   Machine-ID: Присутній (${MACHINEID_SIZE}B)"
else
    echo "   Machine-ID: Відсутній"
fi

if [ -d ~/Library/Application\ Support/Code ]; then
    VSCODE_SIZE=$(du -sh ~/Library/Application\ Support/Code 2>/dev/null | awk '{print $1}')
    echo "   VS Code Support: $VSCODE_SIZE"
else
    echo "   VS Code Support: Відсутній"
fi

echo "\n=================================================="
echo "💡 Команди:"
echo "   ./restore_vscode_backup.sh  - Відновити з бекапу"
echo "   ./deep_vscode_cleanup.sh    - Запустити cleanup"
echo "=================================================="
