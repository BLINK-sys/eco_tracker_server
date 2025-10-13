"""
WSGI entry point для Gunicorn на Render.com
"""
from app import create_app, socketio

app = create_app('production')

if __name__ == "__main__":
    socketio.run(app)

