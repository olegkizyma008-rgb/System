#!/bin/zsh

echo "=================================================="
echo "📊 ІНФОРМАЦІЯ ПРО WINDSURF БЕКАПИ"
echo "=================================================="

# Пошук всіх директорій бекапів
BACKUP_DIRS=($(ls -td /tmp/windsurf_backup_* 2>/dev/null))

if [ ${#BACKUP_DIRS[@]} -eq 0 ]; then
    echo "❌ Директорії бекапів не знайдено"
    echo "   Шукав у: /tmp/windsurf_backup_*"
    exit 1
fi

echo "📁 Знайдено бекапів: ${#BACKUP_DIRS[@]}"
echo ""

for BACKUP_DIR in "${BACKUP_DIRS[@]}"; do
    TIMESTAMP=$(basename "$BACKUP_DIR" | sed 's/windsurf_backup_//')
    BACKUP_DATE=$(date -r "$TIMESTAMP" "+%d.%m.%Y %H:%M:%S" 2>/dev/null || echo "невідомо")
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Бекап #$(basename "$BACKUP_DIR")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📅 Дата створення: $BACKUP_DATE"
    echo "📂 Шлях: $BACKUP_DIR"
    echo "💾 Розмір: $BACKUP_SIZE"
    echo ""
    echo "📄 Вміст:"
    
    # Перевірка наявності файлів
    if [ -f "$BACKUP_DIR/machineid.bak" ]; then
        MACHINE_ID_SIZE=$(ls -lh "$BACKUP_DIR/machineid.bak" 2>/dev/null | awk '{print $5}')
        echo "   ✓ machineid.bak ($MACHINE_ID_SIZE)"
    else
        echo "   ✗ machineid.bak (відсутній)"
    fi
    
    # Підрахунок storage файлів
    STORAGE_COUNT=$(find "$BACKUP_DIR" -name "*.json.bak" 2>/dev/null | wc -l | xargs)
    if [ "$STORAGE_COUNT" -gt 0 ]; then
        echo "   ✓ storage файлів: $STORAGE_COUNT шт."
        find "$BACKUP_DIR" -name "*.json.bak" | while read -r file; do
            FILE_SIZE=$(ls -lh "$file" 2>/dev/null | awk '{print $5}')
            echo "     - $(basename "$(dirname "$file")")/$(basename "$file") ($FILE_SIZE)"
        done
    else
        echo "   ✗ storage файли (відсутні)"
    fi
    
    echo ""
done

# Перевірка процесу автовідновлення
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏰ Процес автовідновлення:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Пошук процесу з sleep 18000
RESTORE_PROCESS=$(ps aux | grep "sleep 18000" | grep -v grep)
if [ -n "$RESTORE_PROCESS" ]; then
    RESTORE_PID=$(echo "$RESTORE_PROCESS" | awk '{print $2}')
    PROCESS_START=$(ps -p "$RESTORE_PID" -o lstart= 2>/dev/null)
    
    echo "✓ Процес активний"
    echo "   PID: $RESTORE_PID"
    echo "   Запущено: $PROCESS_START"
    echo ""
    echo "💡 Команди:"
    echo "   • Перевірити статус: ps -p $RESTORE_PID"
    echo "   • Припинити автовідновлення: kill $RESTORE_PID"
    echo "   • Відновити вручну зараз: ./restore_windsurf_backup.sh"
else
    echo "✗ Процес не активний"
    echo "   Автовідновлення не заплановано або вже виконано"
fi

echo ""
echo "=================================================="
