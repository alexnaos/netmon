#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
network_discovery.py — автообнаружение устройств и обновление network_data.py.
Сканирует сеть (ping + ARP + TCP + HTTP), добавляет новые, удаляет отсутствующие (.128),
чистит CONNECTIONS, сохраняет файл.
"""
import ast, ipaddress, os, re, socket, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

SUBNET = "192.168.1.0/24"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "network_data.py")
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
        r = subprocess.run(["arp","-n",ip], capture_output=True, text=True, timeout=3)
        m = re.search(r"(([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})", r.stdout)
        return m.group(0) if m else None
    except Exception:
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
            ex["notes"] = notes + (" " + ex["notes"] if ex.get("notes") else "")
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
            in_conns = True
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

if __name__ == "__main__":
    main()
