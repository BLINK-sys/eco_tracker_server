from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import config
from models import db
from routes import register_blueprints
import os

# Глобальная переменная для SocketIO
socketio = None

def create_app(config_name=None):
    """Фабрика приложений Flask"""
    global socketio
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    
    # Инициализация расширений
    db.init_app(app)
    
    # Инициализация SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*" if app.config['DEBUG'] else app.config['CORS_ORIGINS'],
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    # Настройка CORS с поддержкой всех необходимых заголовков
    # В режиме разработки разрешаем все localhost порты
    if app.config['DEBUG']:
        CORS(app, 
             resources={r"/api/*": {
                 "origins": "*",
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 3600
             }})
    else:
        CORS(app, 
             resources={r"/api/*": {
                 "origins": app.config['CORS_ORIGINS'],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 3600
             }})
    
    jwt = JWTManager(app)
    migrate = Migrate(app, db)
    
    # Регистрация blueprints
    register_blueprints(app)
    
    # Обработка OPTIONS запросов для CORS
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        # Разрешаем localhost на любом порту в режиме разработки
        if origin and 'localhost' in origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    # Обработчики ошибок JWT
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Токен истек',
            'message': 'Необходима повторная авторизация'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'error': 'Недействительный токен',
            'message': str(error)
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'error': 'Токен отсутствует',
            'message': 'Требуется авторизация'
        }), 401
    
    # Главный маршрут
    @app.route('/')
    def index():
        return jsonify({
            'message': 'EcoTracker API',
            'version': '1.0.0',
            'status': 'running'
        })
    
    # Обработчик ошибок 404
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Ресурс не найден'}), 404
    
    # Обработчик ошибок 500
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
    
    # Регистрация WebSocket событий
    from socket_events import register_socket_events, set_socketio
    set_socketio(socketio)  # Устанавливаем глобальную ссылку
    register_socket_events(socketio)
    
    # Создание таблиц БД
    with app.app_context():
        db.create_all()
        # Инициализация тестовых данных
        from init_data import init_test_data
        init_test_data()
    
    # Запуск умного симулятора датчиков (работает только при активных соединениях)
    # В продакшене это будет заменено на реальные датчики IoT
    try:
        from smart_simulator import start_smart_simulator, set_socketio
        set_socketio(socketio)  # Передаем ссылку на SocketIO
        start_smart_simulator(app)
        print("✅ Smart sensor simulator started successfully")
    except Exception as e:
        print(f"⚠️ Failed to start smart simulator, falling back to regular simulator: {e}")
        try:
            from sensor_simulator import start_sensor_simulator
            start_sensor_simulator(app)
            print("✅ Fallback sensor simulator started successfully")
        except Exception as e2:
            print(f"⚠️ Failed to start any simulator: {e2}")
    
    return app


if __name__ == '__main__':
    app = create_app()
    # Используем socketio.run вместо app.run для поддержки WebSocket
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

