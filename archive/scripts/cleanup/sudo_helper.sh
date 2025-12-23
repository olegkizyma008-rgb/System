#!/bin/zsh
# Допоміжний скрипт для автоматичного введення sudo пароля
# Використовується через SUDO_ASKPASS

# Завантаження змінних з .env файлу
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
if [ ! -f "$REPO_ROOT/cleanup_modules.json" ] && [ -f "$SCRIPT_DIR/../cleanup_modules.json" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
ENV_FILE="$REPO_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    # Читаємо SUDO_PASSWORD з .env
    SUDO_PASSWORD=$(grep '^SUDO_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    echo "$SUDO_PASSWORD"
else
    # Якщо .env не знайдено, використовуємо значення за замовчуванням
    echo ""
fi
