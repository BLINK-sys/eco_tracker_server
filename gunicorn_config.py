"""
Конфигурация Gunicorn для продакшена
"""
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Workers
workers = 2
worker_class = 'eventlet'  # Для поддержки WebSocket

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Timeout
timeout = 120
keepalive = 5

# Предзагрузка приложения
preload_app = True

