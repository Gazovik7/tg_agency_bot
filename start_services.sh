#!/bin/bash

# Активация виртуального окружения
source venv/bin/activate

# Запуск бота в фоновом режиме
nohup python bot.py > bot.log 2>&1 &

# Запуск веб-приложения в фоновом режиме
nohup python app.py > app.log 2>&1 &

# Запуск воркера в фоновом режиме
nohup python worker.py > worker.log 2>&1 &

echo "Все сервисы запущены. Проверьте логи в файлах *.log" 