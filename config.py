import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Базовая конфигурация приложения"""
    
    # Основные настройки Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-please-change')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'
    
    # Настройки базы данных
    # Render.com использует postgres://, но SQLAlchemy требует postgresql://
    database_url = os.getenv('DATABASE_URL', 'sqlite:///ecotracker.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Добавляем параметры SSL для Render PostgreSQL
    if 'postgresql://' in database_url:
        if '?' in database_url:
            database_url += '&sslmode=require'
        else:
            database_url += '?sslmode=require'
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-please-change')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Настройки CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # Часовой пояс
    TIMEZONE = 'Asia/Almaty'


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

