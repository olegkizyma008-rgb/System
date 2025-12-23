#!/bin/zsh

setopt NULL_GLOB

# ═══════════════════════════════════════════════════════════════
#  🎯 UNIFIED EDITOR CLEANUP - Уніфіковане очищення всіх редакторів
#  Підтримка: Windsurf, Antigravity, Cursor, VS Code
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common_functions.sh"

# ─────────────────────────────────────────────────────────────────
# ПАРАМЕТРИ
# ─────────────────────────────────────────────────────────────────
SELECTED_EDITORS=()
CLEAN_ALL=0
SHOW_HELP=0

# Парсинг аргументів
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            CLEAN_ALL=1
            shift
            ;;
        -w|--windsurf)
            SELECTED_EDITORS+=("windsurf")
            shift
            ;;
        -c|--cursor)
            SELECTED_EDITORS+=("cursor")
            shift
            ;;
        -v|--vscode)
            SELECTED_EDITORS+=("vscode")
            shift
            ;;
        -g|--antigravity)
            SELECTED_EDITORS+=("antigravity")
            shift
            ;;
        -h|--help)
            SHOW_HELP=1
            shift
            ;;
        *)
            print_error "Невідомий аргумент: $1"
            SHOW_HELP=1
            shift
            ;;
    esac
done

# Показ довідки
if [[ $SHOW_HELP -eq 1 ]]; then
    echo ""
    echo "🎯 UNIFIED EDITOR CLEANUP"
    echo ""
    echo "Використання: $0 [OPTIONS]"
    echo ""
    echo "Опції:"
    echo "  -a, --all           Очистити всі редактори"
    echo "  -w, --windsurf      Очистити Windsurf"
    echo "  -c, --cursor        Очистити Cursor"
    echo "  -v, --vscode        Очистити VS Code"
    echo "  -g, --antigravity   Очистити Antigravity"
    echo "  -h, --help          Показати цю довідку"
    echo ""
    echo "Приклади:"
    echo "  $0 --all                    # Очистити всі редактори"
    echo "  $0 -w -c                    # Очистити Windsurf та Cursor"
    echo "  $0 --vscode --antigravity   # Очистити VS Code та Antigravity"
    echo ""
    exit 0
fi

# Якщо --all або не вказано редакторів, очищаємо все
if [[ $CLEAN_ALL -eq 1 ]] || [[ ${#SELECTED_EDITORS[@]} -eq 0 ]]; then
    SELECTED_EDITORS=("vscode" "windsurf" "cursor" "antigravity")
fi

print_header "🎯 UNIFIED EDITOR CLEANUP" "$CYAN"
echo "Редактори для очищення: ${SELECTED_EDITORS[*]}"
echo ""

# ─────────────────────────────────────────────────────────────────
# ПЕРЕВІРКА НАЯВНОСТІ РЕДАКТОРІВ
# ─────────────────────────────────────────────────────────────────
AVAILABLE_EDITORS=()
for editor in "${SELECTED_EDITORS[@]}"; do
    local base_path="${EDITOR_PATHS[$editor]}"
    if [ -d "$base_path" ]; then
        AVAILABLE_EDITORS+=("$editor")
        print_success "$editor знайдено: $base_path"
    else
        print_warning "$editor не встановлено (пропускаємо)"
    fi
done

echo ""

if [[ ${#AVAILABLE_EDITORS[@]} -eq 0 ]]; then
    print_error "Не знайдено жодного редактора для очищення"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────
# ОЧИЩЕННЯ КОЖНОГО РЕДАКТОРА
# ─────────────────────────────────────────────────────────────────
TOTAL=${#AVAILABLE_EDITORS[@]}
CURRENT=0

for editor in "${AVAILABLE_EDITORS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${WHITE}[$CURRENT/$TOTAL] Очищення: ${YELLOW}$editor${NC}"
    echo "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Використовуємо спільну функцію
    cleanup_editor_full "$editor"
done

# ─────────────────────────────────────────────────────────────────
# ЗАГАЛЬНИЙ ЗВІТ
# ─────────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo "${GREEN}║${NC}  ${WHITE}✅ ОЧИЩЕННЯ ЗАВЕРШЕНО!${NC}"
echo "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo "${GREEN}║${NC}  ${CYAN}📋 Оброблені редактори:${NC}"
for editor in "${AVAILABLE_EDITORS[@]}"; do
    echo "${GREEN}║${NC}    ✓ $editor"
done
echo "${GREEN}║${NC}"
echo "${GREEN}║${NC}  ${CYAN}🔄 Виконані дії для кожного редактора:${NC}"
echo "${GREEN}║${NC}    ✓ Зупинено процеси"
echo "${GREEN}║${NC}    ✓ Machine ID оновлено"
echo "${GREEN}║${NC}    ✓ Storage файли оновлено"
echo "${GREEN}║${NC}    ✓ Кеші видалено"
echo "${GREEN}║${NC}    ✓ Keychain очищено"
echo "${GREEN}║${NC}"
echo "${GREEN}║${NC}  ${YELLOW}💡 Тепер можна запускати редактори як новий користувач${NC}"
echo "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
