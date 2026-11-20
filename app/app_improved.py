# -*- coding: utf-8 -*-
"""
app_improved.py — улучшенное Flask-приложение для интерактивной карты локальной сети.

Основные улучшения:
1. Исправлено дублирование устройств
2. Добавлено периодическое сканирование
3. Улучшена обработка ошибок
4. Добавлено логирование
5. Исправлены проблемы с кодировкой

Запуск:
    python -m app_improved

Откроет карту по адресу http://<этот-хост>:5000/network
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import re
import socket
from dotenv import load_dotenv

from flask import Flask, jsonify, render_template, request, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import network_data as nd

# Загрузка конфигурации
load_dotenv()

SUBNET = os.environ.get("SUBNET", "192.168.1.0/24")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 128))
PING_TIMEOUT = int(os.environ.get("PING_TIMEOUT", 2))
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", 300))  # 5 минут по умолчанию

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Настройка логирования
if sys.platform == "win32":
    import locale
    locale.setlocale(locale.LC_ALL, '')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'netmon.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    "scanning": False,
    "last_scan_time": None,
    "next_scan_time": None,
}

_lock = threading.Lock()
_scan_thread = None
_stop_event = threading.Event()

def _refresh_status():
    """Пересобирает текущее состояние из данных в data/network_data.py."""
    try:
        devices_payload = []
        alive_icmp = []
        alive_arp = []
        offline = []

        # Используем множество для предотвращения дублирования устройств
        seen_ips = set()
        
        for d in nd.DEVICES:
            ip = "192.168.1." + d["ip"] if not d["ip"].startswith("192.168.1.") else d["ip"]
            
            # Проверка на дублирование
            if ip in seen_ips:
                logger.warning(f"Обнаружено дублирование устройства: {ip}")
                continue
            seen_ips.add(ip)
            
            entry = {
                "ip": ip,
                "mac": d.get("mac", "—"),
                "category": d.get("category", "unknown"),
                "status": d.get("status", "unknown"),
                "ping_rtt": d.get("ping_rtt", "—"),
                "ttl": d.get("ttl", "—"),
                "ports": d.get("ports", "—"),
                "detail_type": d.get("detail_type", "device"),
                "detail_hint": d.get("detail_hint") or ("http://" + ip),
                "notes": d.get("notes", ""),
                "oui": d.get("oui", ""),
                "sources": d.get("sources", ""),
            }
            devices_payload.append(entry)

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
            latest_status["summary"] = f"{len(devices_payload)} устройств, {len(alive_icmp) + len(alive_arp)} онлайн"
            
        logger.info(f"Статус обновлен: {len(devices_payload)} устройств")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса: {e}")

def ping_host(ip):
    """Пинг устройства с таймаутом."""
    try:
        r = subprocess.run(["ping", "-n", "1", "-w", str(PING_TIMEOUT * 1000), ip],
                          capture_output=True, text=True, timeout=PING_TIMEOUT + 2)
        return r.returncode == 0
    except Exception as e:
        logger.debug(f"Ошибка ping {ip}: {e}")
        return False

def scan_network():
    """Сканирование сети с улучшенной обработкой ошибок."""
    logger.info("Запуск сканирования сети...")
    
    with _lock:
        latest_status["scanning"] = True
        latest_status["scan_started"] = time.time()
    
    network_prefix = "192.168.1"
    hosts_to_scan = [f"{network_prefix}.{i}" for i in range(1, 255)]
    
    reachable = []
    start_time = time.time()
    
    try:
        # Параллельный пинг
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_ip = {executor.submit(ping_host, ip): ip for ip in hosts_to_scan}
            
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    if future.result():
                        reachable.append(ip)
                except Exception as e:
                    logger.debug(f"Ошибка при сканировании {ip}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при сканировании сети: {e}")
    
    elapsed = time.time() - start_time
    
    # Для каждого живого хоста: получить MAC и проверить порты
    mac_map = {}
    ports_map = {}
    if reachable:
        with ThreadPoolExecutor(max_workers=min(32, len(reachable))) as executor:
            future_map = {}
            for ip in reachable:
                future_map[executor.submit(get_mac, ip)] = ip
                future_map[executor.submit(scan_ports, ip, COMMON_PORTS)] = ip
            
            for future in as_completed(future_map):
                ip = future_map[future]
                try:
                    result = future.result()
                    if isinstance(result, tuple):
                        mac_map[ip] = result[0]
                        ports_map[ip] = result[1]
                    else:
                        mac_map[ip] = result
                except Exception:
                    pass
    
    # Оставляем только устройства с MAC-адресом или открытыми портами
    devices = []
    known = {}
    for d in nd.DEVICES:
        full = f"192.168.1.{d['ip']}" if not d["ip"].startswith("192.168.1.") else d["ip"]
        known[full] = d
    
    conn_types = nd.DEVICE_CONNECTION_TYPE
    scanner = getattr(nd, "SCANNER_DATA", {})
    
    for ip in reachable:
        mac = mac_map.get(ip)
        ports = ports_map.get(ip, [])
        if mac or ports:
            info = known.get(ip, {})
            open_ports = ports if isinstance(ports, list) else []
            devices.append({
                "ip": ip,
                "name": info.get("name") or f"Устройство {ip.split('.')[-1]}",
                "mac": mac or info.get("mac", "—"),
                "category": info.get("category", "unknown"),
                "status": "online",
                "ping_rtt": "-",
                "ttl": info.get("ttl", "—"),
                "ports": open_ports,
                "connection_type": conn_types.get(ip, info.get("connection_type", "unknown")),
                "detail_type": info.get("detail_type", "device"),
                "detail_hint": info.get("detail_hint") or f"http://{ip}",
                "notes": info.get("notes", ""),
                "hostname": scanner.get(ip, {}).get("hostname", ""),
                "vendor": scanner.get(ip, {}).get("vendor", ""),
            })
    
    devices.sort(key=lambda x: list(map(int, x["ip"].split("."))))
    
    logger.info(f"Сканирование завершено за {elapsed:.2f} сек. Найдено устройств: {len(devices)}, отвели на ping: {len(reachable)}")
    return devices, reachable

def background_scanner():
    """Фоновая задача для периодического сканирования сети."""
    logger.info("Фоновый сканер запущен")
    
    while not _stop_event.is_set():
        try:
            scan_network()
            _refresh_status()
        except Exception as e:
            logger.error(f"Ошибка в фоновом сканере: {e}")
        
        # Ожидание до следующего сканирования
        _stop_event.wait(SCAN_INTERVAL)

def start_background_scanner():
    """Запуск фонового сканера."""
    global _scan_thread
    if _scan_thread is None or not _scan_thread.is_alive():
        _stop_event.clear()
        _scan_thread = threading.Thread(target=background_scanner, daemon=True)
        _scan_thread.start()
        logger.info("Фоновый сканер запущен")

def stop_background_scanner():
    """Остановка фонового сканера."""
    _stop_event.set()
    if _scan_thread and _scan_thread.is_alive():
        _scan_thread.join(timeout=5)
    logger.info("Фоновый сканер остановлен")

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
    """Текущее состояние сети."""
    with _lock:
        payload = dict(latest_status)
    
    payload["total"] = len(payload["devices"])
    payload["alive"] = len(payload["alive_icmp"])
    payload["offline"] = len(payload["offline"])
    payload["elapsed_sec"] = round((datetime.now() - latest_status.get("timestamp", datetime.now())).total_seconds(), 2)
    
    return jsonify(payload)

@app.route("/api/network/scan", methods=["GET", "POST"])
def api_network_scan():
    """Запуск сканирования сети."""
    if request.method == "POST" or request.args.get("force", "").lower() == "true":
        logger.info("Ручной запуск сканирования сети")
        alive_hosts = scan_network()
        
        return jsonify({
            "success": True,
            "alive_hosts": len(alive_hosts),
            "total_scanned": 254,
            "elapsed_sec": round(time.time() - latest_status.get("scan_started", 0), 2),
            "message": f"Найдено {len(alive_hosts)} живых устройств"
        })
    
    # GET запрос возвращает статус сканирования
    with _lock:
        scanning = latest_status.get("scanning", False)
        last_scan = latest_status.get("last_scan_time")
        next_scan = latest_status.get("next_scan_time")
    
    return jsonify({
        "scanning": scanning,
        "last_scan": last_scan,
        "next_scan": next_scan,
        "scan_interval_sec": SCAN_INTERVAL
    })

@app.route("/api/device/<ip>", methods=["GET", "PUT"])
def api_device(ip):
    """Детальная информация об устройстве."""
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
                "detail_hint": d.get("detail_hint") or ("http://" + full_ip),
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
                    logger.info(f"Статус устройства {full_ip} изменен на {new_status}")
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
    seen_ips = set()
    
    for d in nd.DEVICES:
        full_ip = "192.168.1." + d["ip"]
        if full_ip in seen_ips:
            continue
        seen_ips.add(full_ip)
        
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

@app.route("/api/health")
def api_health():
    """Проверка здоровья приложения."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "2.0.0",
        "scanning": latest_status.get("scanning", False)
    })

@app.route("/api/config")
def api_config():
    """Текущая конфигурация приложения."""
    return jsonify({
        "subnet": SUBNET,
        "max_workers": MAX_WORKERS,
        "ping_timeout": PING_TIMEOUT,
        "scan_interval": SCAN_INTERVAL,
        "log_level": logging.getLevelName(logger.getEffectiveLevel()),
        "host": os.environ.get("RADMON_HOST", "192.168.1.103"),
        "port": int(os.environ.get("RADMON_PORT", "5000")),
    })

# ---------- обработчики ошибок ----------

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# ---------- запуск приложения ----------

if __name__ == "__main__":
    # Инициализация при запуске
    _refresh_status()
    
    # Запуск фонового сканера
    start_background_scanner()
    
    host = os.environ.get("RADMON_HOST", "192.168.1.103")
    port = int(os.environ.get("RADMON_PORT", "5000"))
    
    logger.info(f"NetMonitor запущен на http://{host}:{port}")
    logger.info(f"Конфигурация: подсеть={SUBNET}, интервал сканирования={SCAN_INTERVAL} сек")
    
    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Остановка приложения...")
        stop_background_scanner()
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        stop_background_scanner()
        raise