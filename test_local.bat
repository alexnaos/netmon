@echo off
chcp 65001 > nul
title Netmon Local Test
color 0A

echo ========================================
echo    БЫСТРЫЙ ТЕСТ NETMON НА ЛОКАЛЬНОЙ МАШИНЕ
echo ========================================
echo.
echo Этот скрипт запускает Netmon для проверки
echo перед переносом на другую машину.
echo.

:STOP_EXISTING
echo [1/4] Остановка предыдущих запусков...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *netmon*" > nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *Flask*" > nul 2>&1
timeout /t 1 > nul

:SWITCH_CONFIG
echo [2/4] Настройка конфигурации...
(
    echo RADMON_HOST=127.0.0.1
    echo RADMON_PORT=5000
    echo SUBNET=192.168.1.0/24
    echo SCAN_INTERVAL=600
    echo MAX_WORKERS=32
    echo PING_TIMEOUT=1
    echo LOG_LEVEL=INFO
) > .env
echo Конфигурация настроена для локального теста

:START_APP
echo [3/4] Запуск Netmon...
echo.
echo ========================================
echo ЗАПУСК ЛОКАЛЬНОГО ТЕСТА
echo ========================================
echo Адрес: 127.0.0.1:5000
echo Доступные URL:
echo   http://127.0.0.1:5000/network
echo   http://localhost:5000/network
echo.
echo Для остановки нажмите Ctrl+C
echo Логи: app\netmon.log
echo ========================================
echo.

start python -c "import webbrowser; webbrowser.open('http://127.0.0.1:5000/network')"

REM Устанавливаем переменные окружения из .env
for /f "usebackq tokens=1,2 delims==" %%i in (.env) do (
    if not "%%i"=="" if not "%%i:~0,1"="#" set %%i=%%j
)

python app\app.py

:POST_TEST
echo.
echo ========================================
echo ТЕСТ ЗАВЕРШЕН
echo ========================================
echo.
echo Что делать дальше:
echo   1) Проверьте работу в браузере
echo   2) Посмотрите логи в app\netmon.log
echo   3) Для возврата к оригинальной конфигурации:
echo        copy .env.original .env
echo        или запустите setup_and_run.bat
echo.
pause