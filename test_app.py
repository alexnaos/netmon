#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование работы netmon приложения.
"""

import sys
import os
import subprocess
import time
import requests

def test_original_app():
    """Тестирование оригинального приложения."""
    print("Тестирование оригинального приложения...")
    
    # Запуск оригинального приложения в фоне
    proc = subprocess.Popen([sys.executable, "app/app.py"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
    
    time.sleep(3)  # Даем время на запуск
    
    try:
        response = requests.get("http://192.168.1.103:5000/api/network/info", timeout=5)
        print(f"Оригинальное приложение: статус {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Устройств: {data.get('total', 0)}")
            print(f"  Онлайн: {data.get('alive', 0)}")
            print(f"  Офлайн: {data.get('offline', 0)}")
            return True
        else:
            print(f"  Ошибка: {response.text}")
            return False
            
    except Exception as e:
        print(f"  Ошибка подключения: {e}")
        return False
    finally:
        proc.terminate()
        proc.wait()

def test_improved_app():
    """Тестирование улучшенного приложения."""
    print("\nТестирование улучшенного приложения...")
    
    # Запуск улучшенного приложения в фоне
    proc = subprocess.Popen([sys.executable, "app/app_improved.py"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
    
    time.sleep(5)  # Даем больше времени на запуск
    
    try:
        # Проверка health endpoint
        response = requests.get("http://192.168.1.103:5000/api/health", timeout=5)
        print(f"Улучшенное приложение - health: статус {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Статус: {data.get('status', 'unknown')}")
            print(f"  Версия: {data.get('version', 'unknown')}")
        else:
            print(f"  Ошибка health: {response.text}")
        
        # Проверка config endpoint
        response = requests.get("http://192.168.1.103:5000/api/config", timeout=5)
        print(f"Улучшенное приложение - config: статус {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Подсеть: {data.get('subnet', 'unknown')}")
            print(f"  Интервал сканирования: {data.get('scan_interval', 'unknown')} сек")
        else:
            print(f"  Ошибка config: {response.text}")
        
        # Проверка network info
        response = requests.get("http://192.168.1.103:5000/api/network/info", timeout=5)
        print(f"Улучшенное приложение - network info: статус {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Устройств: {data.get('total', 0)}")
            print(f"  Сканирование: {data.get('scanning', False)}")
            return True
        else:
            print(f"  Ошибка network info: {response.text}")
            return False
            
    except Exception as e:
        print(f"  Ошибка подключения: {e}")
        return False
    finally:
        if 'proc' in locals():
            proc.terminate()
            proc.wait()

def test_data_integrity():
    """Проверка целостности данных."""
    print("\nПроверка целостности данных...")
    
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from data import network_data as nd
        
        # Проверка уникальности IP
        ips = set()
        duplicates = []
        
        for device in nd.DEVICES:
            ip = device["ip"]
            if not ip.startswith("192.168.1."):
                ip = "192.168.1." + ip
            
            if ip in ips:
                duplicates.append(ip)
            else:
                ips.add(ip)
        
        if duplicates:
            print(f"  Найдены дублирующиеся IP: {duplicates}")
            return False
        else:
            print(f"  Все IP уникальны ({len(ips)} устройств)")
        
        # Проверка структуры CONNECTIONS
        if not isinstance(nd.CONNECTIONS, list):
            print("  CONNECTIONS не является списком")
            return False
        
        print(f"  Соединений: {len(nd.CONNECTIONS)}")
        
        return True
        
    except Exception as e:
        print(f"  Ошибка при проверке данных: {e}")
        return False

def main():
    """Основная функция."""
    print("=" * 60)
    print("Тестирование сетевого монитора")
    print("=" * 60)
    
    results = []
    
    # Проверка целостности данных
    results.append(("Целостность данных", test_data_integrity()))
    
    # Тестирование оригинального приложения
    results.append(("Оригинальное приложение", test_original_app()))
    
    # Тестирование улучшенного приложения
    results.append(("Улучшенное приложение", test_improved_app()))
    
    print("\n" + "=" * 60)
    print("Результаты тестирования:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ ПРОЙДЕНО" if passed else "❌ ПРОВАЛЕНО"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("Все тесты пройдены успешно!")
    else:
        print("Некоторые тесты не прошли.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)