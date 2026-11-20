# Быстрый старт на текущей машине (192.168.1.103)

## 1. Запуск одним кликом

Откройте командную строку или PowerShell и выполните:

```bash
cd C:\Projects\PlatformIO\netmon
start_netmon.bat
```

Или просто дважды кликните на файл `start_netmon.bat` в проводнике.

## 2. Проверка работы

После запуска откройте браузер и перейдите по адресам:

- **Веб-интерфейс**: http://192.168.1.103:5000/network
- **API информация**: http://192.168.1.103:5000/api/network/info
- **Проверка здоровья**: http://192.168.1.103:5000/api/health

## 3. Основные команды

### Управление сервисом:
```bash
# Статус приложения
python manage_service.py status

# Запуск
python manage_service.py start

# Остановка
python manage_service.py stop

# Перезапуск
python manage_service.py restart

# Просмотр логов
python manage_service.py logs --lines 50
```

### Обновление данных сети:
```bash
# Запуск сканирования через API
curl -X POST http://192.168.1.103:5000/api/network/scan

# Или через CLI сканер
python data\network_discovery.py
```

## 4. Настройка автозапуска

### Для запуска при старте системы:
```bash
# Установка через планировщик задач
netmon_service_windows.bat install

# Проверка установки
schtasks /query /tn "Netmon Service"
```

## 5. Конфигурация

Все настройки в файле `.env`:
```env
RADMON_HOST=192.168.1.103  # IP этой машины
RADMON_PORT=5000           # Порт приложения
SUBNET=192.168.1.0/24     # Ваша локальная сеть
SCAN_INTERVAL=300          # Сканирование каждые 5 минут
LOG_LEVEL=INFO            # Уровень детализации логов
```

## 6. Быстрые проверки

### Проверка запуска:
```bash
# Проверка процесса
tasklist | findstr python

# Проверка порта
netstat -ano | findstr :5000

# Проверка через curl
curl -s http://192.168.1.103:5000/api/network/info | python -c "import json,sys; data=json.load(sys.stdin); print(f'Устройств: {data[\"total\"]}')"
```

### Просмотр логов:
```bash
# Последние ошибки
findstr ERROR app\netmon.log

# Последние 20 строк логов
tail -20 app\netmon.log

# Логи службы
type netmon_service.log
```

## 7. Решение частых проблем

### Порт занят:
```bash
# Поиск процесса
netstat -ano | findstr :5000
# Завершение процесса
taskkill /PID <номер_процесса> /F
```

### Python не найден:
- Убедитесь, что Python установлен и в PATH
- Или используйте полный путь: `C:\Python310\python.exe app\app.py`

### Нет зависимостей:
```bash
pip install -r requirements.txt
```

## 8. Перенос на другую машину

### Подготовка:
1. Сохраните конфигурацию: `copy .env .env.backup`
2. Измените `RADMON_HOST` в `.env` на IP новой машины
3. Запустите `start_netmon.bat`

---

**Приложение готово к работе!** Система будет автоматически сканировать сеть и отображать все устройства на веб-интерфейсе.