#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест локального запуска Netmon.
"""

import os
import subprocess
import sys
import time
import webbrowser


def create_local_config():
    """Создать конфигурацию для локального теста."""
    config = """RADMON_HOST=127.0.0.1
RADMON_PORT=5000
SUBNET=192.168.1.0/24
SCAN_INTERVAL=300
MAX_WORKERS=64
PING_TIMEOUT=2
LOG_LEVEL=DEBUG
"""

    with open('.env', 'w', encoding='utf-8') as f:
        f.write(config)

    print("[OK] Создана локальная конфигурация:")
    print("   Host: 127.0.0.1")
    print("   Port: 5000")
    return True


def check_port_in_use(port=5000):
    """Проверить, занят ли порт."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False


def start_app():
    """Запустить приложение в фоновом режиме."""
    print("[RUN] Запуск Netmon...")

    # Загружаем переменные из .env и устанавливаем в окружение
    env = os.environ.copy()
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env[key] = value
        host = env.get('RADMON_HOST', '127.0.0.1')
        port = env.get('RADMON_PORT', '5000')
        print(f"[CONFIG] Host: {host}, Port: {port}")

    # Используем subprocess для запуска в фоне (без перехвата вывода)
    cmd = [sys.executable, "app/app.py"]

    try:
        # Запускаем процесс с переменными окружения из .env
        # Не перехватываем stdout/stderr чтобы избежать проблем с кодировкой Windows
        process = subprocess.Popen(cmd, env=env)

        # Даем время на запуск
        print("Ожидание запуска (3 секунды)...")
        time.sleep(3)

        # Проверяем, запустилось ли (через порт)
        if check_port_in_use():
            port_val = env.get('RADMON_PORT', '5000')
            print("[OK] Приложение запущено!")
            print(f"[WEB] Открываю браузер на http://127.0.0.1:{port_val}/network")
            webbrowser.open(f'http://127.0.0.1:{port_val}/network')

            print("\n[CHECK] ПРОВЕРЬТЕ:")
            print("1. Открылась ли страница в браузере?")
            print("2. Показывает ли карту сети?")
            print("3. Отображаются ли устройства (~29)?")

            print(f"\n[API] Для проверки API:")
            print(f"   curl http://127.0.0.1:{port_val}/api/network/info")

            print(f"\n[STOP] Для остановки нажмите Ctrl+C")

            # Ждем завершения
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n[STOP] Остановка приложения...")
                process.terminate()
                process.wait(timeout=5)

        else:
            print("[ERROR] Приложение не запустилось (порт не отвечает)")
            process.terminate()

    except Exception as e:
        print(f"[ERROR] Ошибка при запуске: {e}")


def restore_original_config():
    """Восстановить оригинальную конфигурацию."""
    if os.path.exists('.env.original'):
        import shutil
        shutil.copy('.env.original', '.env')
        print("[OK] Оригинальная конфигурация восстановлена")
        print("   Host: 192.168.1.103")
    else:
        print("[WARN] Резервная копия конфигурации не найдена")


def main():
    """Основная функция."""
    print("=" * 50)
    print("        БЫСТРЫЙ ЛОКАЛЬНЫЙ ТЕСТ NETMON")
    print("=" * 50)
    print()

    # Шаг 1: Проверка порта
    if check_port_in_use():
        print("[WARN] Порт 5000 занят!")
        print("   Закройте другие приложения или освободите порт")
        return

    # Шаг 2: Создание конфигурации
    create_local_config()

    # Шаг 3: Запуск приложения
    start_app()

    # Шаг 4: Восстановление конфигурации
    print("\n[RESTORE] Восстанавливаю оригинальную конфигурацию...")
    restore_original_config()

    print("\n" + "=" * 50)
    print("[DONE] Тест завершен!")
    print("=" * 50)
    print("Результаты теста сохранены в app/netmon.log")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[STOP] Тест прерван пользователем")
    except Exception as e:
        print(f"\n[ERROR] Непредвиденная ошибка: {e}")