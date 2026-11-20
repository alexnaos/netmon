@echo off
chcp 65001 > nul
title Netmon Service - 192.168.1.103:5000
color 0A

echo ========================================
echo    Netmon Network Monitor
echo ========================================
echo Запуск на: 192.168.1.103:5000
echo Дата: %date% %time%
echo ========================================
echo.

REM Проверка Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.8+ и добавьте в PATH
    pause
    exit /b 1
)

REM Проверка зависимостей
echo Проверка зависимостей...
pip list | findstr "Flask" > nul
if errorlevel 1 (
    echo Установка зависимостей...
    pip install -r requirements.txt > nul 2>&1
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить зависимости
        pause
        exit /b 1
    )
    echo Зависимости установлены
) else (
    echo Зависимости проверены
)

REM Проверка запущен ли уже сервер
echo Проверка доступности сервера...
curl -s http://192.168.1.103:5000/api/network/info > nul 2>&1
if not errorlevel 1 (
    echo Сервер уже запущен!
    echo Доступен по адресу: http://192.168.1.103:5000
    echo.
    echo Выберите действие:
    echo 1) Открыть в браузере
    echo 2) Остановить и перезапустить
    echo 3) Продолжить без изменений
    echo.
    set /p choice="Выбор [1-3]: "
    
    if "%choice%"=="1" (
        start http://192.168.1.103:5000/network
        pause
        exit /b 0
    )
    
    if "%choice%"=="2" (
        echo Остановка текущего сервера...
        taskkill /F /IM python.exe /FI "WINDOWTITLE eq *netmon*" > nul 2>&1
        timeout /t 2 /nobreak > nul
    )
)

REM Создание .env файла если нет
if not exist ".env" (
    echo Создание файла конфигурации .env...
    (
        echo # Конфигурация Netmon
        echo RADMON_HOST=192.168.1.103
        echo RADMON_PORT=5000
        echo SUBNET=192.168.1.0/24
        echo SCAN_INTERVAL=300
        echo MAX_WORKERS=128
        echo PING_TIMEOUT=2
        echo LOG_LEVEL=INFO
    ) > .env
    echo Файл .env создан
)

echo.
echo Запуск приложения...
echo ========================================
echo.

REM Запуск приложения
python app\app.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ОШИБКА: Приложение завершилось с ошибкой
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Приложение остановлено пользователем
echo ========================================
pause