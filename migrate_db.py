#!/usr/bin/env python3
"""
Скрипт для применения миграций базы данных
"""
from app import create_app
from models import db

def migrate_database():
    """Применяет миграции базы данных"""
    app = create_app('production')
    
    with app.app_context():
        print("🔄 Creating database tables...")
        db.create_all()
        
        print("✅ Database migration completed!")
        print("📊 Tables created:")
        
        # Показываем созданные таблицы
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        for table in tables:
            print(f"  - {table}")
        
        print("\n🎯 Database is ready for production!")

if __name__ == '__main__':
    migrate_database()
