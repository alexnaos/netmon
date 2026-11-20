import socket
import re
import xml.etree.ElementTree as ET
import requests

def discover_upnp_devices():
    """Отправляет SSDP запрос для поиска UPnP устройств в локальной сети."""
    ssdp_request = (
        'M-SEARCH * HTTP/1.1\r\n'
        'HOST: 239.255.255.250:1900\r\n'
        'MAN: "ssdp:discover"\r\n'
        'MX: 2\r\n'
        'ST: upnp:rootdevice\r\n'
        '\r\n'
    )
    
    # Создаем UDP сокет с таймаутом
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(3.0)
    
    # Разрешаем отправку широковещательных пакетов
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        sock.sendto(ssdp_request.encode('utf-8'), ('239.255.255.250', 1900))
    except Exception as e:
        print(f"Ошибка отправки запроса: {e}")
        return []

    locations = set()
    while True:
        try:
            data, _ = sock.recvfrom(65507)
            response = data.decode('utf-8', errors='ignore')
            # Ищем ссылку на XML-описание устройства
            match = re.search(r'LOCATION:\s*(http://\S+)', response, re.IGNORECASE)
            if match:
                locations.add(match.group(1))
        except socket.timeout:
            break
            
    return list(locations)

def get_device_info(xml_url):
    """Скачивает XML-описание и извлекает модель и производителя."""
    try:
        res = requests.get(xml_url, timeout=2)
        if res.status_code != 200:
            return None
        
        # Парсим XML структуру устройства
        root = ET.fromstring(res.text)
        # Очищаем пространство имен (namespaces) для упрощения поиска
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
                
        device = root.find('.//device')
        if device is not None:
            friendly_name = device.findtext('friendlyName', 'Неизвестно')
            manufacturer = device.findtext('manufacturer', 'Неизвестно')
            model_name = device.findtext('modelName', 'Неизвестно')
            model_number = device.findtext('modelNumber', '')
            
            # Извлекаем IP-адрес из URL
            ip_match = re.search(r'https?://([^:/]+)', xml_url)
            ip_address = ip_match.group(1) if ip_match else "Неизвестно"
            
            return {
                'ip': ip_address,
                'manufacturer': manufacturer,
                'model': f"{model_name} {model_number}".strip(),
                'name': friendly_name
            }
    except Exception:
        return None

def main():
    print("🔎 Сканирую сеть на наличие роутеров и сетевых устройств (UPnP)...")
    urls = discover_upnp_devices()
    
    if not urls:
        print("❌ Устройства UPnP не найдены. Проверьте, что вы в одной сети с ними.")
        return

    found_routers = {}
    for url in urls:
        info = get_device_info(url)
        # Фильтруем только уникальные IP, чтобы убрать дубли от одного устройства
        if info and info['ip'] not in found_routers:
            # Отсекаем медиа-серверы, оставляя потенциальные шлюзы/точки доступа
            if any(k in info['manufacturer'].lower() or k in info['model'].lower() 
                   for k in ['keenetic', 'asus', 'tp-link', 'd-link', 'huawei', 'xiaomi', 'router', 'gateway', 'zyxel']):
                found_routers[info['ip']] = info

    print("\n Найдено сетевое оборудование:")
    print("-" * 60)
    for ip, data in found_routers.items():
        print(f"📍 IP-адрес:      {ip}")
        print(f"   Производитель: {data['manufacturer']}")
        print(f"   Модель:        {data['model']}")
        print(f"   Имя в сети:    {data['name']}")
        print("-" * 60)

if __name__ == '__main__':
    main()
