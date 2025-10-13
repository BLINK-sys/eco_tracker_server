"""
WSGI entry point для продакшена
Используется Gunicorn для запуска приложения
"""
import os
from app import create_app, socketio

# Создаем приложение для продакшена
app = create_app('production')

if __name__ == '__main__':
    # Для локального тестирования
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

