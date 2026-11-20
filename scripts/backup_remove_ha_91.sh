#!/bin/bash
# =============================================================================
# Скрипт 1: Бэкап и удаление существующего Home Assistant на 192.168.1.91
# Запускается на машине 91 (вспомогательный сервер, Debian 12, ConnMan, SysV init)
# =============================================================================
set -euo pipefail

HA_CONFIG_DIR="/home/alex/hass_config"
BACKUP_DIR="/home/alex/ha_backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/home/alex/ha_remove_91_$(date +%Y%m%d_%H%M%S).log"

echo "=== НАЧАЛО: Бэкап и удаление HA на .91 ===" | tee -a "$LOG_FILE"
echo "Дата: $(date)" | tee -a "$LOG_FILE"

# 1. Остановить существующий HA (если запущен через Docker)
if command -v docker &>/dev/null; then
    echo "[1/7] Остановка контейнера Docker homeassistant (если есть)..." | tee -a "$LOG_FILE"
    docker stop homeassistant 2>/dev/null || echo "  Контейнер не найден или уже остановлен" | tee -a "$LOG_FILE"
    docker rm homeassistant 2>/dev/null || echo "  Контейнер не найден для удаления" | tee -a "$LOG_FILE"
else
    echo "[1/7] Docker не установлен — пропуск остановки контейнера" | tee -a "$LOG_FILE"
fi

# 2. Остановить HA если запущен как python3-процесс
echo "[2/7] Остановка python3-процессов Home Assistant (если есть)..." | tee -a "$LOG_FILE"
pkill -f "homeassistant" 2>/dev/null || echo "  Процессы homeassistant не найдены" | tee -a "$LOG_FILE"
pkill -f "hass" 2>/dev/null || true

# 3. Создать архивная копия существующей конфигурации
echo "[3/7] Создание архива существующей конфигурации в $BACKUP_DIR..." | tee -a "$LOG_FILE"
mkdir -p "$BACKUP_DIR"
if [ -d "$HA_CONFIG_DIR" ]; then
    tar czf "$BACKUP_DIR/hass_config_$(date +%F).tar.gz" -C /home/alex hass_config/ 2>/dev/null || echo "  Ошибка архивации hass_config" | tee -a "$LOG_FILE"
    echo "  Конфигурация архивирована: $BACKUP_DIR/hass_config_*.tar.gz" | tee -a "$LOG_FILE"
else
    echo "  Директория $HA_CONFIG_DIR не существует — пропуск" | tee -a "$LOG_FILE"
fi

# 4. Архивировать системные файлы HA (если есть)
echo "[4/7] Архивирование системных файлов HA..." | tee -a "$LOG_FILE"
for path in /etc/homeassistant /var/lib/homeassistant /usr/lib/homeassistant; do
    if [ -d "$path" ] || [ -f "$path" ]; then
        tar czf "$BACKUP_DIR/$(basename "$path")_$(date +%F).tar.gz" "$path" 2>/dev/null || true
        echo "  Архивировано: $path" | tee -a "$LOG_FILE"
    fi
done

# 5. Удалить существующую конфигурацию HA (после бэкапа)
echo "[5/7] Удаление существующей конфигурации HA с .91..." | tee -a "$LOG_FILE"
if [ -d "$HA_CONFIG_DIR" ]; then
    rm -rf "$HA_CONFIG_DIR"
    echo "  Удалено: $HA_CONFIG_DIR" | tee -a "$LOG_FILE"
else
    echo "  Директория не найдена — ничего удалять" | tee -a "$LOG_FILE"
fi

# 6. Удалить пакеты Home Assistant (если установлены через pip)
echo "[6/7] Удаление python-пакетов homeassistant..." | tee -a "$LOG_FILE"
pip3 uninstall -y homeassistant 2>/dev/null || echo "  homeassistant не установлен через pip3" | tee -a "$LOG_FILE"
pip uninstall -y homeassistant 2>/dev/null || true

# 7. Итог
echo "[7/7] Готово." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "=== ИТОГ ===" | tee -a "$LOG_FILE"
echo "Бэкап сохранён в: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "Лог операции: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Следующий шаг: скопировать конфигурацию с .103 на .91 скриптом copy_config_103_to_91.sh" | tee -a "$LOG_FILE"