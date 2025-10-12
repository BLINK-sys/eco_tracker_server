from models import db, User, Location, Container, Company, Role, AccessRight
from datetime import datetime, timedelta
import uuid


def init_test_data():
    """Инициализация тестовых данных"""
    
    print("Проверка и инициализация тестовых данных...")
    
    # Создание компании ТОО EcoTracker
    company = Company.query.filter_by(name='ТОО EcoTracker').first()
    if not company:
        company = Company(
            name='ТОО EcoTracker',
            description='Компания по управлению отходами',
            address='ул. Кенесары 52',
            phone='+77009631660',
            email='bocan.anton@mail.ru'
        )
        db.session.add(company)
        print("  - Создана компания: ТОО EcoTracker")
    
    db.session.flush()  # Сохраняем компанию, чтобы получить её ID
    
    # Создание глобальных ролей (один раз для всей системы)
    owner_role = Role.query.filter_by(name='Владелец').first()
    if not owner_role:
        owner_role = Role(
            name='Владелец',
            description='Полный доступ ко всем функциям системы'
        )
        db.session.add(owner_role)
        print("  - Создана роль 'Владелец'")
    
    operator_role = Role.query.filter_by(name='Оператор').first()
    if not operator_role:
        operator_role = Role(
            name='Оператор',
            description='Доступ к мониторингу и управлению площадками'
        )
        db.session.add(operator_role)
        print("  - Создана роль 'Оператор'")
    
    db.session.flush()  # Сохраняем роли, чтобы получить их ID
    
    # Создание пользователей для ТОО EcoTracker
    if not User.query.filter_by(email='bocan.anton@mail.ru').first():
        # Создаем пользователя владельца
        owner = User(
            email='bocan.anton@mail.ru',
            role_id=owner_role.id,
            parent_company_id=company.id
        )
        owner.set_password('123123')
        db.session.add(owner)
        db.session.flush()  # Получаем ID пользователя
        
        # Создаем права доступа для владельца (все включено)
        owner_rights = AccessRight(
            user_id=owner.id,
            can_view_monitoring=True,
            can_view_notifications=True,
            can_view_locations=True,
            can_view_reports=True,
            can_view_admin=True,
            can_manage_users=True,
            can_manage_companies=True,
            can_view_security=True,
            can_manage_notifications=True,
            can_create_locations=True,
            can_edit_locations=True,
            can_delete_locations=True,
            can_create_containers=True,
            can_edit_containers=True,
            can_delete_containers=True
        )
        db.session.add(owner_rights)
        print("  - Создан пользователь владелец: bocan.anton@mail.ru")
    
    if not User.query.filter_by(email='bocan.anton1@mail.ru').first():
        # Создаем пользователя оператора
        operator = User(
            email='bocan.anton1@mail.ru',
            role_id=operator_role.id,
            parent_company_id=company.id
        )
        operator.set_password('123123')
        db.session.add(operator)
        db.session.flush()  # Получаем ID пользователя
        
        # Создаем права доступа для оператора (ограниченные)
        operator_rights = AccessRight(
            user_id=operator.id,
            can_view_monitoring=True,
            can_view_notifications=True,
            can_view_locations=True,
            can_view_reports=False,
            can_view_admin=False,
            can_manage_users=False,
            can_manage_companies=False,
            can_view_security=False,
            can_manage_notifications=False,
            can_create_locations=False,
            can_edit_locations=False,
            can_delete_locations=False,
            can_create_containers=False,
            can_edit_containers=False,
            can_delete_containers=False
        )
        db.session.add(operator_rights)
        print("  - Создан пользователь оператор: bocan.anton1@mail.ru")
    
    # Создание тестовых площадок
    locations_data = [
        {
            'name': 'Мой дом',
            'address': 'улица Мухамед-Хайдара Дулати 78',
            'lat': 51.1662999045894,
            'lng': 71.4417098647614
        },
        {
            'name': 'Евгений Владимирович',
            'address': 'улица Кенесары 89/2',
            'lat': 51.1634876066125,
            'lng': 71.4623149640136
        },
        {
            'name': 'Димон',
            'address': 'улица Бейсекбаева 20',
            'lat': 51.1710223183345,
            'lng': 71.4592250905505
        }
    ]
    
    for loc_data in locations_data:
        if not Location.query.filter_by(name=loc_data['name'], company_id=company.id).first():
            location = Location(
                name=loc_data['name'],
                address=loc_data['address'],
                lat=loc_data['lat'],
                lng=loc_data['lng'],
                company_id=company.id
            )
            db.session.add(location)
            db.session.flush()  # Получаем ID площадки
            
            # Создаем контейнеры для каждой площадки
            for i in range(3):  # 3 контейнера на площадку
                container = Container(
                    location_id=location.id,
                    number=i + 1,  # Номер контейнера
                    fill_level=0,  # Начинаем с пустых контейнеров
                    status='empty'
                )
                db.session.add(container)
            
            print(f"  - Создана площадка: {loc_data['name']} с 3 контейнерами")
    
    # Коммитим все изменения
    try:
        db.session.commit()
        print("[OK] Тестовые данные успешно инициализированы")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Ошибка при сохранении данных: {str(e)}")
        raise


if __name__ == "__main__":
    # Этот блок выполняется только при прямом запуске файла
    from app import create_app
    
    app = create_app()
    with app.app_context():
        init_test_data()