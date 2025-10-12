from models import db, User, Location, Container, Company
from datetime import datetime, timedelta
import uuid


def init_test_data():
    """Инициализация тестовых данных"""
    
    print("Проверка и инициализация тестовых данных...")
    
    # Создание тестовых компаний (если их нет)
    company1 = Company.query.filter_by(name='EcoService Астана').first()
    if not company1:
        company1 = Company(
            name='EcoService Астана',
            description='Компания по сбору и переработке отходов в Астане',
            address='пр. Кабанбай Батыра, 1, Астана',
            phone='+7 (7172) 111-222',
            email='info@ecoservice.kz'
        )
        db.session.add(company1)
        print("  - Создана компания: EcoService Астана")
    
    company2 = Company.query.filter_by(name='ГринТех КЗ').first()
    if not company2:
        company2 = Company(
            name='ГринТех КЗ',
            description='Инновационные решения для управления отходами',
            address='ул. Достык, 25, Астана',
            phone='+7 (7172) 333-444',
            email='contact@greentech.kz'
        )
        db.session.add(company2)
        print("  - Создана компания: ГринТех КЗ")
    
    db.session.flush()  # Сохраняем компании, чтобы получить их ID
    
    # Создание тестовых пользователей с email
    if not User.query.filter_by(email='admin@mail.ru').first():
        admin = User(
            email='admin@mail.ru',
            role='admin',
            parent_company_id=company1.id
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("  - Создан пользователь: admin@mail.ru")
    
    if not User.query.filter_by(email='user@mail.ru').first():
        user = User(
            email='user@mail.ru',
            role='user',
            parent_company_id=company1.id
        )
        user.set_password('user123')
        db.session.add(user)
        print("  - Создан пользователь: user@mail.ru")
    
    if not User.query.filter_by(email='manager@mail.ru').first():
        manager = User(
            email='manager@mail.ru',
            role='user',
            parent_company_id=company2.id
        )
        manager.set_password('manager123')
        db.session.add(manager)
        print("  - Создан пользователь: manager@mail.ru")
    
    # Создание тестовых площадок (если их нет)
    if Location.query.first() is not None:
        print("  - Площадки уже существуют, пропускаем")
        db.session.commit()
        return
    
    # Тестовые данные площадок с UUID и привязкой к компаниям
    # Площадки 1-3 принадлежат EcoService Астана
    # Площадки 4-5 принадлежат ГринТех КЗ
    test_locations = [
        {
            'name': 'Площадка #1',
            'address': 'пр. Кабанбай Батыра, 53, Астана',
            'lat': 51.128,
            'lng': 71.430,
            'containers': [
                {'number': 1, 'status': 'full', 'fill_level': 95},
                {'number': 2, 'status': 'empty', 'fill_level': 5},
                {'number': 3, 'status': 'partial', 'fill_level': 45},
                {'number': 4, 'status': 'empty', 'fill_level': 10},
            ],
            'last_collection': datetime.utcnow() - timedelta(hours=12)
        },
        {
            'name': 'Площадка #2',
            'address': 'пр. Республики, 24, Астана',
            'lat': 51.124,
            'lng': 71.427,
            'containers': [
                {'number': 1, 'status': 'full', 'fill_level': 85},
                {'number': 2, 'status': 'empty', 'fill_level': 0},
                {'number': 3, 'status': 'empty', 'fill_level': 15},
            ],
            'last_collection': datetime.utcnow() - timedelta(hours=8)
        },
        {
            'name': 'Площадка #3',
            'address': 'ул. Сыганак, 15, Астана',
            'lat': 51.120,
            'lng': 71.420,
            'containers': [
                {'number': 1, 'status': 'partial', 'fill_level': 55},
                {'number': 2, 'status': 'partial', 'fill_level': 60},
                {'number': 3, 'status': 'empty', 'fill_level': 20},
                {'number': 4, 'status': 'full', 'fill_level': 90},
            ],
            'last_collection': datetime.utcnow() - timedelta(hours=24)
        },
        {
            'name': 'Площадка #4',
            'address': 'ул. Достык, 13, Астана',
            'lat': 51.126,
            'lng': 71.440,
            'containers': [
                {'number': 1, 'status': 'full', 'fill_level': 100},
                {'number': 2, 'status': 'full', 'fill_level': 95},
                {'number': 3, 'status': 'full', 'fill_level': 90},
                {'number': 4, 'status': 'partial', 'fill_level': 65},
            ],
            'last_collection': datetime.utcnow() - timedelta(hours=36)
        },
        {
            'name': 'Площадка #5',
            'address': 'пр. Туран, 37, Астана',
            'lat': 51.133,
            'lng': 71.436,
            'containers': [
                {'number': 1, 'status': 'full', 'fill_level': 100},
                {'number': 2, 'status': 'full', 'fill_level': 100},
            ],
            'last_collection': datetime.utcnow() - timedelta(hours=48)
        },
    ]
    
    # Создание площадок и контейнеров с автоматической генерацией UUID
    for idx, loc_data in enumerate(test_locations):
        # Первые 3 площадки для company1, остальные для company2
        assigned_company_id = company1.id if idx < 3 else company2.id
        
        location = Location(
            name=loc_data['name'],
            address=loc_data['address'],
            lat=loc_data['lat'],
            lng=loc_data['lng'],
            company_id=assigned_company_id,
            last_collection=loc_data.get('last_collection')
        )
        db.session.add(location)
        db.session.flush()  # Получаем UUID для location
        
        # Создание контейнеров
        for cont_data in loc_data['containers']:
            container = Container(
                location_id=location.id,  # Используем UUID из location
                number=cont_data['number'],
                status=cont_data['status'],
                fill_level=cont_data['fill_level']
            )
            db.session.add(container)
        
        # Обновление статуса площадки
        db.session.flush()
        location.update_status()
    
    db.session.commit()
    print("\n✓ Тестовые данные успешно загружены!")
    print("\n📊 Итого создано:")
    print(f"  - Компании: {Company.query.count()}")
    print(f"  - Пользователи: {User.query.count()}")
    print(f"  - Площадки: {Location.query.count()}")
    print(f"  - Контейнеры: {Container.query.count()}")
    print("\n👤 Учетные данные для входа:")
    print("  - admin@mail.ru / admin123 (администратор)")
    print("  - user@mail.ru / user123 (пользователь)")
    print("  - manager@mail.ru / manager123 (пользователь)")

