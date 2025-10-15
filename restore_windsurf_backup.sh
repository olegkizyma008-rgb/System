#!/bin/zsh

echo "=================================================="
echo "🔄 РУЧНЕ ВІДНОВЛЕННЯ WINDSURF БЕКАПІВ"
echo "=================================================="

# Пошук найновішої директорії бекапу
BACKUP_DIR=$(ls -td /tmp/windsurf_backup_* 2>/dev/null | head -1)

if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Директорія бекапів не знайдена!"
    echo "   Шукав у: /tmp/windsurf_backup_*"
    echo ""
    echo "💡 Можливі причини:"
    echo "   • Бекапи вже відновлено автоматично"
    echo "   • Систему було перезавантажено (бекапи у /tmp видаляються)"
    echo "   • Бекапи було вручну видалено"
    exit 1
fi

echo "📁 Знайдено директорію бекапів: $BACKUP_DIR"
echo ""

# Відображення вмісту бекапу
echo "📦 Вміст бекапу:"
ls -lh "$BACKUP_DIR"
echo ""

read "response?Відновити ці файли? (y/n): "
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "❌ Відновлення скасовано"
    exit 0
fi

echo ""
echo "🔄 Розпочинаю відновлення..."

# Відновлення machineid
if [ -f "$BACKUP_DIR/machineid.bak" ]; then
    MACHINEID_PATH=~/Library/Application\ Support/Windsurf/machineid
    mkdir -p "$(dirname "$MACHINEID_PATH")"
    cp "$BACKUP_DIR/machineid.bak" "$MACHINEID_PATH"
    echo "✅ Machine-ID відновлено"
else
    echo "⚠️  Machine-ID бекап не знайдено"
fi

# Відновлення storage.json файлів
RESTORED_COUNT=0
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
    ((RESTORED_COUNT++))
done

echo ""
read "response?Видалити директорію бекапів? (y/n): "
if [[ "$response" =~ ^[Yy]$ ]]; then
    rm -rf "$BACKUP_DIR"
    echo "🗑️  Директорію бекапів видалено"
else
    echo "💾 Директорія бекапів збережена: $BACKUP_DIR"
fi

echo ""
echo "=================================================="
echo "✅ ВІДНОВЛЕННЯ ЗАВЕРШЕНО!"
echo "=================================================="
echo ""
echo "ℹ️  Відновлені ідентифікатори:"
echo "   • Windsurf тепер розпізнає цю систему як попереднього клієнта"
echo "   • Machine-ID та Device-ID повернуто до оригінальних значень"
echo ""
echo "🔄 Для набуття чинності перезапустіть Windsurf"
echo "=================================================="
