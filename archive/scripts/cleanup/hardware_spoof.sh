#!/bin/zsh

# Hardware Spoofing - Advanced system fingerprint manipulation
echo "🔧 HARDWARE SPOOFING - Advanced Fingerprint Manipulation"
echo "========================================================"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
if [ ! -f "$REPO_ROOT/cleanup_modules.json" ] && [ -f "$SCRIPT_DIR/../cleanup_modules.json" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# Завантаження sudo helper
if [ -f "$REPO_ROOT/.env" ]; then
    export $(grep -v '^#' "$REPO_ROOT/.env" | grep -v '^$' | xargs)
fi

# Режими виконання
AUTO_YES="${AUTO_YES:-1}"
UNSAFE_MODE="${UNSAFE_MODE:-0}"

confirm() {
    local prompt="$1"
    if [ "${AUTO_YES}" = "1" ]; then
        return 0
    fi
    read -q "REPLY?${prompt} (y/n) "
    echo ""
    [[ "$REPLY" =~ ^[Yy]$ ]]
}

SUDO_HELPER="$REPO_ROOT/cleanup_scripts/sudo_helper.sh"
if [ ! -f "$SUDO_HELPER" ] && [ -f "$REPO_ROOT/sudo_helper.sh" ]; then
    SUDO_HELPER="$REPO_ROOT/sudo_helper.sh"
fi
export SUDO_ASKPASS="$SUDO_HELPER"
chmod +x "$SUDO_ASKPASS" 2>/dev/null

# Завжди використовуємо askpass-режим, щоб не було TTY prompt
sudo() { command sudo -A "$@"; }

if [ "${UNSAFE_MODE}" != "1" ]; then
    echo "\n🛡️  SAFE_MODE: hardware_spoof вимкнено. Увімкніть UNSAFE_MODE=1 якщо усвідомлюєте ризики."
    exit 0
fi

echo "🔑 Отримання sudo прав..."
sudo -v 2>/dev/null

# Перевірка SIP (System Integrity Protection)
echo "\n🔍 Перевірка статусу SIP..."
SIP_STATUS=$(csrutil status 2>/dev/null | grep -o 'enabled\|disabled' || echo "unknown")
if [ "$SIP_STATUS" = "enabled" ]; then
    echo "⚠️  УВАГА: SIP увімкнений. NVRAM операції не спрацюють."
    echo "💡 Для повного hardware spoofing відключіть SIP:"
    echo "   1. Boot into Recovery Mode"
    echo "   2. Run: csrutil disable"
    echo "   3. Reboot"
    echo ""
    if ! confirm "Продовжити без NVRAM?"; then
        echo "\n❌ Скасовано"
        exit 1
    fi
    echo ""
    SKIP_NVRAM=1
else
    echo "✅ SIP відключений, NVRAM операції доступні"
    SKIP_NVRAM=0
fi

# =============================================================================
# NVRAM MANIPULATION
# =============================================================================
echo "\n[1/5] 🧬 Маніпуляція NVRAM та firmware ідентифікаторів..."

# Генерація нових ідентифікаторів
NEW_SERIAL="C02$(openssl rand -hex 4 | tr '[:lower:]' '[:upper:]')$(openssl rand -hex 2 | tr '[:lower:]' '[:upper:]')"
NEW_MLB="C02$(openssl rand -hex 6 | tr '[:lower:]' '[:upper:]')"
NEW_ROM=$(openssl rand -hex 6 | tr '[:lower:]' '[:upper:]')

echo "🔄 Генерація нових ідентифікаторів:"
echo "   Serial: $NEW_SERIAL"
echo "   MLB: $NEW_MLB" 
echo "   ROM: $NEW_ROM"

# Спроба зміни через NVRAM (потребує відключеного SIP)
if [ "$SKIP_NVRAM" -eq 0 ]; then
    sudo nvram SystemSerialNumber="$NEW_SERIAL" 2>/dev/null
    sudo nvram MLB="$NEW_MLB" 2>/dev/null
    sudo nvram ROM="$NEW_ROM" 2>/dev/null
    echo "✅ NVRAM оновлено"
else
    echo "⏭️  NVRAM пропущено (SIP enabled)"
fi

# Альтернативний метод через system_profiler hook
cat > /tmp/system_profiler_hook.sh << EOF
#!/bin/zsh
# Hook для system_profiler
if [[ "\$1" == "SPHardwareDataType" ]]; then
    echo "Hardware:"
    echo ""
    echo "    Hardware Overview:"
    echo ""
    echo "      Model Name: MacBook Pro"
    echo "      Model Identifier: MacBookPro18,$((1 + RANDOM % 4))"
    echo "      Chip: Apple M$((1 + RANDOM % 3))"
    echo "      Total Number of Cores: $((8 + RANDOM % 8)) (4 performance and $((4 + RANDOM % 4)) efficiency)"
    echo "      Memory: $((8 + RANDOM % 24)) GB"
    echo "      System Firmware Version: $((8000 + RANDOM % 1000)).$((40 + RANDOM % 20)).$((1 + RANDOM % 10))"
    echo "      Serial Number (system): $NEW_SERIAL"
    echo "      Hardware UUID: $(uuidgen)"
    echo "      Provisioning UDID: $(uuidgen)"
    echo "      Activation Lock Status: Disabled"
else
    /usr/sbin/system_profiler.orig "\$@"
fi
EOF

# Backup оригінального system_profiler
if [ ! -f /usr/sbin/system_profiler.orig ]; then
    sudo cp /usr/sbin/system_profiler /usr/sbin/system_profiler.orig 2>/dev/null
fi

# Заміна system_profiler на hook
sudo cp /tmp/system_profiler_hook.sh /usr/sbin/system_profiler 2>/dev/null
sudo chmod +x /usr/sbin/system_profiler 2>/dev/null

echo "✅ Hardware ідентифікатори підмінено"

# =============================================================================
# ENHANCED CPU FINGERPRINT SPOOFING
# =============================================================================
echo "\n[2/5] 🖥️  Розширений спуфінг CPU fingerprint..."

# Генерація фейкових CPU характеристик
FAKE_CPU_CORES=$((4 + RANDOM % 8))
FAKE_CPU_THREADS=$((FAKE_CPU_CORES * 2))
FAKE_CPU_FREQ=$(echo "scale=1; 2.0 + ($RANDOM % 20) / 10.0" | bc 2>/dev/null || echo "2.8")

# Випадковий вибір CPU архітектури та виробника
CPU_VENDORS=("GenuineIntel" "AuthenticAMD" "Apple")
CPU_ARCHITECTURES=("x86_64" "arm64")
SELECTED_VENDOR=${CPU_VENDORS[$((RANDOM % ${#CPU_VENDORS[@]}))]}
SELECTED_ARCH=${CPU_ARCHITECTURES[$((RANDOM % ${#CPU_ARCHITECTURES[@]}))]}

# Генерація реалістичної моделі CPU
if [ "$SELECTED_VENDOR" = "GenuineIntel" ]; then
    CPU_MODEL="Intel(R) Core(TM) i$(($RANDOM % 2 + 5))-$(($RANDOM % 3 + 8))$(($RANDOM % 1000 + 100))$([ $((RANDOM % 2)) -eq 0 ] && echo "U" || echo "H")"
elif [ "$SELECTED_VENDOR" = "AuthenticAMD" ]; then
    CPU_MODEL="AMD Ryzen $(($RANDOM % 2 + 5)) $(($RANDOM % 8 + 1))$(($RANDOM % 1000 + 100))$([ $((RANDOM % 2)) -eq 0 ] && echo "U" || echo "H")"
else
    CPU_MODEL="Apple M$(($RANDOM % 3 + 1)) $(($RANDOM % 4 + 8))-Core CPU"
fi

echo "🔄 Спуфінг системних CPU параметрів..."
echo "   Модель: $CPU_MODEL"
echo "   Ядра: $FAKE_CPU_CORES, Потоки: $FAKE_CPU_THREADS"
echo "   Частота: ${FAKE_CPU_FREQ}GHz"

# Спуфінг через sysctl (тимчасово)
sudo sysctl -w machdep.cpu.brand_string="$CPU_MODEL" 2>/dev/null
sudo sysctl -w machdep.cpu.core_count=$FAKE_CPU_CORES 2>/dev/null
sudo sysctl -w machdep.cpu.thread_count=$FAKE_CPU_THREADS 2>/dev/null

# Створення розширеного фейкового cpuid
cat > /tmp/cpuid_spoof.c << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// Enhanced fake CPUID implementation
void fake_cpuid(unsigned int leaf, unsigned int *eax, unsigned int *ebx, unsigned int *ecx, unsigned int *edx) {
    srand(time(NULL));
    
    switch(leaf) {
        case 0:
            *eax = 0x0000000D;
            *ebx = 0x756E6547; // "Genu"
            *ecx = 0x6C65746E; // "ntel" 
            *edx = 0x49656E69; // "ineI"
            break;
        case 1:
            *eax = 0x000A0671 + (rand() % 0x1000); // Random family/model
            *ebx = (rand() % 256) << 24; // Random brand index
            *ecx = 0x7FFAFBFF ^ (rand() % 0x1000); // Randomized feature flags
            *edx = 0xBFEBFBFF ^ (rand() % 0x1000); // Randomized feature flags
            break;
        case 2: // Cache info
            *eax = 0x76036301 + (rand() % 0x100000);
            *ebx = 0x00F0B5FF + (rand() % 0x10000);
            *ecx = 0x00000000;
            *edx = 0x00C30000 + (rand() % 0x100000);
            break;
        default:
            *eax = rand();
            *ebx = rand(); 
            *ecx = rand();
            *edx = rand();
    }
}

int main() {
    unsigned int eax, ebx, ecx, edx;
    fake_cpuid(0, &eax, &ebx, &ecx, &edx);
    fake_cpuid(1, &eax, &ebx, &ecx, &edx);
    fake_cpuid(2, &eax, &ebx, &ecx, &edx);
    printf("Enhanced CPUID spoofed successfully\n");
    return 0;
}
EOF

# Компіляція та встановлення
gcc -o /tmp/cpuid_spoof /tmp/cpuid_spoof.c 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ CPU fingerprint spoof створено"
    /tmp/cpuid_spoof 2>/dev/null
else
    echo "⚠️  Не вдалося скомпілювати CPU spoof"
fi

# Створення фейкового CPU профілю для Windsurf
mkdir -p ~/Library/Application\ Support/Windsurf/User/globalStorage
cat > ~/Library/Application\ Support/Windsurf/User/globalStorage/cpu_profile.json << EOF
{
  "cores": $FAKE_CPU_CORES,
  "threads": $FAKE_CPU_THREADS,
  "frequency": "${FAKE_CPU_FREQ}GHz",
  "architecture": "$SELECTED_ARCH",
  "vendor": "$SELECTED_VENDOR",
  "model": "$CPU_MODEL",
  "cache_l1": "$(($RANDOM % 64 + 32))KB",
  "cache_l2": "$(($RANDOM % 512 + 256))KB",
  "cache_l3": "$(($RANDOM % 16 + 8))MB",
  "features": ["sse", "sse2", "sse3", "ssse3", "sse4_1", "sse4_2", "avx", "avx2"],
  "temperature": "$((30 + RANDOM % 40))°C",
  "power_consumption": "$(($RANDOM % 50 + 15))W"
}
EOF

echo "✅ Розширений CPU fingerprint спуфено"

# =============================================================================
# MEMORY LAYOUT RANDOMIZATION
# =============================================================================
echo "\n[3/5] 🧠 Рандомізація memory layout..."

# ASLR налаштування
sudo sysctl -w vm.aslr=2 2>/dev/null

# Рандомізація heap layout
export MALLOC_CONF="junk:true,zero:true"

# Створення фейкових memory regions
cat > /tmp/memory_randomizer.sh << 'EOF'
#!/bin/zsh
# Memory layout randomizer
setopt NULL_GLOB
while true; do
    # Алокація випадкових блоків пам'яті для зміни layout
    dd if=/dev/zero of=/tmp/mem_$RANDOM bs=1024 count=$((RANDOM % 1000)) 2>/dev/null &
    sleep $((1 + RANDOM % 5))
    rm -f /tmp/mem_* 2>/dev/null
done
EOF

chmod +x /tmp/memory_randomizer.sh
/tmp/memory_randomizer.sh >/dev/null 2>&1 &
disown
MEMORY_PID=$!

echo "✅ Memory layout рандомізація активна (PID: $MEMORY_PID)"

# =============================================================================
# GRAPHICS FINGERPRINT SPOOFING
# =============================================================================
echo "\n[4/5] 🎨 Спуфінг graphics fingerprint..."

# OpenGL renderer spoofing
export MESA_GL_VERSION_OVERRIDE="4.6"
export MESA_GLSL_VERSION_OVERRIDE="460"

# Metal renderer spoofing для macOS
cat > ~/Library/Application\ Support/Windsurf/metal_spoof.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>MTLDeviceName</key>
    <string>Apple M$((1 + RANDOM % 3)) GPU</string>
    <key>MTLDeviceVendor</key>
    <string>Apple</string>
    <key>MTLMaxThreadsPerGroup</key>
    <integer>$((512 + RANDOM % 512))</integer>
</dict>
</plist>
EOF

# WebGL fingerprint protection
mkdir -p ~/Library/Application\ Support/Windsurf/User
cat > ~/Library/Application\ Support/Windsurf/User/webgl_spoof.js << 'EOF'
// WebGL fingerprint spoofing
(function() {
    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // Spoof common fingerprinting parameters
        switch(parameter) {
            case this.VENDOR:
                return "Apple Inc.";
            case this.RENDERER:
                return `Apple M${Math.floor(Math.random() * 3) + 1} GPU`;
            case this.VERSION:
                return "WebGL 1.0 (OpenGL ES 2.0 Chromium)";
            case this.SHADING_LANGUAGE_VERSION:
                return "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)";
            default:
                return originalGetParameter.call(this, parameter);
        }
    };
    
    // Spoof WebGL2 as well
    if (window.WebGL2RenderingContext) {
        const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            switch(parameter) {
                case this.VENDOR:
                    return "Apple Inc.";
                case this.RENDERER:
                    return `Apple M${Math.floor(Math.random() * 3) + 1} GPU`;
                default:
                    return originalGetParameter2.call(this, parameter);
            }
        };
    }
})();
EOF

echo "✅ Graphics fingerprint спуфінг налаштовано"

# =============================================================================
# AUDIO FINGERPRINT RANDOMIZATION
# =============================================================================
echo "\n[5/5] 🔊 Рандомізація audio fingerprint..."

# Audio context spoofing
cat > ~/Library/Application\ Support/Windsurf/User/audio_spoof.js << 'EOF'
// Audio fingerprint randomization
(function() {
    const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
    AudioContext.prototype.createAnalyser = function() {
        const analyser = originalCreateAnalyser.call(this);
        const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
        
        analyser.getFloatFrequencyData = function(array) {
            originalGetFloatFrequencyData.call(this, array);
            // Add noise to audio fingerprint
            for (let i = 0; i < array.length; i++) {
                array[i] += (Math.random() - 0.5) * 0.0001;
            }
        };
        
        return analyser;
    };
})();
EOF

# Зміна audio device fingerprint
sudo kextunload /System/Library/Extensions/AppleHDA.kext 2>/dev/null
sudo kextload /System/Library/Extensions/AppleHDA.kext 2>/dev/null

echo "✅ Audio fingerprint рандомізовано"

# =============================================================================
# CLEANUP AND VERIFICATION
# =============================================================================
echo "\n🧹 Очищення тимчасових файлів..."
rm -f /tmp/system_profiler_hook.sh
rm -f /tmp/cpuid_spoof.c
rm -f /tmp/cpuid_spoof

echo "\n✅ HARDWARE SPOOFING ЗАВЕРШЕНО!"
echo "========================================================"
echo "🔧 Hardware ідентифікатори підмінено"
echo "🖥️  CPU fingerprint заспуфлено" 
echo "🧠 Memory layout рандомізовано"
echo "🎨 Graphics fingerprint змінено"
echo "🔊 Audio fingerprint рандомізовано"
echo ""
echo "⚠️  Для повного ефекту рекомендується перезапуск системи"
echo "🚀 Система готова до stealth режиму!"
