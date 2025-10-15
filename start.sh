#!/bin/zsh

# ⚡ ШВИДКИЙ СТАРТ WINDSURF CLEANUP SYSTEM
# Автор: GitHub Copilot
# Версія: 2.0
# Дата: 15.10.2025

clear

cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🚀 WINDSURF CLEANUP SYSTEM v2.0                       ║
║        з автовідновленням ідентифікаторів                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF

echo ""
echo "Доступні опції:"
echo ""
echo "  1️⃣  Запустити ПОВНЕ ОЧИЩЕННЯ (з автовідновленням через 5 год)"
echo "  2️⃣  Перевірити статус бекапів"
echo "  3️⃣  Відновити вручну (раніше 5 годин)"
echo "  4️⃣  Показати швидкі команди"
echo "  5️⃣  Показати схему роботи"
echo "  6️⃣  Читати документацію"
echo "  0️⃣  Вихід"
echo ""
echo -n "Виберіть опцію [0-6]: "

read choice

case $choice in
    1)
        echo ""
        echo "⚠️  УВАГА! Це виконає наступні дії:"
        echo ""
        echo "  ✓ Видалить всі файли Windsurf"
        echo "  ✓ Очистить Keychain"
        echo "  ✓ Створить бекап Machine-ID та Device-ID"
        echo "  ✓ Підмінить ідентифікатори на НОВІ"
        echo "  ✓ Змінить hostname на 'And-MAC'"
        echo "  ✓ Запустить автовідновлення через 5 годин"
        echo ""
        echo -n "Продовжити? (y/n): "
        read confirm
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            ./deep_windsurf_cleanup.sh
        else
            echo "❌ Скасовано"
        fi
        ;;
        
    2)
        echo ""
        echo "📊 Перевірка статусу бекапів..."
        echo ""
        ./check_windsurf_backup.sh
        ;;
        
    3)
        echo ""
        echo "🔄 Ручне відновлення з бекапу..."
        echo ""
        ./restore_windsurf_backup.sh
        ;;
        
    4)
        echo ""
        echo "⚡ Швидкі команди:"
        echo ""
        cat quick_commands.sh | grep -E "^# [0-9]|^./|^scutil|^security" | head -20
        echo ""
        echo "📄 Повний список: cat quick_commands.sh"
        ;;
        
    5)
        echo ""
        echo "📊 Схема роботи системи:"
        echo ""
        cat WORKFLOW.md | head -100
        echo ""
        echo "📄 Повна схема: cat WORKFLOW.md"
        ;;
        
    6)
        echo ""
        echo "📖 Відкриваю документацію..."
        echo ""
        
        if command -v bat &> /dev/null; then
            bat README.md
        elif command -v less &> /dev/null; then
            less README.md
        else
            cat README.md
        fi
        ;;
        
    0)
        echo ""
        echo "👋 До побачення!"
        exit 0
        ;;
        
    *)
        echo ""
        echo "❌ Невірний вибір!"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Підказка: Запустіть './start.sh' знову для головного меню"
echo ""
