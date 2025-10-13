#!/usr/bin/env bash
# exit on error
set -o errexit

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Инициализация базы данных
python init_db.py

