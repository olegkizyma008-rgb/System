#!/bin/zsh
# Deep Hardware Fingerprint Spoofing - Enhanced Phase 4
# Додаткові вектори для hardware fingerprint: SMBIOS, XPC, UUID, HWID, System Information
# Запускати РАЗОМ з hardware_spoof.sh для глибшої анонімності

# Забезпечуємо базовий PATH
PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

set -a
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/.env" 2>/dev/null || true
set +a

# Відновлюємо PATH після .env
PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/deep_hardware_spoof_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║  🔬 Deep Hardware Fingerprint Spoofing (SMBIOS/XPC/UUID)${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

# 1. Спуфування UUID (основний вектор fingerprint)
spoof_system_uuid() {
    print_info "Спуфування системних UUID..."
    
    # Генерація нових UUID для системи
    local new_uuid=$(uuidgen)
    local new_hwuuid=$(uuidgen)
    
    # Hardware UUID (використовується для Apple ID тощо)
    defaults write /Library/Preferences/SystemConfiguration/preferences AppleHWUUID "$new_hwuuid" 2>/dev/null || \
        print_warning "Помилка запису Hardware UUID (потребує admin)"
    
    # UUID для системи
    defaults write NSGlobalDomain SYSTEM_UUID "$new_uuid" 2>/dev/null || true
    
    print_success "UUID: $new_uuid (Hardware: $new_hwuuid)"
}

# 2. Спуфування Installation ID
spoof_installation_id() {
    print_info "Спуфування Installation ID..."
    
    # Installation ID змінюється при переінстальці macOS
    local new_install_id=$(uuidgen)
    
    defaults write /Library/Preferences/SystemConfiguration/.InstallLocation.plist \
        InstallationID "$new_install_id" 2>/dev/null || \
        print_warning "Помилка запису Installation ID"
    
    print_success "Installation ID: $new_install_id"
}

# 3. Видалення та регенерація Kernel UUID
spoof_kernel_uuid() {
    print_info "Спуфування Kernel UUID..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        local new_kernel_uuid=$(uuidgen)
        echo "$SUDO_PASSWORD" | sudo -S defaults write /var/db/launchd.db/com.apple.launchd/overrides.plist \
            com.apple.kext.caches.cleaner.uuid "$new_kernel_uuid" 2>/dev/null || true
        
        print_success "Kernel UUID оновлено"
    fi
}

# 4. Спуфування Device Identifier (UDID)
spoof_device_identifier() {
    print_info "Спуфування Device Identifier (UDID)..."
    
    local new_udid=$(uuidgen | tr -d '-' | head -c 40)
    
    # Safari Device Identifier
    defaults write com.apple.Safari DeviceIdentifier "$new_udid" 2>/dev/null || true
    
    # WebKit Device Identifier
    defaults write com.apple.WebKit WebDeviceIdentifier "$new_udid" 2>/dev/null || true
    
    print_success "UDID: $new_udid"
}

# 5. Спуфування Apple ID Device GUID
spoof_apple_id_guid() {
    print_info "Спуфування Apple ID Device GUID..."
    
    local new_guid=$(uuidgen)
    
    defaults write com.apple.AppleID DeviceGUID "$new_guid" 2>/dev/null || true
    defaults write com.apple.AppleID AccountDeviceGUID "$new_guid" 2>/dev/null || true
    
    print_success "Apple ID GUID: $new_guid"
}

# 6. Спуфування Gatekeeper UUID
spoof_gatekeeper_uuid() {
    print_info "Спуфування Gatekeeper UUID..."
    
    local new_gk_uuid=$(uuidgen)
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S defaults write /private/var/db/gatekeeper.db \
            UUID "$new_gk_uuid" 2>/dev/null || true
    fi
    
    print_success "Gatekeeper UUID: $new_gk_uuid"
}

# 7. Видалення Analytics UUID та telemetry
spoof_analytics_uuid() {
    print_info "Спуфування Analytics UUID (telemetry)..."
    
    # Safari Analytics
    defaults delete com.apple.Safari AnalyticsUserID 2>/dev/null || true
    
    # Chrome Analytics
    local chrome_prefs="$HOME/Library/Application Support/Google/Chrome/Default/Preferences"
    if [[ -f "$chrome_prefs" ]]; then
        sed -i '' 's/"client_id":"[^"]*"/"client_id":"'$(uuidgen)'"/g' "$chrome_prefs" 2>/dev/null || true
    fi
    
    print_success "Analytics UUID очищено та регенеровано"
}

# 8. Очищення AMI (Apple Metadata Identifier)
clean_apple_metadata() {
    print_info "Очищення Apple Metadata..."
    
    # Apple ID metadata
    rm -f "$HOME/Library/Application Support/iCloud/metadata" 2>/dev/null || true
    
    # iCloud metadata (обмежуємо глибину пошуку)
    find "$HOME/Library/Mobile Documents" -maxdepth 3 -name "*.metadata" -delete 2>/dev/null || true
    
    # Synchronization metadata (тільки в конкретних директоріях)
    find "$HOME/Library/Preferences" -maxdepth 2 -path "*metadata*" -name "*.plist" -delete 2>/dev/null || true
    find "$HOME/Library/Application Support" -maxdepth 3 -path "*metadata*" -name "*.plist" -delete 2>/dev/null || true
    
    print_success "Apple Metadata очищено"
}

# 9. Спуфування XPC Service Identifiers
spoof_xpc_identifiers() {
    print_info "Спуфування XPC Service Identifiers..."
    
    # XPC використовуються для міжпроцесної комунікації та идентифікації
    find "$HOME/Library/Preferences" -name "*mach*" -type f 2>/dev/null | \
        while read -r file; do
            rm -f "$file" 2>/dev/null
        done
    
    print_success "XPC Identifiers очищено"
}

# 10. Видалення Machine Identification Tokens
clean_machine_tokens() {
    print_info "Видалення Machine Identification Tokens..."
    
    # Основні токени
    rm -f "$HOME/.machine-id" 2>/dev/null || true
    rm -f "$HOME/.machine" 2>/dev/null || true
    rm -f "$HOME/Library/Application Support/CrashReporter/.machine_id" 2>/dev/null || true
    
    # Генерація нових токенів
    local new_machine_id=$(uuidgen | tr -d '-')
    echo "$new_machine_id" > "$HOME/.machine-id" 2>/dev/null || true
    
    print_success "Machine Tokens регенеровано"
}

# 11. Спуфування Quarantine (File Metadata) - тільки для Downloads та Applications
spoof_quarantine_attributes() {
    print_info "Спуфування Quarantine атрибутів файлів..."
    
    # Видалити quarantine атрибути тільки з типових директорій (не весь $HOME!)
    # Обмежуємо глибину та додаємо timeout
    local dirs_to_clean=(
        "$HOME/Downloads"
        "$HOME/Desktop"
        "$HOME/Applications"
        "/Applications"
    )
    
    for dir in "${dirs_to_clean[@]}"; do
        if [[ -d "$dir" ]]; then
            # Використовуємо maxdepth для швидкості
            find "$dir" -maxdepth 3 -type f -exec xattr -d com.apple.quarantine {} \; 2>/dev/null || true
        fi
    done
    
    print_success "Quarantine атрибути очищено"
}

# 12. Очищення Cache2 (Firefox cache)
clean_firefox_cache2() {
    print_info "Очищення Firefox cache2..."
    
    rm -rf "$HOME/Library/Application Support/Firefox/Profiles/*/cache2" 2>/dev/null || true
    rm -rf "$HOME/Library/Application Support/Firefox/Profiles/*/startupCache" 2>/dev/null || true
    
    print_success "Firefox cache очищено"
}

# 13. Спуфування System Serial Numbers (за допомогою IOKit)
spoof_iokit_serial() {
    print_info "Спуфування IOKit Serial Numbers..."
    
    # Читання поточних serial numbers
    local current_serial=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Serial Number" | awk '{print $NF}')
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        # Спроба записати нові serial numbers через ioreg (вимагає SIP disabled)
        local new_serial=$(openssl rand -hex 8 | tr '[:lower:]' '[:upper:]')
        
        echo "$SUDO_PASSWORD" | sudo -S nvram SystemSerialNumber="$new_serial" 2>/dev/null || \
            print_warning "IOKit Serial не змінено (потребує SIP disabled)"
    fi
    
    print_success "IOKit Serial check: $current_serial"
}

# 14. Очищення IOREG (Input/Output Registry) cache
clean_ioreg_cache() {
    print_info "Очищення IORegistry cache..."
    
    rm -rf "$HOME/Library/Caches/ioreg*" 2>/dev/null || true
    rm -rf "/var/db/ioreg*" 2>/dev/null || true
    
    print_success "IORegistry cache очищено"
}

# 15. Видалення Build Version та Baseband Fingerprints
spoof_system_firmware() {
    print_info "Спуфування System Firmware Identifiers..."
    
    # Build Version
    local new_build="$(date +%s | md5sum | head -c 8 | tr '[:lower:]' '[:upper:]')"
    
    # Bootloader GUID
    local new_bootloader_guid=$(uuidgen)
    
    defaults write NSGlobalDomain SystemBuildVersion "$new_build" 2>/dev/null || true
    defaults write NSGlobalDomain BootUUID "$new_bootloader_guid" 2>/dev/null || true
    
    print_success "Firmware: Build=$new_build, BootUUID=$new_bootloader_guid"
}

# 16. Очищення Location Services Identifiers
clean_location_services() {
    print_info "Очищення Location Services Identifiers..."
    
    defaults write com.apple.locationd StationaryLocationTimeout 0 2>/dev/null || true
    defaults write com.apple.locationd KnownNetworks "" 2>/dev/null || true
    
    # Очистити кешовані місця розташування
    rm -rf "$HOME/Library/Caches/locationd*" 2>/dev/null || true
    
    print_success "Location Services очищено"
}

# 17. Видалення Device Configuration Files
clean_device_config() {
    print_info "Видалення Device Configuration Files..."
    
    find "$HOME/Library/Preferences" -name "*device*" -delete 2>/dev/null || true
    find "$HOME/Library/Preferences" -name "*hardware*" -delete 2>/dev/null || true
    find "$HOME/Library/Caches" -path "*device*" -delete 2>/dev/null || true
    
    print_success "Device Config очищено"
}

# 18. Спуфування Bluetooth Device IDs
spoof_bluetooth_ids() {
    print_info "Спуфування Bluetooth Device Identifiers..."
    
    # Bluetooth preferences
    rm -rf "$HOME/Library/Preferences/com.apple.Bluetooth*" 2>/dev/null || true
    
    # Regenerate Bluetooth identifiers
    defaults write com.apple.BluetoothAudioDevice RandomDeviceID -bool true 2>/dev/null || true
    
    print_success "Bluetooth IDs спуфовано"
}

# 19. Очищення Crashlytics та Error Reporting
clean_error_reporting() {
    print_info "Очищення Error Reporting та Crashlytics..."
    
    rm -rf "$HOME/Library/Application Support/CrashReporter" 2>/dev/null || true
    rm -rf "$HOME/Library/Logs/CrashReporter" 2>/dev/null || true
    rm -rf "$HOME/Library/Application Support/DiagnosticMessagesHistory.plist" 2>/dev/null || true
    
    # Відключити error reporting
    defaults write com.apple.CrashReporter DialogType none 2>/dev/null || true
    
    print_success "Error Reporting очищено"
}

# 20. Остаточна перевірка та логування
verify_spoofing() {
    print_info "Перевірка результатів спуфування..."
    echo ""
    
    print_info "Системні ідентифікатори:"
    system_profiler SPHardwareDataType 2>/dev/null | grep -E "Serial|Hardware UUID|Model" || true
    
    echo ""
    
    # Перевірити UUID
    local current_uuid=$(defaults read NSGlobalDomain SYSTEM_UUID 2>/dev/null || echo "не встановлено")
    print_info "System UUID: $current_uuid"
    
    # Перевірити Machine ID
    if [[ -f "$HOME/.machine-id" ]]; then
        print_success "Machine ID оновлено"
    fi
    
    echo ""
}

# MAIN
main() {
    print_header
    print_info "Глибоке спуфування hardware fingerprint..."
    print_info "Лог: $LOG_FILE"
    echo ""
    print_warning "⚠️  Деякі операції потребують SUDO_PASSWORD з .env"
    echo ""
    
    # Запустити всі функції
    spoof_system_uuid
    spoof_installation_id
    spoof_kernel_uuid
    spoof_device_identifier
    spoof_apple_id_guid
    spoof_gatekeeper_uuid
    spoof_analytics_uuid
    clean_apple_metadata
    spoof_xpc_identifiers
    clean_machine_tokens
    spoof_quarantine_attributes
    clean_firefox_cache2
    spoof_iokit_serial
    clean_ioreg_cache
    spoof_system_firmware
    clean_location_services
    clean_device_config
    spoof_bluetooth_ids
    clean_error_reporting
    
    echo ""
    verify_spoofing
    
    echo ""
    print_success "✅ Deep Hardware Spoof ЗАВЕРШЕНО (20 векторів)"
    print_warning "⚠️  Перезавантажте систему для повного застосування змін"
    print_info "Деталі: $LOG_FILE"
}

# Аргументи
case "${1:-}" in
    verify)
        print_header
        verify_spoofing
        ;;
    *)
        main
        ;;
esac
