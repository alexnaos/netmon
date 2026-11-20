# -*- coding: utf-8 -*-
"""
app.py — лёгкий Flask-сервис для интерактивной карты локальной сети.

Запуск:
    python -m app

Откроет карту по адресу http://<этот-хост>:5000/network, а сам сервер
отдаёт основную страницу по http://<этот-хост>:5000/ и JSON API по /api/*.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import re
import socket

from flask import Flask, jsonify, render_template, request, send_from_directory

from data import network_data as nd

SUBNET = "192.168.1"
MAX_WORKERS = 128
PING_TIMEOUT = 2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

# ---------- состояние сканирования ----------

latest_status = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "subnet": nd.SUBNET,
    "mask": nd.NETWORK_MASK,
    "devices": [],
    "alive_icmp": [],
    "alive_arp": [],
    "offline": [],
    "note": nd.ORIGINAL_NET_MAP_NOTE,
    "summary": "",
}

_lock = threading.Lock()


def _refresh_status():
    """Пересобирает текущее состояние из данных в data/network_data.py."""
    devices_payload = []
    alive_icmp = []
    alive_arp = []
    offline = []

    for d in nd.DEVICES:
        ip = "192.168.1." + d["ip"] if not d["ip"].startswith("192.168.1.") else d["ip"]
        entry = {
            "ip": ip,
            "name": d.get("name", "N/A"),
            "mac": d.get("mac", "—"),
            "category": d.get("category", "unknown"),
            "status": d.get("status", "unknown"),
            "ping_rtt": d.get("ping_rtt", "—"),
            "ttl": d.get("ttl", "—"),
            "ports": d.get("ports", "—"),
            "detail_type": d.get("detail_type", "device"),
            "detail_hint": d.get("detail_hint") or ("http://" + ip),
            "notes": d.get("notes", ""),
        }
        devices_payload.append(entry)

        # Используем статус из database (network_data.py)
        # Он уже обновлён после сканирования (вручную или скриптом)
        status = d.get("status", "unknown")
        if status == "online":
            alive_icmp.append(ip)
        elif status == "offline":
            offline.append(ip)
        else:
            alive_arp.append(ip)

    with _lock:
        latest_status["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        latest_status["devices"] = devices_payload
        latest_status["alive_icmp"] = alive_icmp
        latest_status["alive_arp"] = alive_arp
        latest_status["offline"] = offline
        latest_status["summary"] = f"{len(devices_payload)} устройств"


# ---------- маршруты ----------


@app.route("/network")
def network_map_page():
    """Отдельный маршрут для карты: он и будет открываться в новой вкладке."""
    return render_template("network_map.html")


@app.route("/")
def index():
    return render_template("network_map.html")


@app.route("/api/network/info")
def api_network_info():
    with _lock:
        payload = dict(latest_status)
    payload["total"] = len(payload["devices"])
    payload["alive"] = len(payload["alive_icmp"])
    payload["offline"] = len(payload["offline"])
    payload["elapsed_sec"] = round((datetime.now() - latest_status.get("timestamp", datetime.now())).total_seconds(), 2)
    return jsonify(payload)


def _ping(ip):
    """Пингует один хост, возвращает (ip, alive, rtt)."""
    try:
        # Windows использует -n вместо -c, -w вместо -W (в миллисекундах)
        # shell=True для надёжной работы на Windows
        r = subprocess.run(
            f"ping -n 1 -w {PING_TIMEOUT * 1000} {ip}",
            shell=True, capture_output=True, timeout=PING_TIMEOUT + 2
        )
        if r.returncode == 0:
            # Декодируем вывод для парсинга RTT
            raw = r.stdout
            text = ""
            for enc in ('cp866', 'cp1251', 'utf-8', 'latin-1'):
                try:
                    text = raw.decode(enc, errors='replace')
                    break
                except Exception:
                    continue
            # Парсим RTT
            m = re.search(r"время[=<]([\d.]+)", text, re.IGNORECASE)
            if not m:
                m = re.search(r"time[=<]([\d.]+)", text, re.IGNORECASE)
            rtt = float(m.group(1)) if m else None
            return ip, True, rtt
    except Exception:
        pass
    return ip, False, None


def _get_mac(ip):
    """ARP-запрос для получения MAC-адреса."""
    try:
        # На Windows используем arp -a вместо arp -n
        r = subprocess.run(["arp", "-a", ip], capture_output=True, text=True, timeout=3)
        # На Windows MAC выглядит как: xx-xx-xx-xx-xx-xx
        m = re.search(r"([0-9A-Fa-f]{2}[-:]){5}[0-9A-Fa-f]{2}", r.stdout)
        return m.group(0) if m else None
    except Exception:
        return None


def _scan_port(ip, port):
    """TCP-скан одного порта."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        res = s.connect_ex((ip, port))
        s.close()
        return res == 0
    except Exception:
        return False


def _scan_ports(ip, ports):
    """Параллельный скан нескольких портов на одном хосте."""
    open_ports = []
    with ThreadPoolExecutor(max_workers=len(ports)) as ex:
        futures = {ex.submit(_scan_port, ip, p): p for p in ports}
        for f in as_completed(futures):
            if f.result():
                open_ports.append(futures[f])
    return sorted(open_ports)


COMMON_PORTS = [22, 80, 443, 445, 554, 1883, 3389, 8009, 8123, 8580]


@app.route("/api/network/scan", methods=["GET", "POST"])
def api_network_scan():
    """Реальное сканирование подсети (ping sweep + ARP + TCP).

    Возвращает только устройства, которые ответили на ping.
    """
    start = datetime.now()
    try:
        hosts = [f"{SUBNET}.{i}" for i in range(1, 255)]

        # Параллельный ping sweep
        reachable = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(_ping, ip): ip for ip in hosts}
            for f in as_completed(futures):
                try:
                    ip, ok, rtt = f.result()
                    if ok:
                        reachable.append({"ip": ip, "rtt": rtt})
                except Exception:
                    pass

        # Для каждого живого хоста: ARP (MAC) + TCP-скан
        mac_map = {}
        ports_map = {}
        if reachable:
            with ThreadPoolExecutor(max_workers=min(32, len(reachable))) as ex:
                future_map = {}
                for h in reachable:
                    ip = h["ip"]
                    future_map[ex.submit(_get_mac, ip)] = (ip, "mac")
                    future_map[ex.submit(_scan_ports, ip, COMMON_PORTS)] = (ip, "ports")
                
                for f in as_completed(future_map):
                    try:
                        ip, kind = future_map[f]
                        val = f.result()
                        if kind == "mac":
                            mac_map[ip] = val
                        else:
                            ports_map[ip] = val
                    except Exception:
                        pass

        # Обогащаем известными данными из network_data.py
        known = {}
        for d in nd.DEVICES:
            full = f"192.168.1.{d['ip']}" if not d["ip"].startswith("192.168.1.") else d["ip"]
            known[full] = d

        conn_types = nd.DEVICE_CONNECTION_TYPE
        scanner = getattr(nd, "SCANNER_DATA", {})

        # Оставляем только устройства с MAC-адресом или открытыми портами
        devices = []
        for h in reachable:
            ip = h["ip"]
            mac = mac_map.get(ip)
            ports = ports_map.get(ip, [])
            if mac or ports:
                info = known.get(ip, {})
                devices.append({
                    "ip": ip,
                    "name": info.get("name") or f"Устройство {ip.split('.')[-1]}",
                    "mac": mac or info.get("mac", "—"),
                    "category": info.get("category", "unknown"),
                    "status": "online",
                    "ping_rtt": h["rtt"],
                    "ttl": info.get("ttl", "—"),
                    "ports": ports,
                    "connection_type": conn_types.get(ip, info.get("connection_type", "unknown")),
                    "detail_type": info.get("detail_type", "device"),
                    "detail_hint": info.get("detail_hint") or f"http://{ip}",
                    "notes": info.get("notes", ""),
                    "hostname": scanner.get(ip, {}).get("hostname", ""),
                    "vendor": scanner.get(ip, {}).get("vendor", ""),
                })

        # Сортируем по IP
        devices.sort(key=lambda x: list(map(int, x["ip"].split("."))))

        elapsed = (datetime.now() - start).total_seconds()
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subnet": f"{SUBNET}.0/24",
            "mask": nd.NETWORK_MASK,
            "total_hosts": 254,
            "reachable": len(reachable),
            "alive": len(reachable),
            "devices": devices,
            "devices_count": len(devices),
            "elapsed_sec": round(elapsed, 2),
            "summary": f"Найдено {len(devices)} устройств, {len(reachable)} отвечают на ping ({elapsed:.1f} сек)",
        })
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subnet": f"{SUBNET}.0/24",
            "mask": nd.NETWORK_MASK,
            "total_hosts": 254,
            "reachable": 0,
            "alive": 0,
            "devices": [],
            "devices_count": 0,
            "elapsed_sec": round(elapsed, 2),
            "summary": f"Ошибка сканирования: {e}",
        })


@app.route("/api/device/<ip>", methods=["GET", "PUT"])
def api_device(ip):
    """Детальная информация об устройстве.

    GET  — текущая информация;
    PUT — ручной сброс статуса (online/offline/warning).
    """
    ip = ip.replace("192.168.1.", "")
    for d in nd.DEVICES:
        if d["ip"] == ip:
            full_ip = "192.168.1." + d["ip"]
            entry = {
                "id": d.get("id") or "dev-" + d["ip"],
                "ip": full_ip,
                "name": d["name"],
                "mac": d["mac"],
                "oui": d["oui"],
                "category": d["category"],
                "status": d["status"],
                "ping_rtt": d.get("ping_rtt", "-"),
                "ttl": d.get("ttl", "-"),
                "ports": d.get("ports", "нет"),
                "sources": d.get("sources", ""),
                "notes": d.get("notes", ""),
                "detail_type": d.get("detail_type", "device"),
                "detail_hint": d.get("detail_hint") or ("http://" + entry["ip"]),
                "last_seen": nd.LATEST_SCAN,
                "original_note": nd.ORIGINAL_NET_MAP_NOTE,
                "connection_type": nd.DEVICE_CONNECTION_TYPE.get(full_ip, "unknown"),
                "services": nd.DEVICE_SERVICES.get(full_ip, []),
            }
            if request.method == "PUT":
                payload = request.get_json(silent=True) or {}
                new_status = payload.get("status")
                if new_status in ("online", "offline", "warning"):
                    d["status"] = new_status
                return jsonify(entry)
            return jsonify(entry)

    return jsonify({"error": "device not found"}), 404


@app.route("/api/device/<ip>/services")
def api_device_services(ip):
    """Список сервисов, обнаруженных на устройстве."""
    ip = ip.replace("192.168.1.", "")
    full_ip = "192.168.1." + ip
    for d in nd.DEVICES:
        if d["ip"] == ip:
            return jsonify({
                "ip": full_ip,
                "name": d["name"],
                "services": nd.DEVICE_SERVICES.get(full_ip, []),
            })
    return jsonify({"error": "device not found"}), 404


@app.route("/api/network/topology")
def api_network_topology():
    """Граф соединений между устройствами для визуализации топологии."""
    devices = []
    for d in nd.DEVICES:
        full_ip = "192.168.1." + d["ip"]
        devices.append({
            "ip": full_ip,
            "name": d["name"],
            "category": d.get("category", "unknown"),
            "status": d.get("status", "unknown"),
            "connection_type": nd.DEVICE_CONNECTION_TYPE.get(full_ip, "unknown"),
        })
    return jsonify({
        "devices": devices,
        "connections": nd.CONNECTIONS,
    })


@app.route("/static/<path:filename>")
def static_proxy(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    # Заполнить состояние из data/network_data.py при старте.
    _refresh_status()

    host = os.environ.get("RADMON_HOST", "192.168.1.103")
    port = int(os.environ.get("RADMON_PORT", "5000"))
    print(f"[RadMonitor] serving network map on http://{host}:{port}/network")
    app.run(host=host, port=port, debug=False, threaded=True)
