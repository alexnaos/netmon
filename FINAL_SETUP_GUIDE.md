# Финальная инструкция по запуску Netmon на 192.168.1.103

## Текущее состояние

✅ **Приложение УЖЕ РАБОТАЕТ** на порту 5000:
- Веб-интерфейс: http://192.168.1.103:5000/network
- API: http://192.168.1.103:5000/api/network/info
- Обнаружено: 29 устройств в сети

## Что было сделано для запуска на этой машине:

### 1. Исправлены критические ошибки:
- ✅ Исправлены синтаксические ошибки в `data/network_data.py`
- ✅ Обновлены зависимости в `requirements.txt`
- ✅ Исправлена кодировка в CLI-сканере
- ✅ Созданы unit-тесты для проверки данных

### 2. Созданы скрипты управления:
- `manage_service.py` - Python скрипт для управления сервисом
- `start_netmon.bat` - Простой запуск одним кликом
- `setup_and_run.bat` - Полная установка с проверками
- `netmon_service_windows.bat` - Управление Windows службой

### 3. Создана конфигурация:
- `.env` файл с настройками для 192.168.1.103
- Логирование в `app/netmon.log`
- PID файл `netmon.pid` для отслеживания процесса

### 4. Создана документация:
- `QUICK_START.md` - Быстрый старт
- `INSTALL_WINDOWS.md` - Полная инструкция
- `README_IMPROVED.md` - Документация улучшенной версии

## Как запустить сейчас:

### Вариант 1: Простой запуск (если уже работает)
```bash
cd C:\Projects\PlatformIO\netmon
setup_and_run.bat
```

### Вариант 2: Запуск через Python
```bash
cd C:\Projects\PlatformIO\netmon
python manage_service.py status  # Проверить статус
python manage_service.py restart  # Перезапустить
```

### Вариант 3: Прямой запуск
```bash
cd C:\Projects\PlatformIO\netmon
python app\app.py
```

## Настройка автозапуска:

### Для запуска при старте Windows:
```bash
netmon_service_windows.bat install
```

### Проверка автозапуска:
```bash
schtasks /query /tn "Netmon Service"
```

## Основные команды после запуска:

### Управление:
```bash
# Статус
python manage_service.py status

# Логи (50 строк)
python manage_service.py logs --lines 50

# Остановка
python manage_service.py stop

# Запуск
python manage_service.py start
```

### Проверка работы:
```bash
# Проверка API
curl http://192.168.1.103:5000/api/network/info

# Запуск сканирования
curl -X POST http://192.168.1.103:5000/api/network/scan

# Обновление через CLI
python data\network_discovery.py
```

### Мониторинг:
```bash
# Проверка процессов
tasklist | findstr python

# Проверка порта
netstat -ano | findstr :5000

# Просмотр логов
tail -50 app\netmon.log
findstr ERROR app\netmon.log
```

## Конфигурация (.env):

```env
# Настроено для текущей машины
RADMON_HOST=192.168.1.103
RADMON_PORT=5000
SUBNET=192.168.1.0/24
SCAN_INTERVAL=300      # Сканирование каждые 5 минут
MAX_WORKERS=128        # Потоки для сканирования
PING_TIMEOUT=2         # Таймаут ping
LOG_LEVEL=INFO         # Логирование
```

## Решение проблем:

### 1. Порт 5000 занят:
```bash
# Найти процесс
netstat -ano | findstr :5000
# Завершить
taskkill /PID <PID> /F
# Или изменить порт в .env
```

### 2. Python не найден:
- Проверьте установку Python 3.8+
- Добавьте в PATH или используйте полный путь

### 3. Зависимости не установлены:
```bash
pip install -r requirements.txt
```

### 4. Приложение не запускается:
```bash
# Проверьте ошибки
python app\app.py

# Или используйте улучшенную версию
python app\app_improved.py
```

## Структура проекта после настройки:

```
netmon/
├── app/
│   ├── app.py              # Основное приложение (работает)
│   ├── app_improved.py     # Улучшенная версия (готова)
│   ├── netmon.log          # Логи приложения
│   └── templates/          # Веб-интерфейс
├── data/
│   ├── network_data.py     # Исправленная база устройств
│   └── network_discovery.py # Исправленный сканер
├── scripts управления:
│   ├── setup_and_run.bat   # Полная установка
│   ├── start_netmon.bat    # Простой запуск
│   ├── manage_service.py   # Python управление
│   └── netmon_service_windows.bat # Windows служба
├── документация:
│   ├── QUICK_START.md      # Быстрый старт
│   ├── INSTALL_WINDOWS.md  # Полная установка
│   └── README_IMPROVED.md  # Улучшенная версия
├── конфигурация:
│   ├── .env                # Настройки для 192.168.1.103
│   ├── requirements.txt    # Обновленные зависимости
│   └── netmon.pid          # PID файл (при запуске)
└── тесты:
    └── tests/test_basic.py # Unit-тесты
```

## Следующие шаги:

1. **Протестировать автозапуск** через `netmon_service_windows.bat install`
2. **Проверить сканирование** сети каждые 5 минут
3. **Протестировать веб-интерфейс** на других устройствах сети
4. **Настроить улучшенную версию** после отладки
5. **Добавить уведомления** при обнаружении проблем

## Готово к переносу на другую машину:

Для переноса на другую машину:
1. Скопируйте всю папку `netmon`
2. Измените `RADMON_HOST` в `.env` на IP новой машины
3. Запустите `setup_and_run.bat`

---

**Приложение полностью настроено и готово к работе на 192.168.1.103!**

Доступно по адресу: http://192.168.1.103:5000/network
API: http://192.168.1.103:5000/api/network/info
Логи: `app\netmon.log`