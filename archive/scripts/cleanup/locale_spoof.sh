#!/bin/zsh
# Locale & Timezone Spoofing
# Змінює системну локаль, мову, timezone для маскування identity
# Важливо: впливає на весь систему, потребує перезаваантажу

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
LOG_FILE="/tmp/locale_spoof_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  🌍 Locale & Timezone Spoofing${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
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

# Масив доступних локалей та timezones для рандомізації
RANDOM_LOCALES=(
    "en_GB.UTF-8"      # Британська англійська
    "en_US.UTF-8"      # Американська англійська
    "de_DE.UTF-8"      # Німецька
    "fr_FR.UTF-8"      # Французька
    "es_ES.UTF-8"      # Іспанська
    "it_IT.UTF-8"      # Італійська
    "ja_JP.UTF-8"      # Японська
    "zh_CN.UTF-8"      # Китайська (Спрощена)
    "pl_PL.UTF-8"      # Польська
    "ru_RU.UTF-8"      # Російська
    "uk_UA.UTF-8"      # Українська
    "pt_BR.UTF-8"      # Португальська (Бразилія)
    "ko_KR.UTF-8"      # Корейська
)

RANDOM_TIMEZONES=(
    "America/New_York"
    "America/Los_Angeles"
    "Europe/London"
    "Europe/Berlin"
    "Europe/Paris"
    "Asia/Tokyo"
    "Asia/Shanghai"
    "Australia/Sydney"
    "Asia/Singapore"
    "Europe/Moscow"
    "America/Toronto"
    "America/Mexico_City"
    "America/Sao_Paulo"
    "Africa/Cairo"
)

# 🔧 VPN-до-Locale маппінг (новий - для ClearVPN автодетекції)
declare -A VPN_LOCALE_MAP=(
    ["Ukraine"]="uk_UA.UTF-8"
    ["Україна"]="uk_UA.UTF-8"
    ["UA"]="uk_UA.UTF-8"
    ["USA"]="en_US.UTF-8"
    ["America"]="en_US.UTF-8"
    ["United States"]="en_US.UTF-8"
    ["US"]="en_US.UTF-8"
    ["Germany"]="de_DE.UTF-8"
    ["Deutschland"]="de_DE.UTF-8"
    ["DE"]="de_DE.UTF-8"
    ["France"]="fr_FR.UTF-8"
    ["FR"]="fr_FR.UTF-8"
    ["UK"]="en_GB.UTF-8"
    ["United Kingdom"]="en_GB.UTF-8"
    ["GB"]="en_GB.UTF-8"
    ["Spain"]="es_ES.UTF-8"
    ["ES"]="es_ES.UTF-8"
    ["Japan"]="ja_JP.UTF-8"
    ["JP"]="ja_JP.UTF-8"
    ["Poland"]="pl_PL.UTF-8"
    ["PL"]="pl_PL.UTF-8"
    ["Russia"]="ru_RU.UTF-8"
    ["RU"]="ru_RU.UTF-8"
    ["Canada"]="en_CA.UTF-8"
    ["CA"]="en_CA.UTF-8"
    ["Brazil"]="pt_BR.UTF-8"
    ["BR"]="pt_BR.UTF-8"
)

declare -A VPN_TIMEZONE_MAP=(
    ["Ukraine"]="Europe/Kyiv"
    ["Україна"]="Europe/Kyiv"
    ["UA"]="Europe/Kyiv"
    ["USA"]="America/New_York"
    ["America"]="America/New_York"
    ["United States"]="America/New_York"
    ["US"]="America/New_York"
    ["Germany"]="Europe/Berlin"
    ["Deutschland"]="Europe/Berlin"
    ["DE"]="Europe/Berlin"
    ["France"]="Europe/Paris"
    ["FR"]="Europe/Paris"
    ["UK"]="Europe/London"
    ["United Kingdom"]="Europe/London"
    ["GB"]="Europe/London"
    ["Spain"]="Europe/Madrid"
    ["ES"]="Europe/Madrid"
    ["Japan"]="Asia/Tokyo"
    ["JP"]="Asia/Tokyo"
    ["Poland"]="Europe/Warsaw"
    ["PL"]="Europe/Warsaw"
    ["Russia"]="Europe/Moscow"
    ["RU"]="Europe/Moscow"
    ["Canada"]="America/Toronto"
    ["CA"]="America/Toronto"
    ["Brazil"]="America/Sao_Paulo"
    ["BR"]="America/Sao_Paulo"
)

# 1. Зберегти поточні налаштування
backup_locale_settings() {
    print_info "Зберігаємо поточні локаль налаштування..."
    
    local backup_file="$HOME/.locale_spoof_backup_$(date +%s).txt"
    
    {
        echo "=== Backup Locale Settings ==="
        echo "Date: $(date)"
        echo ""
        echo "Current LANG: $LANG"
        echo "Current LC_ALL: $LC_ALL"
        echo "Current LC_TIME: $LC_TIME"
        echo "Current LC_COLLATE: $LC_COLLATE"
        echo "Current LC_MONETARY: $LC_MONETARY"
        echo "Current LC_NUMERIC: $LC_NUMERIC"
        echo ""
        echo "Timezone: $(date +%Z)"
        echo "UTC Offset: $(date +%z)"
        echo ""
        echo "System Locales Available:"
        locale -a | head -20
    } > "$backup_file"
    
    print_success "Backup збережено: $backup_file"
}

# 🔧 НОВА ФУНКЦІЯ: Детекція VPN з ClearVPN
detect_vpn_country() {
    print_info "Виявлення поточного VPN..." >&2
    
    local vpn_country=""
    
    # Спосіб 1: 🌐 АВТОДЕТЕКЦІЯ через IP (ipinfo.io) - НАЙНАДІЙНІШИЙ
    vpn_country=$(curl -s --connect-timeout 5 ipinfo.io/country 2>/dev/null | tr -d '\n\r ' || echo "")
    
    if [[ -n "$vpn_country" && ${#vpn_country} -eq 2 ]]; then
        print_success "🌐 VPN виявлена через IP (ipinfo.io): $vpn_country" >&2
        echo "$vpn_country"
        return 0
    fi
    
    # Спосіб 2: Прочитати з ClearVPN defaults
    vpn_country=$(defaults read com.clearvpn.mac Country 2>/dev/null || echo "")
    
    if [[ -n "$vpn_country" ]]; then
        print_success "VPN виявлена з ClearVPN: $vpn_country" >&2
        echo "$vpn_country"
        return 0
    fi
    
    # Спосіб 3: Спробувати через launchctl/system preferences
    vpn_country=$(defaults read NSGlobalDomain AppleLocale 2>/dev/null | grep -o "[A-Z][A-Z]" || echo "")
    
    if [[ -n "$vpn_country" ]]; then
        print_success "VPN виявлена з системи: $vpn_country" >&2
        echo "$vpn_country"
        return 0
    fi
    
    # Спосіб 4: Користувацька переменна з .env
    if [[ -n "$VPN_COUNTRY" ]]; then
        print_info "Використання VPN_COUNTRY з .env: $VPN_COUNTRY" >&2
        echo "$VPN_COUNTRY"
        return 0
    fi
    
    # Fallback: запитати користувача
    print_warning "Не вдалося автоматично виявити VPN" >&2
    print_info "Доступні опції: Ukraine, USA, Germany, France, UK, Japan" >&2
    echo "UA"  # Default fallback - Ukraine
}

# 🔧 НОВА ФУНКЦІЯ: Отримати locale по країні VPN
get_locale_for_vpn() {
    local country="$1"
    
    # Нормалізувати назву країни
    country=$(echo "$country" | tr '[:lower:]' '[:upper:]')
    
    # Перевірити в маппінгу
    if [[ -n "${VPN_LOCALE_MAP[$country]}" ]]; then
        echo "${VPN_LOCALE_MAP[$country]}"
    else
        # Fallback на рандомну
        select_random_locale
    fi
}

# 🔧 НОВА ФУНКЦІЯ: Отримати timezone по країні VPN
get_timezone_for_vpn() {
    local country="$1"
    
    # Нормалізувати назву країни
    country=$(echo "$country" | tr '[:lower:]' '[:upper:]')
    
    # Перевірити в маппінгу
    if [[ -n "${VPN_TIMEZONE_MAP[$country]}" ]]; then
        echo "${VPN_TIMEZONE_MAP[$country]}"
    else
        # Fallback на рандомну
        select_random_timezone
    fi
}

# 2. Вибрати рандомну локаль
select_random_locale() {
    local array_size=${#RANDOM_LOCALES[@]}
    local random_index=$((RANDOM % array_size))
    echo "${RANDOM_LOCALES[$random_index]}"
}

# 3. Вибрати рандомний timezone
select_random_timezone() {
    local array_size=${#RANDOM_TIMEZONES[@]}
    local random_index=$((RANDOM % array_size))
    echo "${RANDOM_TIMEZONES[$random_index]}"
}

# 4. Змінити системну локаль (macOS)
set_system_locale() {
    local new_locale="$1"
    
    print_info "Встановлення локалі: $new_locale"
    
    # ⚠️ НЕ чіпаємо AppleLanguages - щоб не змінювати мову системи
    # Тільки встановлюємо AppleLocale для регіональних форматів
    local locale_code="${new_locale%%.*}"  # uk_UA.UTF-8 -> uk_UA
    defaults write NSGlobalDomain AppleLocale -string "$locale_code" 2>/dev/null && \
        print_success "Регіон (AppleLocale): $locale_code" || \
        print_warning "Помилка встановлення регіону"
    
    # Встановити LANG для поточної сесії
    export LANG="$new_locale"
    export LC_ALL="$new_locale"
}

# 5. Змінити системний timezone
set_system_timezone() {
    local new_tz="$1"
    
    print_info "Встановлення timezone: $new_tz"
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        # Потребує sudo для системного timezone
        echo "$SUDO_PASSWORD" | sudo -S systemsetup -settimezone "$new_tz" 2>/dev/null && \
            print_success "Timezone: $new_tz" || \
            print_warning "Помилка встановлення timezone (потребує sudo)"
    else
        # Альтернатива - встановити посилання
        if [[ -f "/usr/share/zoneinfo/$new_tz" ]]; then
            ln -sf "/usr/share/zoneinfo/$new_tz" "$HOME/.timezone" 2>/dev/null && \
                export TZ="$new_tz" && \
                print_success "Timezone встановлено (локально): $new_tz"
        fi
    fi
}

# 6. Змінити формат часу
set_time_format() {
    print_info "Змінення формату часу..."
    
    # macOS Date Format
    defaults write NSGlobalDomain AppleICUForce -bool true 2>/dev/null || true
    
    # Встановити рандомний формат часу
    local time_formats=(
        "HH:mm:ss"      # 24-годинний
        "h:mm:ss a"     # 12-годинний
        "HH:mm"         # 24-годинний без секунд
        "h:mm a"        # 12-годинний без секунд
    )
    
    local random_format="${time_formats[$((RANDOM % ${#time_formats[@]}))]}"
    defaults write NSGlobalDomain NSTimeFormatString "$random_format" 2>/dev/null && \
        print_success "Формат часу: $random_format" || true
}

# 7. Змінити формат дати
set_date_format() {
    print_info "Змінення формату дати..."
    
    local date_formats=(
        "dd/MM/yyyy"    # DD/MM/YYYY
        "MM/dd/yyyy"    # MM/DD/YYYY
        "yyyy-MM-dd"    # ISO 8601
        "dd.MM.yyyy"    # DD.MM.YYYY
        "d MMM yyyy"    # 1 Jan 2023
    )
    
    local random_format="${date_formats[$((RANDOM % ${#date_formats[@]}))]}"
    defaults write NSGlobalDomain NSDateFormatString "$random_format" 2>/dev/null && \
        print_success "Формат дати: $random_format" || true
}

# 8. Змінити символи числових форматів
set_number_format() {
    print_info "Змінення числового формату..."
    
    # Різні розділювачі для чисел
    defaults write NSGlobalDomain AppleICUNumberFormatStrings -dict \
        "decimal_sep" "," \
        "thousands_sep" "." \
        "currency_code" "EUR" 2>/dev/null || true
    
    print_success "Числовий формат змінено (EU-стиль)"
}

# 9. Очистити дані про регіон
clean_region_data() {
    print_info "Видалення даних про регіон..."
    
    # Видалити кешовані регіональні налаштування
    rm -rf "$HOME/Library/Preferences/com.apple.HIToolbox.plist" 2>/dev/null || true
    rm -rf "$HOME/Library/Preferences/.AppleSetupDone" 2>/dev/null || true
    
    print_success "Регіональні дані видалені"
}

# 10. Змінити мову браузера (User-Agent header)
set_browser_language() {
    print_info "Змінення мови браузера..."
    
    # Chrome
    local prefs_path="$HOME/Library/Application Support/Google/Chrome/Default/Preferences"
    if [[ -f "$prefs_path" ]]; then
        sed -i '' 's/"accept_languages":"[^"]*"/"accept_languages":"en-US,en;q=0.9"/' "$prefs_path" 2>/dev/null && \
            print_success "Chrome мова: en-US" || true
    fi
    
    # Safari
    defaults write com.apple.Safari NSBrowserLanguages -array "en-US" 2>/dev/null && \
        print_success "Safari мова: en-US" || true
}

# 11. Спуфити Apple ID регіон
spoof_apple_id_region() {
    print_info "Спуфування Apple ID регіону..."
    
    defaults write com.apple.AppleID AppleIDAccountRegion "US" 2>/dev/null && \
        print_success "Apple ID регіон: US" || true
}

# 12. Встановити рандомний input method
set_input_method() {
    print_info "Встановлення методу введення..."
    
    # Системне введення
    defaults write com.apple.HIToolbox AppleCurrentKeyboardLayoutIdentifier "com.apple.keylayout.US" 2>/dev/null && \
        print_success "Input Method: US" || true
}

# 13. Очистити System Locale preferences
clean_system_prefs() {
    print_info "Очищення системних Preferences..."
    
    # Видалити всі locale-специфічні preferences
    find "$HOME/Library/Preferences" -name "*Locale*" -o -name "*Language*" 2>/dev/null | \
        while read -r file; do
            rm -f "$file" 2>/dev/null
        done
    
    print_success "Системні preferences очищені"
}

# 14. Перевірка поточних налаштувань
verify_changes() {
    print_info "Перевірка встановлених налаштувань..."
    echo ""
    
    print_info "Поточна локаль: $(locale | head -1)"
    print_info "Поточний Timezone: $(date +%Z)"
    print_info "UTC Offset: $(date +%z)"
    print_info "Мова системи: $(defaults read NSGlobalDomain AppleLanguages 2>/dev/null | head -1)"
    print_info "Формат часу: $(defaults read NSGlobalDomain NSTimeFormatString 2>/dev/null)"
    print_info "Формат дати: $(defaults read NSGlobalDomain NSDateFormatString 2>/dev/null)"
    
    echo ""
}

# MAIN
main() {
    print_header
    print_info "Старт маскування локалі та timezone..."
    print_info "Лог: $LOG_FILE"
    echo ""
    print_warning "⚠️  Деякі зміни вимагають перезавантаження"
    echo ""
    
    # Зберегти поточні налаштування
    backup_locale_settings
    echo ""
    
    # 🔧 НОВА ЛОГІКА: Спробувати виявити VPN
    local vpn_country=$(detect_vpn_country)
    print_info "Визначена країна VPN: $vpn_country"
    echo ""
    
    # Вибрати параметри на основі VPN або рандомні
    local new_locale=$(get_locale_for_vpn "$vpn_country")
    local new_tz=$(get_timezone_for_vpn "$vpn_country")
    
    print_info "Встановлення локалі: $new_locale"
    print_info "Встановлення timezone: $new_tz"
    echo ""
    
    # Застосувати зміни
    set_system_locale "$new_locale"
    set_system_timezone "$new_tz"
    set_time_format
    set_date_format
    set_number_format
    clean_region_data
    set_browser_language
    spoof_apple_id_region
    set_input_method
    clean_system_prefs
    
    echo ""
    verify_changes
    
    echo ""
    print_success "✅ Маскування локалі ЗАВЕРШЕНО (синхронізовано з VPN)"
    print_warning "⚠️  Перезавантажте систему для повного застосування змін"
    print_info "Деталі: $LOG_FILE"
}

# Аргументи
case "${1:-}" in
    verify)
        print_header
        verify_changes
        ;;
    restore)
        print_header
        if [[ -n "$2" ]]; then
            print_info "Відновлення з backup: $2"
            cat "$2"
        fi
        ;;
    *)
        main
        ;;
esac
