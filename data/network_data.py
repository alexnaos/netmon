# -*- coding: utf-8 -*-
"""
network_data.py — структурированные устройства из network_map.md.

Снимок: 15.10.2026 20:20, подсеть 192.168.1.0/24.
"""

LATEST_SCAN = "15.10.2026 20:20"
SUBNET = "192.168.1.0/24"
NETWORK_MASK = "255.255.255.0"

CATEGORIES = {
    "gateway": "gateway", "router": "gateway", "access_point": "access_point",
    "switch": "switch", "nas": "nas", "camera": "camera", "tv": "tv",
    "audio": "audio", "phone": "phone", "control": "control",
    "server": "server", "broker": "broker", "web": "web",
    "edge_device": "edge_device", "pc": "pc", "unknown": "unknown",
}

DEVICES = [
    {"ip": "1", "name": "Основной роутер Keenetic", "mac": "54:10:7B:00:22:86",
     "oui": "Keenetic (Guangdong Jeton)", "category": "router", "status": "online",
     "ping_rtt": "64", "ttl": 64, "ports": "80, 22, 53", "sources": "103, 56",
     "notes": "Web:80, DNS:53. Шлюз/роутер сети.",
     "detail_type": "router", "detail_hint": "http://192.168.1.1"},
    {"ip": "20", "name": "ESP32 Диммер", "mac": "30:76:F5:F4:81:0C",
     "oui": "Espressif", "category": "control", "status": "warning",
     "ping_rtt": "82-187 мс", "ttl": 64, "ports": "80", "sources": "56",
     "notes": "HTTP:80. Широкие RSSI-прыжки 82–187 мс.",
     "detail_type": "web", "detail_hint": "http://192.168.1.20"},
    {"ip": "23", "name": "MQTT брокер", "mac": "02:07:0A:D9:85:6B",
     "oui": "локальный", "category": "broker", "status": "online",
     "ping_rtt": "64", "ttl": 64, "ports": "80, 22, 445, 1883", "sources": "103, 56",
     "notes": "orange.local. MQTT:1883, HTTP:80, SSH:22, SMB:445.",
     "detail_type": "web", "detail_hint": "http://192.168.1.23"},
    {"ip": "50", "name": "Mesh-узел Keenetic", "mac": "50:FF:20:66:75:FF",
     "oui": "Keenetic", "category": "router", "status": "online",
     "ping_rtt": "1 мс", "ttl": 64, "ports": "22, 80, 443", "sources": "103, 56",
     "notes": "KeeneticOS Web Panel, Sloboda100 ch1. WiFi-хосты на нём не видят камеру .196.",
     "detail_type": "router", "detail_hint": "http://192.168.1.50"},
    {"ip": "56", "name": "DomSloboda [ТЫ]", "mac": "E8:9C:25:9A:14:D4",
     "oui": "Realtek", "category": "pc", "status": "online",
     "ping_rtt": "-", "ttl": 128, "ports": "22, 445, 554, 3389, 5432", "sources": "103",
     "notes": "Главный сканер Ethernet. Видит всю локальную сеть.",
     "detail_type": "pc", "detail_hint": "https://192.168.1.56"},
    {"ip": "58", "name": "Home Assistant #3", "mac": "88:AE:1D:9A:15:A6",
     "oui": "COMPAL", "category": "server", "status": "online",
     "ping_rtt": "64", "ttl": 64, "ports": "22, 445, 8123", "sources": "103, 56",
     "notes": "HA:8123, SSH, SMB. Docker-контейнер.",
     "detail_type": "web", "detail_hint": "http://192.168.1.58:8123"},
    {"ip": "76", "name": "Интернет-радио \"Звук\" (zvuk.local)", "mac": "80:65:99:5B:E5:7C",
     "oui": "Espressif Inc.", "category": "audio", "status": "offline",
     "ping_rtt": "-", "ttl": "-", "ports": "нет", "sources": "бэкап 13.06.2026",
     "notes": "mDNS: zvuk.local (ESP32-S2 Wi-Fi, ожидает USB-прошивку). Сейчас офлайн.",
     "detail_type": "audio", "detail_hint": "http://192.168.1.76"},
    {"ip": "103", "name": "Home Assistant #1 (Wi-Fi->.50)", "mac": "74:2F:68:9D:20:B3",
     "oui": "AzureWave", "category": "server", "status": "online",
     "ping_rtt": "64", "ttl": 64, "ports": "22, 445, 1883, 8123, 8580", "sources": "56",
     "notes": "HA:8123, camera-web:8580, mosquitto:1883. Wi-Fi роумит на mesh .50.",
     "detail_type": "web", "detail_hint": "http://192.168.1.103:103"},
    {"ip": "128", "name": "TCL TV (2-й IP, один MAC)", "mac": "38:26:56:D1:AD:5F",
     "oui": "TCL King", "category": "tv", "status": "offline",
     "ping_rtt": "-", "ttl": "-", "ports": "нет", "sources": "ARP.56",
     "notes": "В ARP есть, но не отвечает ICMP. Два IP одного MAC.",
     "detail_type": "tv", "detail_hint": "http://192.168.1.128"},
    {"ip": "142", "name": "Xiaomi", "mac": "7C:D6:61:C1:D9:CF",
     "oui": "Xiaomi Communications", "category": "control", "status": "online",
     "ping_rtt": "62-67 мс", "ttl": 64, "ports": "нет", "sources": "ARP.56",
     "notes": "ICMP отвечает, порты не сканировались.",
     "detail_type": "control", "detail_hint": "http://192.168.1.142"},
    {"ip": "150", "name": "Oppo", "mac": "AC:7A:94:37:53:59",
     "oui": "Guangdong Oppo", "category": "phone", "status": "unknown",
     "ping_rtt": "-", "ttl": "-", "ports": "нет", "sources": "ARP 14.10",
     "notes": "Портов не найдено, сервисы не обнаружены.",
     "detail_type": "phone", "detail_hint": "http://192.168.1.150"},
    {"ip": "153", "name": "nginx", "mac": "6C:21:A2:33:DE:6A",
     "oui": "AMPAK", "category": "web", "status": "online",
     "ping_rtt": "64", "ttl": 64, "ports": "80, 22, 445, 1883", "sources": "103, 56",
     "notes": "HTTP:80, SSH:22, SMB:445, MQTT:1883.",
     "detail_type": "web", "detail_hint": "http://192.168.1.153"},
    {"ip": "196", "name": "PTZ-камера EYEPLUS/Ginatex", "mac": "BC:2B:02:7C:7F:F0",
     "oui": "China Dragon", "category": "camera", "status": "warning",
     "ping_rtt": "1-3 мс / 63-81 мс (с .56); 100% loss (с .103)", "ttl": 64,
     "ports": "80, 554", "sources": "ARP.56",
     "notes": "HTTP:80, RTSP:554. Wi-Fi камера, через mesh .50 недоступна.",
     "detail_type": "camera", "detail_hint": "http://192.168.1.196"},
    {"ip": "219", "name": "TCL TV", "mac": "38:26:56:D1:AD:5F",
     "oui": "TCL King", "category": "tv", "status": "online",
     "ping_rtt": "64", "ttl": 64, "ports": "8009", "sources": "103, 56",
     "notes": "HTTP:8009. Второй IP, тот же MAC что .128.",
     "detail_type": "tv", "detail_hint": "http://192.168.1.219:8009"},
]

OFFLINE_NOTES = "Отсутствуют в сети: .42 (HA #2), .60 (Sercomm), .68 (камера), .76 (Ростелеком), .80/.92/.93/.94 (RadMonitor), .96 (Mercusys), .91/.186 (NAS), .220 (Sonoff), .49 (камера #1)."

# Сканер 111.html: hostname и производитель по IP
SCANNER_DATA = {
    "192.168.1.1":   {"hostname": "Jeton_AX3000_Core.lan", "vendor": ""},
    "192.168.1.10":  {"hostname": "", "vendor": "Sercomm Corporation."},
    "192.168.1.20":  {"hostname": "esp32-F4810C.lan", "vendor": ""},
    "192.168.1.23":  {"hostname": "orange", "vendor": ""},
    "192.168.1.42":  {"hostname": "", "vendor": "Hon Hai Precision Ind. Co.,Ltd."},
    "192.168.1.43":  {"hostname": "", "vendor": ""},
    "192.168.1.49":  {"hostname": "", "vendor": ""},
    "192.168.1.50":  {"hostname": "", "vendor": "Keenetic Limited"},
    "192.168.1.56":  {"hostname": "host.docker.internal", "vendor": ""},
    "192.168.1.58":  {"hostname": "antix", "vendor": "COMPAL INFORMATION (KUNSHAN) CO., LTD."},
    "192.168.1.60":  {"hostname": "", "vendor": "Sercomm Corporation."},
    "192.168.1.76":  {"hostname": "zvuk.local", "vendor": ""},
    "192.168.1.80":  {"hostname": "NOTRBOOK", "vendor": "ASUSTek COMPUTER INC."},
    "192.168.1.91":  {"hostname": "", "vendor": "Hon Hai Precision Ind. Co.,Ltd."},
    "192.168.1.93":  {"hostname": "webbanya3.local", "vendor": "Espressif Inc."},
    "192.168.1.94":  {"hostname": "esp01-relay.local", "vendor": ""},
    "192.168.1.97":  {"hostname": "", "vendor": ""},
    "192.168.1.103": {"hostname": "debian.lan", "vendor": "AzureWave Technology Inc."},
    "192.168.1.104": {"hostname": "", "vendor": ""},
    "192.168.1.105": {"hostname": "", "vendor": "HUAWEI TECHNOLOGIES CO.,LTD"},
    "192.168.1.106": {"hostname": "", "vendor": ""},
    "192.168.1.109": {"hostname": "", "vendor": ""},
    "192.168.1.111": {"hostname": "Alenushka", "vendor": "ASUSTek COMPUTER INC."},
    "192.168.1.115": {"hostname": "", "vendor": ""},
    "192.168.1.125": {"hostname": "", "vendor": ""},
    "192.168.1.142": {"hostname": "xiaomi_wifi", "vendor": "Xiaomi Communications Co Ltd"},
    "192.168.1.153": {"hostname": "", "vendor": ""},
    "192.168.1.161": {"hostname": "", "vendor": ""},
    "192.168.1.195": {"hostname": "", "vendor": "ASUSTek COMPUTER INC."},
    "192.168.1.196": {"hostname": "", "vendor": ""},
    "192.168.1.219": {"hostname": "", "vendor": "TCL"},
    "192.168.1.220": {"hostname": "", "vendor": ""},
}

DEVICE_SERVICES = {
    "192.168.1.1": [
        {"name": "Keenetic Web UI", "type": "http", "port": 80, "url": "http://192.168.1.1",
         "desc": "Веб-интерфейс роутера KeeneticOS"},
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.1",
         "desc": "Командный доступ к роутеру"},
        {"name": "DNS", "type": "dns", "port": 53, "url": "192.168.1.1:53",
         "desc": "DNS-сервер сети"},
    ],
    "192.168.1.20": [
        {"name": "ESP32 Web", "type": "http", "port": 80, "url": "http://192.168.1.20",
         "desc": "Веб-интерфейс диммера ESP32"},
    ],
    "192.168.1.23": [
        {"name": "MQTT Broker", "type": "mqtt", "port": 1883, "url": "mqtt://192.168.1.23:1883",
         "desc": "MQTT брокер"},
        {"name": "Web UI", "type": "http", "port": 80, "url": "http://192.168.1.23",
         "desc": "Веб-интерфейс"},
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.23",
         "desc": "SSH доступ"},
        {"name": "SMB", "type": "smb", "port": 445, "url": "\\\\192.168.1.23",
         "desc": "Сетевые папки"},
    ],
    "192.168.1.50": [
        {"name": "Keenetic Mesh Web", "type": "http", "port": 80, "url": "http://192.168.1.50",
         "desc": "Веб-панель mesh-узла Keenetic"},
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.50",
         "desc": "SSH доступ"},
        {"name": "HTTPS", "type": "http", "port": 443, "url": "https://192.168.1.50",
         "desc": "Безопасный веб-интерфейс"},
    ],
    "192.168.1.56": [
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.56",
         "desc": "Командный доступ к машине 56"},
        {"name": "SMB", "type": "smb", "port": 445, "url": "\\\\192.168.1.56",
         "desc": "Сетевые папки"},
        {"name": "RTSP", "type": "rtsp", "port": 554, "url": "rtsp://192.168.1.56:554",
         "desc": "Видеопоток RTSP"},
        {"name": "RDP", "type": "rdp", "port": 3389, "url": "rdp://192.168.1.56",
         "desc": "Удалённый рабочий стол"},
        {"name": "PostgreSQL", "type": "postgres", "port": 5432, "url": "postgres://192.168.1.56:5432",
         "desc": "База данных PostgreSQL"},
    ],
    "192.168.1.58": [
        {"name": "Home Assistant #3", "type": "web", "port": 8123, "url": "http://192.168.1.58:8123",
         "desc": "Home Assistant контейнер #3"},
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.58",
         "desc": "SSH доступ"},
        {"name": "SMB", "type": "smb", "port": 445, "url": "\\\\192.168.1.58",
         "desc": "Сетевые папки"},
    ],
    "192.168.1.76": [
        {"name": "Радио \"Звук\"", "type": "http", "port": 80, "url": "http://192.168.1.76",
         "desc": "Управление интернет-радио (mDNS: zvuk.local, сейчас офлайн)"},
    ],
    "192.168.1.103": [
        {"name": "Home Assistant #1", "type": "web", "port": 8123, "url": "http://192.168.1.103:8123",
         "desc": "Home Assistant контейнер #1"},
        {"name": "Camera-web", "type": "web", "port": 8580, "url": "http://192.168.1.103:8580",
         "desc": "Веб-камера"},
        {"name": "MQTT", "type": "mqtt", "port": 1883, "url": "mqtt://192.168.1.103:1883",
         "desc": "MQTT брокер"},
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.103",
         "desc": "Командный доступ к машине 103"},
        {"name": "SMB", "type": "smb", "port": 445, "url": "\\\\192.168.1.103",
         "desc": "Сетевые папки"},
    ],
    "192.168.1.128": [
        {"name": "TCL TV (Web)", "type": "http", "port": 80, "url": "http://192.168.1.128",
         "desc": "Веб-интерфейс TCL TV (второй IP того же устройства, сейчас офлайн)"},
    ],
    "192.168.1.142": [
        {"name": "Xiaomi (ICMP)", "type": "custom", "port": 0, "url": "192.168.1.142",
         "desc": "Устройство отвечает на пинг, открытые порты не проверялись"},
    ],
    "192.168.1.150": [
        {"name": "Oppo (телефон)", "type": "custom", "port": 0, "url": "192.168.1.150",
         "desc": "Мобильное устройство, сервисы не обнаружены"},
    ],
    "192.168.1.153": [
        {"name": "nginx Web", "type": "http", "port": 80, "url": "http://192.168.1.153",
         "desc": "Веб-сервер nginx"},
        {"name": "SSH", "type": "ssh", "port": 22, "url": "ssh://192.168.1.153",
         "desc": "Командный доступ"},
        {"name": "SMB", "type": "smb", "port": 445, "url": "\\\\192.168.1.153",
         "desc": "Сетевые папки"},
        {"name": "MQTT", "type": "mqtt", "port": 1883, "url": "mqtt://192.168.1.153:1883",
         "desc": "MQTT брокер"},
    ],
    "192.168.1.196": [
        {"name": "PTZ-камера HTTP", "type": "http", "port": 80, "url": "http://192.168.1.196",
         "desc": "Веб-интерфейс камеры EYEPLUS/Ginatex"},
        {"name": "RTSP", "type": "rtsp", "port": 554, "url": "rtsp://192.168.1.196:554",
         "desc": "Видеопоток RTSP камеры"},
    ],
    "192.168.1.219": [
        {"name": "TCL TV (Web)", "type": "http", "port": 8009, "url": "http://192.168.1.219:8009",
         "desc": "Веб-интерфейс TCL TV (второй IP, тот же MAC что .128)"},
    ],
}

# ---------- Тип подключения устройства ----------
# wired — Ethernet, wifi — Wi-Fi
DEVICE_CONNECTION_TYPE = {
    "192.168.1.1": "wired",
    "192.168.1.20": "wifi",
    "192.168.1.23": "wired",
    "192.168.1.50": "wired",
    "192.168.1.56": "wired",
    "192.168.1.58": "wired",
    "192.168.1.76": "wifi",
    "192.168.1.103": "wifi",
    "192.168.1.128": "wifi",
    "192.168.1.142": "wifi",
    "192.168.1.150": "wifi",
    "192.168.1.153": "wired",
    "192.168.1.196": "wifi",
    "192.168.1.219": "wired",
}

# ---------- Соединения между устройствами (топология) ----------
# from -> kto, to -> komu, type — wired/wifi
CONNECTIONS = [
    {"from": "192.168.1.1", "to": "192.168.1.50", "type": "wired"},
    {"from": "192.168.1.1", "to": "192.168.1.56", "type": "wired"},
    {"from": "192.168.1.1", "to": "192.168.1.23", "type": "wired"},
    {"from": "192.168.1.1", "to": "192.168.1.20", "type": "wifi"},
    {"from": "192.168.1.1", "to": "192.168.1.76", "type": "wifi"},
    {"from": "192.168.1.50", "to": "192.168.1.103", "type": "wifi"},
    {"from": "192.168.1.50", "to": "192.168.1.196", "type": "wifi"},
    {"from": "192.168.1.56", "to": "192.168.1.58", "type": "wired"},
    {"from": "192.168.1.56", "to": "192.168.1.153", "type": "wired"},
    {"from": "192.168.1.56", "to": "192.168.1.219", "type": "wired"},
    {"from": "192.168.1.56", "to": "192.168.1.128", "type": "wifi"},
    {"from": "192.168.1.56", "to": "192.168.1.142", "type": "wifi"},
    {"from": "192.168.1.103", "to": "192.168.1.150", "type": "wifi"},
    {"from": "192.168.1.1", "to": "192.168.1.153", "type": "wired"},
]


ORIGINAL_NET_MAP_NOTE = (
    'Снято 15.10.2026 20:20 при сканировании .103 (Wi-Fi) + .56 (Ethernet). '
    'Метод: ICMP-sweep /24 + ARP (обе стороны) + TCP-скан + ping(TTL) + HTTP-пробы + OUI.'
)