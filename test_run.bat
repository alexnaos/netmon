@echo off
chcp 65001 > nul
cd /d c:\Projects\PlatformIO\netmon

echo === Тест запуска Netmon ===
echo.

echo [1] Проверка зависимостей...
pip install -r requirements.txt > nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)
echo Зависимости установлены

echo.
echo [2] Запуск Netmon...
python app/app.py > app\netmon.log 2>&1

if errorlevel 1 (
    echo ОШИБКА: Не удалось запустить приложение
    echo.
    echo Логи:
    type app\netmon.log
    pause
    exit /b 1
)

echo.
echo Приложение запущено.
echo Откройте в браузере: http://127.0.0.1:5000
echo.
echo Для остановки нажмите Ctrl+C в этом окне
echo.
pause
echo.
echo === Проверка API ===
curl -s http://127.0.0.1:5000/api/network/info | head -c 200
echo.
echo === Проверка веб-страницы ===
curl -s http://127.0.0.1:5000/ | head -c 200
echo.
echo === Готово ===