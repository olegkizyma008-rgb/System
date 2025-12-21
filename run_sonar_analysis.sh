#!/bin/bash

# SonarCloud Analysis Script
# This script helps you run SonarCloud analysis manually

echo "🔍 SonarCloud Analysis Setup"
echo "============================"
echo ""

# Check if sonar-scanner is installed
if ! command -v sonar-scanner &> /dev/null; then
    echo "❌ SonarScanner не встановлено"
    echo ""
    echo "📋 Інструкції з встановлення:"
    echo ""
    echo "1. Завантажте SonarScanner:"
    echo "   wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip"
    echo ""
    echo "2. Розпакуйте архів:"
    echo "   unzip sonar-scanner-cli-5.0.1.3006-linux.zip"
    echo ""
    echo "3. Додайте в PATH:"
    echo "   export PATH=$PATH:$(pwd)/sonar-scanner-5.0.1.3006-linux/bin"
    echo ""
    echo "4. Або встановіть через Homebrew (Mac):"
    echo "   brew install sonar-scanner"
    echo ""
    exit 1
fi

echo "✅ SonarScanner встановлено"
echo ""

# Check for SonarCloud token
if [ -z "$SONAR_TOKEN" ]; then
    echo "⚠️  Змінна середовища SONAR_TOKEN не встановлена"
    echo ""
    echo "📋 Як отримати токен:"
    echo "1. Зайдіть на https://sonarcloud.io/"
    echo "2. Увійдіть через GitHub (olegkizima01)"
    echo "3. Зайдіть в 'My Account' → 'Security' → 'Generate Tokens'"
    echo "4. Створіть новий токен"
    echo "5. Експортуйте його: export SONAR_TOKEN='your_token_here'"
    echo ""
    exit 1
fi

echo "✅ Токен SonarCloud доступний"
echo ""

echo "🚀 Запуск аналізу..."
echo ""

# Run the analysis
sonar-scanner \
    -Dsonar.organization=olegkizima01 \
    -Dsonar.projectKey=olegkizima01_System \
    -Dsonar.sources=. \
    -Dsonar.host.url=https://sonarcloud.io \
    -Dsonar.login=$SONAR_TOKEN

echo ""
echo "🎉 Аналіз завершено!"
echo ""
echo "🔗 Перегляньте результати на:"
echo "https://sonarcloud.io/dashboard?id=olegkizima01_System"
echo ""