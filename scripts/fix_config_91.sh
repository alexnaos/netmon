#!/bin/bash
# =============================================================================
# Скрипт 4: Правка configuration.yaml Home Assistant для 192.168.1.91
# Запускается на машине 91 после копирования конфига с .103 и установки HA
# Делает:
#   1. Бэкап текущего configuration.yaml
#   2. Меняет MQTT broker на удалённый (.23:1883 или .103:1883)
#   3. Закомментирует/убирает настройки специфичные только для .103
#   4. Меняет ссылки с .103 на .91 где нужно
# =============================================================================
set -euo pipefail

CONFIG_FILE="/home/alex/hass_config/configuration.yaml"
BACKUP_FILE="/home/alex/hass_config/configuration.yaml.bak_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/home/alex/ha_fix_config_91_$(date +%Y%m%d_%H%M%S).log"

# MQTT брокер по умолчанию — можно изменить на 192.168.1.103 если preferred
MQTT_BROKER="192.168.1.23"
MQTT_PORT="1883"

echo "=== ПРАВКА КОНФИГУРАЦИИ HA ДЛЯ .91 ===" | tee -a "$LOG_FILE"
echo "Файл: $CONFIG_FILE" | tee -a "$LOG_FILE"
echo "MQTT брокер: $MQTT_BROKER:$MQTT_PORT" | tee -a "$LOG_FILE"
echo "Дата: $(date)" | tee -a "$LOG_FILE"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ОШИБКА: Файл $CONFIG_FILE не найден." | tee -a "$LOG_FILE"
    exit 1
fi

# 1. Бэкап
echo "[1/6] Создание бэкапа $BACKUP_FILE..." | tee -a "$LOG_FILE"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "  Бэкап сохранён" | tee -a "$LOG_FILE"

# 2. Настройка MQTT — указать удалённый брокер (на .91 нет локального mosquitto)
echo "[2/6] Настройка MQTT broker -> $MQTT_BROKER:$MQTT_PORT..." | tee -a "$LOG_FILE"

# Если секция mqtt: существует — заменить broker и порт
if grep -q "^mqtt:" "$CONFIG_FILE"; then
    echo "  Sekция mqtt: найдена — обновляю broker и port..." | tee -a "$LOG_FILE"
    # Заменяем broker на удалённый
    sed -i "s/^\([[:space:]]*broker:[[:space:]]*\).*/\1$MQTT_BROKER/" "$CONFIG_FILE"
    sed -i "s/^\([[:space:]]*port:[[:space:]]*\).*/\1$MQTT_PORT/" "$CONFIG_FILE"
    echo "  broker=$MQTT_BROKER, port=$MQTT_PORT" | tee -a "$LOG_FILE"
else
    echo "  Sekция mqtt: не найдена — добавляю в конец файла..." | tee -a "$LOG_FILE"
    cat >> "$CONFIG_FILE" << EOF

# MQTT для .91 (удалённый брокер, локальный mosquitto отсутствует)
mqtt:
  broker: $MQTT_BROKER
  port: $MQTT_PORT
EOF
    echo "  Sekция mqtt: добавлена" | tee -a "$LOG_FILE"
fi

# 3. Убрать/закомментировать настройки специфичные только для .103
echo "[3/6] Проверка и комментирование настроек специфичных для .103..." | tee -a "$LOG_FILE"

# Список паттернов, которые обычно специфичны для .103 (локальный mosquitto, локальные интеграции)
# Мы не удаляем, а комментируем, чтобы можно было вернуть если нужно
PATTERNS_TO_COMMENT=(
    "# broker: 127.0.0.1"
    "# broker: localhost"
    "# broker: 192.168.1.103"
    "# host: 192.168.1.103"
    "# host: localhost"
    "# host: 127.0.0.1"
)

for pattern in "${PATTERNS_TO_COMMENT[@]}"; do
    if grep -q "$pattern" "$CONFIG_FILE" 2>/dev/null; then
        echo "  Найден паттерн: $pattern — комментирую..." | tee -a "$LOG_FILE"
        # Добавляем комментарий маркера если уже не закомментировано
        sed -i "/$pattern/s/^/# [MIGRATE-91] /" "$CONFIG_FILE" 2>/dev/null || true
    fi
done

# 4. Заменить жёсткие ссылки на .103 на .91 в конфиге (где это уместно)
echo "[4/6] Замена ссылок .103 -> .91 в конфигурации..." | tee -a "$LOG_FILE"
# Примеры: URL, веб-хуки, локальные адреса (кроме MQTT брокера, который остаётся .23)
sed -i 's/192\.168\.1\.103/192.168.1.91/g' "$CONFIG_FILE" 2>/dev/null || true
echo "  Замены применены (проверьте вручную критичные места)" | tee -a "$LOG_FILE"

# 5. Показать итоговый diff (кратко)
echo "[5/6] Краткий обзор изменений..." | tee -a "$LOG_FILE"
echo "  Бэкап: $BACKUP_FILE" | tee -a "$LOG_FILE"
echo "  MQTT broker: $(grep -E '^\s*broker:' "$CONFIG_FILE" | head -1 || echo 'не найден')" | tee -a "$LOG_FILE"
echo "  MQTT port:   $(grep -E '^\s*port:' "$CONFIG_FILE" | head -1 || echo 'не найден')" | tee -a "$LOG_FILE"

# 6. Перезапуск HA контейнера чтобы применились настройки
echo "[6/6] Перезапуск контейнера Home Assistant..." | tee -a "$LOG_FILE"
if command -v docker &>/dev/null; then
    docker restart homeassistant 2>/dev/null && echo "  Контейнер перезапущен" | tee -a "$LOG_FILE" || echo "  Не удалось перезапустить контейнер" | tee -a "$LOG_FILE"
else
    echo "  Docker не найден — перезапустите HA вручную" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "=== ГОТОВО ===" | tee -a "$LOG_FILE"
echo "Конфигурация скорректирована под .91" | tee -a "$LOG_FILE"
echo "Бэкап: $BACKUP_FILE" | tee -a "$LOG_FILE"
echo "Лог: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "ВАЖНО: Проверьте вручную $CONFIG_FILE перед использованием!" | tee -a "$LOG_FILE"
echo "  1. Убедитесь что mqtt broker указывает на $MQTT_BROKER:$MQTT_PORT"
echo "  2. Проверьте что все ссылки на .103 заменены на .91 где нужно"
echo "  3. Проверьте автоматизации и интеграции — некоторые могут быть привязаны к .103"
echo "" | tee -a "$LOG_FILE"
echo "Доступ к HA: http://192.168.1.91:8123" | tee -a "$LOG_FILE"