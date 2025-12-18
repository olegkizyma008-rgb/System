#!/bin/zsh

# Визначаємо realpath скрипта (працює з будь-якого місця)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Strict check for Python 3.12 .venv
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
  source "$SCRIPT_DIR/.venv/bin/activate"
  PYTHON_EXE="$SCRIPT_DIR/.venv/bin/python"
else
  echo "❌ .venv не знайдено. Будь ласка, запустіть ./setup.sh спочатку." >&2
  exit 1
fi

# Verify version in venv
VENV_VERSION=$("$PYTHON_EXE" --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$VENV_VERSION" != "3.12" ]; then
  echo "❌ .venv використовує Python $VENV_VERSION, але потрібно 3.12. Запустіть ./setup.sh." >&2
  exit 1
fi

# Завантажуємо .env, якщо є (включаючи SUDO_PASSWORD)
if [ -f "$SCRIPT_DIR/.env" ]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ "$line" =~ ^[[:alpha:]_][[:alnum:]_]*= ]]; then
      key="${line%%=*}"
      value="${line#*=}"
      value=$(echo "$value" | sed 's/^"//;s/"$//;s/^'\''//;s/'\''$//')
      export "$key=$value"
    fi
  done < "$SCRIPT_DIR/.env"
fi

# Створюємо директорію для налаштувань, якщо її немає
mkdir -p "$HOME/.system_cli"

# Якщо потрібні sudo-права (наприклад для fs_usage/dtrace), перевіряємо наявність пароля
if [ -n "$SUDO_PASSWORD" ]; then
  # Тихо перевіряємо, чи пароль працює (без інтерактивного запиту)
  echo "$SUDO_PASSWORD" | sudo -S -k true 2>/dev/null
  if [ $? -eq 0 ]; then
    export SUDO_ASKPASS="$HOME/.system_cli/.sudo_askpass"
    cat > "$SUDO_ASKPASS" <<EOF
#!/bin/bash
echo "$SUDO_PASSWORD"
EOF
    chmod 700 "$SUDO_ASKPASS"
    
    # Видаляємо старий .sudo_askpass з кореня, якщо він там лишився
    [ -f "$SCRIPT_DIR/.sudo_askpass" ] && rm "$SCRIPT_DIR/.sudo_askpass"
  else
    echo "Попередження: пароль sudo не дійсний. sudo-команди можуть не працювати." >&2
  fi
fi

export TOKENIZERS_PARALLELISM=false

# Запускаємо cli.py з усіма аргументами
"$PYTHON_EXE" "$SCRIPT_DIR/cli.py" "$@"

# Очищення при виході
if [ -f "$HOME/.system_cli/.sudo_askpass" ]; then
  rm "$HOME/.system_cli/.sudo_askpass"
fi