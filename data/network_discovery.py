#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""network_discovery.py — автообнаружение устройств."""
import ast, ipaddress, os, re, socket, subprocess, sys, json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SUBNET = "192.168.1.0/24"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "network_data.py")
SCAN_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "network_scan.json")
COMMON_PORTS = [22, 80, 443, 445, 1883, 3389, 554, 8123, 8580, 8009]
PING_TIMEOUT = 2
PORT_TIMEOUT = 1
HTTP_TIMEOUT = 2
MAX_WORKERS = 60

def ping_host(ip):
    try:
        r = subprocess.run(["ping","-c","1","-W",str(PING_TIMEOUT),ip],
                           capture_output=True, text=True, timeout=PING_TIMEOUT+2)
        return r.returncode == 0
    except Exception:
        return False

def get_mac(ip):
    try:
        with open('/proc/net/arp', 'r', encoding='utf-8') as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) >= 4 and parts[0] == ip:
                    mac = parts[3]
                    if mac and mac != '00:00:00:00:00:00':
                        return mac
    except Exception:
        pass
    try:
        r = subprocess.run(['ip','neigh','show',ip], capture_output=True, text=True, timeout=3)
        m = re.search(r'lladdr\s+([0-9A-Fa-f:]{17})', r.stdout)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None

def scan_port(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(PORT_TIMEOUT)
        res = s.connect_ex((ip, port)); s.close()
        return res == 0
    except Exception:
        return False

def http_probe(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(HTTP_TIMEOUT); s.connect((ip, port))
        s.send(f"GET / HTTP/1.0\r\nHost: {ip}\r\n\r\n".encode())
        data = s.recv(2048).decode(errors="ignore"); s.close()
        m = re.search(r"Server:\s*([^\r\n]+)", data, re.I)
        if m: return m.group(1).strip()
        m = re.search(r"<title>([^<]+)</title>", data, re.I)
        if m: return m.group(1).strip()
    except Exception:
        pass
    return None

def get_rtt(ip):
    try:
        r = subprocess.run(["ping","-c","3","-W",str(PING_TIMEOUT),ip],
                           capture_output=True, text=True, timeout=PING_TIMEOUT*4)
        out = r.stdout
        m = re.search(r"min/avg/max/mdev = [\d.]+/([\d.]+)/", out)
        if m: return m.group(1)
        m = re.search(r"time=([\d.]+)\s*ms", out)
        if m: return m.group(1)
    except Exception:
        pass
    return "-"

def discover_mdns():
    mdns = {}
    try:
        r = subprocess.run(["avahi-browse","-at","--resolve","--no-dns"],
                           capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            m = re.search(r"IPv4\s+(\S+)\s+_([^\s]+)\._tcp\s+local\s+(\S+)", line)
            if m:
                ipm = re.search(r"(\d+\.\d+\.\d+\.\d+)", m.group(3))
                if ipm: mdns[ipm.group(1)] = m.group(2)
    except Exception:
        pass
    return mdns

def save_to_json(devices, connections, alive_icmp, alive_arp, offline, summary, note):
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "subnet": SUBNET,
        "mask": "255.255.255.0",
        "devices": devices,
        "alive_icmp": alive_icmp,
        "alive_arp": alive_arp,
        "offline": offline,
        "note": note,
        "summary": summary,
        "connections": connections,
    }
    os.makedirs(os.path.dirname(SCAN_JSON_PATH), exist_ok=True)
    tmp = SCAN_JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SCAN_JSON_PATH)
    print(f"[Discovery] Сохранено в {SCAN_JSON_PATH}: {len(devices)} устройств, {len(connections)} связей")

def _scan_one(full_ip, d=None):
    ip_short = full_ip.split(".")[-1]
    alive = ping_host(full_ip)
    mac = get_mac(full_ip) if alive else None
    if mac is None and isinstance(d, dict):
        mac = d.get("mac")
    ports = []
    http = None
    if alive:
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(scan_port, full_ip, p): p for p in COMMON_PORTS}
            for f in as_completed(futs):
                if f.result():
                    ports.append(futs[f])
        ports.sort()
        for p in (80, 8009, 8123, 8580):
            if p in ports:
                http = http_probe(full_ip, p)
                break
    rtt = get_rtt(full_ip) if alive else "-"
    return {
        "ip": ip_short,
        "mac": mac or "00:00:00:00:00:00",
        "ports": ports,
        "http": http,
        "rtt": rtt,
        "_full": full_ip,
    }

def run_discovery():
    src, ns = read_data(DATA_FILE)
    devices = ns.get("DEVICES", [])
    mdns = discover_mdns()

    disc = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for d in devices:
            full_ip = "192.168.1." + str(d["ip"])
            futures[ex.submit(_scan_one, full_ip, d)] = d
        for fut in as_completed(futures):
            try:
                res = fut.result()
                if res:
                    disc.append(res)
            except Exception as e:
                print(f"  [!] Ошибка сканирования хоста: {e}")

    for d in disc:
        ip = d["ip"]; full_ip = d.pop("_full"); ex_ = find_ip(devices, ip)
        ports_str = ", ".join(map(str, d["ports"])) if d["ports"] else "нет"
        status = "online" if d["ports"] or d["rtt"] != "-" else "warning"
        parts = []
        if d["http"]: parts.append(f"HTTP: {d['http']}")
        if d["rtt"] != "-": parts.append(f"RTT ~{d['rtt']} мс")
        if full_ip in mdns: parts.append(f"mDNS: {mdns[full_ip]}.local")
        notes = ". ".join(parts) if parts else "Автообнаружение."
        if ex_:
            ex_["status"] = status; ex_["ports"] = ports_str
            ex_["ping_rtt"] = d["rtt"]; ex_["mac"] = d["mac"]
            ex_["notes"] = notes
            if full_ip in mdns and mdns[full_ip] not in ex_.get("name", ""):
                ex_["name"] = f"{ex_['name']} ({mdns[full_ip]}.local)"
            print(f"  [~] Обновлено: {ip}")
        else:
            name = f"{mdns[full_ip]}.local" if full_ip in mdns else f"Устройство {ip}"
            hint = f"http://{full_ip}" if 80 in d["ports"] else (f"http://{full_ip}:{d['ports'][0]}" if d["ports"] else None)
            devices.append({"ip": ip, "name": name, "mac": d["mac"], "oui": "auto",
                            "category": category(d["ports"]), "status": status,
                            "ping_rtt": d["rtt"], "ttl": "64", "ports": ports_str,
                            "sources": "auto-discovery", "notes": notes,
                            "detail_type": "web", "detail_hint": hint})
            print(f"  [+] Добавлено: {ip} — {name}")

    print("\n[4/4] Очистка CONNECTIONS...")
    valid = {f"192.168.1.{str(d['ip'])}" for d in devices}
    conns = ns.get("CONNECTIONS", [])
    conns = [c for c in conns if str(c["from"]) in valid and str(c["to"]) in valid]
    removed = len(ns.get("CONNECTIONS", [])) - len(conns)
    if removed: print(f"  Удалено связей: {removed}")

    print("\n[5/5] Запись network_data.py ...")
    write_data(DATA_FILE, src, devices, conns, ns)
    print(f"Готово. Устройств: {len(devices)}, связей: {len(conns)}")

    alive_icmp = []
    alive_arp = []
    offline = []
    for d in devices:
        full_ip = "192.168.1." + d["ip"] if not d["ip"].startswith("192.168.1.") else d["ip"]
        status = d.get("status", "unknown")
        if status == "online":
            alive_icmp.append(full_ip)
            alive_arp.append(full_ip)
        else:
            offline.append(full_ip)

    summary = f"{len(devices)} устройств, {len(conns)} связей, {len(alive_icmp)} онлайн"

    save_to_json(devices, conns, alive_icmp, alive_arp, offline, summary, ns.get("ORIGINAL_NET_MAP_NOTE", ""))

    return devices, conns, alive_icmp, alive_arp, offline, summary

def read_data(path):
    with open(path, "r", encoding="utf-8") as f: src = f.read()
    tree = ast.parse(src); ns = {}
    exec(compile(tree, path, "exec"), ns)
    return src, ns

def find_ip(devices, ip):
    for d in devices:
        if str(d["ip"]) == str(ip): return d
    return None

def category(ports):
    if 1883 in ports: return "broker"
    if 8123 in ports or 8580 in ports: return "server"
    if 554 in ports: return "camera"
    if 8009 in ports: return "tv"
    if 80 in ports or 443 in ports: return "web"
    if 22 in ports: return "pc"
    return "unknown"

def write_data(path, src, devices, conns, ns):
    lines = src.splitlines(keepends=True)
    out = []
    in_devices = in_conns = False
    brace = 0
    for line in lines:
        s = line.strip()
        if s.startswith("DEVICES = ["):
            in_devices = True; brace = line.count("[") - line.count("]")
            out.append("DEVICES = [\n")
            for d in devices:
                out.append("    {\n")
                for k,v in d.items():
                    out.append(f'        "{k}": ')
                    if v is None: out.append("None,\n")
                    elif isinstance(v, str): out.append(repr(v) + ",\n")
                    else: out.append(repr(v) + ",\n")
                out.append("    },\n")
            out.append("]\n")
            continue
        if s.startswith("CONNECTIONS = ["):
            in_conns = True; brace = line.count("[") - line.count("]")
            out.append("CONNECTIONS = [\n")
            for c in conns:
                out.append(f'    {{"from": {c["from"]!r}, "to": {c["to"]!r}, "type": {c["type"]!r}}},\n')
            out.append("]\n")
            continue
        if in_devices or in_conns:
            brace += line.count("[") + line.count("{") - line.count("]") - line.count("}")
            if brace <= 0:
                in_devices = in_conns = False
            continue
        out.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)

def main():
    if not os.path.exists(DATA_FILE):
        print("ERROR: not found", DATA_FILE); sys.exit(1)
    src, ns = read_data(DATA_FILE)
    devices = list(ns.get("DEVICES", []))
    print(f"=== Discovery {SUBNET} ===\nВ базе: {len(devices)} устройств")

    mdns = discover_mdns()
    if mdns: print(f"mDNS имён: {len(mdns)}")

    net = ipaddress.ip_network(SUBNET, strict=False)
    alive = []
    print("\n[1/4] Ping sweep...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(ping_host, str(ip)): str(ip) for ip in net.hosts()}
        for f in as_completed(futs):
            if f.result(): alive.append(futs[f])
    alive.sort(key=lambda x: [int(o) for o in x.split(".")])
    print(f"Живых: {len(alive)}")

    print("\n[2/4] ARP + TCP + HTTP...")
    disc = []
    for ip in alive:
        ip_short = ip.split(".")[-1]
        mac = get_mac(ip)
        ports = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(scan_port, ip, p): p for p in COMMON_PORTS}
            for f in as_completed(futs):
                if f.result(): ports.append(futs[f])
        ports.sort()
        http = None
        for p in (80, 8009, 8123, 8580):
            if p in ports:
                http = http_probe(ip, p); break
        rtt = get_rtt(ip)
        disc.append({"ip": ip_short, "mac": mac or "00:00:00:00:00:00",
                     "ports": ports, "http": http, "rtt": rtt, "_full": ip})
        print(f"  {ip}: MAC={mac} порты={ports} RTT={rtt} HTTP={http}")

    print("\n[3/4] Сверка с базой...")
    found = {d["ip"] for d in disc}
    for d in devices:
        if str(d["ip"]) not in found:
            d["status"] = "offline"
            d["ports"] = "нет"
            d["ping_rtt"] = "-"
            print(f"  [!] Офлайн (не отвечает): {d['ip']} — {d.get('name','')}")

    for d in disc:
        ip = d["ip"]; full_ip = d.pop("_full"); ex = find_ip(devices, ip)
        ports_str = ", ".join(map(str,d["ports"])) if d["ports"] else "нет"
        status = "online" if d["ports"] or d["rtt"] != "-" else "warning"
        parts = []
        if d["http"]: parts.append(f"HTTP: {d['http']}")
        if d["rtt"] != "-": parts.append(f"RTT ~{d['rtt']} мс")
        if full_ip in mdns: parts.append(f"mDNS: {mdns[full_ip]}.local")
        notes = ". ".join(parts) if parts else "Автообнаружение."
        if ex:
            ex["status"] = status; ex["ports"] = ports_str
            ex["ping_rtt"] = d["rtt"]; ex["mac"] = d["mac"]
            ex["notes"] = notes
            if full_ip in mdns and mdns[full_ip] not in ex.get("name",""):
                ex["name"] = f"{ex['name']} ({mdns[full_ip]}.local)"
            print(f"  [~] Обновлено: {ip}")
        else:
            name = f"{mdns[full_ip]}.local" if full_ip in mdns else f"Устройство {ip}"
            hint = f"http://{full_ip}" if 80 in d["ports"] else (f"http://{full_ip}:{d['ports'][0]}" if d["ports"] else None)
            devices.append({"ip": ip, "name": name, "mac": d["mac"], "oui": "auto",
                            "category": category(d["ports"]), "status": status,
                            "ping_rtt": d["rtt"], "ttl": "64", "ports": ports_str,
                            "sources": "auto-discovery", "notes": notes,
                            "detail_type": "web", "detail_hint": hint})
            print(f"  [+] Добавлено: {ip} — {name}")

    print("\n[4/4] Очистка CONNECTIONS...")
    valid = {f"192.168.1.{str(d['ip'])}" for d in devices}
    conns = ns.get("CONNECTIONS", [])
    conns = [c for c in conns if str(c["from"]) in valid and str(c["to"]) in valid]
    removed = len(ns.get("CONNECTIONS", [])) - len(conns)
    if removed: print(f"  Удалено связей: {removed}")

    print("\n[5/5] Запись network_data.py ...")
    write_data(DATA_FILE, src, devices, conns, ns)
    print(f"Готово. Устройств: {len(devices)}, связей: {len(conns)}")

if __name__ == "__main__":
    run_discovery()
