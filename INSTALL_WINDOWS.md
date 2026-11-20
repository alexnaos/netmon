# Установка Netmon на текущую машину (192.168.1.103)

## Краткое описание

Данная инструкция описывает установку и настройку сетевого монитора Netmon на текущей машине с IP-адресом 192.168.1.103.

## Требования

- Windows 10/11
- Python 3.8 или выше
- Доступ к сети 192.168.1.0/24
- Права администратора (для установки автозапуска)

## Быстрая установка

### 1. Клонирование проекта (если еще не сделано)
```bash
cd C:\Projects\PlatformIO
git clone <репозиторий> netmon
cd netmon
```

### 2. Запуск установки одним кликом
Запустите файл `start_netmon.bat`:
1. Нажмите Win+R
2. Введите: `C:\Projects\PlatformIO\netmon\start_netmon.bat`
3. Нажмите Enter

Или откройте проводник и дважды кликните на `start_netmon.bat`

## Ручная установка

### 1. Проверка Python
```bash
python --version
# Должно быть Python 3.8+
```

### 2. Установка зависимостей
```bash
cd C:\Projects\PlatformIO\netmon
pip install -r requirements.txt
```

### 3. Запуск приложения
```bash
python app\app.py
```

### 4. Проверка работы
Откройте браузер и перейдите по адресу:
- Веб-интерфейс: http://192.168.1.103:5000/network
- API информация: http://192.168.1.103:5000/api/network/info

## Управление сервисом

### Использование скрипта управления
```bash
# Запуск
python manage_service.py start

# Остановка
python manage_service.py stop

# Перезапуск
python manage_service.py restart

# Статус
python manage_service.py status

# Логи (последние 20 строк)
python manage_service.py logs

# Логи (50 строк)
python manage_service.py logs --lines 50
```

### Использование улучшенной версии
```bash
# Запуск улучшенной версии
python manage_service.py start --improved

# Перезапуск улучшенной версии
python manage_service.py restart --improved
```

## Настройка автозапуска

### Способ 1: Через планировщик задач (рекомендуется)
```bash
# Установка автозапуска
netmon_service_windows.bat install

# Удаление автозапуска
netmon_service_windows.bat uninstall
```

### Способ 2: Через ярлык в автозагрузке
1. Создайте ярлык для `start_netmon.bat`
2. Поместите ярлык в папку автозагрузки:
   ```
   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
   ```

## Конфигурация

### Файл .env
При первом запуске автоматически создается файл `.env`:
```env
# Конфигурация Netmon
RADMON_HOST=192.168.1.103  # IP адрес сервера
RADMON_PORT=5000           # Порт приложения
SUBNET=192.168.1.0/24     # Мониторируемая подсеть
SCAN_INTERVAL=300         # Интервал сканирования в секундах (5 минут)
MAX_WORKERS=128           # Количество потоков для сканирования
PING_TIMEOUT=2            # Таймаут ping в секундах
LOG_LEVEL=INFO            # Уровень логирования (DEBUG, INFO, WARNING, ERROR)
```

### Изменение конфигурации
1. Отредактируйте файл `.env`
2. Перезапустите приложение:
   ```bash
   python manage_service.py restart
   ```

## Просмотр логов

### Основные логи приложения
```bash
# Последние 50 строк
tail -50 app\netmon.log

# Весь файл
type app\netmon.log

# Поиск ошибок
findstr ERROR app\netmon.log

# Логи в реальном времени (требуется Git Bash или WSL)
tail -f app\netmon.log
```

### Логи службы управления
```bash
# Логи скрипта управления
type netmon_service.log

# Последние 20 строк
tail -20 netmon_service.log
```

## Мониторинг работы

### Проверка статуса
```bash
# Через скрипт
python manage_service.py status

# Через curl
curl http://192.168.1.103:5000/api/health

# Проверка API
curl http://192.168.1.103:5000/api/network/info | python -m json.tool
```

### Проверка процессов
```bash
# Поиск процессов netmon
tasklist | findstr netmon

# Поиск процессов Python
tasklist | findstr python

# Детальная информация
wmic process where "name='python.exe'" get ProcessId,CommandLine
```