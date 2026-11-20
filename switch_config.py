#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для переключения между конфигурациями Netmon.
Позволяет быстро менять настройки для разных сред.
"""

import os
import shutil
import sys

def backup_current_config():
    """Создание резервной копии текущей конфигурации."""
    if os.path.exists('.env'):
        shutil.copy2('.env', '.env.backup')
        print("✅ Текущая конфигурация сохранена в .env.backup")
    else:
        print("⚠️ Текущий .env не найден")

def switch_to_local():
    """Переключение на локальную конфигурацию (127.0.0.1)."""
    backup_current_config()
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write("""# Локальная конфигурация для тестирования
RADMON_HOST=127.0.0.1
RADMON_PORT=5000
SUBNET=192.168.1.0/24
SCAN_INTERVAL=300
MAX_WORKERS=64
PING_TIMEOUT=2
LOG_LEVEL=DEBUG
""")
    
    print("✅ Переключено на локальную конфигурацию (127.0.0.1)")
    print("   Доступно по адресу: http://127.0.0.1:5000/network")

def switch_to_all_interfaces():
    """Переключение на конфигурацию для всех интерфейсов (0.0.0.0)."""
    backup_current_config()
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write("""# Конфигурация для всех сетевых интерфейсов
RADMON_HOST=0.0.0.0
RADMON_PORT=5000
SUBNET=192.168.1.0/24
SCAN_INTERVAL=300
MAX_WORKERS=128
PING_TIMEOUT=2
LOG_LEVEL=INFO
""")
    
    print("✅ Переключено на конфигурацию для всех интерфейсов (0.0.0.0)")
    print("   Доступно по адресам:")
    print("   - http://127.0.0.1:5000/network")
    print("   - http://localhost:5000/network")
    print("   - http://192.168.1.103:5000/network (если доступен)")

def switch_to_original():
    """Переключение на оригинальную конфигурацию (192.168.1.103)."""
    backup_current_config()
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write("""# Оригинальная конфигурация для продакшена
RADMON_HOST=192.168.1.103
RADMON_PORT=5000
SUBNET=192.168.1.0/24
SCAN_INTERVAL=300
MAX_WORKERS=128
PING_TIMEOUT=2
LOG_LEVEL=INFO
""")
    
    print("✅ Переключено на оригинальную конфигурацию (192.168.1.103)")
    print("   Доступно по адресу: http://192.168.1.103:5000/network")

def restore_backup():
    """Восстановление из резервной копии."""
    if os.path.exists('.env.backup'):
        shutil.copy2('.env.backup', '.env')
        print("✅ Конфигурация восстановлена из .env.backup")
    else:
        print("❌ Файл .env.backup не найден")

def show_current_config():
    """Показать текущую конфигурацию."""
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
        print("📋 ТЕКУЩАЯ КОНФИГУРАЦИЯ:")
        print("=" * 40)
        print(content)
        print("=" * 40)
        
        # Извлекаем основные параметры
        lines = content.split('\n')
        host = "не найден"
        for line in lines:
            if line.startswith('RADMON_HOST='):
                host = line.split('=')[1]
        
        print(f"\n🌐 Приложение будет запущено на: {host}:5000")
        
        if host == "127.0.0.1":
            print("🔒 Доступно только локально")
            print("   URL: http://127.0.0.1:5000/network")
        elif host == "0.0.0.0":
            print("🌍 Доступно со всех интерфейсов")
            print("   URL: http://127.0.0.1:5000/network")
            print("   URL: http://localhost:5000/network")
            print("   URL: http://192.168.1.103:5000/network (если доступен)")
        elif host == "192.168.1.103":
            print("🏠 Оригинальная продакшен конфигурация")
            print("   URL: http://192.168.1.103:5000/network")
    else:
        print("❌ Файл .env не найден")

def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Переключение конфигураций Netmon")
    parser.add_argument('action', choices=['local', 'all', 'original', 'restore', 'show'],
                       help='Действие с конфигурацией')
    
    args = parser.parse_args()
    
    if args.action == 'local':
        switch_to_local()
    elif args.action == 'all':
        switch_to_all_interfaces()
    elif args.action == 'original':
        switch_to_original()
    elif args.action == 'restore':
        restore_backup()
    elif args.action == 'show':
        show_current_config()
    
    print("\n📝 Для применения изменений перезапустите приложение:")
    print("   python manage_service.py restart")
    print("   или запустите start_local_test.bat")

if __name__ == "__main__":
    main()