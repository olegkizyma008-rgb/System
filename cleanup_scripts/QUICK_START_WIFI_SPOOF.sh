#!/bin/bash

# MikroTik WiFi & MAC Spoofing - Quick Start Guide
# Швидкий старт для спойфинга WiFi та MAC адреси

# КРОК 1: Налаштування SSH ключа на MikroTik
# ============================================
# Якщо ви вже це зробили, перейдіть до кроку 2

# Отримайте вміст вашого публічного ключа:
cat ~/.ssh/id_ed25519.pub

# На MikroTik (через SSH або серійний доступ):
# ssh admin@192.168.88.1 або через консоль MikroTik:
/user ssh-keys add public-key-file=stdin user=admin
# Вставте публічний ключ і натисніть Ctrl+D


# КРОК 2: Перевірити підключення
# ==============================
cd /Users/dev/Documents/GitHub/System
./cleanup_scripts/mikrotik_wifi_spoof.sh status


# КРОК 3: Виконати спойфинг
# ==========================
sudo ./cleanup_scripts/mikrotik_wifi_spoof.sh spoof


# КРОК 4: Перевірити нові параметри
# =================================
./cleanup_scripts/mikrotik_wifi_spoof.sh status


# РЕКОМЕНДАЦІЇ:
# =============
# 1. Запускайте спойфинг регулярно (кожні 2-4 години)
# 2. Гостьева WiFi назва та IP змінюються кожного разу
# 3. Пароль залишається: 00000000
# 4. Помежите до бібліотеки для автоматизації через cron


# КОМАНДИ ДЛЯ АВТОМАТИЗАЦІЇ:
# =========================

# Додати в ~/.zshrc або ~/.bash_profile для легкого доступу:
# alias wifi-spoof="sudo /Users/dev/Documents/GitHub/System/cleanup_scripts/mikrotik_wifi_spoof.sh spoof"
# alias wifi-status="cd /Users/dev/Documents/GitHub/System && ./cleanup_scripts/mikrotik_wifi_spoof.sh status"

# Запланувати в cron для автоматичного запуску кожні 3 години:
# EDITOR=nano crontab -e
# Додайте рядок:
# 0 */3 * * * /usr/bin/sudo /Users/dev/Documents/GitHub/System/cleanup_scripts/mikrotik_wifi_spoof.sh spoof >> /var/log/wifi_spoof.log 2>&1
