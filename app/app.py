# -*- coding: utf-8 -*-
"""app.py — лёгкий Flask-сервис для интерактивной карты локальной сети."""

import os
import sys
import json
import time
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import network_data as nd

SCAN_INTERVAL = 30

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
SCAN_JSON_PATH = os.path.join(PROJECT_DIR, "data", "network_scan.json")

app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

_lock = threading.Lock()
_scan_running = False


def _full_ip(ip):
    s = str(ip)
    if s.startswith("192.168.1."):
        return s
    return "192.168.1." + s


def _merge_multi_ip(entries):
    by_ip = {e.get("ip"): e for e in entries}
    consumed = set()
    out = []

    def _alive(ent):
        return ent is not None and ent.get("status", "online") not in ("offline", "unknown")

    for e in entries:
        ip = e.get("ip")
        if ip in consumed:
            continue
        grp = nd.MULTI_IP_MAP.get(ip)
        if not grp:
            out.append(e)
            continue

        group_ips = [grp["primary"]] + list(grp.get("aliases") or [])
        members = []
        for gip in group_ips:
            ent = by_ip.get(gip)
            if ent is not None:
                consumed.add(gip)
            members.append({
                "ip": gip,
                "alive": _alive(ent),
                "ping_rtt": ent.get("ping_rtt") if ent is not None else None,
            })

        present = [by_ip[gip] for gip in group_ips if gip in by_ip]
        if not present:
            out.append(e)
            continue
        base = dict(by_ip[grp["primary"]] if grp["primary"] in by_ip else present[0])

        alive_ips = [m["ip"] for m in members if m["alive"]]
        active_ip = alive_ips[0] if alive_ips else None
        if active_ip is not None:
            base["ping_rtt"] = by_ip[active_ip].get("ping_rtt")

        ports_lists = [e2.get("ports") for e2 in present
                       if isinstance(e2.get("ports"), list)]
        if ports_lists:
            base["ports"] = sorted({p for pl in ports_lists for p in pl})

        if base.get("status") != "warning":
            base["status"] = "online" if alive_ips else "offline"

        def _short(a):
            return "." + a.rsplit(".", 1)[-1]

        note = "Один хост с несколькими IP: " + ", ".join(_short(m["ip"]) for m in members)
        if active_ip:
            note += "; активный интерфейс: " + _short(active_ip) + "."
        else:
            note += "; сейчас ни один интерфейс не отвечает."

        base["ip"] = grp["primary"]
        base["active_ip"] = active_ip
        base["ips"] = members
        base["notes"] = (str(base.get("notes") or "").strip() + " " + note).strip()
        out.append(base)

    return out


def _normalize_device(d):
    if not isinstance(d, dict):
        return d
    ndev = dict(d)
    if "ip" in ndev:
        ndev["ip"] = _full_ip(ndev["ip"])
    return ndev


def _read_raw():
    try:
        with open(SCAN_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = None
    if not isinstance(data, dict):
        data = None
    if data is None:
        devices = []
        for d in getattr(nd, "DEVICES", []):
            ip = "192.168.1." + str(d["ip"]) if not str(d["ip"]).startswith("192.168.1.") else str(d["ip"])
            devices.append({
                "ip": ip,
                "name": d.get("name"),
                "mac": d.get("mac"),
                "category": d.get("category", "unknown"),
                "status": d.get("status", "unknown"),
                "ping_rtt": d.get("ping_rtt", "-"),
                "ttl": d.get("ttl", "-"),
                "ports": d.get("ports", "нет"),
                "notes": d.get("notes", ""),
            })
        alive_icmp = []
        alive_arp = []
        offline = []
        for d in devices:
            st = d.get("status", "unknown")
            if st == "online":
                alive_icmp.append(d["ip"])
            elif st == "offline":
                offline.append(d["ip"])
            else:
                alive_arp.append(d["ip"])
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subnet": getattr(nd, "SUBNET", "192.168.1.0/24"),
            "mask": getattr(nd, "NETWORK_MASK", "255.255.255.0"),
            "devices": devices,
            "alive_icmp": alive_icmp,
            "alive_arp": alive_arp,
            "offline": offline,
            "note": getattr(nd, "ORIGINAL_NET_MAP_NOTE", ""),
            "summary": f"{len(devices)} устройств",
            "connections": getattr(nd, "CONNECTIONS", []),
        }
    # normalize
    data["devices"] = [_normalize_device(d) for d in (data.get("devices") or [])]
    return data


def load_scan_data():
    return _read_raw()


def save_scan_data(data):
    os.makedirs(os.path.dirname(SCAN_JSON_PATH), exist_ok=True)
    to_save = dict(data)
    to_save["devices"] = [_normalize_device(d) for d in (to_save.get("devices") or [])]
    tmp = SCAN_JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SCAN_JSON_PATH)


def background_scan():
    global _scan_running
    while True:
        try:
            _scan_running = True
            from data import network_discovery as disc
            devices, connections, alive_icmp, alive_arp, offline, summary = disc.run_discovery()
            norm_devices = [_normalize_device(d) for d in (devices or [])]
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "subnet": getattr(nd, "SUBNET", "192.168.1.0/24"),
                "mask": getattr(nd, "NETWORK_MASK", "255.255.255.0"),
                "devices": norm_devices,
                "alive_icmp": alive_icmp,
                "alive_arp": alive_arp,
                "offline": offline,
                "note": getattr(nd, "ORIGINAL_NET_MAP_NOTE", ""),
                "summary": summary,
                "connections": connections,
            }
            save_scan_data(payload)
            print(f"[RadMonitor] Фоновое сканирование завершено: {summary}")
        except Exception as e:
            print(f"[RadMonitor] Ошибка фонового сканирования: {e}")
        finally:
            _scan_running = False
        time.sleep(SCAN_INTERVAL)


def start_background_scanner():
    t = threading.Thread(target=background_scan, daemon=True)
    t.start()


def run_single_scan():
    global _scan_running
    try:
        _scan_running = True
        from data import network_discovery as disc
        devices, connections, alive_icmp, alive_arp, offline, summary = disc.run_discovery()
        norm_devices = [_normalize_device(d) for d in (devices or [])]
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subnet": getattr(nd, "SUBNET", "192.168.1.0/24"),
            "mask": getattr(nd, "NETWORK_MASK", "255.255.255.0"),
            "devices": norm_devices,
            "alive_icmp": alive_icmp,
            "alive_arp": alive_arp,
            "offline": offline,
            "note": getattr(nd, "ORIGINAL_NET_MAP_NOTE", ""),
            "summary": summary,
            "connections": connections,
        }
        save_scan_data(payload)
        print(f"[RadMonitor] Ручное сканирование завершено: {summary}")
    except Exception as e:
        print(f"[RadMonitor] Ошибка ручного сканирования: {e}")
    finally:
        _scan_running = False


@app.route("/")
def index():
    return render_template("network_map.html")


@app.route("/network")
def network():
    return render_template("network_map.html")


@app.route("/api/network/info")
def api_network_info():
    data = load_scan_data()
    data = dict(data)
    raw_devices = [_normalize_device(d) for d in (data.get("devices") or [])]
    data["devices"] = _merge_multi_ip(raw_devices)
    data["total"] = len(data["devices"])
    data["alive"] = len(data.get("alive_icmp") or []) + len(data.get("alive_arp") or [])
    data["offline"] = len(data.get("offline") or [])
    data["scanning"] = _scan_running
    return jsonify(data)


@app.route("/api/network/scan")
def api_network_scan():
    global _scan_running
    if _scan_running:
        return jsonify({"status": "scanning", "message": "Сканирование уже выполняется"}), 202
    threading.Thread(target=run_single_scan, daemon=True).start()
    return jsonify({"status": "started", "message": "Сканирование запущено в фоне"})


@app.route("/api/network/scan/status")
def api_scan_status():
    return jsonify({"scanning": _scan_running})


@app.route("/api/network/topology")
def api_network_topology():
    data = load_scan_data()
    devices = []
    for d in (data.get("devices") or []):
        dd = _normalize_device(d)
        full_ip = dd.get("ip")
        devices.append({
            "ip": full_ip,
            "name": dd.get("name"),
            "category": dd.get("category", "unknown"),
            "status": dd.get("status", "unknown"),
            "connection_type": nd.DEVICE_CONNECTION_TYPE.get(full_ip, "unknown"),
        })
    if not devices:
        for d in getattr(nd, "DEVICES", []):
            full_ip = _full_ip(d.get("ip"))
            devices.append({
                "ip": full_ip,
                "name": d.get("name"),
                "category": d.get("category", "unknown"),
                "status": d.get("status", "unknown"),
                "connection_type": nd.DEVICE_CONNECTION_TYPE.get(full_ip, "unknown"),
            })
    connections = data.get("connections")
    if not connections:
        connections = getattr(nd, "CONNECTIONS", [])
    return jsonify({"devices": devices, "connections": connections})


@app.route("/api/device/<ip>", methods=["GET", "PUT"])
def api_device(ip):
    requested = _full_ip(ip)
    grp = nd.MULTI_IP_MAP.get(requested)
    full_ip = requested
    if grp:
        full_ip = grp["primary"]
    short_ip = full_ip.rsplit(".", 1)[-1]

    data = load_scan_data()
    scan_dev = None
    for d in (data.get("devices") or []):
        dd = _normalize_device(d)
        if dd.get("ip") == full_ip or str(dd.get("ip", "")).endswith("." + short_ip):
            scan_dev = dd
            break

    nd_dev = None
    for d in getattr(nd, "DEVICES", []):
        if str(d.get("ip")) == short_ip:
            nd_dev = d
            break

    if nd_dev is None and scan_dev is None:
        return jsonify({"error": "device not found"}), 404

    entry = {
        "id": (nd_dev.get("id") if nd_dev else None) or ("dev-" + short_ip),
        "ip": full_ip,
        "name": (scan_dev.get("name") if scan_dev else None) or (nd_dev.get("name") if nd_dev else None) or ("Устройство " + short_ip),
        "mac": (scan_dev.get("mac") if scan_dev else None) or (nd_dev.get("mac") if nd_dev else "—"),
        "oui": (nd_dev.get("oui") if nd_dev else ""),
        "category": (scan_dev.get("category") if scan_dev else None) or (nd_dev.get("category") if nd_dev else "unknown"),
        "status": (scan_dev.get("status") if scan_dev else None) or (nd_dev.get("status") if nd_dev else "unknown"),
        "ping_rtt": (scan_dev.get("ping_rtt") if scan_dev else None),
        "ttl": (nd_dev.get("ttl") if nd_dev else "-"),
        "ports": (scan_dev.get("ports") if scan_dev else None),
        "sources": (nd_dev.get("sources") if nd_dev else ""),
        "notes": (scan_dev.get("notes") if scan_dev else None) or (nd_dev.get("notes") if nd_dev else ""),
        "detail_type": (nd_dev.get("detail_type") if nd_dev else "device"),
        "detail_hint": (nd_dev.get("detail_hint") if nd_dev else None) or ("http://" + full_ip),
        "last_seen": data.get("timestamp"),
        "original_note": data.get("note") or getattr(nd, "ORIGINAL_NET_MAP_NOTE", ""),
        "connection_type": nd.DEVICE_CONNECTION_TYPE.get(full_ip, "unknown"),
        "services": nd.DEVICE_SERVICES.get(full_ip, []),
    }
    if entry["ping_rtt"] is None:
        entry["ping_rtt"] = (nd_dev.get("ping_rtt") if nd_dev else "-")
    if entry["ports"] is None:
        entry["ports"] = (nd_dev.get("ports") if nd_dev else "нет")

    if request.method == "PUT":
        payload = request.get_json(silent=True) or {}
        new_status = payload.get("status")
        if new_status in ("online", "offline", "warning"):
            # update scan JSON
            raw = load_scan_data()
            for d in (raw.get("devices") or []):
                dd = _normalize_device(d)
                if dd.get("ip") == full_ip:
                    d["status"] = new_status
            save_scan_data(raw)
            entry["status"] = new_status
        return jsonify(entry)
    return jsonify(entry)


@app.route("/api/device/<ip>/services")
def api_device_services(ip):
    ip = ip.replace("192.168.1.", "")
    full_ip = "192.168.1." + ip
    grp = nd.MULTI_IP_MAP.get(full_ip)
    if grp:
        full_ip = grp["primary"]
        ip = full_ip.rsplit(".", 1)[-1]
    for d in getattr(nd, "DEVICES", []):
        if d["ip"] == ip:
            services = list(nd.DEVICE_SERVICES.get(full_ip, []))
            if grp:
                seen = {(s.get("type"), s.get("port")) for s in services}
                for alias in grp["aliases"]:
                    for s in nd.DEVICE_SERVICES.get(alias, []):
                        if (s.get("type"), s.get("port")) not in seen:
                            seen.add((s.get("type"), s.get("port")))
                            services.append(s)
            return jsonify({
                "ip": full_ip,
                "name": d["name"],
                "services": services,
            })
    return jsonify({"error": "device not found"}), 404


@app.route("/static/<path:filename>")
def static_proxy(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    if not os.path.exists(SCAN_JSON_PATH):
        save_scan_data(load_scan_data())
    start_background_scanner()

    host = os.environ.get("RADMON_HOST", "192.168.1.103")
    port = int(os.environ.get("RADMON_PORT", "5000"))
    print(f"[RadMonitor] serving network map on http://{host}:{port}/network")
    app.run(host=host, port=port, debug=False, threaded=True)
