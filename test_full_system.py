#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полный тест системы Netmon на машине 192.168.1.103
"""

import os
import sys
import json
import subprocess
import time
import requests
from datetime import datetime

def print_step(step, message):
    """Вывод шага с таймстампом."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] [{step}] {message}")

def test_1_python_environment():
    """Тест 1: Проверка окружения Python."""
    print_step("1", "Проверка окружения Python")
    
    try:
        result = subprocess.run([sys.executable, "--version"], 
                              capture_output=True, text=True)
        python_version = result.stdout.strip()
        print(f"  Python: {python_version}")
        return True
    except Exception as e:
        print(f"  Ошибка: {e}")
        return False

def test_2_dependencies():
    """Тест 2: Проверка зависимостей."""
    print_step("2", "Проверка зависимостей")
    
    required = ["flask", "requests"]
    missing = []
    
    for dep in required:
        try:
            subprocess.run([sys.executable, "-c", f"import {dep}; print('OK')"], 
                          capture_output=True, text=True)
            print(f"  {dep}: OK")
        except Exception:
            missing.append(dep)
    
    if missing:
        print(f"  Отсутствуют: {missing}")
        return False
    return True

def test_3_config_files():
    """Тест 3: Проверка конфигурационных файлов."""
    print_step("3", "Проверка файлов конфигурации")
    
    required_files = [
        ("app/app.py", "Основное приложение"),
        ("data/network_data.py", "База данных устройств"),
        (".env", "Конфигурация окружения"),
        ("requirements.txt", "Зависимости"),
    ]
    
    all_exist = True
    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"  {description}: OK")
        else:
            print(f"  {description}: НЕ НАЙДЕН ({file_path})")
            all_exist = False
    
    return all_exist

def test_4_current_app_running():
    """Тест 4: Проверка запущенного приложения."""
    print_step("4", "Проверка запущенного приложения")
    
    try:
        response = requests.get("http://192.168.1.103:5000/api/network/info", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Приложение запущено: OK")
            print(f"  Устройств в сети: {data.get('total', 0)}")
            print(f"  Онлайн: {data.get('alive', 0)}")
            print(f"  Офлайн: {data.get('offline', 0)}")
            return True
        else:
            print(f"  Ошибка HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  Приложение не отвечает: {e}")
        return False

def test_5_web_interface():
    """Тест 5: Проверка веб-интерфейса."""
    print_step("5", "Проверка веб-интерфейса")
    
    try:
        response = requests.get("http://192.168.1.103:5000/network", timeout=5)
        
        if response.status_code == 200:
            print(f"  Веб-интерфейс: OK")
            return True
        else:
            print(f"  Ошибка HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  Веб-интерфейс недоступен: {e}")
        return False

def test_6_scan_api():
    """Тест 6: Проверка API сканирования."""
    print_step("6", "Проверка API сканирования")
    
    try:
        # Проверка статуса сканирования
        response = requests.get("http://192.168.1.103:5000/api/network/scan", timeout=5)
        
        if response.status_code == 200:
            print(f"  API сканирования: OK")
            return True
        else:
            print(f"  Ошибка HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  API недоступен: {e}")
        return False

def test_7_manage_scripts():
    """Тест 7: Проверка скриптов управления."""
    print_step("7", "Проверка скриптов управления")
    
    scripts_to_test = [
        ("manage_service.py", "status", "Скрипт управления"),
        ("data/network_discovery.py", "", "CLI сканер"),
    ]
    
    all_ok = True
    for script, arg, description in scripts_to_test:
        if not os.path.exists(script):
            print(f"  {description}: НЕ НАЙДЕН ({script})")
            all_ok = False
            continue
        
        try:
            if arg:
                result = subprocess.run([sys.executable, script, arg], 
                                      capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run([sys.executable, script], 
                                      capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"  {description}: OK")
            else:
                print(f"  {description}: Ошибка (код: {result.returncode})")
                all_ok = False
                
        except Exception as e:
            print(f"  {description}: Исключение ({e})")
            all_ok = False
    
    return all_ok

def test_8_data_integrity():
    """Тест 8: Проверка целостности данных."""
    print_step("8", "Проверка целостности данных")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from data import network_data as nd
        
        # Проверка устройств
        print(f"  Устройств в базе: {len(nd.DEVICES)}")
        
        # Проверка соединений
        print(f"  Соединений в топологии: {len(nd.CONNECTIONS)}")
        
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
            print(f"  Дублирующиеся IP: {duplicates}")
            return False
        
        print(f"  Все IP уникальны: OK")
        return True
        
    except Exception as e:
        print(f"  Ошибка проверки данных: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("=" * 70)
    print("ПОЛНЫЙ ТЕСТ СИСТЕМЫ NETMON")
    print(f"Машина: 192.168.1.103:5000")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("Окружение Python", test_1_python_environment),
        ("Зависимости", test_2_dependencies),
        ("Файлы конфигурации", test_3_config_files),
        ("Запущенное приложение", test_4_current_app_running),
        ("Веб-интерфейс", test_5_web_interface),
        ("API сканирования", test_6_scan_api),
        ("Скрипты управления", test_7_manage_scripts),
        ("Целостность данных", test_8_data_integrity),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\nОшибка при выполнении теста '{test_name}': {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "ПРОЙДЕНО" if passed else "ПРОВАЛЕНО"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print(f"\nПриложение готово к работе:")
        print(f"  Веб-интерфейс: http://192.168.1.103:5000/network")
        print(f"  API информация: http://192.168.1.103:5000/api/network/info")
        print(f"  Управление: python manage_service.py [start|stop|restart|status|logs]")
    else:
        print("НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("\nРекомендации:")
        print("  1. Проверьте установку Python и зависимостей")
        print("  2. Убедитесь что порт 5000 свободен")
        print("  3. Запустите setup_and_run.bat для автоматической настройки")
    
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nТестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        sys.exit(1)