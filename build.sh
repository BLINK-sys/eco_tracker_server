#!/usr/bin/env bash
# Скрипт для сборки и инициализации приложения на Render

set -o errexit

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Инициализация базы данных и применение миграций
python -c "
from app import create_app
from models import db

app = create_app('production')
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
    
    # Инициализация тестовых данных
    from init_data import init_test_data
    init_test_data()
    print('Initial data loaded successfully')
"

echo "Build completed successfully!"

