#!/bin/zsh

setopt NULL_GLOB

# Забезпечуємо базовий PATH для системних утиліт
PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

# ═══════════════════════════════════════════════════════════════
#  🏠 HOSTNAME SPOOF - Зміна hostname для приховування ідентичності
#  Централізований модуль для зміни hostname (виведений з інших скриптів)
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common_functions.sh"

# Перевірка UNSAFE_MODE
check_safe_mode "hostname_spoof"

print_header "🏠 HOSTNAME SPOOF" "$CYAN"

# ─────────────────────────────────────────────────────────────────
# ПАРАМЕТРИ
# ─────────────────────────────────────────────────────────────────
RESTORE_HOURS="${RESTORE_HOURS:-4}"  # Через скільки годин відновити
SKIP_RESTORE="${SKIP_RESTORE:-0}"    # Пропустити планування відновлення

# Парсинг аргументів
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--restore-hours)
            RESTORE_HOURS="$2"
            shift 2
            ;;
        -n|--no-restore)
            SKIP_RESTORE=1
            shift
            ;;
        -s|--set)
            CUSTOM_HOSTNAME="$2"
            shift 2
            ;;
        -o|--original)
            RESTORE_ORIGINAL=1
            shift
            ;;
        -h|--help)
            echo ""
            echo "🏠 HOSTNAME SPOOF"
            echo ""
            echo "Використання: $0 [OPTIONS]"
            echo ""
            echo "Опції:"
            echo "  -r, --restore-hours N   Відновити hostname через N годин (за замовчуванням: 4)"
            echo "  -n, --no-restore        Не планувати автоматичне відновлення"
            echo "  -s, --set NAME          Встановити конкретний hostname"
            echo "  -o, --original          Відновити оригінальний hostname зараз"
            echo "  -h, --help              Показати цю довідку"
            echo ""
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────────
# ОТРИМАННЯ SUDO ПРАВ
# ─────────────────────────────────────────────────────────────────
print_info "Отримання прав адміністратора..."
check_sudo

# ─────────────────────────────────────────────────────────────────
# ЗБЕРЕЖЕННЯ ОРИГІНАЛЬНОГО HOSTNAME
# ─────────────────────────────────────────────────────────────────
ORIGINAL_HOSTNAME_FILE="$REPO_ROOT/.original_hostname"

CURRENT_HOSTNAME=$(scutil --get HostName 2>/dev/null)
CURRENT_LOCAL=$(scutil --get LocalHostName 2>/dev/null)
CURRENT_COMPUTER=$(scutil --get ComputerName 2>/dev/null)

# Зберігаємо оригінал якщо ще не збережено
if [ ! -f "$ORIGINAL_HOSTNAME_FILE" ]; then
    echo "${CURRENT_HOSTNAME:-DEVs-Mac-Studio}" > "$ORIGINAL_HOSTNAME_FILE"
    print_info "Оригінальний hostname збережено: $(cat "$ORIGINAL_HOSTNAME_FILE")"
fi

ORIGINAL_HOSTNAME=$(cat "$ORIGINAL_HOSTNAME_FILE")

# ─────────────────────────────────────────────────────────────────
# ВІДНОВЛЕННЯ ОРИГІНАЛУ (якщо запитано)
# ─────────────────────────────────────────────────────────────────
if [[ "$RESTORE_ORIGINAL" == "1" ]]; then
    print_step 1 2 "Відновлення оригінального hostname..."
    
    sudo scutil --set HostName "$ORIGINAL_HOSTNAME" 2>/dev/null
    sudo scutil --set LocalHostName "$ORIGINAL_HOSTNAME" 2>/dev/null
    sudo scutil --set ComputerName "$ORIGINAL_HOSTNAME" 2>/dev/null
    
    print_step 2 2 "Очищення DNS кешу..."
    sudo dscacheutil -flushcache 2>/dev/null
    sudo killall -HUP mDNSResponder 2>/dev/null
    
    print_success "Hostname відновлено: $ORIGINAL_HOSTNAME"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────
# ГЕНЕРАЦІЯ ТА ВСТАНОВЛЕННЯ НОВОГО HOSTNAME
# ─────────────────────────────────────────────────────────────────
print_step 1 4 "Поточний hostname..."
echo "  📝 HostName: ${CURRENT_HOSTNAME:-не встановлено}"
echo "  📝 LocalHostName: ${CURRENT_LOCAL:-не встановлено}"
echo "  📝 ComputerName: ${CURRENT_COMPUTER:-не встановлено}"

print_step 2 4 "Генерація нового hostname..."
if [ -n "$CUSTOM_HOSTNAME" ]; then
    NEW_HOSTNAME="$CUSTOM_HOSTNAME"
else
    NEW_HOSTNAME=$(generate_hostname)
fi
echo "  🎲 Новий hostname: $NEW_HOSTNAME"

print_step 3 4 "Встановлення hostname..."
sudo scutil --set HostName "$NEW_HOSTNAME" 2>/dev/null
sudo scutil --set LocalHostName "$NEW_HOSTNAME" 2>/dev/null
sudo scutil --set ComputerName "$NEW_HOSTNAME" 2>/dev/null

# Очищення DNS кешу
sudo dscacheutil -flushcache 2>/dev/null
sudo killall -HUP mDNSResponder 2>/dev/null

print_success "Hostname змінено на: $NEW_HOSTNAME"

# ─────────────────────────────────────────────────────────────────
# ПЛАНУВАННЯ ВІДНОВЛЕННЯ
# ─────────────────────────────────────────────────────────────────
if [[ "$SKIP_RESTORE" != "1" ]]; then
    print_step 4 4 "Планування відновлення hostname..."
    
    RESTORE_SECONDS=$((RESTORE_HOURS * 3600))
    RESTORE_SCRIPT="/tmp/hostname_restore_$$.sh"
    
    cat > "$RESTORE_SCRIPT" << EOF
#!/bin/zsh
sleep $RESTORE_SECONDS
echo "⏰ Відновлення оригінального hostname: $ORIGINAL_HOSTNAME"
sudo scutil --set HostName "$ORIGINAL_HOSTNAME" 2>/dev/null
sudo scutil --set LocalHostName "$ORIGINAL_HOSTNAME" 2>/dev/null
sudo scutil --set ComputerName "$ORIGINAL_HOSTNAME" 2>/dev/null
sudo dscacheutil -flushcache 2>/dev/null
sudo killall -HUP mDNSResponder 2>/dev/null
rm -f "$RESTORE_SCRIPT"
EOF
    
    chmod +x "$RESTORE_SCRIPT"
    nohup "$RESTORE_SCRIPT" > /tmp/hostname_restore_$$.log 2>&1 &
    
    RESTORE_PID=$!
    print_success "Відновлення заплановано через $RESTORE_HOURS годин (PID: $RESTORE_PID)"
else
    print_step 4 4 "Пропуск планування відновлення..."
    print_warning "Hostname НЕ буде автоматично відновлено"
fi

# ─────────────────────────────────────────────────────────────────
# ЗВІТ
# ─────────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo "${GREEN}║${NC}  ${WHITE}✅ HOSTNAME ЗМІНЕНО!${NC}"
echo "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo "${GREEN}║${NC}  ${CYAN}📋 Деталі:${NC}"
echo "${GREEN}║${NC}    Оригінальний: ${YELLOW}$ORIGINAL_HOSTNAME${NC}"
echo "${GREEN}║${NC}    Новий:        ${YELLOW}$NEW_HOSTNAME${NC}"
if [[ "$SKIP_RESTORE" != "1" ]]; then
    echo "${GREEN}║${NC}    Відновлення:  ${YELLOW}через $RESTORE_HOURS годин${NC}"
fi
echo "${GREEN}║${NC}"
echo "${GREEN}║${NC}  ${YELLOW}💡 Для негайного відновлення:${NC}"
echo "${GREEN}║${NC}    $0 --original"
echo "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
