#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска улучшенного netmon приложения.
"""

import os
import sys
import subprocess
import time
import signal
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Проверка установленных зависимостей."""
    required = [
        "flask",
        "requests",
        "python-dotenv",
    ]
    
    missing = []
    for dep in required:
        try:
            __import__(dep.replace("-", "_"))
        except ImportError:
            missing.append(dep)
    
    if missing:
        logger.warning(f"Отсутствующие зависимости: {missing}")
        logger.info("Установка недостающих зависимостей...")
        
        # Создаем виртуальное окружение если его нет
        venv_path = os.path.join(os.path.dirname(__file__), ".venv")
        if not os.path.exists(venv_path):
            logger.info("Создание виртуального окружения...")
            subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
        
        # Устанавливаем зависимости
        pip_path = os.path.join(venv_path, "Scripts", "pip") if os.name == "nt" else os.path.join(venv_path, "bin", "pip")
        
        try:
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
            logger.info("Зависимости успешно установлены")
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка установки зависимостей: {e}")
            return False
    
    return True

def run_improved_app():
    """Запуск улучшенного приложения."""
    if not check_dependencies():
        logger.error("Не удалось проверить/установить зависимости")
        return False
    
    # Проверяем наличие файла .env, создаем если его нет
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_file):
        logger.warning("Файл .env не найден, создаем стандартный...")
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("""# Конфигурация сетевого монитора
RADMON_HOST=192.168.1.103
RADMON_PORT=5000
SUBNET=192.168.1.0/24
SCAN_INTERVAL=300  # Интервал сканирования в секундах (5 минут)
MAX_WORKERS=128
PING_TIMEOUT=2
LOG_LEVEL=INFO
""")
    
    # Запускаем приложение
    app_path = os.path.join(os.path.dirname(__file__), "app", "app_improved.py")
    
    if not os.path.exists(app_path):
        logger.error(f"Файл приложения не найден: {app_path}")
        return False
    
    logger.info(f"Запуск улучшенного приложения из {app_path}")
    
    try:
        # Импортируем и запускаем приложение напрямую
        sys.path.insert(0, os.path.dirname(__file__))
        
        from app.app_improved import app
        
        # Получаем параметры из .env
        from dotenv import load_dotenv
        load_dotenv()
        
        host = os.environ.get("RADMON_HOST", "192.168.1.103")
        port = int(os.environ.get("RADMON_PORT", "5000"))
        
        logger.info(f"Приложение запущено на http://{host}:{port}")
        logger.info("Нажмите Ctrl+C для остановки")
        
        app.run(host=host, port=port, debug=False, threaded=True)
        return True
        
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_original_app():
    """Запуск оригинального приложения."""
    app_path = os.path.join(os.path.dirname(__file__), "app", "app.py")
    
    if not os.path.exists(app_path):
        logger.error(f"Оригинальный файл приложения не найден: {app_path}")
        return False
    
    logger.info(f"Запуск оригинального приложения из {app_path}")
    
    try:
        # Запускаем оригинальное приложение как модуль
        subprocess.run([sys.executable, app_path], check=True)
        return True
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске оригинального приложения: {e}")
        return False

def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Запуск сетевого монитора")
    parser.add_argument("--improved", action="store_true", help="Запуск улучшенной версии")
    parser.add_argument("--original", action="store_true", help="Запуск оригинальной версии")
    parser.add_argument("--test", action="store_true", help="Запуск тестов")
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("Запуск тестов...")
        test_path = os.path.join(os.path.dirname(__file__), "tests", "test_basic.py")
        if os.path.exists(test_path):
            subprocess.run([sys.executable, "-m", "unittest", test_path])
        else:
            logger.error("Файл тестов не найден")
        return
    
    if args.original:
        run_original_app()
    else:
        # По умолчанию запускаем улучшенную версию
        run_improved_app()

if __name__ == "__main__":
    main()