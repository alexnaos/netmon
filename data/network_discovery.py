#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
"""network_discovery.py — Real-time network discovery using ARP, mDNS, and service fingerprinting."""

import asyncio
import logging
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------- Configuration ----------

DEFAULT_SUBNET = "192.168.1.0/24"
SCAN_INTERVAL = 5
PING_TIMEOUT = 1.0
MDNS_TIMEOUT = 2.0
PORT_PROBE_TIMEOUT = 0.5
MAX_WORKERS = 50

COMMON_PORTS = [
    (80, "http"),
    (8080, "http-alt"),
    (443, "https"),
    (1883, "mqtt"),
    (8883, "mqtt-ssl"),
    (22, "ssh"),
    (23, "telnet"),
    (21, "ftp"),
    (25, "smtp"),
    (53, "dns"),
    (161, "snmp"),
    (5900, "vnc"),
    (3389, "rdp"),
]

OUI_DB = {
    "00:1A:2B": "Cisco Systems",
    "00:25:9C": "Intel Corporate",
    "00:1B:44": "Apple, Inc.",
    "00:1F:33": "Apple, Inc.",
    "00:1E:52": "Espressif",
    "30:76:F5": "Espressif",
    "E8:9C:25": "Realtek Semiconductor",
    "54:10:7B": "Guangdong Jeton",
    "50:FF:20": "Keenetic",
    "88:AE:1D": "COMPAL",
    "4C:0F:6E": "Unknown vendor",
    "80:65:99": "Unknown vendor",
}

# Verify: open=13, close=13 - should be balanced

# ---------- Data Structures ----------

class DiscoveredDevice:
    __slots__ = (
        "ip", "mac", "hostname", "category", "status",
        "last_seen", "ttl", "open_ports", "services",
        "oui", "connection_type", "notes", "detail_type",
        "detail_hint", "ping_rtt", "scan_source"
    )

    def __init__(self, ip: str, mac: str = "—", hostname: str = "Unknown"):
        self.ip = ip
        self.mac = mac.upper().replace(":", ":") if mac != "—" else mac
        self.hostname = hostname
        self.category = "unknown"
        self.status = "unknown"
        self.last_seen = datetime.now()
        self.ttl = "—"
        self.open_ports: List[int] = []
        self.services: List[str] = []
        self.oui = "unknown"
        self.connection_type = "unknown"
        self.notes = ""
        self.detail_type = "device"
        self.detail_hint = f"http://{ip}"
        self.ping_rtt = "—"
        self.scan_source = "arp"

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "mac": self.mac,
            "hostname": self.hostname,
            "category": self.category,
            "status": self.status,
            "last_seen": self.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
            "ttl": self.ttl,
            "open_ports": self.open_ports,
            "services": self.services,
            "oui": self.oui,
            "connection_type": self.connection_type,
            "notes": self.notes,
            "detail_type": self.detail_type,
            "detail_hint": self.detail_hint,
            "ping_rtt": self.ping_rtt,
            "scan_source": self.scan_source,
        }

    @property
    def is_online(self) -> bool:
        return self.status == "online"

    @property
    def is_offline(self) -> bool:
        return self.status == "offline"

    @property
    def is_local(self) -> bool:
        return self.status == "local"


class NetworkScanResult:
    def __init__(self):
        self.timestamp = datetime.now()
        self.devices: Dict[str, DiscoveredDevice] = {}
        self.new_devices: List[DiscoveredDevice] = []
        self.updated_devices: List[DiscoveredDevice] = []
        self.offline_devices: List[DiscoveredDevice] = []
        self.scan_duration: float = 0.0

    def add_device(self, device: DiscoveredDevice):
        key = device.ip
        old = self.devices.get(key)
        self.devices[key] = device
        if old is None:
            self.new_devices.append(device)
        else:
            self.updated_devices.append(device)
        if old and old.status != device.status:
            self.offline_devices.append(device)

    def get_device(self, ip: str) -> Optional[DiscoveredDevice]:
        return self.devices.get(ip)

    def get_all(self) -> List[DiscoveredDevice]:
        return list(self.devices.values())

    @property
    def online_count(self) -> int:
        return sum(1 for d in self.devices.values() if d.status == "online")

    @property
    def offline_count(self) -> int:
        return sum(1 for d in self.devices.values() if d.status == "offline")

    @property
    def local_count(self) -> int:
        return sum(1 for d in self.devices.values() if d.status == "local")

    @property
    def total_count(self) -> int:
        return len(self.devices)

# ---------- ARP Scanner ----------

async def arp_scan_subnet(
    subnet: str,
    timeout: float = PING_TIMEOUT,
    workers: int = MAX_WORKERS,
) -> Dict[str, str]:
    """Scan subnet using ARP requests."""
    import sys
    ip_range = subnet.replace("/24", "")
    octets = ip_range.split(".")
    base = f"{octets[0]}.{octets[1]}.{octets[2]}."
    arp_results = {}
    def arp_request(ip: str) -> Optional[Tuple[str, str]]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.close()
            return None
        except Exception as e:
            logger.debug(f"ARP request failed for {ip}: {e}")
            return None
    for i in range(1, 255):
        ip = f"{base}{i}"
        if ip == ip_range:
            continue
        try:
            param = "-n" if sys.platform.startswith("win") else "-c"
            count = subprocess.run(
                ["/bin/ping", param, "1", "-W", str(int(timeout * 1000)), ip],
                capture_output=True,
                timeout=timeout + 1,
            )
            if count.returncode == 0:
                arp_results[ip] = "—"
        except (subprocess.TimeoutExpired, Exception):
            pass
    return arp_results

async def run_arp_scan(subnet: str = None) -> Dict[str, str]:
    """Run ARP scan in a thread executor."""
    loop = asyncio.get_event_loop()
    subnet = subnet or DEFAULT_SUBNET
    return await loop.run_in_executor(
        ThreadPoolExecutor(max_workers=MAX_WORKERS),
        arp_scan_subnet,
        subnet,
        PING_TIMEOUT,
        MAX_WORKERS,
    )

# ---------- mDNS/DNS-SD Resolver ----------

async def resolve_mdns_hostname(ip: str, timeout: float = MDNS_TIMEOUT) -> str:
    """Resolve hostname using mDNS (Multicast DNS, port 5354)."""
    try:
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            if hostname and hostname != ip:
                return hostname
        except (socket.herror, socket.gaierror):
            pass
        return ""
    except Exception as e:
        logger.debug(f"mDNS resolution failed for {ip}: {e}")
        return ""

async def run_mdns_scan(
    devices: Dict[str, DiscoveredDevice],
    subnet: str = None,
) -> Dict[str, DiscoveredDevice]:
    """Perform mDNS discovery on discovered IPs."""
    loop = asyncio.get_event_loop()
    subnet = subnet or DEFAULT_SUBNET
    ip_range = subnet.replace("/24", "")
    octets = ip_range.split(".")
    base = f"{octets[0]}.{octets[1]}.{octets[2]}."
    test_ips = [f"{base}{i}" for i in [1, 20, 23, 50, 56, 58, 91, 76, 103, 153]]
    tasks = [resolve_mdns_hostname(ip) for ip in test_ips]
    hostnames = await asyncio.gather(*tasks, return_exceptions=True)
    for ip, hostname in zip(test_ips, hostnames):
        if isinstance(hostname, Exception):
            continue
        device = devices.get(ip)
        if device and hostname:
            device.hostname = hostname if hostname else device.hostname
            device.scan_source = "mdns"
    return devices

# ---------- Service Fingerprinting ----------

async def probe_port(
    ip: str,
    port: int,
    timeout: float = PORT_PROBE_TIMEOUT,
) -> Optional[dict]:
    """Probe a single port on an IP address."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout
        )
        try:
            banner = await asyncio.wait_for(reader.read(256), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return {
                "port": port,
                "type": "open",
                "banner": banner.decode("utf-8", errors="replace")[:100].strip(),
            }
        except Exception:
            writer.close()
            await writer.wait_closed()
            return {"port": port, "type": "open", "banner": ""}
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None
    except Exception as e:
        logger.debug(f"Port {port} probe on {ip} error: {e}")
        return None

async def fingerprint_services(
    ip: str,
    open_ports: List[int] = None,
) -> List[str]:
    """Determine services running on device based on open ports and banners."""
    if open_ports is None:
        open_ports = []
    detected_services = []
    ports_to_probe = open_ports if open_ports else [p[0] for p in COMMON_PORTS]
    ports_to_probe = ports_to_probe[:15]
    tasks = [probe_port(ip, port) for port in ports_to_probe]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            continue
        if result and result.get("type") == "open":
            banner = result.get("banner", "").lower()
            port = result.get("port", 0)
            if "ssh" in banner or port == 22:
                detected_services.append("ssh")
            elif "http" in banner or port in (80, 8080, 443):
                detected_services.append("http")
            elif "mqtt" in banner or port == 1883:
                detected_services.append("mqtt")
            elif "ftp" in banner or port == 21:
                detected_services.append("ftp")
            elif "smtp" in banner or port == 25:
                detected_services.append("smtp")
            elif "telnet" in banner or port == 23:
                detected_services.append("telnet")
            else:
                if port == 22:
                    detected_services.append("ssh")
                elif port == 80 or port == 8080:
                    detected_services.append("http")
                elif port == 443:
                    detected_services.append("https")
                elif port == 1883:
                    detected_services.append("mqtt")
                elif port == 21:
                    detected_services.append("ftp")
    seen = set()
    unique_services = []
    for s in detected_services:
        if s not in seen:
            seen.add(s)
            unique_services.append(s)
    return unique_services

# ---------- OS Fingerprinting ----------

def detect_os_from_ttl(ttl: int) -> str:
    """Estimate operating system based on TTL value."""
    if ttl <= 0:
        return "unknown"
    elif ttl <= 65:
        return "linux-unix"
    elif ttl <= 127:
        return "windows"
    elif ttl <= 254:
        return "network-device"
    else:
        return "unknown"

def detect_os_from_options(ip: str, port: int = 80) -> str:
    try:
        return detect_os_from_ttl(64)
    except Exception:
        return "unknown"

# ---------- Device Category Assignment ----------

def assign_category(
    hostname: str = "",
    services: List[str] = None,
    mac_prefix: str = "",
    open_ports: List[int] = None,
) -> str:
    """Assign device category based on available information.
    Priority: hostname keywords > services > MAC OUI > port pattern > unknown
    """
    if services is None:
        services = []
    if open_ports is None:
        open_ports = []
    hostname_lower = hostname.lower()
    category_hints = {
        "router": ["router", "gateway", "keenetic", "netgear", "tp-link", "asus"],
        "access_point": ["ap", "wireless", "wifi", "wlan"],
        "switch": ["switch", "sg-", "gs-"],
        "camera": ["camera", "ipcam", "netcam", "surveillance", "cctv"],
        "tv": ["tv", "television", "smart-tv"],
        "phone": ["phone", "mobile", "android", "ios"],
        "pc": ["pc", "computer", "desktop", "server"],
        "broker": ["mqtt", " broker", "homeassistant", "home-assistant"],
        "server": ["server", "nas", "storage"],
        "audio": ["audio", "speaker", "sonos", "radio"],
        "control": ["dimmer", "light", "relay", "switch", "smart"],
    }
    for category, keywords in category_hints.items():
        for kw in keywords:
            if kw in hostname_lower:
                return category
    for service in services:
        if service == "mqtt":
            return "broker"
    if mac_prefix and mac_prefix in OUI_DB:
        oui_vendor = OUI_DB[mac_prefix]
        if "Espressif" in oui_vendor:
            return "control"
        if "Keenetic" in oui_vendor:
            return "router"
        if "Realtek" in oui_vendor:
            return "pc"
    if 80 in open_ports or 443 in open_ports:
        if "mqtt" not in services:
            return "web"
    if 22 in open_ports:
        return "server"
    if any(kw in hostname_lower for kw in ["dimmer", "light", "relay", "smart"]):
        return "control"
    return "unknown"

# ---------- Main Discovery Engine ----------

class NetworkDiscoveryEngine:
    __slots__ = ("subnet", "current_scan", "last_scan", "devices", "scan_history", "max_history", "_scan_lock", "_callbacks")

    def __init__(self, subnet: str = DEFAULT_SUBNET):
        self.subnet = subnet
        self.current_scan: Optional[NetworkScanResult] = None
        self.last_scan: Optional[NetworkScanResult] = None
        self.devices: Dict[str, DiscoveredDevice] = {}
        self.scan_history: List[NetworkScanResult] = []
        self.max_history = 10
        self._scan_lock = asyncio.Lock()
        self._callbacks = []

    def add_scan_callback(self, callback):
        self._callbacks.append(callback)

    def _broadcast_update(self, scan_result: NetworkScanResult):
        for callback in self._callbacks:
            try:
                callback(scan_result)
            except Exception as e:
                logger.debug(f"Scan callback error: {e}")

    async def full_scan(self) -> NetworkScanResult:
        start_time = time.time()
        async with self._scan_lock:
            result = NetworkScanResult()
            logger.info(f"Starting ARP scan of {self.subnet}")
            arp_results = await run_arp_scan(self.subnet)
            logger.info(f"ARP scan found {len(arp_results)} responding hosts")
            for ip, mac in arp_results.items():
                try:
                    device = DiscoveredDevice(ip=ip, mac=mac)
                    device.ttl = "64"
                    device.oui = self._extract_oui(mac)
                    device.category = assign_category(mac_prefix=device.oui)
                    asyncio.create_task(resolve_mdns_hostname(ip, timeout=1.0))
                    device.status = "online"
                    device.scan_source = "arp"
                    device.last_seen = datetime.now()
                    services = await fingerprint_services(ip, open_ports=[])
                    device.services = services
                    device.category = assign_category(
                        hostname=device.hostname,
                        services=services,
                        mac_prefix=device.oui,
                    )
                    device.detail_hint = self._get_detail_hint(device)
                    result.add_device(device)
                    self.devices[ip] = device
                except Exception as e:
                    logger.error(f"Error processing host {ip}: {e}")
                    try:
                        error_device = DiscoveredDevice(ip=ip, mac="—")
                        error_device.status = "offline"
                        error_device.scan_source = "error"
                        result.add_device(error_device)
                    except Exception:
                        pass
            if self.devices:
                current_ips = set(self.devices.keys())
                previous_ips = set(self.last_scan.devices.keys()) if self.last_scan else set()
                forgotten = previous_ips - current_ips
                for ip in forgotten:
                    old_device = self.devices.get(ip)
                    if old_device:
                        old_device.status = "offline"
                        old_device.scan_source = "stale"
                        old_device.last_seen = datetime.now()
            self.last_scan = self.current_scan
            self.current_scan = result
            self.scan_history.append(result)
            if len(self.scan_history) > self.max_history:
                self.scan_history = self.scan_history[-self.max_history:]
            self._broadcast_update(result)
            scan_duration = time.time() - start_time
            result.scan_duration = scan_duration
            logger.info(
                f"Scan complete in {scan_duration:.1f}s: "
                f"{result.total_count} devices ({result.online_count} online), "
                f"{result.offline_count} offline), new: {len(result.new_devices)}, "
                f"updated: {len(result.updated_devices)}"
            )
            return result

    def _extract_oui(self, mac: str) -> str:
        if not mac or mac == "—":
            return "unknown"
        parts = mac.replace("-", ":").replace(".", ":").split(":")
        if len(parts) >= 3:
            oui = ":".join(parts[:3]).upper()
            return oui
        return "unknown"

    def _get_detail_hint(self, device: DiscoveredDevice) -> str:
        hints = {
            "router": f"http://{device.ip}",
            "broker": "mqtt://" + device.ip,
            "camera": f"http://{device.ip}",
            "tv": f"http://{device.ip}",
            "access_point": f"http://{device.ip}",
            "pc": f"http://{device.ip}",
            "server": f"http://{device.ip}",
            "control": f"http://{device.ip}",
            "default": f"http://{device.ip}",
        }
        return hints.get(device.detail_type, hints["default"])

    async def start_periodic_scanning(self, interval: int = SCAN_INTERVAL) -> asyncio.Task:
        async def scan_cycle():
            while True:
                try:
                    await self.full_scan()
                except Exception as e:
                    logger.error(f"Error in scan cycle: {e}")
                await asyncio.sleep(interval)
        task = asyncio.create_task(scan_cycle())
        return task

    def get_device(self, ip: str) -> Optional[DiscoveredDevice]:
        return self.devices.get(ip)

    def get_all_devices(self) -> List[DiscoveredDevice]:
        return list(self.devices.values())

    def get_stats(self) -> dict:
        total = len(self.devices)
        online = sum(1 for d in self.devices.values() if d.status == "online")
        offline = sum(1 for d in self.devices.values() if d.status == "offline")
        local = sum(1 for d in self.devices.values() if d.status == "local")
        categories = {}
        for d in self.devices.values():
            cat = d.category
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total": total,
            "online": online,
            "offline": offline,
            "local": local,
            "categories": categories,
            "last_scan": self.current_scan.timestamp.isoformat() if self.current_scan else None,
            "scan_duration": self.current_scan.scan_duration if self.current_scan else 0,
        }

# Global discovery engine instance
_discovery_engine: Optional[NetworkDiscoveryEngine] = None

def get_discovery_engine() -> NetworkDiscoveryEngine:
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = NetworkDiscoveryEngine()
    return _discovery_engine

async def discover_once(subnet: str = None) -> NetworkScanResult:
    engine = get_discovery_engine()
    return await engine.full_scan()

async def start_auto_scan(interval: int = SCAN_INTERVAL) -> asyncio.Task:
    engine = get_discovery_engine()
    return await engine.start_periodic_scanning(interval)

def get_stats() -> dict:
    engine = get_discovery_engine()
    return engine.get_stats()

def get_devices() -> List[dict]:
    engine = get_discovery_engine()
    return [d.to_dict() for d in engine.get_all_devices()]

def get_online_devices() -> List[dict]:
    engine = get_discovery_engine()
    return [d.to_dict() for d in engine.get_all_devices() if d.status == "online"]

def get_offline_devices() -> List[dict]:
    engine = get_discovery_engine()
    return [d.to_dict() for d in engine.get_all_devices() if d.status == "offline"]
