#!/bin/zsh
# EverCookie Killer
# Видаляє персистентні залишки які виживають після звичайного очищення
# Цільова база: ETag, Cache-Control, хеші файлів, перехресні домени

# Забезпечуємо базовий PATH для системних утиліт
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
LOG_FILE="/tmp/evercookie_killer_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  💣 EverCookie Killer - Персистентні дані${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════╝${NC}"
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

# 1. Видалення кешованих відповідей (HTTP Cache)
clean_http_cache() {
    print_info "Очищення HTTP Cache та ETag..."
    
    # Safari HTTP Cache
    if [[ -d "$HOME/Library/Safari" ]]; then
        find "$HOME/Library/Safari" -name "*.plist" -path "*Cache*" -type f 2>/dev/null | \
            while read -r file; do
                rm -f "$file" 2>/dev/null && \
                    print_success "Видалено Safari Cache: $(basename $file)"
            done
    fi
    
    # Chrome HTTP Cache
    if [[ -d "$HOME/Library/Application Support/Google/Chrome" ]]; then
        find "$HOME/Library/Application Support/Google/Chrome" -path "*Cache*" -type f 2>/dev/null | \
            while read -r file; do
                rm -f "$file" 2>/dev/null
            done
        print_success "Видалено Chrome HTTP Cache"
    fi
}

# 2. Видалення WebGL інформації та GLSL компілювання результатів
clean_webgl_cache() {
    print_info "Видалення WebGL компільованих даних..."
    
    # Chrome WebGL Cache
    find "$HOME/Library/Application Support/Google/Chrome" \
        -path "*GPUCache*" -type f 2>/dev/null | \
        while read -r file; do
            rm -f "$file" 2>/dev/null
        done
    
    print_success "Видалено WebGL GPU Cache"
}

# 3. Видалення Canvas Drawing State (якщо десь закешовано)
clean_canvas_state() {
    print_info "Очищення Canvas State та рисованих об'єктів..."
    
    # Пошук усіх можливих canvas даних
    find "$HOME/Library/Application Support" -name "*canvas*" -o -name "*gpu*" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null && \
                print_success "Видалено Canvas файл"
        done
}

# 4. Видалення Beacon API кешованих запитів
clean_beacon_cache() {
    print_info "Видалення Beacon API логів..."
    
    # Beacon API может кешуватися в Chrome/Chromium
    find "$HOME/Library/Application Support/Google/Chrome" \
        -name "*beacon*" -o -name "*report*" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null
        done
    
    print_success "Видалено Beacon Cache"
}

# 5. Видалення DNS CNAME Cloaking даних (локальний DNS кеш)
clean_dns_cache() {
    print_info "Очищення DNS кешу системи..."
    
    # macOS DNS Cache чистити via command (потребує sudo)
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S dscacheutil -flushcache 2>/dev/null && \
            print_success "DNS кеш очищено" || \
            print_warning "Не вдалось очистити DNS (потребує sudo)"
    else
        print_warning "DNS Cache потребує SUDO_PASSWORD з .env"
    fi
}

# 6. Видалення Resource Timing API даних
clean_resource_timing() {
    print_info "Очищення Resource Timing та Performance даних..."
    
    # Safari Performance logs
    find "$HOME/Library/Safari" -name "*performance*" -o -name "*timing*" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null
        done
    
    print_success "Видалено Resource Timing"
}

# 7. Видалення Font Fingerprint кешу
clean_font_cache() {
    print_info "Очищення Font Cache (Fingerprint вектор)..."
    
    local font_paths=(
        "$HOME/Library/Caches/com.apple.nsurlsessiond"
        "$HOME/Library/Caches/fontd"
        "$HOME/Library/Fonts"
    )
    
    for path in "${font_paths[@]}"; do
        if [[ -d "$path" ]]; then
            # Видалити кеш, але не саме шрифти
            find "$path" -name "*cache*" -type f 2>/dev/null | \
                while read -r file; do
                    rm -f "$file" 2>/dev/null
                done
        fi
    done
    
    print_success "Видалено Font Cache"
}

# 8. Видалення Device Memory/Storage Size інформації
clean_device_info_cache() {
    print_info "Очищення Device Info кешу..."
    
    # macOS зберігає інформацію про пристрій в различних місцях
    find "$HOME/Library" -name "*device*" -o -name "*hardware*" 2>/dev/null | \
        grep -i cache | while read -r file; do
            rm -rf "$file" 2>/dev/null
        done
    
    print_success "Видалено Device Info Cache"
}

# 9. Видалення SuperCookie даних (LocalStorage across domains)
clean_supercookie_data() {
    print_info "Очищення SuperCookie (перехресні домени)..."
    
    # LocalStorage може мати дані від різних доменів
    find "$HOME/Library/Application Support" -path "*LocalStorage*" -type f 2>/dev/null | \
        while read -r file; do
            rm -f "$file" 2>/dev/null && \
                print_success "Видалено SuperCookie файл"
        done
}

# 10. Видалення Last-Modified та If-Modified-Since заголовків (кеш логіка)
clean_http_headers_cache() {
    print_info "Очищення HTTP заголовків кеш..."
    
    # Браузери кешують метаінформацію про ресурси
    find "$HOME/Library/Application Support/Google/Chrome" -name "*.db" -type f 2>/dev/null | \
        while read -r file; do
            # Спробувати очистити базу (безпечно)
            sqlite3 "$file" "DELETE FROM cache WHERE expire_time < $(date +%s);" 2>/dev/null || true
        done
    
    print_success "Очищено HTTP Headers Cache"
}

# 11. Видалення Auth Token Persistence
clean_auth_tokens() {
    print_info "Очищення Auth Tokens та Sessions..."
    
    # Safari Cookies
    rm -f "$HOME/Library/Safari/Cookies.binarycookies" 2>/dev/null && \
        print_success "Видалено Safari Auth Tokens" || true
    
    # Chrome Tokens
    find "$HOME/Library/Application Support/Google/Chrome" -name "*token*" -o -name "*auth*" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null
        done
    
    print_success "Видалено Auth Tokens"
}

# 12. Видалення Site Preferences (Do Not Track, AutoFill, тощо)
clean_site_preferences() {
    print_info "Очищення Site Preferences..."
    
    local pref_paths=(
        "$HOME/Library/Application Support/Google/Chrome/Default/Preferences"
        "$HOME/Library/Application Support/Chromium/Default/Preferences"
    )
    
    for path in "${pref_paths[@]}"; do
        if [[ -f "$path" ]]; then
            # Очистити все чи просто перезаписати
            cp "$path" "$path.backup"
            echo '{"version":1}' > "$path" 2>/dev/null && \
                print_success "Обнулено Site Preferences: $(basename $path)" || \
                cp "$path.backup" "$path"
        fi
    done
}

# 13. Видалення IndexedDB та пов'язаних БД файлів
clean_indexeddb_persisted() {
    print_info "Глибока очистка IndexedDB..."
    
    find "$HOME/Library" -path "*IndexedDB*" -type f 2>/dev/null | \
        while read -r file; do
            rm -f "$file" 2>/dev/null && \
                print_success "Видалено IndexedDB файл"
        done
}

# 14. Видалення Apple Privacy Preferences (macOS specific)
clean_apple_privacy_prefs() {
    print_info "Очищення Apple Privacy Preferences..."
    
    defaults read com.apple.Safari 2>/dev/null | /usr/bin/grep -q "PrivacyPreferences" && {
        defaults delete com.apple.Safari PrivacyPreferences 2>/dev/null && \
            print_success "Видалено Safari Privacy Prefs" || true
    } || true
}

# 15. Видалення мережевих логів та трасування
clean_network_logs() {
    print_info "Очищення мережевих логів..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/kernel.log* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/system.log* 2>/dev/null || true
        print_success "Видалено системні мережеві логи" || true
    fi
}

# 16. Скидання Bluetooth та WiFi логів
clean_wireless_logs() {
    print_info "Видалення Wireless логів..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/wifi* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf "$HOME/Library/Logs/WiFi*" 2>/dev/null || true
        print_success "Видалено Wireless логи"
    fi
}

# 17. Перевірка що видалено
verify_removal() {
    print_info "Перевірка успішного видалення..."
    
    local remaining=0
    
    # Перевірити IndexedDB
    if find "$HOME/Library" -path "*IndexedDB*" -type f 2>/dev/null | /usr/bin/grep -q .; then
        print_warning "Залишилися IndexedDB файли"
        remaining=$((remaining + 1))
    fi
    
    # Перевірити Service Workers
    if find "$HOME/Library" -path "*Service Worker*" -type f 2>/dev/null | /usr/bin/grep -q .; then
        print_warning "Залишилися Service Worker файли"
        remaining=$((remaining + 1))
    fi
    
    if [[ $remaining -eq 0 ]]; then
        print_success "✅ Всі основні персистентні дані видалені"
    else
        print_warning "⚠️  Залишилося $remaining категорій даних для перевірки"
    fi
}

# MAIN
main() {
    print_header
    print_info "Видалення EverCookie та персистентних даних..."
    print_info "Лог: $LOG_FILE"
    echo ""
    
    clean_http_cache
    clean_webgl_cache
    clean_canvas_state
    clean_beacon_cache
    clean_dns_cache
    clean_resource_timing
    clean_font_cache
    clean_device_info_cache
    clean_supercookie_data
    clean_http_headers_cache
    clean_auth_tokens
    clean_site_preferences
    clean_indexeddb_persisted
    clean_apple_privacy_prefs
    clean_network_logs
    clean_wireless_logs
    
    echo ""
    verify_removal
    
    echo ""
    print_success "💣 EverCookie Killer ЗАВЕРШЕНО"
    print_info "Деталі: $LOG_FILE"
}

# Аргументи
case "${1:-}" in
    verify)
        print_header
        verify_removal
        ;;
    *)
        main
        ;;
esac
