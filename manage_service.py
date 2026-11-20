#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт управления сервисом netmon для запуска на текущей машине.
Позволяет запускать, останавливать и проверять статус приложения.
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('netmon_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NetmonService:
    """Управление сервисом netmon."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.pid_file = os.path.join(self.base_dir, 'netmon.pid')
        self.log_file = os.path.join(self.base_dir, 'netmon_service.log')
        self.app_path = os.path.join(self.base_dir, 'app', 'app.py')
        self.improved_app_path = os.path.join(self.base_dir, 'app', 'app_improved.py')
        self.process = None
        
    def get_pid(self):
        """Получение PID запущенного процесса."""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, IOError):
                return None
        return None
    
    def save_pid(self, pid):
        """Сохранение PID процесса."""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(pid))
            logger.info(f"PID сохранен: {pid}")
        except IOError as e:
            logger.error(f"Ошибка сохранения PID: {e}")
    
    def remove_pid(self):
        """Удаление файла PID."""
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
            logger.info("Файл PID удален")
    
    def load_env_file(self):
        """Загрузка переменных окружения из файла .env."""
        env_path = os.path.join(self.base_dir, '.env')
        if not os.path.exists(env_path):
            logger.warning("Файл .env не найден, используются переменные по умолчанию")
            return {}
        
        env_vars = {}
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value
                        os.environ[key] = value
            logger.info(f"Загружено {len(env_vars)} переменных из .env")
        except Exception as e:
            logger.error(f"Ошибка загрузки .env: {e}")
        return env_vars

    def check_app_running(self):
        """Проверка, запущено ли приложение."""
        try:
            import requests
            host = os.environ.get("RADMON_HOST", "127.0.0.1")
            port = os.environ.get("RADMON_PORT", "5000")
            response = requests.get(f"http://{host}:{port}/api/network/info", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def start(self, use_improved=False):
        """Запуск приложения."""
        # Загружаем переменные из .env
        self.load_env_file()

        if self.check_app_running():
            logger.warning("Приложение уже запущено")
            return False

        # Выбор версии приложения
        app_to_run = self.improved_app_path if use_improved else self.app_path
        
        if not os.path.exists(app_to_run):
            logger.error(f"Файл приложения не найден: {app_to_run}")
            return False
        
        logger.info(f"Запуск {'улучшенной' if use_improved else 'оригинальной'} версии приложения...")
        
        try:
            # Запуск в фоновом режиме
            self.process = subprocess.Popen(
                [sys.executable, app_to_run],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            self.save_pid(self.process.pid)
            logger.info(f"Приложение запущено с PID: {self.process.pid}")
            
            # Ждем запуска
            for i in range(10):
                time.sleep(1)
                if self.check_app_running():
                    logger.info("Приложение успешно запущено и отвечает на запросы")
                    return True
            
            logger.warning("Приложение запущено, но не отвечает на запросы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска приложения: {e}")
            return False
    
    def stop(self):
        """Остановка приложения."""
        pid = self.get_pid()
        
        if pid:
            try:
                # Попытка корректной остановки
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Сигнал SIGTERM отправлен процессу {pid}")
                
                # Ждем завершения
                for i in range(5):
                    time.sleep(1)
                    try:
                        os.kill(pid, 0)  # Проверка существования процесса
                    except OSError:
                        logger.info(f"Процесс {pid} завершен")
                        self.remove_pid()
                        return True
                
                # Принудительная остановка
                logger.warning(f"Принудительная остановка процесса {pid}")
                os.kill(pid, signal.SIGKILL)
                self.remove_pid()
                return True
                
            except Exception as e:
                logger.error(f"Ошибка остановки процесса {pid}: {e}")
                return False
        else:
            logger.warning("PID не найден, попытка остановки через проверку состояния")
            
            if not self.check_app_running():
                logger.info("Приложение не запущено")
                self.remove_pid()
                return True
            
            # Попробуем найти и завершить процесс
            try:
                result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/FI', 'WINDOWTITLE eq netmon*'],
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("Процессы Python с netmon остановлены")
                    self.remove_pid()
                    return True
            except Exception:
                pass
            
            logger.error("Не удалось остановить приложение")
            return False
    
    def restart(self, use_improved=False):
        """Перезапуск приложения."""
        logger.info("Перезапуск приложения...")
        self.stop()
        time.sleep(2)
        return self.start(use_improved)
    
    def status(self):
        """Проверка статуса приложения."""
        pid = self.get_pid()
        is_running = self.check_app_running()
        
        status_info = {
            "pid": pid,
            "is_running": is_running,
            "pid_file_exists": os.path.exists(self.pid_file),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app_path": self.app_path if os.path.exists(self.app_path) else None,
            "improved_app_path": self.improved_app_path if os.path.exists(self.improved_app_path) else None,
        }
        
        return status_info
    
    def tail_logs(self, lines=20):
        """Просмотр логов."""
        log_path = os.path.join(self.base_dir, 'app', 'netmon.log')
        
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:])
            except Exception as e:
                return f"Ошибка чтения логов: {e}"
        else:
            return "Файл логов не найден"

def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Управление сервисом netmon")
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'logs'],
                       help='Действие с сервисом')
    parser.add_argument('--improved', action='store_true', 
                       help='Использовать улучшенную версию приложения')
    parser.add_argument('--lines', type=int, default=20,
                       help='Количество строк логов для просмотра (только для logs)')
    
    args = parser.parse_args()
    
    service = NetmonService()
    
    if args.action == 'start':
        success = service.start(args.improved)
        sys.exit(0 if success else 1)
        
    elif args.action == 'stop':
        success = service.stop()
        sys.exit(0 if success else 1)
        
    elif args.action == 'restart':
        success = service.restart(args.improved)
        sys.exit(0 if success else 1)
        
    elif args.action == 'status':
        status = service.status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
    elif args.action == 'logs':
        logs = service.tail_logs(args.lines)
        print(logs)

if __name__ == "__main__":
    main()