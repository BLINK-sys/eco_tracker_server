#!/usr/bin/env python3
"""
Скрипт для принудительного применения индексов БД
"""
from app import create_app
from models import db
from sqlalchemy import text

def apply_indexes():
    """Применяет индексы для оптимизации запросов"""
    app = create_app('production')
    
    with app.app_context():
        print("🔄 Applying database indexes...")
        
        # Создаем индексы напрямую через SQL
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);", 
            "CREATE INDEX IF NOT EXISTS idx_users_parent_company_id ON users(parent_company_id);",
            "CREATE INDEX IF NOT EXISTS idx_access_rights_user_id ON access_rights(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_containers_location_id ON containers(location_id);",
            "CREATE INDEX IF NOT EXISTS idx_locations_company_id ON locations(company_id);",
        ]
        
        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
                print(f"✅ Applied: {index_sql}")
            except Exception as e:
                print(f"⚠️ Warning: {index_sql} - {e}")
        
        db.session.commit()
        print("🎯 Database indexes applied successfully!")

if __name__ == '__main__':
    apply_indexes()
