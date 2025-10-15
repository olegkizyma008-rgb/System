#!/bin/zsh
# Швидкі команди для роботи з Windsurf Cleanup System

# ============================================
# ОСНОВНІ КОМАНДИ
# ============================================

# 1. Запустити повне очищення з автовідновленням через 5 годин
./deep_windsurf_cleanup.sh

# 2. Перевірити статус бекапів
./check_windsurf_backup.sh

# 3. Відновити вручну (раніше 5 годин)
./restore_windsurf_backup.sh

# ============================================
# КОРИСНІ КОМАНДИ
# ============================================

# Знайти всі бекапи
ls -lhd /tmp/windsurf_backup_*

# Перевірити процес автовідновлення
ps aux | grep "sleep 18000" | grep -v grep

# Припинити автовідновлення
# kill <PID>  # PID показано після запуску cleanup скрипта

# Зберегти бекап назавжди (замінити TIMESTAMP!)
# cp -r /tmp/windsurf_backup_TIMESTAMP ~/Documents/windsurf_backup_safe

# Переглянути вміст бекапу
# ls -lhR /tmp/windsurf_backup_*/

# Переглянути поточний machine-id
# cat ~/Library/Application\ Support/Windsurf/machineid

# Переглянути поточний storage
# cat ~/Library/Application\ Support/Windsurf/storage.json | jq .

# Перевірити hostname
scutil --get HostName

# Переглянути Keychain записи Windsurf
security find-generic-password -l "Windsurf"

# ============================================
# НАЛАГОДЖЕННЯ
# ============================================

# Якщо автовідновлення не спрацювало:
# 1. Перевірте чи існує бекап
ls -ld /tmp/windsurf_backup_*

# 2. Перевірте чи активний процес
ps aux | grep "sleep 18000"

# 3. Відновіть вручну
./restore_windsurf_backup.sh

# ============================================
# ТЕСТУВАННЯ (БЕЗ ВИКОНАННЯ)
# ============================================

# Подивитися що буде видалено (dry-run)
# Відредагуйте скрипт: замініть rm -rf на echo "Would remove:"

# Перевірити які процеси Windsurf запущені
ps aux | grep -i windsurf

# Знайти всі файли Windsurf в системі
find ~ -iname "*windsurf*" 2>/dev/null | head -20
