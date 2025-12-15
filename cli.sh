#!/bin/zsh

# Визначаємо realpath скрипта (працює з будь-якого місця)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Активуємо віртуальне оточення, якщо є
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Завантажуємо .env, якщо є (включаючи SUDO_PASSWORD)
if [ -f ".env" ]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Пропускаємо коментарі та порожні рядки
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    
    # Видаляємо пробіли на початку/кінці
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # Якщо є знак '=', розділяємо на ключ і значення
    if [[ "$line" =~ ^[[:alpha:]_][[:alnum:]_]*= ]]; then
      key="${line%%=*}"
      value="${line#*=}"
      # Видаляємо лапки з значення
      value=$(echo "$value" | sed 's/^"//;s/"$//;s/^'\''//;s/'\''$//')
      export "$key=$value"
    fi
  done < .env
fi

# Перевіряємо python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 не знайдено. Встановіть python3 (brew install python3)" >&2
  exit 1
fi

# Перевіряємо cli.py
if [ ! -f "$SCRIPT_DIR/cli.py" ]; then
  echo "cli.py не знайдено в $SCRIPT_DIR" >&2
  exit 1
fi

export TOKENIZERS_PARALLELISM=false

# Якщо потрібні sudo-права (наприклад для fs_usage/dtrace), перевіряємо наявність пароля
if [ -n "$SUDO_PASSWORD" ]; then
  # Тихо перевіряємо, чи пароль працює (без інтерактивного запиту)
  echo "$SUDO_PASSWORD" | sudo -S -k true 2>/dev/null
  if [ $? -eq 0 ]; then
    export SUDO_ASKPASS="$SCRIPT_DIR/.sudo_askpass"
    cat > "$SCRIPT_DIR/.sudo_askpass" <<'EOF'
#!/bin/bash
echo "$SUDO_PASSWORD"
EOF
    chmod 700 "$SCRIPT_DIR/.sudo_askpass"
  else
    echo "Попередження: пароль sudo не дійсний. sudo-команди можуть не працювати." >&2
  fi
fi

# Запускаємо cli.py з усіма аргументами
exec python3 "$SCRIPT_DIR/cli.py" "$@"