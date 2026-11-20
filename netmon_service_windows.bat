@echo off
chcp 65001 > nul
echo ========================================
echo Netmon Service Manager - Windows
echo ========================================
echo.

if "%1"=="" (
    echo Использование: %~nx0 [команда]
    echo.
    echo Команды:
    echo   install     - Установка службы автозапуска
    echo   uninstall   - Удаление службы автозапуска
    echo   start       - Запуск приложения
    echo   stop        - Остановка приложения
    echo   restart     - Перезапуск приложения
    echo   status      - Проверка статуса
    echo   logs        - Просмотр логов
    echo.
    echo Пример: %~nx0 start
    goto :eof
)

set PYTHON_EXE=python
set PROJECT_DIR=%~dp0
set APP_DIR=%PROJECT_DIR%app
set LOG_DIR=%PROJECT_DIR%logs

REM Проверка Python
%PYTHON_EXE% --version > nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не найден или не установлен
    echo Установите Python 3.8+ и добавьте в PATH
    pause
    exit /b 1
)

if not exist "%APP_DIR%" (
    echo Ошибка: Директория приложения не найдена: %APP_DIR%
    pause
    exit /b 1
)

if "%1"=="install" (
    echo Установка автозапуска через планировщик задач...
    
    REM Создание задачи в планировщике
    schtasks /Create /SC ONSTART /TN "Netmon Service" /TR "%PROJECT_DIR%netmon_service_windows.bat start" /RU SYSTEM /RL HIGHEST
    
    if errorlevel 1 (
        echo Ошибка при создании задачи в планировщике
        echo Попробуйте запустить от имени администратора
        pause
        exit /b 1
    )
    
    echo Задача успешно создана
    echo Приложение будет запускаться при старте системы
    goto :eof
)

if "%1"=="uninstall" (
    echo Удаление задачи из планировщика...
    
    schtasks /Delete /TN "Netmon Service" /F
    
    if errorlevel 1 (
        echo Задача не найдена или ошибка удаления
    ) else (
        echo Задача успешно удалена
    )
    goto :eof
)

if "%1"=="start" (
    echo Запуск приложения Netmon...
    
    if exist "%PROJECT_DIR%netmon.pid" (
        echo Приложение уже запущено (PID файл существует)
        echo Используйте 'restart' для перезапуска
        goto :eof
    )
    
    REM Создание директории логов если нет
    if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
    
    REM Запуск через Python скрипт
    echo Запуск приложения...
    start "Netmon Service" /B %PYTHON_EXE% "%PROJECT_DIR%app\app.py"
    
    REM Запись PID
    echo %PROCESS_ID% > "%PROJECT_DIR%netmon.pid"
    
    echo Приложение запущено
    echo Доступно по адресу: http://192.168.1.103:5000
    echo Логи: %PROJECT_DIR%app\netmon.log
    goto :eof
)

if "%1"=="stop" (
    echo Остановка приложения Netmon...
    
    if not exist "%PROJECT_DIR%netmon.pid" (
        echo PID файл не найден, приложение может быть не запущено
    ) else (
        set /p PID=<"%PROJECT_DIR%netmon.pid"
        echo Остановка процесса PID: %PID%
        taskkill /PID %PID% /F > nul 2>&1
        del "%PROJECT_DIR%netmon.pid" > nul 2>&1
        echo Приложение остановлено
    )
    
    REM Дополнительная проверка через taskkill по имени
    taskkill /IM python.exe /FI "WINDOWTITLE eq *netmon*" /F > nul 2>&1
    goto :eof
)

if "%1"=="restart" (
    echo Перезапуск приложения Netmon...
    call %0 stop
    timeout /t 3 /nobreak > nul
    call %0 start
    goto :eof
)

if "%1"=="status" (
    echo Проверка статуса Netmon...
    echo.
    
    if exist "%PROJECT_DIR%netmon.pid" (
        set /p PID=<"%PROJECT_DIR%netmon.pid"
        echo PID файл существует: %PID%
        
        tasklist /FI "PID eq %PID%" | findstr "python" > nul
        if errorlevel 1 (
            echo Процесс не найден (возможно завершен)
        ) else (
            echo Процесс запущен
        )
    ) else (
        echo PID файл не найден
    )
    
    echo.
    echo Проверка доступности веб-интерфейса...
    curl -s -o nul -w "HTTP код: %%{http_code}\n" http://192.168.1.103:5000/api/network/info 2>nul || echo Веб-интерфейс недоступен
    goto :eof
)

if "%1"=="logs" (
    echo Последние строки логов:
    echo ========================================
    if exist "%PROJECT_DIR%app\netmon.log" (
        tail -20 "%PROJECT_DIR%app\netmon.log" 2>nul || type "%PROJECT_DIR%app\netmon.log" | more +L-20
    ) else (
        echo Файл логов не найден
    )
    goto :eof
)

echo Неизвестная команда: %1
echo Используйте без параметров для справки