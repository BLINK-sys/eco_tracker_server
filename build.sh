#!/usr/bin/env bash
# Скрипт для сборки и инициализации приложения на Render

set -o errexit

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Инициализация базы данных и применение миграций
python migrate_db.py

# Инициализация тестовых данных
python -c "
from app import create_app
from init_data import init_test_data

app = create_app('production')
with app.app_context():
    init_test_data()
    print('✅ Initial data loaded successfully')
"

echo "Build completed successfully!"

