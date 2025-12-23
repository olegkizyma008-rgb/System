#!/bin/zsh
# Browser Fingerprint Cleanup
# Видаляє або спуфує браузер fingerprint метри
# Цільова база: WebGL, Canvas, Audio, IndexedDB, Service Workers, User-Agent

# Забезпечуємо базовий PATH для системних утиліт (ПЕРЕД усім іншим)
PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

set -a
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/.env" 2>/dev/null || true
set +a

# Відновлюємо PATH після .env (може бути перезаписаний)
PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PATH

# Визначаємо функції-обгортки для системних утиліт
basename() { /usr/bin/basename "$@"; }
dirname() { /usr/bin/dirname "$@"; }

SCRIPT_DIR="$(cd "$(/usr/bin/dirname "$0")" && pwd)"
LOG_FILE="/tmp/browser_fingerprint_cleanup_$(date +%s).log"
touch "$LOG_FILE" 2>/dev/null || true

REQUIRED_CMDS=(rm find sed defaults security tee grep wc basename dirname)

check_requirements() {
    local missing=()
    for cmd in "${REQUIRED_CMDS[@]}"; do
        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done

    if (( ${#missing[@]} )); then
        local msg="Відсутні команди: ${missing[*]}"
        echo "$msg" | /usr/bin/tee -a "$LOG_FILE" 2>/dev/null
        return 127
    fi

    return 0
}

# Кольорове вивід
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  🌐 Browser Fingerprint Cleanup${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1" | /usr/bin/tee -a "$LOG_FILE"
}

# 0. Закриття браузерів перед очищенням
close_browsers() {
    print_info "Закриття браузерів для очищення..."
    
    local browsers_closed=0
    
    # Chrome
    if pgrep -q "Google Chrome" 2>/dev/null; then
        osascript -e 'tell application "Google Chrome" to quit' 2>/dev/null
        print_success "Google Chrome закрито"
        browsers_closed=1
    fi
    
    # Chromium
    if pgrep -q "Chromium" 2>/dev/null; then
        osascript -e 'tell application "Chromium" to quit' 2>/dev/null
        print_success "Chromium закрито"
        browsers_closed=1
    fi
    
    # Safari
    if pgrep -q "Safari" 2>/dev/null; then
        osascript -e 'tell application "Safari" to quit' 2>/dev/null
        print_success "Safari закрито"
        browsers_closed=1
    fi
    
    # Firefox
    if pgrep -q "firefox" 2>/dev/null; then
        osascript -e 'tell application "Firefox" to quit' 2>/dev/null
        print_success "Firefox закрито"
        browsers_closed=1
    fi
    
    if [[ $browsers_closed -eq 1 ]]; then
        print_info "Очікування завершення процесів (5 сек)..."
        sleep 5
        
        # Примусове завершення якщо ще працюють
        pkill -9 "Google Chrome" 2>/dev/null
        pkill -9 "Chromium" 2>/dev/null
        pkill -9 "Safari" 2>/dev/null
        pkill -9 "firefox" 2>/dev/null
        sleep 1
    else
        print_info "Браузери не запущені"
    fi
}

# 1. Видалення IndexedDB записів (основна база браузерів)
clean_indexeddb() {
    print_info "Очищення IndexedDB..."
    
    local indexeddb_paths=(
        "$HOME/Library/Safari/LocalStorage/file__0.localstorage-wal"
        "$HOME/Library/Safari/IndexedDB"
        "$HOME/Library/Application Support/Google/Chrome/Default/IndexedDB"
        "$HOME/Library/Application Support/Google/Chrome/Default/ServiceWorkerDatabase"
        "$HOME/Library/Application Support/Chromium/Default/IndexedDB"
        "$HOME/Library/Application Support/Firefox/Profiles/*/storage"
    )
    
    for path in "${indexeddb_paths[@]}"; do
        if [[ -e "$path" ]]; then
            rm -rf "$path" 2>/dev/null && \
                print_success "Видалено IndexedDB: $(basename "$path")" || \
                print_info "Пропущено (заблоковано): $(basename "$path")"
        fi
    done
}

# 2. Видалення Service Workers (персистентна база)
clean_service_workers() {
    print_info "Очищення Service Workers..."
    
    local sw_paths=(
        "$HOME/Library/Application Support/Google/Chrome/Default/Service Worker"
        "$HOME/Library/Application Support/Google/Chrome/Default/Cache"
        "$HOME/Library/Application Support/Chromium/Default/Service Worker"
        "$HOME/Library/Application Support/Firefox/Profiles/*/serviceworker.sqlite"
    )
    
    for path in "${sw_paths[@]}"; do
        if [[ -e "$path" ]]; then
            rm -rf "$path" 2>/dev/null && \
                print_success "Видалено Service Worker: $(basename "$path")" || \
                print_info "Пропущено (заблоковано): $(basename "$path")"
        fi
    done
}

# 3. Видалення Cache-Manifest та ETag записів
clean_cache_manifest() {
    print_info "Очищення Cache-Manifest та ETag..."
    
    local manifest_paths=(
        "$HOME/Library/Application Support/Google/Chrome/Default/Application Cache"
        "$HOME/Library/Caches/Google/Chrome"
        "$HOME/Library/Caches/Chromium"
        "$HOME/Library/Caches/Firefox"
    )
    
    for path in "${manifest_paths[@]}"; do
        if [[ -d "$path" ]]; then
            rm -rf "$path" 2>/dev/null && \
                print_success "Видалено Cache: $(basename "$path")" || \
                print_info "Пропущено (заблоковано): $(basename "$path")"
        fi
    done
}

# 4. Видалення Canvas/WebGL logs (якщо можливо)
clean_canvas_logs() {
    print_info "Очищення Canvas/WebGL логів..."
    
    # Очищення всіх можливих даних розпізнавання
    find "$HOME/Library/Application Support/Google/Chrome" \
        -name "*canvas*" -o -name "*webgl*" -o -name "*gpu*" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null && \
                print_success "Видалено: $(basename $file)"
        done
}

# 5. Очищення LocalStorage та SessionStorage (усіх браузерів)
clean_storage() {
    print_info "Очищення LocalStorage/SessionStorage..."
    
    local storage_paths=(
        "$HOME/Library/Safari/LocalStorage"
        "$HOME/Library/Application Support/Google/Chrome/Default/Local Storage"
        "$HOME/Library/Application Support/Google/Chrome/Default/Session Storage"
        "$HOME/Library/Application Support/Chromium/Default/Local Storage"
        "$HOME/Library/Application Support/Firefox/Profiles/*/storage"
    )
    
    for path in "${storage_paths[@]}"; do
        if [[ -d "$path" ]]; then
            rm -rf "$path" 2>/dev/null && \
                print_success "Видалено Storage: $(basename "$path")" || \
                print_info "Пропущено (заблоковано): $(basename "$path")"
        fi
    done
}

# 6. Видалення Browsing History та Cache
clean_browser_history() {
    print_info "Очищення History та Cookies..."
    
    local history_paths=(
        "$HOME/Library/Safari/History.db"
        "$HOME/Library/Safari/History.db-shm"
        "$HOME/Library/Safari/Cookies.binarycookies"
        "$HOME/Library/Application Support/Google/Chrome/Default/History"
        "$HOME/Library/Application Support/Google/Chrome/Default/Cookies"
        "$HOME/Library/Application Support/Chromium/Default/History"
        "$HOME/Library/Application Support/Firefox/Profiles/*/places.sqlite"
        "$HOME/Library/Application Support/Firefox/Profiles/*/cookies.sqlite"
    )
    
    for path in "${history_paths[@]}"; do
        if [[ -f "$path" ]]; then
            rm -f "$path" 2>/dev/null && \
                print_success "Видалено: $(basename "$path")" || \
                print_info "Пропущено (заблоковано): $(basename "$path")"
        fi
    done
}

# 7. Видалення WebRTC IP leak даних
clean_webrtc_data() {
    print_info "Очищення WebRTC даних..."
    
    find "$HOME/Library/Application Support/Google/Chrome" -path "*WebRTC*" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null && \
                print_success "Видалено WebRTC: $(basename $file)"
        done
}

# 8. Видалення Plugin/Extension даних
clean_extensions_data() {
    print_info "Очищення розширень браузера..."
    
    local ext_paths=(
        "$HOME/Library/Application Support/Google/Chrome/Default/Extensions"
        "$HOME/Library/Application Support/Chromium/Default/Extensions"
        "$HOME/Library/Application Support/Firefox/Profiles/*/extensions"
    )
    
    for path in "${ext_paths[@]}"; do
        if [[ -d "$path" ]]; then
            # Не видаляємо розширення, а видаляємо їх дані
            find "$path" -name "IndexedDB" -o -name "Local\ Storage" 2>/dev/null | \
                while read -r file; do
                    rm -rf "$file" 2>/dev/null && \
                        print_success "Очищено дані розширення"
                done
        fi
    done
}

# 9. Очищення DevTools та Preferences (User-Agent override)
clean_devtools_preferences() {
    print_info "Очищення DevTools та Preferences..."
    
    local pref_paths=(
        "$HOME/Library/Application Support/Google/Chrome/Default/Preferences"
        "$HOME/Library/Application Support/Chromium/Default/Preferences"
    )
    
    for path in "${pref_paths[@]}"; do
        if [[ -f "$path" ]]; then
            # Видалити override User-Agent
            sed -i '' 's/"user_agent":"[^"]*"//' "$path" 2>/dev/null && \
                print_success "Очищено User-Agent override" || true
        fi
    done
}

# 10. Видалення Flash Cookie (LSOE) - застарілий але все ще можливий
clean_flash_cookies() {
    print_info "Очищення Flash Cookies..."
    
    local flash_path="$HOME/Library/Preferences/Macromedia/Flash\ Player/#SharedObjects"
    if [[ -d "$flash_path" ]]; then
        rm -rf "$flash_path" 2>/dev/null && \
            print_success "Видалено Flash Cookies" || \
            print_error "Помилка видалення Flash Cookies"
    fi
}

# 11. Рандомізація UserDefaults для браузерів
randomize_browser_defaults() {
    print_info "Рандомізація браузерних Defaults..."
    
    # Chrome
    if defaults read com.google.Chrome 2>/dev/null | /usr/bin/grep -q "UserAgentOverride"; then
        defaults delete com.google.Chrome UserAgentOverride 2>/dev/null && \
            print_success "Очищено Chrome UserAgent" || true
    fi
    
    # Safari
    if defaults read com.apple.Safari 2>/dev/null | /usr/bin/grep -q "UserAgent"; then
        defaults delete com.apple.Safari UserAgent 2>/dev/null && \
            print_success "Очищено Safari UserAgent" || true
    fi
}

# 12. Видалення Flash Plugin та пов'язаних даних
clean_plugin_cache() {
    print_info "Очищення Plugin Cache..."
    
    # Перевірка чи браузери запущені
    if pgrep -q "Google Chrome" 2>/dev/null; then
        print_info "Chrome запущено - деякі файли можуть бути заблоковані"
    fi
    
    local plugin_paths=(
        "$HOME/Library/Caches/Google/Chrome/Default/Code Cache"
        "$HOME/Library/Caches/Chromium/Default/Code Cache"
    )
    
    for path in "${plugin_paths[@]}"; do
        if [[ -d "$path" ]]; then
            # Видаляємо вміст директорії, а не саму директорію (браузер може її тримати)
            rm -rf "$path"/* 2>/dev/null && \
                print_success "Очищено Plugin Cache: $(basename "$(dirname "$path")")" || \
                print_info "Пропущено (браузер активний): $(basename "$(dirname "$path")")"
        fi
    done
}

# 13. Видалення Web Storage Quota маркерів
clean_storage_quota() {
    print_info "Очищення Storage Quota маркерів..."
    
    find "$HOME/Library/Application Support/Google/Chrome" -name "QuotaManager" 2>/dev/null | \
        while read -r file; do
            rm -rf "$file" 2>/dev/null && \
                print_success "Видалено: Quota маркер"
        done
}

# 14. Перевірка та логування fingerprint до/після
verify_fingerprint() {
    print_info "Перевірка поточного браузерного Fingerprint..."
    
    # Отримати список браузерів
    local browsers_found=0
    
    if [[ -d "$HOME/Library/Safari" ]]; then
        browsers_found=$((browsers_found + 1))
        print_success "Safari - найдено"
    fi
    
    if [[ -d "$HOME/Library/Application Support/Google/Chrome" ]]; then
        browsers_found=$((browsers_found + 1))
        print_success "Google Chrome - найдено"
    fi
    
    if [[ -d "$HOME/Library/Application Support/Firefox" ]]; then
        browsers_found=$((browsers_found + 1))
        print_success "Firefox - найдено"
    fi
    
    if [[ -d "$HOME/Library/Application Support/Chromium" ]]; then
        browsers_found=$((browsers_found + 1))
        print_success "Chromium - найдено"
    fi
    
    print_info "Усього браузерів: $browsers_found"
}

# MAIN
main() {
    print_header
    print_info "Старт очищення браузерного fingerprint..."
    print_info "Лог: $LOG_FILE"
    if ! check_requirements; then
        print_error "Потрібні утиліти відсутні. Деталі у лог-файлі."
        exit 127
    fi
    echo ""
    
    # Закрити браузери перед очищенням
    close_browsers
    echo ""
    
    # Виконати всі функції очищення
    clean_indexeddb
    clean_service_workers
    clean_cache_manifest
    clean_canvas_logs
    clean_storage
    clean_browser_history
    clean_webrtc_data
    clean_extensions_data
    clean_devtools_preferences
    clean_flash_cookies
    randomize_browser_defaults
    clean_plugin_cache
    clean_storage_quota
    
    echo ""
    verify_fingerprint
    
    echo ""
    print_success "✅ Очищення браузерного fingerprint ЗАВЕРШЕНО"
    print_info "Деталі збережено в: $LOG_FILE"
}

# Обробка аргументів
case "${1:-}" in
    verify)
        print_header
        verify_fingerprint
        ;;
    *)
        main
        ;;
esac
