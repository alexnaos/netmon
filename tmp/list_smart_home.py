#!/usr/bin/env python3
"""
Сбор списка устройств умного дома на Orange Pi.
Источники:
  1. MQTT (Mosquitto) — топики и retained-сообщения
  2. Node-RED — flows и узлы (если доступен API)
  3. Сеть — ARP-таблица (кто из устройств онлайн)
"""

import json
import subprocess
import socket
import re
import os
import sys
from collections import defaultdict

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883
NODERED_URL = "http://127.0.0.1:1880"

def run(cmd, timeout=10):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=timeout).stdout
    except Exception:
        return ""

def get_mqtt_topics():
    """Список топиков через mosquitto_sub (кратковременная подписка)."""
    if not shutil_which("mosquitto_sub"):
        return []
    # подписываемся на всё на 3 секунды, собираем retained
    out = run(f"timeout 3 mosquitto_sub -h {MQTT_HOST} -p {MQTT_PORT} "
              f"-t '#' -v -W 3 2>/dev/null")
    topics = []
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if parts:
            topics.append(parts[0])
    return sorted(set(topics))

def get_retained_values(topics, limit=50):
    """Пробуем вытащить retained-значения по каждому топику."""
    result = {}
    for t in topics[:limit]:
        out = run(f"timeout 1 mosquitto_sub -h {MQTT_HOST} -p {MQTT_PORT} "
                  f"-t '{t}' -C 1 -W 1 2>/dev/null")
        if out.strip():
            result[t] = out.strip()[:200]
    return result

def get_nodered_flows():
    """Пытаемся получить список узлов Node-RED через HTTP API."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{NODERED_URL}/flows", timeout=3) as r:
            flows = json.loads(r.read().decode())
        return flows
    except Exception:
        return []

def get_arp_devices():
    """Устройства в локальной сети из ARP-таблицы."""
    out = run("ip neigh show")
    devices = []
    for line in out.splitlines():
        m = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+dev\s+(\S+)\s+lladdr\s+(\S+)\s+(\S+)", line)
        if m:
            ip, iface, mac, state = m.groups()
            devices.append({"ip": ip, "iface": iface, "mac": mac, "state": state})
    return devices

def shutil_which(cmd):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        f = os.path.join(p, cmd)
        if os.access(f, os.X_OK):
            return f
    return None

def main():
    print("=" * 60)
    print("СПИСОК УСТРОЙСТВ УМНОГО ДОМА")
    print("=" * 60)

    # 1. MQTT
    topics = get_mqtt_topics()
    print(f"\n[MQTT] Найдено топиков: {len(topics)}")
    # группируем по префиксу (первый уровень)
    groups = defaultdict(list)
    for t in topics:
        prefix = t.split("/")[0]
        groups[prefix].append(t)
    for prefix, ts in sorted(groups.items()):
        print(f"  {prefix}/  ({len(ts)} топиков)")
        for t in ts[:5]:
            print(f"    - {t}")
        if len(ts) > 5:
            print(f"    ... ещё {len(ts)-5}")

    # 2. Retained-значения (первые 30)
    print("\n[MQTT] Retained-значения (первые 30):")
    retained = get_retained_values(topics, limit=30)
    for t, v in list(retained.items())[:30]:
        print(f"  {t} = {v}")

    # 3. Node-RED
    flows = get_nodered_flows()
    if flows:
        nodes = [f for f in flows if f.get("type") not in ("tab", "subflow")]
        print(f"\n[Node-RED] Узлов: {len(nodes)}")
        types = defaultdict(int)
        for n in nodes:
            types[n.get("type", "?")] += 1
        for t, c in sorted(types.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}")
        # MQTT-узлы с топиками
        mqtt_nodes = [n for n in nodes if n.get("type") == "mqtt in"]
        if mqtt_nodes:
            print("  MQTT in-узлы:")
            for n in mqtt_nodes[:20]:
                print(f"    - {n.get('topic', '?')} ({n.get('name', '')})")
    else:
        print("\n[Node-RED] API недоступен (проверьте, что nodered слушает 1880)")

    # 4. Сеть
    arp = get_arp_devices()
    print(f"\n[Сеть] Устройств в ARP-таблице: {len(arp)}")
    for d in arp:
        print(f"  {d['ip']:15} {d['mac']:17} {d['iface']:8} {d['state']}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()