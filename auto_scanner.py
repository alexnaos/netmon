#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический сканер сети Netmon.
Запускается как сервис и периодически сканирует сеть,
добавляя новые устройства и обновляя статусы в network_data.py.

Запуск:
    python auto_scanner.py          # запуск вручную
    python manage_service.py start   # запуск как сервис

Настройки в .env:
    SCAN_INTERVAL=300               # интервал сканирования (секунды), по умолчанию 300
    PING_TIMEOUT=2                  # таймаут ping в секундах
    MAX_WORKERS=64                  # параллельные потоки
"""

import os
import sys
import time
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Загрузка .env
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value.strip().strip('"').strip("'")

# Импорт сканера
from data.network_discovery import (  # noqa
    SUBNET,
    MAX_WORKERS,
    PING_TIMEOUT,
    scan_network,
    write_data,
    read_data
)

# Конфигурация
SCAN_INTERVAL = int(os.environ.get('SCAN_INTERVAL', '300'))
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '64'))
PING_TIMEOUT = int(os.environ.get('PING_TIMEOUT', '2'))

# Файл с последним сканированием
LAST_RUN_FILE = os.path.join(BASE_DIR, 'app', 'last_scan.json')
PID_FILE = os.path.join(BASE_DIR, 'app', 'auto_scanner.pid')

def log(msg):
    """Логирование."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [AUTOSCAN] {msg}')

def load_last_scan():
    """Загрузка хранилища последнего сканирования."""
    if os.path.exists(LAST_RUN_FILE):
        try:
            with open(LAST_RUN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'devices': {}, 'timestamp': None}

def save_last_scan(data):
    """Сохранение хранилища последнего сканирования."""
    os.makedirs(os.path.dirname(LAST_RUN_FILE), exist_ok=True)
    with open(LAST_RUN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_scan():
    """
    Выполнить сканирование сети и обновить network_data.py.
    Возвращает статистику.
    """
    log(f"Запуск сканирования сети {SUBNET}...")
    
    try:
        # Импортируем функции сканера
        from data.network_discovery import scan_network, write_data, read_data
        
        devices, conns, stats = scan_network(
            subnet=SUBNET,
            max_workers=MAX_WORKERS,
            ping_timeout=PING_TIMEOUT,
            verbose=True
        )
        
        # Загружаем текущие данные
        src, ns = read_data(DATA_FILE)
        
        # Обновляем devices
        ns['DEVICES'] = devices
        
        # Обновляем CONNECTIONS
        ns['CONNECTIONS'] = conns
        
        # Записываем обновлённый файл
        write_data(DATA_FILE, src, devices, conns, ns)
        
        # Сохраняем статистику
        save_last_scan({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'devices_count': len(devices),
            'connections_count': len(conns),
            'stats': stats,
            'subnet': SUBNET,
            'scan_interval': SCAN_INTERVAL
        })
        
        log(f"Готово: {len(devices)} устройств, {len(conns)} связей")
        return stats
        
    except Exception as e:
        log(f"Ошибка сканирования: {e}")
        import traceback
        log(traceback.format_exc())
        return {}

def periodic_scan():
    """
    Бесконечный цикл сканирования с заданным интервалом.
    """
    log("=== Начало автосканирования ===")
    log(f"Интервал сканирования: {SCAN_INTERVAL} сек")
    log(f"Максимум потоков: {MAX_WORKERS}")
    log(f"Таймаут ping: {PING_TIMEOUT} сек")
    log(f"Подсеть: {SUBNET}")
    
    # Выполним первый сканирование сразу
    run_scan()
    
    while True:
        try:
            # Ждём SCAN_INTERVAL секунд
            log(f"Ожидание {SCAN_INTERVAL} сек для следующего сканирования...")
            time.sleep(SCAN_INTERVAL)
            
            # Выполняем сканирование
            log(f"[{datetime.now().strftime('%H:%M:%S')}] Начинаем сканирование...")
            run_scan()
            
        except KeyboardInterrupt:
            log("Остановка автосканирования...")
            break
        except Exception as e:
            log(f"Непредвиденная ошибка: {e}")
            time.sleep(60)  # Ждём минуту перед повтором

def create_pid_file():
    """Создание PID-файла для управления сервисом."""
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, 'w', encoding='utf-8') as f:
        f.write(str(os.getpid()))
    log(f"PID-файл создан: {PID_FILE}")

def remove_pid_file():
    """Удаление PID-файла."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
        log("PID-файл удалён")

def main():
    """Основная функция."""
    create_pid_file()
    
    try:
        periodic_scan()
    finally:
        remove_pid_file()

if __name__ == "__main__":
    main()