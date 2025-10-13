"""
Скрипт инициализации базы данных для продакшена
Создает таблицы и заполняет начальными данными
"""
from app import create_app
from models import db
from init_data import init_test_data

def init_database():
    """Инициализация базы данных"""
    app = create_app('production')
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Tables created")
        
        print("\nInitializing data...")
        init_test_data()
        print("✓ Data initialized")
        
        print("\n✓ Database initialization completed!")

if __name__ == '__main__':
    init_database()

