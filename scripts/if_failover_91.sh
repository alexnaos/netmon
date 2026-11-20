#!/bin/bash
# ============================================================================
# if_failover_91.sh — Переключатель сетевых интерфейсов на сервере 91 (malek)
# eth0 (провод) приоритетнее wlan0 (Wi-Fi). IP .91 переезжает между ними.
# ============================================================================

set -u

MAIN_IP="192.168.1.91"
GW="192.168.1.1"
ETH0="eth0"
WLAN0="wlan0"
LOG="/var/log/if_failover_91.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Проверяем линк на eth0
cat /sys/class/net/$ETH0/carrier 2>/dev/null | grep -q "1"
ETH_LINK=$?

IP_ON_ETH0=$(ip addr show dev $ETH0 2>/dev/null | grep -c "$MAIN_IP" || true)
IP_ON_WLAN0=$(ip addr show dev $WLAN0 2>/dev/null | grep -c "$MAIN_IP" || true)

if [ $ETH_LINK -eq 0 ]; then
    # ШТАТ: кабель подключен
    log "ШТАТ: eth0 имеет линк. IP $MAIN_IP на eth0."
    if [ "$IP_ON_WLAN0" -gt 0 ]; then
        log "Удаляю $MAIN_IP/24 с wlan0 (возврат на провод)..."
        ip addr del "$MAIN_IP/24" dev $WLAN0 2>/dev/null || true
    fi
    if [ "$IP_ON_ETH0" -eq 0 ]; then
        log "Добавляю $MAIN_IP/24 на eth0..."
        ip addr add "$MAIN_IP/24" dev $ETH0 2>/dev/null || true
    fi
    ip route replace default via $GW dev $ETH0 metric 10 2>/dev/null || true
    ip route del default via $GW dev $WLAN0 metric 50 2>/dev/null || true
    ip route flush cache 2>/dev/null || true
    log "ШТАТ: сеть стабильна. eth0 активен."
else
    # АВАРИЯ: кабель отключен
    log "АВАРИЯ: eth0 без линка! Переключаюсь на wlan0..."
    if [ "$IP_ON_WLAN0" -eq 0 ]; then
        log "Добавляю $MAIN_IP/24 на wlan0..."
        ip addr add "$MAIN_IP/24" dev $WLAN0 2>/dev/null || true
        arping -c 4 -A -I $WLAN0 "$MAIN_IP" >/dev/null 2>&1 || true
    fi
    if [ "$IP_ON_ETH0" -gt 0 ]; then
        ip addr del "$MAIN_IP/24" dev $ETH0 2>/dev/null || true
    fi
    
    # Безопасная замена шлюзов (replace вместо жесткого del)
    ip route replace default via $GW dev $WLAN0 metric 50 2>/dev/null || true
    ip route del default via $GW dev $ETH0 metric 10 2>/dev/null || true
    
    # ИСПРАВЛЕНИЕ: Автоматически уничтожаем петли маршрутизации через Docker-порты veth
    if ip route show | grep -q "dev veth"; then
        log "АВАРИЯ: Обнаружен фантомный шлюз Docker! Зачищаю мусорные маршруты..."
        ip route del 0.0.0.0 dev $(ip route show | grep "0.0.0.0 dev veth" | awk '{print $3}') 2>/dev/null || true
        ip route del default dev $(ip route show | grep "default dev veth" | awk '{print $3}') 2>/dev/null || true
    fi

    ip route flush cache 2>/dev/null || true
    log "АВАРИЯ: переключение завершено. wlan0 активен с IP $MAIN_IP."
fi
