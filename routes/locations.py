from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Location, Container, Collection, User
from datetime import datetime

locations_bp = Blueprint('locations', __name__)


@locations_bp.route('', methods=['GET'])
def get_locations():
    """Получение списка всех площадок с возможностью фильтрации по компании"""
    try:
        company_id = request.args.get('company_id')
        
        if company_id:
            # Фильтрация по компании
            locations = Location.query.filter_by(company_id=company_id).all()
        else:
            # Все площадки
            locations = Location.query.all()
        
        return jsonify([location.to_dict() for location in locations]), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка получения площадок: {str(e)}'}), 500


@locations_bp.route('/<string:location_id>', methods=['GET'])
def get_location(location_id):
    """Получение информации о конкретной площадке"""
    try:
        location = Location.query.get(location_id)
        
        if not location:
            return jsonify({'error': 'Площадка не найдена'}), 404
        
        return jsonify(location.to_dict()), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка получения площадки: {str(e)}'}), 500


@locations_bp.route('', methods=['POST', 'OPTIONS'])
@jwt_required()
def create_location():
    """Создание новой площадки"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['name', 'address', 'lat', 'lng']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        # Проверка компании (если указана)
        company_id = data.get('company_id')
        if company_id:
            from models import Company
            company = Company.query.get(company_id)
            if not company:
                return jsonify({'error': 'Компания не найдена'}), 404
        
        # Создание площадки (UUID генерируется автоматически)
        location = Location(
            name=data['name'],
            address=data['address'],
            lat=float(data['lat']),
            lng=float(data['lng']),
            company_id=company_id,
            status=data.get('status', 'empty')
        )
        
        db.session.add(location)
        db.session.flush()  # Получаем UUID для location
        
        # Создание контейнеров
        containers_data = data.get('containers', [])
        for container_data in containers_data:
            container = Container(
                location_id=location.id,  # Используем сгенерированный UUID
                number=container_data['number'],
                status=container_data.get('status', 'empty'),
                fill_level=container_data.get('fill_level', 0)
            )
            db.session.add(container)
        
        db.session.flush()
        location.update_status()
        db.session.commit()
        
        return jsonify({
            'message': 'Площадка создана успешно',
            'location': location.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания площадки: {str(e)}'}), 500


@locations_bp.route('/<string:location_id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
def update_location(location_id):
    """Обновление информации о площадке"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        location = Location.query.get(location_id)
        
        if not location:
            return jsonify({'error': 'Площадка не найдена'}), 404
        
        data = request.get_json()
        
        # Обновление полей
        if 'name' in data:
            location.name = data['name']
        if 'address' in data:
            location.address = data['address']
        if 'lat' in data:
            location.lat = float(data['lat'])
        if 'lng' in data:
            location.lng = float(data['lng'])
        if 'status' in data:
            location.status = data['status']
        if 'company_id' in data:
            # Проверка существования компании
            if data['company_id']:
                from models import Company
                company = Company.query.get(data['company_id'])
                if not company:
                    return jsonify({'error': 'Компания не найдена'}), 404
            location.company_id = data['company_id']
        
        location.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Площадка обновлена успешно',
            'location': location.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления площадки: {str(e)}'}), 500


@locations_bp.route('/<string:location_id>', methods=['DELETE'])
@jwt_required()
def delete_location(location_id):
    """Удаление площадки"""
    try:
        location = Location.query.get(location_id)
        
        if not location:
            return jsonify({'error': 'Площадка не найдена'}), 404
        
        db.session.delete(location)
        db.session.commit()
        
        return jsonify({'message': 'Площадка удалена успешно'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления площадки: {str(e)}'}), 500


@locations_bp.route('/<string:location_id>/collect', methods=['POST'])
@jwt_required()
def collect_waste(location_id):
    """Регистрация сбора мусора с площадки"""
    try:
        current_user_id = get_jwt_identity()
        location = Location.query.get(location_id)
        
        if not location:
            return jsonify({'error': 'Площадка не найдена'}), 404
        
        data = request.get_json() or {}
        
        # Создание записи о сборе
        collection = Collection(
            location_id=location_id,
            containers_count=len(location.containers),
            notes=data.get('notes'),
            collected_by=current_user_id
        )
        
        db.session.add(collection)
        
        # Обновление статуса всех контейнеров на "пустой"
        for container in location.containers:
            container.status = 'empty'
            container.fill_level = 0
        
        # Обновление времени последнего сбора
        location.last_collection = datetime.utcnow()
        location.update_status()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Сбор мусора зарегистрирован',
            'collection': collection.to_dict(),
            'location': location.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка регистрации сбора: {str(e)}'}), 500

