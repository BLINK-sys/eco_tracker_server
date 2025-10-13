"""
Конфигурация Gunicorn для продакшена
"""
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Workers
workers = 1  # Для WebSocket лучше использовать 1 worker
worker_class = 'gevent'  # Для поддержки WebSocket и PostgreSQL

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Timeout
timeout = 120
keepalive = 5

# Предзагрузка приложения
preload_app = False  # False для gevent

