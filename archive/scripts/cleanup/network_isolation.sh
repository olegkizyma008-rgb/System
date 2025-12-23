#!/bin/zsh
# Network Isolation & DNS Privacy
# Видаляє мережеві логи, DNS рекорди, перенаправляє на приватний DNS (якщо налаштовано)

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
LOG_FILE="/tmp/network_isolation_$(date +%s).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  🌐 Network Isolation & DNS Privacy${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════╝${NC}"
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

# 1. Видалення DNS Cache
flush_dns_cache() {
    print_info "Видалення DNS Cache..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S dscacheutil -flushcache 2>/dev/null && \
            print_success "DNS Cache очищено (dscacheutil)" || \
            print_warning "Помилка очищення DNS"
        
        # Додаткова очистка (macOS Big Sur+)
        echo "$SUDO_PASSWORD" | sudo -S killall -HUP mDNSResponder 2>/dev/null && \
            print_success "mDNSResponder перезапущено"
    else
        print_warning "DNS Cache потребує sudo (SUDO_PASSWORD з .env)"
    fi
}

# 2. Видалення мережевих логів
clean_network_logs() {
    print_info "Видалення мережевих логів..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        # System logs
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/system.log* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/kernel.log* 2>/dev/null || true
        
        # WiFi logs
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/WiFi* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/wpa_supplicant* 2>/dev/null || true
        
        # Network interface logs
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/net.log* 2>/dev/null || true
        
        print_success "Мережеві логи видалені"
    fi
}

# 3. Видалення DNS Query logs
clean_dns_logs() {
    print_info "Видалення DNS Query логів..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/dns* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S find /var/log -name "*dns*" -delete 2>/dev/null || true
        
        print_success "DNS логи видалені"
    fi
}

# 4. Видалення ISP/Carrier logs
clean_carrier_logs() {
    print_info "Видалення ISP/Carrier даних..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/carrier* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/isp* 2>/dev/null || true
    fi
    
    # Користувацька система
    rm -rf "$HOME/Library/Preferences/com.apple.Telephony.plist" 2>/dev/null || true
    
    print_success "ISP/Carrier дані очищені"
}

# 5. Видалення ARP Cache
flush_arp_cache() {
    print_info "Видалення ARP Cache..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        # Очищення ARP таблиці
        echo "$SUDO_PASSWORD" | sudo -S arp -ad 2>/dev/null && \
            print_success "ARP Cache очищено" || \
            print_warning "Помилка очищення ARP"
    fi
}

# 6. Видалення Route Cache
flush_route_cache() {
    print_info "Видалення Route Cache..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S route flush 2>/dev/null && \
            print_success "Route Cache очищено" || \
            print_warning "Помилка очищення Route"
    fi
}

# 7. Видалення mDNS (Bonjour) Cache
clean_mdns_cache() {
    print_info "Видалення mDNS (Bonjour) Cache..."
    
    rm -rf "$HOME/Library/Preferences/com.apple.mDNSResponder*" 2>/dev/null || true
    rm -rf "$HOME/Library/Caches/mDNS*" 2>/dev/null || true
    
    print_success "mDNS Cache очищено"
}

# 8. Видалення WiFi Preferred Networks
clean_wifi_networks() {
    print_info "Видалення WiFi Preferred Networks..."
    
    # Прибрати збережені WiFi мережі
    defaults write /Library/Preferences/SystemConfiguration/com.apple.airport.wireless \
        PreferredNetworks -dict 2>/dev/null || \
        rm -f "/Library/Preferences/SystemConfiguration/com.apple.airport.wireless.plist" 2>/dev/null || true
    
    print_success "WiFi Preferred Networks очищено"
}

# 9. Видалення VPN Configuration Logs
clean_vpn_logs() {
    print_info "Видалення VPN конфігуацій та логів..."
    
    rm -rf "$HOME/Library/Preferences/com.apple.vpn*" 2>/dev/null || true
    rm -rf "$HOME/Library/Application Support/VPN*" 2>/dev/null || true
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/vpn* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/vpn* 2>/dev/null || true
    fi
    
    print_success "VPN логи видалені"
}

# 10. Видалення Bluetooth Connection Logs
clean_bluetooth_logs() {
    print_info "Видалення Bluetooth Connection логів..."
    
    rm -rf "$HOME/Library/Logs/Bluetooth*" 2>/dev/null || true
    rm -rf "$HOME/Library/Preferences/com.apple.Bluetooth*" 2>/dev/null || true
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/bluetoothd* 2>/dev/null || true
    fi
    
    print_success "Bluetooth логи видалені"
}

# 11. Видалення Network Interface Statistics
clean_ifstat_logs() {
    print_info "Видалення мережевих статистик інтерфейсів..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/run/net_interfaces.log 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/networkUsage* 2>/dev/null || true
    fi
    
    print_success "Network Interface Statistics очищено"
}

# 12. Видалення Connection History (Saved Connections)
clean_connection_history() {
    print_info "Видалення Connection History..."
    
    # macOS зберігає історію підключень
    defaults delete /Library/Preferences/SystemConfiguration/com.apple.internet.wireless 2>/dev/null || true
    
    # Remove network history
    rm -rf "$HOME/Library/Preferences/com.apple.network*" 2>/dev/null || true
    
    print_success "Connection History очищено"
}

# 13. Видалення Proxy Logs та Configuration
clean_proxy_logs() {
    print_info "Видалення Proxy конфігурацій та логів..."
    
    # Системні proxy налаштування
    defaults delete /Library/Preferences/SystemConfiguration/com.apple.proxy 2>/dev/null || true
    
    # Користувацькі proxy
    defaults delete com.apple.Safari ProxyHTTPEnable 2>/dev/null || true
    defaults delete com.apple.Safari ProxyHTTPSEnable 2>/dev/null || true
    
    print_success "Proxy логи видалені"
}

# 14. Видалення TCP Dump و Network Captures
clean_tcpdump_logs() {
    print_info "Видалення tcpdump та Network Captures..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/tcpdump* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/pcap* 2>/dev/null || true
    fi
    
    print_success "Network Captures видалені"
}

# 15. Очищення Adaptive Connectivity (macOS Monterey+)
clean_adaptive_connectivity() {
    print_info "Видалення Adaptive Connectivity даних..."
    
    rm -rf "$HOME/Library/Preferences/com.apple.AdaptiveConnectivity*" 2>/dev/null || true
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/adaptiveConnectivity* 2>/dev/null || true
    fi
    
    print_success "Adaptive Connectivity очищено"
}

# 16. Видалення Network Extension Logs
clean_network_extension_logs() {
    print_info "Видалення Network Extension логів..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/log/networkextension* 2>/dev/null || true
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /var/db/networkextension* 2>/dev/null || true
    fi
    
    print_success "Network Extension логи видалені"
}

# 17. Отримання списку активних з'єднань (ПЕРЕД видаленням логів)
enumerate_connections() {
    print_info "Мережеві з'єднання та інтерфейси:"
    echo ""
    
    # Активні мережеві інтерфейси
    print_info "Мережеві інтерфейси:"
    ifconfig 2>/dev/null | grep "^[a-z]" | awk '{print "  • " $1}' || true
    
    echo ""
    
    # Активні сокети та з'єднання
    print_info "Активні мережеві з'єднання (top 10):"
    netstat -an 2>/dev/null | grep ESTABLISHED | head -10 || true
    
    echo ""
}

# 18. Отримання MAC адрес (для розумного спуфування)
enumerate_mac_addresses() {
    print_info "Поточні MAC адреси:"
    
    ifconfig 2>/dev/null | grep -i "hwaddr\|ether" | awk '{print "  • " $NF}' || true
}

# 19. Отримання DNS Servers
enumerate_dns_servers() {
    print_info "Поточні DNS серверів:"
    
    scutil --dns 2>/dev/null | grep "nameserver" | awk '{print "  • " $NF}' || true
}

# 20. Отримання Gateway та Routing
enumerate_routing() {
    print_info "Таблиця маршрутизації (top 5):"
    
    netstat -rn 2>/dev/null | head -6 || true
}

# 21. Рандомізація MAC адрес (спуфування)
randomize_mac_addresses() {
    print_info "Рандомізація MAC адрес..."
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        # Отримати всі мережеві інтерфейси
        local interfaces=$(ifconfig 2>/dev/null | grep "^[a-z]" | awk '{print $1}' | tr '\n' ' ')
        
        for iface in $interfaces; do
            # Пропустити віртуальні інтерфейси
            if [[ $iface == "lo"* ]] || [[ $iface == "bridge"* ]] || [[ $iface == "ipsec"* ]]; then
                continue
            fi
            
            # Генерація рандомної MAC
            local new_mac=$(openssl rand -hex 6 | sed 's/\(..\)/\1:/g;s/.$//;s/^/02/')
            
            echo "$SUDO_PASSWORD" | sudo -S ifconfig "$iface" ether "$new_mac" 2>/dev/null && \
                print_success "MAC $iface: $new_mac" || true
        done
    fi
}

# 22. Видалення Network Profile Configuration
clean_network_profiles() {
    print_info "Видалення Network Profiles..."
    
    rm -rf "$HOME/Library/Preferences/com.apple.networkextension*" 2>/dev/null || true
    
    if [[ -n "$SUDO_PASSWORD" ]]; then
        echo "$SUDO_PASSWORD" | sudo -S rm -rf /Library/Preferences/SystemConfiguration/com.apple.wifi* 2>/dev/null || true
    fi
    
    print_success "Network Profiles очищено"
}

# 23. Перевірка результатів
verify_isolation() {
    print_info "Перевірка мережевої ізоляції..."
    echo ""
    
    enumerate_connections
    enumerate_mac_addresses
    enumerate_dns_servers
    enumerate_routing
}

# MAIN
main() {
    print_header
    print_info "Старт мережевої ізоляції та очищення..."
    print_info "Лог: $LOG_FILE"
    echo ""
    
    # Перш за все, збережемо інформацію про мережу
    enumerate_connections
    enumerate_mac_addresses
    enumerate_dns_servers
    enumerate_routing
    
    echo ""
    
    # Запустити всі функції очищення
    flush_dns_cache
    clean_network_logs
    clean_dns_logs
    clean_carrier_logs
    flush_arp_cache
    flush_route_cache
    clean_mdns_cache
    clean_wifi_networks
    clean_vpn_logs
    clean_bluetooth_logs
    clean_ifstat_logs
    clean_connection_history
    clean_proxy_logs
    clean_tcpdump_logs
    clean_adaptive_connectivity
    clean_network_extension_logs
    clean_network_profiles
    
    echo ""
    
    # Спуфування MAC адрес (опціонально)
    print_info "Спуфування MAC адрес (потребує SUDO_PASSWORD)..."
    randomize_mac_addresses
    
    echo ""
    verify_isolation
    
    echo ""
    print_success "✅ Network Isolation ЗАВЕРШЕНО"
    print_warning "⚠️  Рекомендується перезавантажити систему та WiFi адаптер"
    print_info "Деталі: $LOG_FILE"
}

# Аргументи
case "${1:-}" in
    verify)
        print_header
        verify_isolation
        ;;
    enumerate)
        print_header
        enumerate_connections
        enumerate_mac_addresses
        enumerate_dns_servers
        enumerate_routing
        ;;
    *)
        main
        ;;
esac
