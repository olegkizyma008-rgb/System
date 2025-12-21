#!/bin/zsh

setopt NULL_GLOB

# ═══════════════════════════════════════════════════════════════
#  💻 VS CODE IDENTIFIER CLEANUP - Повне очищення ідентифікаторів
#  Використовує спільні функції з common_functions.sh
#  ПРИМІТКА: Hostname виведено в hostname_spoof.sh
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common_functions.sh"

# Перевірка UNSAFE_MODE
check_safe_mode "vscode_identifier_cleanup"

print_header "💻 VS CODE IDENTIFIER CLEANUP" "$CYAN"
print_info "Очищення ідентифікаторів Visual Studio Code"
echo ""

# ─────────────────────────────────────────────────────────────────
# VSCODE-СПЕЦИФІЧНІ ШЛЯХИ
# ─────────────────────────────────────────────────────────────────
VSCODE_BASE="$HOME/Library/Application Support/Code"

# 1. Зупинка VS Code
print_step 1 6 "Зупинка VS Code..."
pkill -f "Visual Studio Code" 2>/dev/null
pkill -f "Code" 2>/dev/null
sleep 2
print_success "VS Code зупинено"

# 2. Очищення Machine ID
print_step 2 6 "Оновлення Machine ID..."
MACHINEID_PATH="$VSCODE_BASE/machineid"
if [ -f "$MACHINEID_PATH" ]; then
    NEW_MACHINE_ID=$(generate_machine_id)
    echo "$NEW_MACHINE_ID" > "$MACHINEID_PATH"
    print_success "Machine ID оновлено: $NEW_MACHINE_ID"
else
    print_info "Machine ID файл не знайдено"
fi

# 3. Очищення Storage файлів
print_step 3 6 "Оновлення Storage файлів..."
STORAGE_PATHS=(
    "$VSCODE_BASE/storage.json"
    "$VSCODE_BASE/User/globalStorage/storage.json"
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
print_step 4 6 "Видалення кешів та баз даних..."
CACHE_PATHS=(
    "$VSCODE_BASE/User/globalStorage/state.vscdb"
    "$VSCODE_BASE/User/globalStorage/state.vscdb.backup"
    "$VSCODE_BASE/Local Storage"
    "$VSCODE_BASE/Session Storage"
    "$VSCODE_BASE/IndexedDB"
    "$VSCODE_BASE/databases"
    "$VSCODE_BASE/GPUCache"
    "$VSCODE_BASE/CachedData"
    "$VSCODE_BASE/Code Cache"
    "$VSCODE_BASE/User/workspaceStorage"
    "$VSCODE_BASE/logs"
)

for path in "${CACHE_PATHS[@]}"; do
    safe_remove "$path"
done
print_success "Кеші та бази даних видалено"

# 5. Очищення Keychain
print_step 5 6 "Очищення Keychain..."
VSCODE_KEYCHAIN_SERVICES=(
    "Code"
    "Visual Studio Code"
    "com.microsoft.VSCode"
    "VS Code"
    "GitHub"
    "github.com"
    "Microsoft"
    "microsoft.com"
    "vscode.github-authentication"
    "vscode.microsoft-authentication"
)

for service in "${VSCODE_KEYCHAIN_SERVICES[@]}"; do
    security delete-generic-password -s "$service" 2>/dev/null
    security delete-internet-password -s "$service" 2>/dev/null
    security delete-generic-password -l "$service" 2>/dev/null
done
print_success "Keychain очищено"

# 6. Видалення cookies та веб-даних
print_step 6 6 "Видалення cookies та веб-даних..."
WEB_DATA_PATHS=(
    "$VSCODE_BASE/Cookies"
    "$VSCODE_BASE/Cookies-journal"
    "$VSCODE_BASE/Network Persistent State"
    "$VSCODE_BASE/TransportSecurity"
    "$VSCODE_BASE/Trust Tokens"
    "$VSCODE_BASE/SharedStorage"
    "$VSCODE_BASE/WebStorage"
)

for path in "${WEB_DATA_PATHS[@]}"; do
    safe_remove "$path"
done
print_success "Cookies та веб-дані видалено"

# ─────────────────────────────────────────────────────────────────
# ЗВІТ
# ─────────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo "${GREEN}║${NC}  ${WHITE}✅ ОЧИЩЕННЯ ІДЕНТИФІКАТОРІВ ЗАВЕРШЕНО!${NC}                    ${GREEN}║${NC}"
echo "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo "${GREEN}║${NC}  ${CYAN}📋 Виконані дії:${NC}"
echo "${GREEN}║${NC}    ✓ Machine ID оновлено"
echo "${GREEN}║${NC}    ✓ Storage файли оновлено"
echo "${GREEN}║${NC}    ✓ Кеші та бази даних видалено"
echo "${GREEN}║${NC}    ✓ Keychain очищено"
echo "${GREEN}║${NC}    ✓ Cookies та веб-дані видалено"
echo "${GREEN}║${NC}"
echo "${GREEN}║${NC}  ${YELLOW}💡 Для зміни hostname запустіть: hostname_spoof.sh${NC}"
echo "${GREEN}║${NC}  ${YELLOW}💡 Тепер можна запускати VS Code як новий користувач${NC}"
echo "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
