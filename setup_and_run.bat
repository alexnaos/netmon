@echo off
chcp 65001 > nul
title Netmon Setup & Run - 192.168.1.103
color 0A

echo ========================================
echo    NETMON SETUP AND RUN
echo ========================================
echo Машина: 192.168.1.103
echo Дата: %date% %time%
echo Директория: %CD%
echo ========================================
echo.

:CHECK_PYTHON
echo [1/5] Проверка Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.8+ с сайта python.org
    echo Не забудьте добавить в PATH при установке
    pause
    exit /b 1
)
python --version
echo.

:CHECK_DEPS
echo [2/5] Проверка зависимостей...
pip list | findstr "Flask" > nul
if errorlevel 1 (
    echo Установка зависимостей из requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить зависимости
        echo Попробуйте: pip install -r requirements.txt --user
        pause
        exit /b 1
    )
    echo Зависимости успешно установлены
) else (
    echo Зависимости уже установлены
)
echo.

:CHECK_ENV
echo [3/5] Проверка конфигурации...
if not exist ".env" (
    echo Создание файла .env...
    (
        echo # Конфигурация Netmon для 192.168.1.103
        echo RADMON_HOST=192.168.1.103
        echo RADMON_PORT=5000
        echo SUBNET=192.168.1.0/24
        echo SCAN_INTERVAL=300
        echo MAX_WORKERS=128
        echo PING_TIMEOUT=2
        echo LOG_LEVEL=INFO
    ) > .env
    echo Файл .env создан
) else (
    echo Файл .env уже существует
)
echo.

:CHECK_RUNNING
echo [4/5] Проверка запущенного приложения...
curl -s http://192.168.1.103:5000/api/network/info > nul 2>&1
if not errorlevel 1 (
    echo Приложение УЖЕ ЗАПУЩЕНО!
    echo.
    echo Доступные адреса:
    echo   Веб-интерфейс: http://192.168.1.103:5000/network
    echo   API информация: http://192.168.1.103:5000/api/network/info
    echo.
    echo Выберите действие:
    echo   1) Открыть в браузере
    echo   2) Остановить и перезапустить
    echo   3) Продолжить без изменений
    echo   4) Выход
    echo.
    set /p choice="Ваш выбор [1-4]: "
    
    if "%choice%"=="1" (
        start http://192.168.1.103:5000/network
        echo Открываю в браузере...
        timeout /t 3 > nul
        exit /b 0
    )
    
    if "%choice%"=="2" (
        echo Остановка текущего сервера...
        taskkill /F /IM python.exe /FI "WINDOWTITLE eq *netmon*" > nul 2>&1
        taskkill /F /IM python.exe /FI "WINDOWTITLE eq *Flask*" > nul 2>&1
        timeout /t 2 > nul
        goto START_APP
    )
    
    if "%choice%"=="3" (
        echo Продолжаем без изменений...
        exit /b 0
    )
    
    if "%choice%"=="4" (
        echo Выход...
        exit /b 0
    )
    
    echo Неверный выбор, выход...
    exit /b 1
)

:START_APP
echo [5/5] Запуск приложения Netmon...
echo.
echo Запускаю приложение на порту 5000...
echo Приложение будет доступно по адресу:
echo   http://192.168.1.103:5000/network
echo.
echo Для остановки нажмите Ctrl+C в этом окне
echo.
echo ========================================
echo.

python app\app.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ОШИБКА: Приложение завершилось с ошибкой
    echo ========================================
    echo.
    echo Проверьте:
    echo   1) Python установлен и в PATH
    echo   2) Зависимости установлены (pip install -r requirements.txt)
    echo   3) Порт 5000 свободен
    echo   4) Файл app\app.py существует
    echo.
    echo Логи ошибок в app\netmon.log
    pause
    exit /b 1
)

echo.
echo ========================================
echo Приложение остановлено пользователем
echo ========================================
echo.
echo Для повторного запуска выполните:
echo   python app\app.py
echo или
echo   setup_and_run.bat
echo.
pause