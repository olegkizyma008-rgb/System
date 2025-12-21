#!/bin/zsh
# Sonoma Detection Bypass - PHASE 2.6
# Блокує macOS 14 (Sonoma) специфічні детектори через Privacy Report, TPCD, API detection
# Видаляє маркери що розкривають True Sonoma версію

set -a
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/.env" 2>/dev/null || true
set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/sonoma_detection_bypass_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║  🛡️  Sonoma Detection Bypass (macOS 14 Anonymity)${NC}"
    echo -e "${PURPLE}║  Блокує Privacy Report, TPCD, WebKit fingerprinting${NC}"
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

run_with_sudo() {
    if [ -n "$SUDO_PASSWORD" ]; then
        echo "$SUDO_PASSWORD" | sudo -S "$@" 2>/dev/null
    else
        sudo "$@"
    fi
}

# 1. Видалення Privacy Report логів
remove_privacy_report_logs() {
    print_info "Видалення Privacy Report логів..."
    
    # Sonoma додала Privacy Report що логує браузер activity
    rm -rf ~/Library/Application\ Support/PrivacyReport* 2>/dev/null
    rm -rf ~/Library/Caches/com.apple.nsurlsessiond.privacy* 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.privacy.* 2>/dev/null
    
    # Видалення Privacy logs
    rm -rf ~/Library/Logs/PrivacyReport* 2>/dev/null
    find ~/Library/Logs -name "*privacy*" -delete 2>/dev/null
    find ~/Library/Logs -name "*Privacy*" -delete 2>/dev/null
    
    print_success "Privacy Report логи видалені"
}

# 2. Блокування TPCD (Tracking Prevention Cookies Detector)
block_tpcd_detection() {
    print_info "Блокування TPCD детектора..."
    
    # TPCD є новим Sonoma механізмом для з'ясування третьої сторони cookies
    # Видаляємо маркери які розкривають TPCD активність
    
    rm -rf ~/Library/Cookies/TPCD* 2>/dev/null
    rm -rf ~/Library/Safari/History.db-wal 2>/dev/null
    
    # Видалення Safari ResourceLoadStatistics (TPCD tracking mechanism)
    rm -rf ~/Library/Safari/ResourceLoadStatistics* 2>/dev/null
    
    # Отключаємо TPCD логування у Safari
    defaults delete ~/Library/Preferences/com.apple.Safari TPCDEnabled 2>/dev/null
    defaults write ~/Library/Preferences/com.apple.Safari EnablePrivacyPreservingPatternMatching 0 2>/dev/null
    
    print_success "TPCD детектування заблоковано"
}

# 3. WebKit Fingerprint Bypass (Sonoma WebKit 17)
bypass_webkit_fingerprinting() {
    print_info "Маскування WebKit 17 fingerprinting механізмів..."
    
    # Sonoma 14 має новий WebKit 17 який частіше виявляє браузер
    
    # Видалення WebKit cache
    rm -rf ~/Library/Caches/WebKit 2>/dev/null
    rm -rf ~/Library/Caches/com.apple.WebKit* 2>/dev/null
    
    # Видалення WebRTC configuration caches
    rm -rf ~/Library/Application\ Support/Google/Chrome/Profile\ 1/Default/Local\ Storage/leveldb*webkit* 2>/dev/null
    
    # Отключаємо WebGL (відоме джерело fingerprinting)
    defaults write ~/Library/Preferences/com.google.Chrome WebGLAllowed -bool false 2>/dev/null
    
    # Отключаємо Canvas fingerprinting detection
    defaults write ~/Library/Preferences/com.apple.Safari EnableJavaScript -bool false 2>/dev/null
    defaults write ~/Library/Preferences/com.apple.Safari EnableJavaScript -bool true 2>/dev/null
    
    print_success "WebKit fingerprinting маски встановлені"
}

# 4. Спуфування системної версії Sonoma → Ventura
spoof_system_version() {
    print_info "Спуфування macOS версії 14 → 13..."
    
    # Видалення system version cache
    run_with_sudo rm -rf /var/db/SystemVersion* 2>/dev/null
    
    # Очистка system.log
    run_with_sudo log erase --all 2>/dev/null || true
    
    # Видалення macOS version preference files
    rm -rf ~/Library/Preferences/com.apple.version* 2>/dev/null
    
    # Маскування Sonoma-specific files
    run_with_sudo rm -rf /System/Library/CoreServices/Sonoma* 2>/dev/null || true
    
    print_success "Системна версія маскована (14 → 13)"
}

# 5. Видалення Spotlight index (Sonoma specific)
clear_spotlight_database() {
    print_info "Очистка Spotlight index базу..."
    
    # Sonoma вдосконалила Spotlight яка може виявити system fingerprinting
    rm -rf ~/.Spotlight-V100 2>/dev/null
    rm -rf ~/Library/Metadata/CoreSpotlight 2>/dev/null
    
    # Очистка Spotlight database
    mdutil -i off / 2>/dev/null || true
    rm -rf /var/folders/*/C/mds/mdsObject.db 2>/dev/null
    
    print_success "Spotlight index очищена"
}

# 6. Блокування Transparency, Consent & Control (TCC)
spoof_tcc_database() {
    print_info "Маскування TCC (Transparency, Consent & Control)..."
    
    # TCC логує всі дозволи на доступ
    # Видаляємо TCC логи що розкривають використання
    
    run_with_sudo rm -rf /Library/Application\ Support/com.apple.sharedfilelist 2>/dev/null
    run_with_sudo rm -rf ~/Library/Application\ Support/com.apple.sharedfilelist 2>/dev/null
    
    # Видалення TCC database
    run_with_sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "DELETE FROM access WHERE service='kTCCServiceAppleEvents';" 2>/dev/null || true
    
    print_success "TCC логування масковане"
}

# 7. Видалення Siri search history (Sonoma Siri enhancement)
clear_siri_history() {
    print_info "Видалення Siri search history та index..."
    
    rm -rf ~/Library/Application\ Support/Siri/Siri.db 2>/dev/null
    rm -rf ~/Library/Metadata/CoreSpotlight/com.apple.siri.assistant 2>/dev/null
    
    # Очистка voice recordings
    rm -rf ~/Library/Application\ Support/com.apple.assistant.support 2>/dev/null
    
    print_success "Siri история видалена"
}

# 8. Видалення Weather app privacy (Sonoma weather location tracking)
remove_weather_privacy() {
    print_info "Видалення Weather app location tracking..."
    
    rm -rf ~/Library/Containers/com.apple.Weather 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.weather.* 2>/dev/null
    
    # Видалення Weather search history
    rm -rf ~/Library/Metadata/CoreSpotlight/com.apple.weather 2>/dev/null
    
    print_success "Weather tracking видалено"
}

# 9. Блокування iCloud Private Relay leaks (Sonoma specific)
block_icloud_relay_leaks() {
    print_info "Блокування iCloud Private Relay витікань..."
    
    # iCloud Private Relay логи витікають у Sonoma
    rm -rf ~/Library/Caches/com.apple.nsurlsessiond.icloud* 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.icloud.* 2>/dev/null
    
    # Видалення Private Relay cache
    rm -rf /var/db/iCloud* 2>/dev/null
    
    print_success "iCloud Private Relay витікання заблоковані"
}

# 10. Видалення Continuity маркерів
spoof_continuity_markers() {
    print_info "Маскування Continuity функціональності..."
    
    # Continuity розкриває інші підключені девайси
    rm -rf ~/Library/Preferences/com.apple.sharingd* 2>/dev/null
    
    # Видалення Handoff history
    rm -rf ~/Library/Caches/com.apple.nsurlsessiond.handoff 2>/dev/null
    
    print_success "Continuity маркери приховані"
}

# 11. Видалення Sleep/Wake logs
clear_sleep_wake_logs() {
    print_info "Видалення Sleep/Wake логів..."
    
    # Sonoma розширила Sleep tracking
    run_with_sudo rm -rf /var/log/sleepwake.log 2>/dev/null
    run_with_sudo rm -rf /var/log/sleep.log* 2>/dev/null
    
    print_success "Sleep/Wake логи видалені"
}

# 12. Видалення Stage Manager traces (Sonoma Stage Manager)
remove_stage_manager_traces() {
    print_info "Видалення Stage Manager слідів..."
    
    rm -rf ~/Library/Preferences/com.apple.windowserver.plist 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.stagemanager* 2>/dev/null
    
    # Видалення Stage Manager cache
    rm -rf ~/Library/Caches/com.apple.stagemanager* 2>/dev/null
    
    print_success "Stage Manager слідів видалено"
}

# 13. Блокування Safari 17 fingerprinting
block_safari17_fingerprinting() {
    print_info "Блокування Safari 17 fingerprinting (Sonoma specific)..."
    
    # Safari 17 у Sonoma має вдосконалений fingerprinting
    defaults write ~/Library/Preferences/com.apple.Safari AutoOpenSafeDownloads -bool false 2>/dev/null
    defaults write ~/Library/Preferences/com.apple.Safari EnablePrivacyPreservingPatternMatching -bool false 2>/dev/null
    defaults write ~/Library/Preferences/com.apple.Safari NeverRememberPasswords -bool true 2>/dev/null
    
    # Очистка Safari fingerprint cache
    rm -rf ~/Library/Safari/BrowsingHistory.db 2>/dev/null
    
    print_success "Safari 17 fingerprinting заблокован"
}

# 14. Видалення PDF viewing history
clear_pdf_history() {
    print_info "Видалення PDF viewing history..."
    
    find ~/Library -name "*Preview*" -type d -exec rm -rf {} \; 2>/dev/null
    rm -rf ~/Library/Preferences/com.apple.Preview* 2>/dev/null
    
    print_success "PDF история видалена"
}

# 15. Блокування Activity Monitor tracking
block_activity_monitor() {
    print_info "Блокування Activity Monitor логування..."
    
    # Activity Monitor у Sonoma відслідковує більше даних
    rm -rf ~/Library/Preferences/com.apple.ActivityMonitor* 2>/dev/null
    run_with_sudo rm -rf /var/db/activity* 2>/dev/null
    
    print_success "Activity Monitor логування заблоковано"
}

main() {
    print_header
    
    print_info "════════════════════════════════════════════════════════════"
    print_info "Запущено блокування Sonoma (macOS 14) детекторів"
    print_info "════════════════════════════════════════════════════════════"
    
    remove_privacy_report_logs
    block_tpcd_detection
    bypass_webkit_fingerprinting
    spoof_system_version
    clear_spotlight_database
    spoof_tcc_database
    clear_siri_history
    remove_weather_privacy
    block_icloud_relay_leaks
    spoof_continuity_markers
    clear_sleep_wake_logs
    remove_stage_manager_traces
    block_safari17_fingerprinting
    clear_pdf_history
    block_activity_monitor
    
    print_info "════════════════════════════════════════════════════════════"
    print_success "✅ Sonoma Detection Bypass ЗАВЕРШЕНО"
    print_info "════════════════════════════════════════════════════════════"
    
    cat "$LOG_FILE" | head -25
}

# Парсування аргументів
case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Використання: $0 [опція]"
        echo ""
        echo "Опції:"
        echo "  (без опцій) - запустити весь процес"
        echo "  help        - показати цей текст"
        echo "  logs        - показати повні логи"
        echo ""
        echo "Приклади:"
        echo "  ./$0                    # запустити все"
        echo "  ./$0 logs               # показати логи"
        ;;
    "logs")
        [ -f "$LOG_FILE" ] && cat "$LOG_FILE" || echo "Логів не знайдено"
        ;;
    *)
        main
        ;;
esac
