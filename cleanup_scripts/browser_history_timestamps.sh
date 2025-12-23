#!/bin/zsh
# Browser History Timestamps Spoofing - PHASE B/2
# Спуфує часи доступу до браузер файлів щоб приховати recent usage
# Додає фіктивні гапи та нестандартні паттерни у файлових часах

set -a
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$REPO_ROOT/.env" 2>/dev/null || true
set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/browser_history_timestamps_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║  📅 Browser History Timestamps Spoofing (Timeline Masking)${NC}"
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

# 1. Спуфування Safari history access times
spoof_safari_timestamps() {
    print_info "Спуфування Safari history timestamps..."
    
    # Safari BrowsingHistory.db - містить дати переглядів
    if [ -f ~/Library/Safari/BrowsingHistory.db ]; then
        # Встановлюємо старі дати (2 місяці тому)
        local old_date=$(($(date +%s) - 5184000))  # -60 днів
        local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
        
        touch -t "$new_date" ~/Library/Safari/BrowsingHistory.db 2>/dev/null
        print_success "Safari history timestamps спуфовані (-60 днів)"
    fi
    
    # Safari Cookies файл
    if [ -f ~/Library/Cookies/Cookies.binarycookies ]; then
        local old_date=$(($(date +%s) - 2592000))  # -30 днів
        local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
        
        touch -t "$new_date" ~/Library/Cookies/Cookies.binarycookies 2>/dev/null
        print_success "Safari cookies timestamps спуфовані (-30 днів)"
    fi
}

# 2. Спуфування Chrome history timestamps
spoof_chrome_timestamps() {
    print_info "Спуфування Chrome/Chromium history timestamps..."
    
    local chrome_dirs=(
        ~/Library/Application\ Support/Google/Chrome
        ~/Library/Application\ Support/Chromium
        ~/Library/Application\ Support/BraveSoftware/Brave-Browser
    )
    
    for chrome_dir in "${chrome_dirs[@]}"; do
        if [ -d "$chrome_dir" ]; then
            # History файл
            if [ -f "$chrome_dir/Default/History" ]; then
                local old_date=$(($(date +%s) - 7776000))  # -90 днів
                local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
                
                touch -t "$new_date" "$chrome_dir/Default/History" 2>/dev/null
                print_success "Chrome history timestamps спуфовані"
            fi
            
            # Top Sites (frecency ranking)
            if [ -f "$chrome_dir/Default/Top Sites" ]; then
                local old_date=$(($(date +%s) - 5184000))  # -60 днів
                local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
                
                touch -t "$new_date" "$chrome_dir/Default/Top Sites" 2>/dev/null
                print_success "Chrome Top Sites timestamps спуфовані"
            fi
        fi
    done
}

# 3. Спуфування Firefox history timestamps
spoof_firefox_timestamps() {
    print_info "Спуфування Firefox history timestamps..."
    
    if [ -d ~/.mozilla/firefox ]; then
        # places.sqlite - основна база історії
        local places_file=$(find ~/.mozilla/firefox -name "places.sqlite" 2>/dev/null | head -1)
        
        if [ -f "$places_file" ]; then
            local old_date=$(($(date +%s) - 6048000))  # -70 днів
            local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
            
            touch -t "$new_date" "$places_file" 2>/dev/null
            print_success "Firefox places.sqlite timestamps спуфовані"
        fi
        
        # Downloads file
        local downloads_file=$(find ~/.mozilla/firefox -name "downloads.sqlite" 2>/dev/null | head -1)
        if [ -f "$downloads_file" ]; then
            local old_date=$(($(date +%s) - 3456000))  # -40 днів
            local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
            
            touch -t "$new_date" "$downloads_file" 2>/dev/null
            print_success "Firefox downloads.sqlite timestamps спуфовані"
        fi
    fi
}

# 4. Додавання фіктивних гапів у файлових часах
add_fake_usage_gaps() {
    print_info "Додавання фіктивних гапів у браузер файлах..."
    
    # Створюємо фіктивні 'gap periods' щоб було невідомо коли браузер дійсно використовувався
    
    # Safari preferences
    if [ -f ~/Library/Preferences/com.apple.Safari.plist ]; then
        # Встановлюємо різні випадкові старі дати
        local dates_array=(
            "202310011200"  # October 2023
            "202309150800"  # September 2023
            "202308201600"  # August 2023
        )
        
        local rand_date=${dates_array[$RANDOM % ${#dates_array[@]}]}
        touch -t "$rand_date" ~/Library/Preferences/com.apple.Safari.plist 2>/dev/null
    fi
    
    print_success "Фіктивні usage gaps додані"
}

# 5. Рандомізація file modification times
randomize_file_mod_times() {
    print_info "Рандомізація modification times браузер кешів..."
    
    # Cache directories з випадковими старими датами
    local cache_dirs=(
        ~/Library/Caches/Google/Chrome
        ~/Library/Caches/Firefox
        ~/Library/Safari
    )
    
    for cache_dir in "${cache_dirs[@]}"; do
        if [ -d "$cache_dir" ]; then
            # Генеруємо випадкову дату між 3-6 місяцами тому
            local days_back=$((RANDOM % 120 + 90))  # 90-210 днів
            local old_date=$(($(date +%s) - (days_back * 86400)))
            local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
            
            find "$cache_dir" -type f -exec touch -t "$new_date" {} \; 2>/dev/null
            print_success "Cache modification times рандомізовані: $cache_dir"
        fi
    done
}

# 6. Спуфування Recent Searches timestamps
spoof_recent_searches() {
    print_info "Спуфування Recent Searches timestamps..."
    
    # Safari Recent Searches
    rm -rf ~/Library/Safari/LastSession.plist 2>/dev/null
    rm -rf ~/Library/Safari/RecentSearches* 2>/dev/null
    
    # Chrome omnibox history
    if [ -d ~/Library/Application\ Support/Google/Chrome/Default ]; then
        # Видаляємо Web Data що містить search history
        rm -rf ~/Library/Application\ Support/Google/Chrome/Default/Web\ Data* 2>/dev/null
        print_success "Chrome search history видалена"
    fi
    
    # Firefox search history
    rm -rf ~/.mozilla/firefox/*/search.json.mozlz4 2>/dev/null
    
    print_success "Recent searches очищена та спуфована"
}

# 7. Видалення access-related metadata
clear_file_metadata() {
    print_info "Видалення file access metadata..."
    
    # macOS stores extended attributes на файлах
    # які можуть розповісти коли файл був відкритий
    
    # Очистка extended attributes на браузер файлах
    xattr -c ~/Library/Safari/* 2>/dev/null
    xattr -c ~/Library/Preferences/com.apple.Safari.plist 2>/dev/null
    
    for chrome_dir in ~/Library/Application\ Support/Google/Chrome/*/; do
        [ -d "$chrome_dir" ] && xattr -c "$chrome_dir"* 2>/dev/null
    done
    
    print_success "File access metadata очищена"
}

# 8. Спуфування Last-Modified HTTP headers
spoof_http_header_dates() {
    print_info "Спуфування HTTP header dates у cache файлах..."
    
    # HTTP cache files містять оригінальні Last-Modified дати зі серверів
    # Ми їх робимо старшими щоб виглядало як сайти давно не відвідувалися
    
    local http_cache_dirs=(
        ~/Library/Caches/Google/Chrome/Default/Cache
        ~/Library/Caches/Firefox
    )
    
    for cache_dir in "${http_cache_dirs[@]}"; do
        if [ -d "$cache_dir" ]; then
            # Встановлюємо всім файлам дату 3+ місяці тому
            local old_date=$(($(date +%s) - 7776000))  # -90 днів
            local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
            
            find "$cache_dir" -type f -exec touch -t "$new_date" {} \; 2>/dev/null
            print_success "HTTP cache header dates спуфовані"
        fi
    done
}

# 9. Видалення download history timestamps
clear_download_history() {
    print_info "Видалення download history та timestamps..."
    
    # Safari downloads
    rm -rf ~/Library/Safari/DownloadHistory.plist 2>/dev/null
    
    # Chrome downloads
    if [ -d ~/Library/Application\ Support/Google/Chrome/Default ]; then
        # History (downloads tab)
        sqlite3 ~/Library/Application\ Support/Google/Chrome/Default/History \
            "DELETE FROM downloads;" 2>/dev/null
    fi
    
    # Firefox downloads
    if [ -f ~/.mozilla/firefox/*/downloads.sqlite ]; then
        sqlite3 ~/.mozilla/firefox/*/downloads.sqlite \
            "DELETE FROM moz_downloads;" 2>/dev/null
    fi
    
    print_success "Download history очищена"
}

# 10. Спуфування session restore timestamps
spoof_session_timestamps() {
    print_info "Спуфування session restore timestamps..."
    
    # Safari session
    if [ -f ~/Library/Safari/LastSession.plist ]; then
        local old_date=$(($(date +%s) - 2592000))  # -30 днів
        local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
        touch -t "$new_date" ~/Library/Safari/LastSession.plist 2>/dev/null
        print_success "Safari session timestamps спуфовані"
    fi
    
    # Chrome sessions
    for session_file in ~/Library/Application\ Support/Google/Chrome/Default/Sessions/*; do
        [ -f "$session_file" ] && {
            local old_date=$(($(date +%s) - 1728000))  # -20 днів
            local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
            touch -t "$new_date" "$session_file" 2>/dev/null
        }
    done
    
    print_success "Session restore timestamps спуфовані"
}

# 11. Видалення bookmark access times
clear_bookmark_timestamps() {
    print_info "Видалення bookmark access timestamp tracking..."
    
    # Safari bookmarks
    if [ -f ~/Library/Safari/Bookmarks.plist ]; then
        local old_date=$(($(date +%s) - 10368000))  # -120 днів
        local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
        touch -t "$new_date" ~/Library/Safari/Bookmarks.plist 2>/dev/null
        print_success "Safari bookmarks timestamps спуфовані"
    fi
    
    # Chrome bookmarks
    if [ -f ~/Library/Application\ Support/Google/Chrome/Default/Bookmarks ]; then
        local old_date=$(($(date +%s) - 10368000))  # -120 днів
        local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
        touch -t "$new_date" ~/Library/Application\ Support/Google/Chrome/Default/Bookmarks 2>/dev/null
        print_success "Chrome bookmarks timestamps спуфовані"
    fi
    
    print_success "Bookmark timestamps очищена"
}

# 12. Додавання фіктивних activity gaps
add_fake_activity_gaps() {
    print_info "Додавання фіктивних activity gaps для уникнення correlation..."
    
    # Створюємо фіктивні 'activity pause periods' щоб було невідомо
    # коли насправді браузер використовувався
    
    # Встановлюємо деякі файли на очень стару дату (2023)
    touch -t "202301011000" ~/Library/Safari/History.db 2>/dev/null
    
    # Інші на дещо свіжішу (30 днів тому)
    local old_date=$(($(date +%s) - 2592000))
    local new_date=$(date -r $old_date +%Y%m%d%H%M.%S)
    touch -t "$new_date" ~/Library/Safari/Bookmarks.plist 2>/dev/null
    
    print_success "Фіктивні activity gaps додані для timeline masking"
}

main() {
    print_header
    
    print_info "════════════════════════════════════════════════════════════"
    print_info "Запущено спуфування браузер history timestamps"
    print_info "════════════════════════════════════════════════════════════"
    
    spoof_safari_timestamps
    spoof_chrome_timestamps
    spoof_firefox_timestamps
    add_fake_usage_gaps
    randomize_file_mod_times
    spoof_recent_searches
    clear_file_metadata
    spoof_http_header_dates
    clear_download_history
    spoof_session_timestamps
    clear_bookmark_timestamps
    add_fake_activity_gaps
    
    print_info "════════════════════════════════════════════════════════════"
    print_success "✅ Browser History Timestamps Spoofing ЗАВЕРШЕНО"
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
