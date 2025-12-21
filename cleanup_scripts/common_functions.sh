#!/bin/zsh

# ═══════════════════════════════════════════════════════════════
#  📦 COMMON FUNCTIONS - Спільні функції для всіх cleanup модулів
#  Використовується: Windsurf, Antigravity, Cursor, VS Code
# ═══════════════════════════════════════════════════════════════

# Запобігаємо повторному завантаженню
[[ -n "$COMMON_FUNCTIONS_LOADED" ]] && return 0
export COMMON_FUNCTIONS_LOADED=1

# ─────────────────────────────────────────────────────────────────
# ВИЗНАЧЕННЯ ШЛЯХІВ
# ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
REPO_ROOT="$SCRIPT_DIR"
if [ ! -f "$REPO_ROOT/cleanup_modules.json" ] && [ -f "$SCRIPT_DIR/../cleanup_modules.json" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# ─────────────────────────────────────────────────────────────────
# ЗАВАНТАЖЕННЯ ЗМІННИХ СЕРЕДОВИЩА
# ─────────────────────────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs 2>/dev/null)
fi

# Режими виконання
export AUTO_YES="${AUTO_YES:-1}"
export UNSAFE_MODE="${UNSAFE_MODE:-0}"

# ─────────────────────────────────────────────────────────────────
# SUDO HELPER
# ─────────────────────────────────────────────────────────────────
SUDO_HELPER="$REPO_ROOT/cleanup_scripts/sudo_helper.sh"
if [ ! -f "$SUDO_HELPER" ] && [ -f "$REPO_ROOT/sudo_helper.sh" ]; then
    SUDO_HELPER="$REPO_ROOT/sudo_helper.sh"
fi
export SUDO_ASKPASS="$SUDO_HELPER"
chmod +x "$SUDO_ASKPASS" 2>/dev/null

# Перевизначення sudo для використання askpass
sudo() { command sudo -A "$@"; }

# ─────────────────────────────────────────────────────────────────
# КОЛЬОРИ ДЛЯ ВИВОДУ
# ─────────────────────────────────────────────────────────────────
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export WHITE='\033[1;37m'
export NC='\033[0m'

# ─────────────────────────────────────────────────────────────────
# ФУНКЦІЇ ВИВОДУ
# ─────────────────────────────────────────────────────────────────
print_header() {
    local title="$1"
    local color="${2:-$CYAN}"
    echo ""
    echo -e "${color}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${color}║${NC}  ${WHITE}$title${NC}"
    echo -e "${color}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    local step="$1"
    local total="$2"
    local message="$3"
    echo -e "${BLUE}[$step/$total]${NC} $message"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# ─────────────────────────────────────────────────────────────────
# ФУНКЦІЇ ГЕНЕРАЦІЇ ІДЕНТИФІКАТОРІВ
# ─────────────────────────────────────────────────────────────────
generate_uuid() {
    uuidgen | tr '[:upper:]' '[:lower:]'
}

generate_machine_id() {
    openssl rand -hex 16
}

generate_machine_id_32() {
    openssl rand -hex 32
}

generate_mac_address() {
    # Локально адміністрована MAC-адреса (починається з 02)
    printf '02:%02x:%02x:%02x:%02x:%02x' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256))
}

# ─────────────────────────────────────────────────────────────────
# ФУНКЦІЇ HOSTNAME
# ─────────────────────────────────────────────────────────────────
REAL_NAMES=("Alex" "James" "Michael" "David" "Robert" "John" "Richard" "Charles" "Daniel" "Matthew" "Anthony" "Mark" "Donald" "Steven" "Paul" "Andrew" "Joshua" "Kenneth" "Kevin" "Brian" "George" "Edward" "Ronald" "Timothy" "Jason" "Jeffrey" "Ryan" "Jacob" "Gary" "Nicholas" "Eric" "Jonathan" "Stephen" "Larry" "Justin" "Scott" "Brandon" "Benjamin" "Samuel" "Frank" "Gregory" "Alexander" "Patrick" "Dennis" "Jerry" "Tyler" "Aaron" "Jose" "Adam" "Henry" "Nathan" "Zachary" "Kyle" "Walter" "Peter" "Harold" "Jeremy" "Keith" "Roger" "Gerald" "Carl" "Terry" "Sean" "Austin" "Arthur" "Lawrence" "Jesse" "Dylan" "Bryan" "Joe" "Jordan" "Billy" "Bruce" "Albert" "Willie" "Gabriel" "Logan" "Alan" "Juan" "Wayne" "Roy" "Ralph" "Randy" "Eugene" "Vincent" "Russell" "Elijah" "Louis" "Bobby" "Philip" "Johnny" "Bradley" "Noah" "Emma" "Olivia" "Ava" "Sophia" "Isabella" "Mia" "Charlotte" "Amelia" "Harper" "Evelyn" "Abigail" "Emily" "Elizabeth" "Sofia" "Avery" "Ella" "Scarlett" "Grace" "Chloe" "Victoria" "Riley" "Aria" "Lily" "Aubrey" "Zoey" "Penelope" "Lillian" "Addison" "Layla" "Natalie" "Camila" "Hannah" "Brooklyn" "Zoe" "Nora" "Leah" "Savannah" "Audrey" "Claire" "Eleanor" "Skylar" "Ellie" "Samantha" "Stella" "Paisley" "Violet" "Mila" "Allison" "Alexa" "Anna" "Hazel" "Aaliyah" "Ariana" "Lucy" "Caroline" "Sarah" "Genesis" "Kennedy" "Sadie" "Gabriella" "Madelyn" "Adeline" "Maya")

PLACE_NAMES=("Studio" "Office" "Desktop" "Workspace" "Workstation" "Lab" "Server" "Machine" "System" "Device" "Node" "Box" "Computer" "Platform" "Station" "Terminal" "Host" "Client" "Instance" "Pod" "iMac" "MacBook" "MacStudio" "MacPro" "Mini" "Pro" "Air" "MBP" "MBA" "Mac" "Laptop" "Tower" "Rig" "Setup" "Build" "Dev" "Work" "Home" "Personal" "Main" "Primary" "Secondary" "Backup" "Test" "Prod" "Local" "Remote" "Cloud" "Edge" "Core" "Hub" "Gateway")

SUFFIXES=("01" "02" "1" "2" "Pro" "Plus" "Max" "Ultra" "SE" "Air" "Mini" "Lite")
PREFIXES=("Dev" "Work" "Home" "Office" "Main" "My" "The")

generate_hostname() {
    local attempt=0
    local max_attempts=10
    local format=$((RANDOM % 5))
    local new_hostname=""
    
    while [ $attempt -lt $max_attempts ]; do
        case $format in
            0)
                new_hostname="${REAL_NAMES[$((RANDOM % ${#REAL_NAMES[@]}))]}-${PLACE_NAMES[$((RANDOM % ${#PLACE_NAMES[@]}))]}"
                ;;
            1)
                new_hostname="${REAL_NAMES[$((RANDOM % ${#REAL_NAMES[@]}))]}-${PLACE_NAMES[$((RANDOM % ${#PLACE_NAMES[@]}))]}-${SUFFIXES[$((RANDOM % ${#SUFFIXES[@]}))]}"
                ;;
            2)
                new_hostname="${PREFIXES[$((RANDOM % ${#PREFIXES[@]}))]}-${REAL_NAMES[$((RANDOM % ${#REAL_NAMES[@]}))]}"
                ;;
            3)
                new_hostname="${REAL_NAMES[$((RANDOM % ${#REAL_NAMES[@]}))]}s-${PLACE_NAMES[$((RANDOM % ${#PLACE_NAMES[@]}))]}"
                ;;
            4)
                new_hostname="${PLACE_NAMES[$((RANDOM % ${#PLACE_NAMES[@]}))]}-${REAL_NAMES[$((RANDOM % ${#REAL_NAMES[@]}))]}"
                ;;
        esac
        
        # Валідація
        if [ -n "$new_hostname" ] && [ ${#new_hostname} -gt 3 ] && [[ "$new_hostname" != "-"* ]] && [[ "$new_hostname" != *"-" ]]; then
            echo "$new_hostname"
            return 0
        fi
        
        attempt=$((attempt + 1))
        format=$((RANDOM % 5))
    done
    
    # Fallback
    echo "User-Mac-$RANDOM"
}

# ─────────────────────────────────────────────────────────────────
# ДОПОМІЖНІ ФУНКЦІЇ
# ─────────────────────────────────────────────────────────────────
safe_remove() {
    local path="$1"
    if [ -e "$path" ]; then
        rm -rf "$path" 2>/dev/null
        print_success "Видалено: $(basename "$path")"
        return 0
    fi
    return 1
}

safe_remove_glob() {
    local pattern="$1"
    local matched=0
    for path in $~pattern; do
        [ -e "$path" ] && safe_remove "$path" && matched=1
    done
    return $matched
}

confirm() {
    local prompt="$1"
    if [ "${AUTO_YES}" = "1" ]; then
        return 0
    fi
    read -q "REPLY?${prompt} (y/n) "
    echo ""
    [[ "$REPLY" =~ ^[Yy]$ ]]
}

check_safe_mode() {
    local script_name="$1"
    if [ "${UNSAFE_MODE}" != "1" ]; then
        echo ""
        print_warning "SAFE_MODE: $script_name вимкнено."
        print_info "Увімкніть UNSAFE_MODE=1 у .env якщо потрібно виконати небезпечні операції."
        exit 0
    fi
}

check_sudo() {
    sudo -v 2>/dev/null
    if [ $? -ne 0 ]; then
        print_error "Не вдалося отримати sudo права. Перевірте SUDO_PASSWORD у .env"
        exit 1
    fi
    print_success "Права адміністратора отримано"
}

# ─────────────────────────────────────────────────────────────────
# ВИЗНАЧЕННЯ РЕДАКТОРІВ ТА ЇХ ШЛЯХІВ
# ─────────────────────────────────────────────────────────────────
declare -A EDITOR_PATHS
EDITOR_PATHS[vscode]="$HOME/Library/Application Support/Code"
EDITOR_PATHS[windsurf]="$HOME/Library/Application Support/Windsurf"
EDITOR_PATHS[cursor]="$HOME/Library/Application Support/Cursor"
EDITOR_PATHS[antigravity]="$HOME/Library/Application Support/Antigravity"

declare -A EDITOR_PROCESS_NAMES
EDITOR_PROCESS_NAMES[vscode]="Code"
EDITOR_PROCESS_NAMES[windsurf]="Windsurf"
EDITOR_PROCESS_NAMES[cursor]="Cursor"
EDITOR_PROCESS_NAMES[antigravity]="Antigravity"

declare -A EDITOR_BUNDLE_IDS
EDITOR_BUNDLE_IDS[vscode]="com.microsoft.VSCode"
EDITOR_BUNDLE_IDS[windsurf]="com.exafunction.windsurf"
EDITOR_BUNDLE_IDS[cursor]="com.todesktop.230313mzl4w4u92"
EDITOR_BUNDLE_IDS[antigravity]="com.google.antigravity"

declare -A EDITOR_KEYCHAIN_SERVICES
EDITOR_KEYCHAIN_SERVICES[vscode]="Code Visual\ Studio\ Code com.microsoft.VSCode VS\ Code GitHub github.com Microsoft microsoft.com"
EDITOR_KEYCHAIN_SERVICES[windsurf]="Windsurf windsurf com.windsurf Windsurf\ Editor Codeium\ Windsurf Codeium codeium codeium.com api.codeium.com com.exafunction.windsurf"
EDITOR_KEYCHAIN_SERVICES[cursor]="Cursor cursor com.cursor Cursor\ Editor cursor.sh api.cursor.sh com.todesktop.230313mzl4w4u92"
EDITOR_KEYCHAIN_SERVICES[antigravity]="Antigravity antigravity Google\ Antigravity google-antigravity antigravity.google.com api.antigravity.google.com com.google.antigravity"

# ─────────────────────────────────────────────────────────────────
# ФУНКЦІЇ ОЧИЩЕННЯ РЕДАКТОРІВ
# ─────────────────────────────────────────────────────────────────
stop_editor() {
    local editor="$1"
    local process_name="${EDITOR_PROCESS_NAMES[$editor]}"
    
    if [ -n "$process_name" ]; then
        pkill -f "$process_name" 2>/dev/null
        sleep 2
        print_success "Зупинено $process_name"
    fi
}

cleanup_editor_machine_id() {
    local editor="$1"
    local base_path="${EDITOR_PATHS[$editor]}"
    local machineid_path="$base_path/machineid"
    
    if [ -f "$machineid_path" ]; then
        local new_id=$(generate_machine_id)
        echo "$new_id" > "$machineid_path"
        print_success "Machine ID оновлено: $new_id"
    fi
}

cleanup_editor_storage() {
    local editor="$1"
    local base_path="${EDITOR_PATHS[$editor]}"
    
    local storage_paths=(
        "$base_path/storage.json"
        "$base_path/User/globalStorage/storage.json"
    )
    
    for storage_path in "${storage_paths[@]}"; do
        if [ -f "$storage_path" ]; then
            local new_device_id=$(generate_uuid)
            local new_session_id=$(generate_uuid)
            local new_machine_id=$(generate_machine_id)
            local new_mac_machine_id=$(generate_machine_id)
            
            cat > "$storage_path" << EOF
{
  "telemetry.machineId": "$new_machine_id",
  "telemetry.macMachineId": "$new_mac_machine_id",
  "telemetry.devDeviceId": "$new_device_id",
  "telemetry.sqmId": "{$(generate_uuid)}",
  "install.time": "$(date +%s)000",
  "sessionId": "$new_session_id",
  "firstSessionDate": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
  "lastSessionDate": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
}
EOF
            print_success "Storage оновлено: $(basename "$storage_path")"
        fi
    done
}

cleanup_editor_caches() {
    local editor="$1"
    local base_path="${EDITOR_PATHS[$editor]}"
    
    local cache_paths=(
        "$base_path/User/globalStorage/state.vscdb"
        "$base_path/User/globalStorage/state.vscdb.backup"
        "$base_path/Local Storage"
        "$base_path/Session Storage"
        "$base_path/IndexedDB"
        "$base_path/databases"
        "$base_path/GPUCache"
        "$base_path/CachedData"
        "$base_path/Code Cache"
        "$base_path/User/workspaceStorage"
        "$base_path/logs"
        "$base_path/Cookies"
        "$base_path/Cookies-journal"
        "$base_path/Network Persistent State"
        "$base_path/TransportSecurity"
        "$base_path/Trust Tokens"
        "$base_path/SharedStorage"
        "$base_path/WebStorage"
    )
    
    for path in "${cache_paths[@]}"; do
        safe_remove "$path"
    done
}

cleanup_editor_keychain() {
    local editor="$1"
    local services="${EDITOR_KEYCHAIN_SERVICES[$editor]}"
    
    for service in ${(s: :)services}; do
        # Видаляємо екрановані пробіли
        service="${service//\\ / }"
        security delete-generic-password -s "$service" 2>/dev/null
        security delete-internet-password -s "$service" 2>/dev/null
        security delete-generic-password -l "$service" 2>/dev/null
    done
    print_success "Keychain очищено для $editor"
}

# Повне очищення редактора
cleanup_editor_full() {
    local editor="$1"
    local base_path="${EDITOR_PATHS[$editor]}"
    local process_name="${EDITOR_PROCESS_NAMES[$editor]}"
    
    print_header "🧹 Очищення $editor" "$CYAN"
    
    # 1. Зупинка процесу
    print_step 1 5 "Зупинка $process_name..."
    stop_editor "$editor"
    
    # 2. Machine ID
    print_step 2 5 "Оновлення Machine ID..."
    cleanup_editor_machine_id "$editor"
    
    # 3. Storage
    print_step 3 5 "Оновлення Storage..."
    cleanup_editor_storage "$editor"
    
    # 4. Caches
    print_step 4 5 "Видалення кешів..."
    cleanup_editor_caches "$editor"
    
    # 5. Keychain
    print_step 5 5 "Очищення Keychain..."
    cleanup_editor_keychain "$editor"
    
    print_success "Очищення $editor завершено!"
}
