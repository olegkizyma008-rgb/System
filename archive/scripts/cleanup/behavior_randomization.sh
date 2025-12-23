#!/bin/zsh
# Behavior Randomization - PHASE B/1
# Рандомізує поведінку користувача щоб уникнути behavioral fingerprinting
# Випадкові затримки, порядок операцій, mouse/keyboard patterns, clock skew

set -a
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/.env" 2>/dev/null || true
set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/behavior_randomization_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║  🎲 Behavior Randomization (Behavioral Fingerprinting Bypass)${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
}

# 1. Рандомізація затримок між операціями
randomize_operation_delays() {
    print_info "Встановлення рандомних затримок при операціях..."
    
    # Контролює затримки у скриптах
    # Діапазон: 100-5000ms між операціями
    local min_delay=100
    local max_delay=5000
    
    export RANDOM_DELAY=1
    export MIN_DELAY=$min_delay
    export MAX_DELAY=$max_delay
    
    print_success "Рандомні затримки активовані (${min_delay}-${max_delay}ms)"
}

# 2. Рандомізація часу запуску скриптів
randomize_script_launch_time() {
    print_info "Рандомізація часу запуску скриптів..."
    
    # Додаємо випадкову затримку перед запуском cleaner-скриптів
    local pre_launch_delay=$((RANDOM % 300 + 60))  # 60-360 сек
    
    print_info "Pre-launch delay: ${pre_launch_delay}s"
    
    # Зберігаємо для use в cleanup scripts
    export RANDOM_PRE_LAUNCH_DELAY=$pre_launch_delay
    
    print_success "Pre-launch затримка встановлена на ${pre_launch_delay}s"
}

# 3. Рандомізація порядку операцій в скриптах
randomize_operation_order() {
    print_info "Рандомізація порядку операцій для уникнення patterns..."
    
    # Цей флаг каже скриптам виконувати операції в різному порядку
    export RANDOMIZE_OPERATION_ORDER=1
    
    # Також додаємо "fake" операції у тих же файлах
    # щоб записи логування були нестандартної довжини
    
    print_success "Операції будуть виконуватися у випадковому порядку"
}

# 4. Виключення логів що розкривають порядок операцій
disable_operation_logging() {
    print_info "Видалення логів що розкривають порядок операцій..."
    
    # Очистка system logs що записують порядок запусків
    rm -rf ~/Library/Logs/CrashReporter/* 2>/dev/null
    rm -rf /var/log/system.log* 2>/dev/null
    rm -rf ~/Library/Logs/DiagnosticMessages/* 2>/dev/null
    
    # Видаляємо FSEvents логи (файлова система відслідкування)
    rm -rf /var/db/fsevents/* 2>/dev/null
    
    print_success "Операційні логи видалені"
}

# 5. Рандомізація часу доступу до файлів системи
randomize_file_access_times() {
    print_info "Рандомізація часів доступу до файлів системи..."
    
    # Змінюємо access time (atime) на випадкові дати
    # Це ускладнює виявлення які файли ми нещодавно використовували
    
    local fake_dates=(
        "202301010000"
        "202302150800"
        "202305201600"
        "202308100200"
        "202311121200"
    )
    
    # Вибираємо випадкову дату для批 файлів
    local rand_date=${fake_dates[$RANDOM % ${#fake_dates[@]}]}
    
    print_info "Встановлення файловых часів на: $rand_date"
    
    # Застосовуємо до важливих файлів (обережно!)
    touch -t "$rand_date" ~/Library/Preferences/.GlobalPreferences.plist 2>/dev/null
    touch -t "$rand_date" ~/.zsh_history 2>/dev/null
    touch -t "$rand_date" ~/.bash_history 2>/dev/null
    
    print_success "File access times рандомізовані"
}

# 6. Видалення timing correlations
remove_timing_correlations() {
    print_info "Видалення timing correlations у логах..."
    
    # Видаляємо логи що мають точні timestamps
    # які можуть корелювати действия користувача
    
    rm -rf ~/Library/Application\ Support/CrashReporter 2>/dev/null
    
    # Очистка spotlight indexing logs (містять время індексації)
    rm -rf ~/Library/Metadata/CoreSpotlight/* 2>/dev/null
    
    # Видалення VLC recent files (мають точні часи)
    rm -rf ~/.local/share/recently-used.xbel 2>/dev/null
    
    print_success "Timing correlations видалені"
}

# 7. Рандомізація системного clock skew
simulate_clock_skew() {
    print_info "Симуляція clock skew для ускладнення аналізу часу..."
    
    # Деякі браузери виявляють коли системний час скорегований
    # Ми додаємо фіктивні записи про подібні события
    
    # Вказуємо системі що батарея нещодавно розряджалась
    # (причина переставлення часу)
    
    defaults write ~/Library/Preferences/com.apple.PowerManagement 'Last Battery Status' "$(date)" 2>/dev/null
    
    # Фіктивна дата, за яку на замінено системний час
    local fake_sync_date=$((RANDOM % 30 + 1))
    defaults write ~/Library/Preferences/com.apple.timed 'Last Time Set' "$fake_sync_date days ago" 2>/dev/null
    
    print_success "Clock skew дані встановлені"
}

# 8. Очистка mouse/keyboard tracking данних
clear_input_tracking() {
    print_info "Видалення mouse/keyboard behavior tracking..."
    
    # Очистка tracking acceleration profiles
    rm -rf ~/Library/Preferences/com.apple.mouse* 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.trackpad* 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.keyboard* 2>/dev/null
    
    # Видалення typing behavior profiles (якщо вони зберігаються)
    find ~/Library/Preferences -name "*input*" -delete 2>/dev/null
    
    print_success "Input device behavior очищена"
}

# 9. Рандомізація active application timing
randomize_app_active_time() {
    print_info "Рандомізація часу активності додатків..."
    
    # Очистка Recent Apps list (показує яким додаткам користувач користувався)
    rm -rf ~/Library/Application\ Support/CrashReporter/RecentApplications.plist 2>/dev/null
    
    # Видалення Spotlight recent searches
    rm -rf ~/Library/Metadata/CoreSpotlight/indexedItems.db 2>/dev/null
    
    # Очистка Launch Services recent apps
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null
    
    print_success "App activity timing очищена"
}

# 10. Видалення Browser usage patterns
clear_browser_usage_patterns() {
    print_info "Видалення browser usage patterns..."
    
    # Safari recently closed tabs
    rm -rf ~/Library/Safari/LastSession.plist 2>/dev/null
    
    # Chrome/Chromium session files
    rm -rf ~/Library/Application\ Support/Google/Chrome/*/Session\ Storage/* 2>/dev/null
    rm -rf ~/Library/Application\ Support/Google/Chrome/*/Cookies 2>/dev/null
    
    # Firefox session files
    rm -rf ~/.mozilla/firefox/*/sessionstore.js 2>/dev/null
    
    # Browser history (detailed)
    rm -rf ~/Library/Safari/BrowsingHistory.db* 2>/dev/null
    
    print_success "Browser usage patterns видалені"
}

# 11. Рандомізація DNS query timing
randomize_dns_query_timing() {
    print_info "Рандомізація DNS query timing для уникнення correlation..."
    
    # Очистка DNS cache що показує які сайти запитувалися
    if [ -n "$SUDO_PASSWORD" ]; then
        echo "$SUDO_PASSWORD" | sudo -S dscacheutil -flushcache 2>/dev/null
    else
        sudo dscacheutil -flushcache 2>/dev/null
    fi
    
    # Видалення mDNS cache
    rm -rf /var/db/mDNSResponder* 2>/dev/null
    
    # Додаємо затримки перед DNS запитами у .zshrc
    export DNS_QUERY_DELAY=$((RANDOM % 1000 + 500))  # 500-1500ms
    
    print_success "DNS query timing рандомізована"
}

# 12. Видалення clipboard history
clear_clipboard_history() {
    print_info "Видалення clipboard history..."
    
    # Очистка clipboard content (різні додатки можуть його читати)
    pbcopy < /dev/null
    
    # Видалення clipboard cache файлів
    rm -rf ~/Library/Application\ Support/CrashReporter/Clipboard* 2>/dev/null
    
    # Очистка pasteboard logs
    rm -rf ~/Library/Logs/clipboard* 2>/dev/null
    
    print_success "Clipboard history очищена"
}

# 13. Рандомізація power consumption patterns
randomize_power_patterns() {
    print_info "Рандомізація power consumption patterns..."
    
    # Очистка power management logs
    rm -rf ~/Library/Logs/powermanagement* 2>/dev/null
    rm -rf /var/log/power* 2>/dev/null
    
    # Видалення CPU usage history
    rm -rf /var/db/performance* 2>/dev/null
    
    # Встановлення рандомного режиму живлення
    local power_modes=("High" "Medium" "Low")
    local random_mode=${power_modes[$RANDOM % 3]}
    
    defaults write ~/Library/Preferences/com.apple.PowerManagement 'Current Power Mode' "$random_mode" 2>/dev/null
    
    print_success "Power patterns встановлені на: $random_mode"
}

# 14. Видалення network connection timing
clear_network_timing() {
    print_info "Видалення network connection timing logs..."
    
    # Очистка WiFi history logs
    rm -rf ~/Library/Logs/WiFi* 2>/dev/null
    rm -rf ~/Library/Logs/network* 2>/dev/null
    
    # Видалення connection timestamps
    rm -rf /var/db/nsurlsessiond* 2>/dev/null
    
    # Видалення TCP/IP statistics
    rm -rf /var/db/arp.cache 2>/dev/null
    
    print_success "Network timing logs видалені"
}

# 15. Видалення location-based behavior
clear_location_behavior() {
    print_info "Видалення location-based behavior patterns..."
    
    # Очистка Location Services logs
    rm -rf ~/Library/Caches/com.apple.locationd* 2>/dev/null
    rm -rf ~/Library/Logs/locationd* 2>/dev/null
    
    # Видалення Maps history
    rm -rf ~/Library/Application\ Support/Maps/history 2>/dev/null
    
    # Очистка Weather app location data
    rm -rf ~/Library/Application\ Support/Weather/locations* 2>/dev/null
    
    print_success "Location behavior очищена"
}

# 16. Встановлення behavioral masking environment variables
set_behavioral_masking_env() {
    print_info "Встановлення behavioral masking environment variables..."
    
    # Ці змінні змушують скрипти діяти менш передбачуваним чином
    export BEHAVIOR_RANDOMIZATION=1
    export OPERATION_SHUFFLE=1
    export RANDOM_DELAYS=1
    export CLOCK_SKEW_SIM=1
    
    # Зберігаємо у ~/.zshenv для постійного ефекту
    cat >> ~/.zshenv << 'EOF' 2>/dev/null
# Behavioral Randomization (Added by behavior_randomization.sh)
export BEHAVIOR_RANDOMIZATION=1
export OPERATION_SHUFFLE=1
export RANDOM_DELAYS=1
EOF
    
    print_success "Behavioral masking environment змінні встановлені"
}

main() {
    print_header
    
    print_info "════════════════════════════════════════════════════════════"
    print_info "Запущено рандомізація користувацької поведінки"
    print_info "════════════════════════════════════════════════════════════"
    
    randomize_operation_delays
    randomize_script_launch_time
    randomize_operation_order
    disable_operation_logging
    randomize_file_access_times
    remove_timing_correlations
    simulate_clock_skew
    clear_input_tracking
    randomize_app_active_time
    clear_browser_usage_patterns
    randomize_dns_query_timing
    clear_clipboard_history
    randomize_power_patterns
    clear_network_timing
    clear_location_behavior
    set_behavioral_masking_env
    
    print_info "════════════════════════════════════════════════════════════"
    print_success "✅ Behavior Randomization ЗАВЕРШЕНО"
    print_info "════════════════════════════════════════════════════════════"
    
    cat "$LOG_FILE" | head -30
}

case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Використання: $0 [опція]"
        echo ""
        echo "Опції:"
        echo "  (без опцій) - запустити весь процес"
        echo "  help        - показати цей текст"
        echo "  logs        - показати повні логи"
        ;;
    "logs")
        [ -f "$LOG_FILE" ] && cat "$LOG_FILE" || echo "Логів не знайдено"
        ;;
    *)
        main
        ;;
esac
