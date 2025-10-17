# 🔐 API Ключі Codeium - Де вони зберігаються

## Проблема

Windsurf зберігає API ключі Codeium в SQLite базі даних `state.vscdb`. 
Навіть після видалення всіх файлів конфігурації, якщо ця база не видалена - 
**Windsurf все одно "пам'ятає" попередню автентифікацію**.

## Основне місце зберігання

```bash
~/Library/Application Support/Windsurf/User/globalStorage/state.vscdb
~/Library/Application Support/Windsurf/User/globalStorage/state.vscdb.backup
```

### Що зберігається в state.vscdb

```sql
-- Приклад даних з бази:
codeium.windsurf | {"codeium.installationId":"...", "apiServerUrl":"..."}
codeium.windsurf-windsurf_auth | Ім'я користувача
codeium.windsurf-windsurf_auth- | UUID сесії
secret://{"extensionId":"codeium.windsurf","key":"windsurf_auth.sessions"} | Зашифрований токен
```

## Інші місця зберігання

### 1. Local Storage
```bash
~/Library/Application Support/Windsurf/Local Storage/
```

### 2. Session Storage
```bash
~/Library/Application Support/Windsurf/Session Storage/
```

### 3. IndexedDB
```bash
~/Library/Application Support/Windsurf/IndexedDB/
```

### 4. macOS Keychain
```bash
security find-generic-password -s "Codeium"
security find-generic-password -s "Windsurf"
security find-internet-password -s "codeium.com"
```

## Рішення

### ✅ Що робить скрипт `deep_windsurf_cleanup.sh`

1. **СПОЧАТКУ** очищає бази даних та сховища:
   ```bash
   rm -rf ~/Library/Application Support/Windsurf/User/globalStorage/state.vscdb*
   rm -rf ~/Library/Application Support/Windsurf/Local Storage
   rm -rf ~/Library/Application Support/Windsurf/Session Storage
   ```

2. **ПОТІМ** зберігає бекапи machine-id та інших ідентифікаторів

3. **ПОТІМ** підміняє ідентифікатори на нові

4. **В КІНЦІ** видаляє всю папку `Application Support/Windsurf` повністю

### ✅ Що робить скрипт `check_api_traces.sh`

Перевіряє всі можливі місця зберігання API даних і показує:
- ✅ Зелений - файл/запис відсутній (чисто)
- ❌ Червоний - файл/запис знайдено (потрібне очищення)

## Перевірка

### До очищення
```bash
./check_api_traces.sh
# Покаже червоні ❌ для всіх файлів де є API дані
```

### Очищення
```bash
./deep_windsurf_cleanup.sh
```

### Після очищення
```bash
./check_api_traces.sh
# Має показати зелені ✅ для всіх критичних файлів
```

## Критична послідовність в скрипті

```bash
# 1. Очищення баз даних (ДО резервування)
rm state.vscdb*
rm Local Storage
rm Session Storage

# 2. Резервування machine-id
cp machineid → backup/

# 3. Підміна machine-id
echo "новий-id" > machineid

# 4. Очищення Keychain
security delete-generic-password -s "Codeium"

# 5. ПОВНЕ видалення Application Support/Windsurf
rm -rf ~/Library/Application Support/Windsurf
```

## Висновок

**Проблема була в тому, що:**
- Скрипт спочатку видаляв всю папку `Application Support/Windsurf`
- Потім намагався працювати з файлами всередині неї
- API ключі в `state.vscdb` могли "вижити" через кешування

**Рішення:**
- Тепер скрипт **спочатку** очищає бази даних
- **Потім** зберігає тільки machine-id (не API дані)
- **В кінці** видаляє всю папку повністю

**Результат:**
- API ключі Codeium **гарантовано** видаляються
- Windsurf бачить систему як **нового клієнта**
- Не підходить попередній API ключ ✅
