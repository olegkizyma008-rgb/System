#!/bin/bash

# Скрипт для перевірки всіх можливих слідів API ключів Codeium

echo "🔍 Перевірка всіх можливих місць зберігання API ключів Codeium..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Кольори для виводу
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${RED}❌ ЗНАЙДЕНО:${NC} $1"
        return 1
    else
        echo -e "${GREEN}✅ ВІДСУТНІЙ:${NC} $1"
        return 0
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${RED}❌ ЗНАЙДЕНО:${NC} $1"
        return 1
    else
        echo -e "${GREEN}✅ ВІДСУТНІЙ:${NC} $1"
        return 0
    fi
}

issues_found=0

echo "\n📁 Перевірка файлів конфігурації:"
check_file ~/Library/Application\ Support/Windsurf/storage.json || ((issues_found++))
check_file ~/Library/Application\ Support/Windsurf/machineid || ((issues_found++))
check_file ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json || ((issues_found++))

echo "\n🗄️  Перевірка баз даних (тут може зберігатися API ключ):"
check_file ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb || ((issues_found++))
check_file ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb.backup || ((issues_found++))
check_file ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb-shm || ((issues_found++))
check_file ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb-wal || ((issues_found++))

echo "\n💾 Перевірка локальних сховищ:"
check_dir ~/Library/Application\ Support/Windsurf/Local\ Storage || ((issues_found++))
check_dir ~/Library/Application\ Support/Windsurf/Session\ Storage || ((issues_found++))
check_dir ~/Library/Application\ Support/Windsurf/IndexedDB || ((issues_found++))
check_dir ~/Library/Application\ Support/Windsurf/databases || ((issues_found++))

echo "\n📦 Перевірка workspaceStorage (може містити API токени):"
check_dir ~/Library/Application\ Support/Windsurf/User/workspaceStorage || ((issues_found++))

echo "\n🔐 Перевірка Keychain записів:"
echo "Пошук записів Codeium..."
if security find-generic-password -s "Codeium" 2>/dev/null | grep -q "password:"; then
    echo -e "${RED}❌ ЗНАЙДЕНО:${NC} Codeium generic password в Keychain"
    ((issues_found++))
else
    echo -e "${GREEN}✅ ВІДСУТНІЙ:${NC} Codeium generic password"
fi

if security find-internet-password -s "codeium.com" 2>/dev/null | grep -q "password:"; then
    echo -e "${RED}❌ ЗНАЙДЕНО:${NC} Codeium internet password в Keychain"
    ((issues_found++))
else
    echo -e "${GREEN}✅ ВІДСУТНІЙ:${NC} Codeium internet password"
fi

if security find-generic-password -s "Windsurf" 2>/dev/null | grep -q "password:"; then
    echo -e "${RED}❌ ЗНАЙДЕНО:${NC} Windsurf в Keychain"
    ((issues_found++))
else
    echo -e "${GREEN}✅ ВІДСУТНІЙ:${NC} Windsurf в Keychain"
fi

echo "\n🔍 Пошук будь-яких файлів з 'codeium' або 'api' в назві:"
FOUND_FILES=$(find ~/Library/Application\ Support/Windsurf -type f -iname "*codeium*" -o -iname "*api*" 2>/dev/null)
if [ -n "$FOUND_FILES" ]; then
    echo -e "${RED}❌ ЗНАЙДЕНО файли:${NC}"
    echo "$FOUND_FILES"
    ((issues_found++))
else
    echo -e "${GREEN}✅ Не знайдено файлів з 'codeium' або 'api'${NC}"
fi

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $issues_found -eq 0 ]; then
    echo -e "${GREEN}✅ ВСЕ ЧИСТО! Жодних слідів API ключів не знайдено.${NC}"
else
    echo -e "${YELLOW}⚠️  ЗНАЙДЕНО $issues_found потенційних місць зберігання API даних!${NC}"
    echo "💡 Рекомендація: Запустіть deep_windsurf_cleanup.sh для повного очищення"
fi
