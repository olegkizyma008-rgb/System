#!/bin/zsh

# ═══════════════════════════════════════════════════════════════
#  🔍 ПЕРЕВІРКА ЯКОСТІ CLEANUP ІДЕНТИФІКАТОРІВ
#  Перевіряє чи були правильно очищені всі ідентифікатори
# ═══════════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════════════════"
echo "🔍 ПЕРЕВІРКА ЯКОСТІ CLEANUP ІДЕНТИФІКАТОРІВ"
echo "════════════════════════════════════════════════════════════"
echo ""

# Кольори
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

# Функції для логування
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    ((WARNINGS++))
}

info() {
    echo -e "${BLUE}ℹ️  INFO${NC}: $1"
}

# ═══════════════════════════════════════════════════════════════
# ПЕРЕВІРКА WINDSURF
# ═══════════════════════════════════════════════════════════════

echo -e "${BLUE}[1/4] WINDSURF ІДЕНТИФІКАТОРИ${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Machine-ID
if [ -f ~/Library/Application\ Support/Windsurf/machineid ]; then
    MACHINE_ID=$(cat ~/Library/Application\ Support/Windsurf/machineid)
    if [ ${#MACHINE_ID} -ge 32 ]; then
        pass "Machine-ID існує та має достатню довжину (${#MACHINE_ID} символів)"
    else
        warn "Machine-ID занадто короткий (${#MACHINE_ID} символів, потрібно ≥32)"
    fi
else
    fail "Machine-ID файл не знайдено"
fi

# 2. state.vscdb (КРИТИЧНО - НЕ повинна існувати!)
if [ -f ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb ]; then
    fail "state.vscdb все ще існує (повинна бути видалена!)"
else
    pass "state.vscdb видалена (API ключі не збережені)"
fi

# 3. state.vscdb.backup
if [ -f ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb.backup ]; then
    fail "state.vscdb.backup все ще існує"
else
    pass "state.vscdb.backup видалена"
fi

# 4. Browser IndexedDB
BROWSER_WINDSURF=$(find ~/Library/Application\ Support/Google/Chrome -path "*/IndexedDB/*windsurf*" 2>/dev/null | wc -l)
if [ "$BROWSER_WINDSURF" -eq 0 ]; then
    pass "Browser IndexedDB windsurf.com очищена (Chrome)"
else
    fail "Знайдено $BROWSER_WINDSURF файлів в Browser IndexedDB (Chrome)"
fi

# 5. Keychain (перевірка на залишки)
KEYCHAIN_WINDSURF=$(security find-generic-password -s "Windsurf" 2>/dev/null | wc -l)
KEYCHAIN_CODEIUM=$(security find-generic-password -s "Codeium" 2>/dev/null | wc -l)
KEYCHAIN_API=$(security find-internet-password -s "api.codeium.com" 2>/dev/null | wc -l)

if [ "$KEYCHAIN_WINDSURF" -eq 0 ] && [ "$KEYCHAIN_CODEIUM" -eq 0 ] && [ "$KEYCHAIN_API" -eq 0 ]; then
    pass "Keychain очищена (Windsurf, Codeium, API)"
else
    if [ "$KEYCHAIN_WINDSURF" -gt 0 ]; then
        fail "Знайдено записи Windsurf в Keychain"
    fi
    if [ "$KEYCHAIN_CODEIUM" -gt 0 ]; then
        fail "Знайдено записи Codeium в Keychain"
    fi
    if [ "$KEYCHAIN_API" -gt 0 ]; then
        fail "Знайдено записи api.codeium.com в Keychain"
    fi
fi

# 6. Local Storage
if [ -d ~/Library/Application\ Support/Windsurf/Local\ Storage ]; then
    fail "Local Storage все ще існує"
else
    pass "Local Storage видалена"
fi

# 7. Session Storage
if [ -d ~/Library/Application\ Support/Windsurf/Session\ Storage ]; then
    fail "Session Storage все ще існує"
else
    pass "Session Storage видалена"
fi

# 8. IndexedDB
if [ -d ~/Library/Application\ Support/Windsurf/IndexedDB ]; then
    fail "IndexedDB все ще існує"
else
    pass "IndexedDB видалена"
fi

# ═══════════════════════════════════════════════════════════════
# ПЕРЕВІРКА VS CODE
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BLUE}[2/4] VS CODE ІДЕНТИФІКАТОРИ${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Machine-ID
if [ -f ~/Library/Application\ Support/Code/machineid ]; then
    MACHINE_ID=$(cat ~/Library/Application\ Support/Code/machineid)
    if [ ${#MACHINE_ID} -ge 32 ]; then
        pass "Machine-ID існує та має достатню довжину (${#MACHINE_ID} символів)"
    else
        warn "Machine-ID занадто короткий (${#MACHINE_ID} символів, потрібно ≥32)"
    fi
else
    fail "Machine-ID файл не знайдено"
fi

# 2. state.vscdb
if [ -f ~/Library/Application\ Support/Code/User/globalStorage/state.vscdb ]; then
    fail "state.vscdb все ще існує (повинна бути видалена!)"
else
    pass "state.vscdb видалена"
fi

# 3. Browser IndexedDB (vscode.dev)
BROWSER_VSCODE=$(find ~/Library/Application\ Support/Google/Chrome -path "*/IndexedDB/*vscode*" 2>/dev/null | wc -l)
if [ "$BROWSER_VSCODE" -eq 0 ]; then
    pass "Browser IndexedDB vscode.dev очищена (Chrome)"
else
    warn "Знайдено $BROWSER_VSCODE файлів в Browser IndexedDB (vscode.dev)"
fi

# 4. GitHub.com IndexedDB
BROWSER_GITHUB=$(find ~/Library/Application\ Support/Google/Chrome -path "*/IndexedDB/*github*" 2>/dev/null | wc -l)
if [ "$BROWSER_GITHUB" -eq 0 ]; then
    pass "Browser IndexedDB github.com очищена (Chrome)"
else
    warn "Знайдено $BROWSER_GITHUB файлів в Browser IndexedDB (github.com)"
fi

# ═══════════════════════════════════════════════════════════════
# ПЕРЕВІРКА СИСТЕМНИХ ПАРАМЕТРІВ
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BLUE}[3/4] СИСТЕМНІ ПАРАМЕТРИ${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Hostname
HOSTNAME=$(scutil --get HostName 2>/dev/null)
if [ -n "$HOSTNAME" ]; then
    if [ ${#HOSTNAME} -gt 3 ] && [[ "$HOSTNAME" != "-"* ]] && [[ "$HOSTNAME" != *"-" ]]; then
        pass "Hostname валідний: $HOSTNAME"
    else
        fail "Hostname невалідний: '$HOSTNAME'"
    fi
else
    fail "Hostname не встановлено"
fi

# 2. DNS кеш
info "DNS кеш очищується автоматично при перезавантаженні"

# ═══════════════════════════════════════════════════════════════
# ПЕРЕВІРКА БРАУЗЕРІВ
# ═══════════════════════════════════════════════════════════════

echo ""
echo -e "${BLUE}[4/4] БРАУЗЕРНІ ДАНІ${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Chrome
CHROME_WINDSURF=$(find ~/Library/Application\ Support/Google/Chrome -path "*/IndexedDB/*windsurf*" -o -path "*/Local Storage/*windsurf*" 2>/dev/null | wc -l)
if [ "$CHROME_WINDSURF" -eq 0 ]; then
    pass "Chrome: Windsurf дані очищені"
else
    warn "Chrome: Знайдено $CHROME_WINDSURF файлів Windsurf"
fi

# Safari
SAFARI_WINDSURF=$(find ~/Library/Safari/IndexedDB -name "*windsurf*" 2>/dev/null | wc -l)
if [ "$SAFARI_WINDSURF" -eq 0 ]; then
    pass "Safari: Windsurf дані очищені"
else
    warn "Safari: Знайдено $SAFARI_WINDSURF файлів Windsurf"
fi

# Firefox
FIREFOX_WINDSURF=$(find ~/Library/Application\ Support/Firefox/Profiles -path "*/storage/*windsurf*" 2>/dev/null | wc -l)
if [ "$FIREFOX_WINDSURF" -eq 0 ]; then
    pass "Firefox: Windsurf дані очищені"
else
    warn "Firefox: Знайдено $FIREFOX_WINDSURF файлів Windsurf"
fi

# ═══════════════════════════════════════════════════════════════
# РЕЗУЛЬТАТИ
# ═══════════════════════════════════════════════════════════════

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📊 РЕЗУЛЬТАТИ ПЕРЕВІРКИ"
echo "════════════════════════════════════════════════════════════"
echo ""
echo -e "✅ Пройдено:  ${GREEN}$PASSED${NC}"
echo -e "❌ Помилок:   ${RED}$FAILED${NC}"
echo -e "⚠️  Попередж: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 УСПІХ! Всі перевірки пройдені!${NC}"
    echo ""
    echo "✅ Система готова до використання"
    echo "✅ Всі ідентифікатори очищені"
    echo "✅ Браузерні дані видалені"
    if [ $WARNINGS -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Але є $WARNINGS попереджень - перевірте їх${NC}"
    fi
    exit 0
else
    echo -e "${RED}❌ ПОМИЛКА! Знайдено $FAILED проблем!${NC}"
    echo ""
    echo "🔧 Рекомендації:"
    echo "1. Запустіть cleanup скрипт ще раз"
    echo "2. Перевірте чи закриті всі IDE"
    echo "3. Перезавантажте систему"
    echo "4. Запустіть цю перевірку ще раз"
    exit 1
fi
