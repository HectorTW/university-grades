#!/bin/bash

# Скрипт для автоматизированного тестирования безопасности
# Использование: ./SECURITY_TESTING_SCRIPT.sh http://localhost:5000

TARGET_URL=${1:-"http://localhost:5000"}
REPORT_DIR="security_reports"
DATE=$(date +%Y%m%d_%H%M%S)

echo "🔒 Запуск аудита безопасности для: $TARGET_URL"
echo "📁 Отчеты будут сохранены в: $REPORT_DIR/"
echo ""

# Создаем директорию для отчетов
mkdir -p "$REPORT_DIR"

echo "1️⃣ Проверка заголовков безопасности..."
curl -I "$TARGET_URL" -o "$REPORT_DIR/headers_$DATE.txt"
echo "   ✓ Заголовки сохранены в $REPORT_DIR/headers_$DATE.txt"

echo ""
echo "2️⃣ Проверка открытых портов (требует nmap)..."
if command -v nmap &> /dev/null; then
    HOST=$(echo $TARGET_URL | sed -e 's|^[^/]*//||' -e 's|/.*$||' | cut -d: -f1)
    nmap -sV -p- "$HOST" -oN "$REPORT_DIR/nmap_scan_$DATE.txt" 2>/dev/null
    echo "   ✓ Сканирование портов завершено"
else
    echo "   ⚠ nmap не установлен, пропускаем проверку портов"
fi

echo ""
echo "3️⃣ Проверка SSL/TLS (если используется HTTPS)..."
if [[ $TARGET_URL == https://* ]]; then
    HOST=$(echo $TARGET_URL | sed -e 's|^[^/]*//||' -e 's|/.*$||' | cut -d: -f1)
    if command -v openssl &> /dev/null; then
        echo | openssl s_client -connect "$HOST:443" -showcerts 2>/dev/null | \
            openssl x509 -noout -text > "$REPORT_DIR/ssl_info_$DATE.txt" 2>/dev/null
        echo "   ✓ SSL информация сохранена"
    else
        echo "   ⚠ openssl не установлен"
    fi
else
    echo "   ⚠ HTTPS не используется, пропускаем проверку SSL"
fi

echo ""
echo "4️⃣ Проверка зависимостей Python на уязвимости..."
if command -v safety &> /dev/null; then
    safety check --json > "$REPORT_DIR/safety_check_$DATE.json" 2>&1
    safety check > "$REPORT_DIR/safety_check_$DATE.txt" 2>&1
    echo "   ✓ Проверка через safety завершена"
else
    echo "   ⚠ safety не установлен. Установите: pip install safety"
fi

if command -v pip-audit &> /dev/null; then
    pip-audit --rate-limit 20 --format json > "$REPORT_DIR/pip_audit_$DATE.json" 2>&1
    pip-audit --rate-limit 20 > "$REPORT_DIR/pip_audit_$DATE.txt" 2>&1
    echo "   ✓ Проверка через pip-audit завершена"
else
    echo "   ⚠ pip-audit не установлен. Установите: pip install pip-audit"
fi

echo ""
echo "5️⃣ Проверка через OWASP ZAP (требует Docker)..."
if command -v docker &> /dev/null; then
    echo "   Запуск OWASP ZAP baseline scan..."
    docker run -t owasp/zap2docker-stable zap-baseline.py \
        -t "$TARGET_URL" \
        -J "$REPORT_DIR/zap_report_$DATE.json" \
        -r "$REPORT_DIR/zap_report_$DATE.html" 2>&1 | \
        tee "$REPORT_DIR/zap_output_$DATE.txt"
    echo "   ✓ OWASP ZAP сканирование завершено"
else
    echo "   ⚠ Docker не установлен, пропускаем OWASP ZAP"
fi

echo ""
echo "6️⃣ Проверка через Nuclei (требует nuclei)..."
if command -v nuclei &> /dev/null; then
    HOST=$(echo $TARGET_URL | sed -e 's|^[^/]*//||' -e 's|/.*$||')
    nuclei -u "$TARGET_URL" -o "$REPORT_DIR/nuclei_scan_$DATE.txt" -silent 2>&1
    echo "   ✓ Nuclei сканирование завершено"
else
    echo "   ⚠ nuclei не установлен. Установите: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
fi

echo ""
echo "7️⃣ Проверка через securityheaders.com API..."
if command -v curl &> /dev/null; then
    HOST=$(echo $TARGET_URL | sed -e 's|^[^/]*//||' -e 's|/.*$||' | cut -d: -f1)
    curl -s "https://securityheaders.com/?q=$TARGET_URL&followRedirects=on" \
        -o "$REPORT_DIR/securityheaders_$DATE.html" 2>/dev/null
    echo "   ✓ Проверка заголовков через securityheaders.com завершена"
    echo "   ℹ Откройте $REPORT_DIR/securityheaders_$DATE.html в браузере"
fi

echo ""
echo "8️⃣ Проверка через Mozilla Observatory (требует curl)..."
if command -v curl &> /dev/null; then
    HOST=$(echo $TARGET_URL | sed -e 's|^[^/]*//||' -e 's|/.*$||' | cut -d: -f1)
    curl -s "https://observatory.mozilla.org/api/v1/analyze?host=$HOST" \
        -o "$REPORT_DIR/observatory_$DATE.json" 2>/dev/null
    echo "   ✓ Проверка через Mozilla Observatory завершена"
    echo "   ℹ Просмотрите результаты: cat $REPORT_DIR/observatory_$DATE.json"
fi

echo ""
echo "✅ Аудит завершен!"
echo "📊 Все отчеты сохранены в: $REPORT_DIR/"
echo ""
echo "📋 Следующие шаги:"
echo "   1. Просмотрите все отчеты в директории $REPORT_DIR/"
echo "   2. Исправьте найденные проблемы"
echo "   3. Проведите ручное тестирование критичных функций"
echo "   4. Повторите аудит после исправлений"

