#!/bin/bash
# =============================================================================
# Скрипт 2: Копирование конфигурации Home Assistant с 192.168.1.103 на 192.168.1.91
# Запускается на машине 103 (источник) или с любой машины с доступом к обоим серверам
# Требуется: ssh-key доступ alex@192.168.1.91 без пароля
# =============================================================================
set -euo pipefail

SOURCE_HOST="alex@192.168.1.103"
SOURCE_CONFIG="/home/alex/hass_config"
TARGET_HOST="alex@192.168.1.91"
TARGET_CONFIG="/home/alex/hass_config"

LOG_FILE="/home/alex/ha_copy_config_$(date +%Y%m%d_%H%M%S).log"

echo "=== КОПИРОВАНИЕ КОНФИГУРАЦИИ HA: .103 -> .91 ===" | tee -a "$LOG_FILE"
echo "Источник: $SOURCE_HOST:$SOURCE_CONFIG" | tee -a "$LOG_FILE"
echo "Цель:     $TARGET_HOST:$TARGET_CONFIG" | tee -a "$LOG_FILE"
echo "Дата: $(date)" | tee -a "$LOG_FILE"

# Проверка SSH доступа к цели
echo "[1/4] Проверка SSH доступа к $TARGET_HOST..." | tee -a "$LOG_FILE"
ssh -o BatchMode=yes "$TARGET_HOST" "echo 'SSH OK'" 2>/dev/null || {
    echo "ОШИБКА: Нет SSH-доступа к $TARGET_HOST. Настройте ключи ~/.ssh/id_ed25519 или id_rsa." | tee -a "$LOG_FILE"
    exit 1
}
echo "  SSH доступ OK" | tee -a "$LOG_FILE"

# Проверка наличия конфига на источнике
echo "[2/4] Проверка конфигурации на источнике $SOURCE_HOST..." | tee -a "$LOG_FILE"
ssh "$SOURCE_HOST" "test -d $SOURCE_CONFIG && echo 'CONFIG EXISTS'" 2>/dev/null || {
    echo "ОШИБКА: Директория $SOURCE_CONFIG не найдена на $SOURCE_HOST" | tee -a "$LOG_FILE"
    exit 1
}
echo "  Конфигурация найдена на источнике" | tee -a "$LOG_FILE"

# Копирование конфигурации (rsync с исключением runtime-файлов)
echo "[3/4] Копирование конфигурации через rsync..." | tee -a "$LOG_FILE"
ssh "$SOURCE_HOST" "rsync -avz --delete \
    --exclude='.storage' \
    --exclude='.cache' \
    --exclude='*.db' \
    --exclude='*.log' \
    --exclude='backups' \
    --exclude='deps' \
    --exclude='python_packages' \
    --exclude='__pycache__' \
    $SOURCE_CONFIG/ $TARGET_HOST:$TARGET_CONFIG/" 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "[4/4] Проверка скопированных файлов на цели..." | tee -a "$LOG_FILE"
ssh "$TARGET_HOST" "ls -la $TARGET_CONFIG/" | tee -a "$LOG_FILE"
ssh "$TARGET_HOST" "test -f $TARGET_CONFIG/configuration.yaml && echo 'configuration.yaml: OK' || echo 'configuration.yaml: НЕ НАЙДЕН!'" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=== ГОТОВО ===" | tee -a "$LOG_FILE"
echo "Конфигурация скопирована с .103 на .91" | tee -a "$LOG_FILE"
echo "Лог: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Следующий шаг: запустить fix_config_91.sh на машине .91 для правки настроек под .91" | tee -a "$LOG_FILE"