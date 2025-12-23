#!/bin/bash

# SonarCloud Analysis Script
# This script helps you run SonarCloud analysis manually

echo "🔍 SonarCloud Analysis Setup"
echo "============================"
echo ""

# Determine scanner command
if command -v sonar-scanner &> /dev/null; then
    SCANNER_CMD="sonar-scanner"
else
    SCANNER_CMD="npx -y sonarqube-scanner"
    echo "💡 Використання npx для sonarqube-scanner"
fi

echo "🚀 Запуск аналізу..."
echo ""

# Run the analysis
$SCANNER_CMD \
    -Dsonar.organization=olegkizima01 \
    -Dsonar.projectKey=olegkizima01_System2 \
    -Dsonar.sources=. \
    -Dsonar.host.url=https://sonarcloud.io \
    -Dsonar.token=$SONAR_TOKEN

echo ""
echo "🎉 Аналіз завершено!"
echo ""
echo "🔗 Перегляньте результати на:"
echo "https://sonarcloud.io/dashboard?id=olegkizima01_System"
echo ""