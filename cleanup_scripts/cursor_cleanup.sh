#!/bin/zsh

setopt NULL_GLOB

# ═══════════════════════════════════════════════════════════════
#  🖱️  CURSOR CLEANUP - Очищення ідентифікаторів Cursor Editor
#  Видаляє всі ідентифікатори для Cursor AI Editor
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common_functions.sh"

print_header "🖱️  CURSOR CLEANUP" "$CYAN"
print_info "Очищення ідентифікаторів Cursor Editor"
echo ""

# ─────────────────────────────────────────────────────────────────
# CURSOR-СПЕЦИФІЧНІ ШЛЯХИ
# ─────────────────────────────────────────────────────────────────
CURSOR_BASE="$HOME/Library/Application Support/Cursor"
CURSOR_CACHES="$HOME/Library/Caches/Cursor"
CURSOR_PREFS="$HOME/Library/Preferences/com.todesktop.230313mzl4w4u92.plist"
CURSOR_APP="/Applications/Cursor.app"

# ─────────────────────────────────────────────────────────────────
# ОСНОВНЕ ОЧИЩЕННЯ
# ─────────────────────────────────────────────────────────────────

# 1. Зупинка процесів Cursor
print_step 1 8 "Зупинка Cursor..."
pkill -f "Cursor" 2>/dev/null
pkill -f "cursor" 2>/dev/null
sleep 2
print_success "Cursor зупинено"

# 2. Очищення Machine ID
print_step 2 8 "Оновлення Machine ID..."
MACHINEID_PATH="$CURSOR_BASE/machineid"
if [ -f "$MACHINEID_PATH" ]; then
    NEW_MACHINE_ID=$(generate_machine_id)
    echo "$NEW_MACHINE_ID" > "$MACHINEID_PATH"
    print_success "Machine ID оновлено: $NEW_MACHINE_ID"
else
    print_info "Machine ID файл не знайдено"
fi

# 3. Очищення Storage файлів
print_step 3 8 "Оновлення Storage файлів..."
STORAGE_PATHS=(
    "$CURSOR_BASE/storage.json"
    "$CURSOR_BASE/User/globalStorage/storage.json"
)

for STORAGE_PATH in "${STORAGE_PATHS[@]}"; do
    if [ -f "$STORAGE_PATH" ]; then
        NEW_DEVICE_ID=$(generate_uuid)
        NEW_SESSION_ID=$(generate_uuid)
        NEW_MACHINE_ID_TELEMETRY=$(generate_machine_id)
        NEW_MAC_MACHINE_ID=$(generate_machine_id)
        
        cat > "$STORAGE_PATH" << EOF
{
  "telemetry.machineId": "$NEW_MACHINE_ID_TELEMETRY",
  "telemetry.macMachineId": "$NEW_MAC_MACHINE_ID",
  "telemetry.devDeviceId": "$NEW_DEVICE_ID",
  "telemetry.sqmId": "{$(generate_uuid)}",
  "install.time": "$(date +%s)000",
  "sessionId": "$NEW_SESSION_ID",
  "firstSessionDate": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
  "lastSessionDate": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
}
EOF
        print_success "Storage оновлено: $(basename "$STORAGE_PATH")"
    fi
done

# 4. Видалення кешів та баз даних
print_step 4 8 "Видалення кешів та баз даних..."
CACHE_PATHS=(
    "$CURSOR_BASE/User/globalStorage/state.vscdb"
    "$CURSOR_BASE/User/globalStorage/state.vscdb.backup"
    "$CURSOR_BASE/Local Storage"
    "$CURSOR_BASE/Session Storage"
    "$CURSOR_BASE/IndexedDB"
    "$CURSOR_BASE/databases"
    "$CURSOR_BASE/GPUCache"
    "$CURSOR_BASE/CachedData"
    "$CURSOR_BASE/Code Cache"
    "$CURSOR_BASE/User/workspaceStorage"
    "$CURSOR_BASE/logs"
    "$CURSOR_CACHES"
)

for path in "${CACHE_PATHS[@]}"; do
    safe_remove "$path"
done
print_success "Кеші видалено"

# 5. Очищення Keychain
print_step 5 8 "Очищення Keychain..."
CURSOR_KEYCHAIN_SERVICES=(
    "Cursor"
    "cursor"
    "com.cursor"
    "Cursor Editor"
    "cursor.sh"
    "api.cursor.sh"
    "com.todesktop.230313mzl4w4u92"
    "cursor.com"
    "auth.cursor.sh"
)

for service in "${CURSOR_KEYCHAIN_SERVICES[@]}"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
    security delete-generic-password -l "$service" 2>/dev/null
done
print_success "Keychain очищено"

# 6. Видалення cookies та веб-даних
print_step 6 8 "Видалення cookies та веб-даних..."
WEB_DATA_PATHS=(
    "$CURSOR_BASE/Cookies"
    "$CURSOR_BASE/Cookies-journal"
    "$CURSOR_BASE/Network Persistent State"
    "$CURSOR_BASE/TransportSecurity"
    "$CURSOR_BASE/Trust Tokens"
    "$CURSOR_BASE/SharedStorage"
    "$CURSOR_BASE/WebStorage"
)

for path in "${WEB_DATA_PATHS[@]}"; do
    safe_remove "$path"
done
print_success "Веб-дані видалено"

# 7. Очищення Cursor-специфічних даних
print_step 7 8 "Очищення Cursor-специфічних даних..."

# Cursor AI conversation history
safe_remove "$CURSOR_BASE/User/globalStorage/cursor.cursor-ai"
safe_remove "$CURSOR_BASE/User/globalStorage/cursor-composer"

# Cursor settings that may contain identifiers
CURSOR_STATE_FILES=(
    "$CURSOR_BASE/User/globalStorage/cursor.cursor-auth"
    "$CURSOR_BASE/User/globalStorage/cursor-telemetry"
)

for path in "${CURSOR_STATE_FILES[@]}"; do
    safe_remove "$path"
done

# Preferences plist
safe_remove "$CURSOR_PREFS"

print_success "Cursor-специфічні дані очищено"

# 8. Очищення системних списків
print_step 8 8 "Очищення системних списків..."
# Recent Documents
safe_remove_glob "$HOME/Library/Application Support/com.apple.sharedfilelist/*cursor*"
safe_remove_glob "$HOME/Library/Application Support/com.apple.sharedfilelist/*Cursor*"
# Saved State
safe_remove "$HOME/Library/Saved Application State/com.todesktop.230313mzl4w4u92.savedState"
print_success "Системні списки очищено"

# ─────────────────────────────────────────────────────────────────
# ЗВІТ
# ─────────────────────────────────────────────────────────────────
echo ""
echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo "${WHITE}📊 ЗВІТ ОЧИЩЕННЯ CURSOR:${NC}"
echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

# Перевірка залишків
REMAINING=$(find "$HOME/Library" -iname "*cursor*" -not -path "*/Cursor.app/*" 2>/dev/null | wc -l | tr -d ' ')

if [ "$REMAINING" -eq 0 ]; then
    print_success "Cursor ідентифікатори: ОЧИЩЕНО"
else
    print_warning "Знайдено $REMAINING залишкових файлів Cursor"
fi

# Перевірка Keychain
KEYCHAIN_CHECK=$(security find-generic-password -s "Cursor" 2>/dev/null | wc -l)
if [ "$KEYCHAIN_CHECK" -eq 0 ]; then
    print_success "Keychain: ОЧИЩЕНО"
else
    print_warning "Keychain: Знайдено записи"
fi

echo "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
print_success "Очищення Cursor Editor завершено!"
print_info "Тепер можна запускати Cursor як новий користувач"
echo ""
