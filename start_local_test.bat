@echo off
chcp 65001 > nul
title Netmon Local Test
color 0E

echo ========================================
echo    NETMON LOCAL TEST LAUNCHER
echo ========================================
echo Тестирование перед переносом на другую машину
echo ========================================
echo.

:CHECK_PYTHON
echo [1/4] Проверка Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.8+ и добавьте в PATH
    pause
    exit /b 1
)
python --version
echo.

:CHOOSE_HOST
echo [2/4] Выбор адреса запуска:
echo.
echo   1) 127.0.0.1 (только локальный доступ)
echo   2) 0.0.0.0 (все сетевые интерфейсы)
echo   3) 192.168.1.103 (оригинальный адрес)
echo.
set /p choice="Выберите вариант [1-3]: "

if "%choice%"=="1" (
    set HOST=127.0.0.1
    set HOST_DESC=локальный (127.0.0.1)
) else if "%choice%"=="2" (
    set HOST=0.0.0.0
    set HOST_DESC=все интерфейсы (0.0.0.0)
) else if "%choice%"=="3" (
    set HOST=192.168.1.103
    set HOST_DESC=оригинальный (192.168.1.103)
) else (
    echo Неверный выбор, используем 127.0.0.1
    set HOST=127.0.0.1
    set HOST_DESC=локальный (127.0.0.1)
)

echo Выбран адрес: %HOST_DESC%
echo.

:CHECK_DEPS
echo [3/4] Проверка зависимостей...
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
echo.

:CREATE_CONFIG
echo [4/4] Создание конфигурации для %HOST%...
(
    echo # Конфигурация Netmon для локального тестирования
    echo RADMON_HOST=%HOST%
    echo RADMON_PORT=5000
    echo SUBNET=192.168.1.0/24
    echo SCAN_INTERVAL=300
    echo MAX_WORKERS=64
    echo PING_TIMEOUT=2
    echo LOG_LEVEL=DEBUG
) > .env.test

echo Конфигурация создана в .env.test
echo.

:CHECK_RUNNING
echo Проверка запущенных приложений...
curl -s http://127.0.0.1:5000/api/network/info > nul 2>&1
if not errorlevel 1 (
    echo Обнаружено запущенное приложение на порту 5000!
    echo.
    echo Выберите действие:
    echo   1) Остановить и продолжить
    echo   2) Открыть в браузере и выйти
    echo   3) Выйти
    echo.
    set /p choice2="Ваш выбор [1-3]: "
    
    if "%choice2%"=="1" (
        echo Остановка приложения...
        taskkill /F /IM python.exe /FI "WINDOWTITLE eq *netmon*" > nul 2>&1
        taskkill /F /IM python.exe /FI "WINDOWTITLE eq *Flask*" > nul 2>&1
        timeout /t 2 > nul
    ) else if "%choice2%"=="2" (
        start http://127.0.0.1:5000/network
        echo Открываю в браузере...
        timeout /t 3 > nul
        exit /b 0
    ) else (
        echo Выход...
        exit /b 0
    )
)

:START_APP
echo.
echo ========================================
echo ЗАПУСК ЛОКАЛЬНОГО ТЕСТА
echo ========================================
echo Адрес: %HOST%:5000
echo Доступные URL:
echo   http://127.0.0.1:5000/network
if not "%HOST%"=="127.0.0.1" (
    echo   http://localhost:5000/network
    if "%HOST%"=="0.0.0.0" (
        echo   http://192.168.1.103:5000/network (если доступен)
    )
)
echo.
echo Для остановки нажмите Ctrl+C в этом окне
echo Логи будут сохраняться в app\netmon.log
echo.
echo ========================================
echo.

REM Копируем тестовую конфигурацию в основной .env
copy .env.test .env > nul

REM Устанавливаем переменные окружения из .env
for /f "usebackq tokens=1,2 delims==" %%i in (.env) do (
    if not "%%i"=="" if not "%%i:~0,1"="#" set %%i=%%j
)

REM Запускаем приложение
python app\app.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ОШИБКА: Приложение завершилось с ошибкой
    echo ========================================
    echo.
    echo Проверьте:
    echo   1) Порт 5000 свободен
    echo   2) Файл app\app.py существует
    echo   3) Зависимости установлены
    echo.
    echo Логи ошибок в app\netmon.log
    pause
    exit /b 1
)

echo.
echo ========================================
echo Локальный тест завершен
echo ========================================
echo.
echo Для возврата к оригинальной конфигурации:
echo   copy .env.original .env
echo или запустите setup_and_run.bat
echo.
pause