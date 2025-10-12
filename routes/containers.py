from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Container, Location
from datetime import datetime

containers_bp = Blueprint('containers', __name__)


@containers_bp.route('/<string:container_id>', methods=['GET'])
def get_container(container_id):
    """Получение информации о контейнере"""
    try:
        container = Container.query.get(container_id)
        
        if not container:
            return jsonify({'error': 'Контейнер не найден'}), 404
        
        return jsonify(container.to_dict()), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка получения контейнера: {str(e)}'}), 500


@containers_bp.route('/<string:container_id>', methods=['PUT'])
@jwt_required()
def update_container(container_id):
    """Обновление статуса контейнера"""
    try:
        container = Container.query.get(container_id)
        
        if not container:
            return jsonify({'error': 'Контейнер не найден'}), 404
        
        data = request.get_json()
        
        # Обновление полей
        if 'status' in data:
            container.status = data['status']
        
        if 'fill_level' in data:
            fill_level = int(data['fill_level'])
            container.fill_level = fill_level
            
            # Автоматическое определение статуса по уровню заполнения
            if fill_level == 0:
                container.status = 'empty'
            elif fill_level < 70:
                container.status = 'partial'
            else:
                container.status = 'full'
        
        container.updated_at = datetime.utcnow()
        
        # Обновление статуса площадки
        location = container.location
        location.update_status()
        location.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Контейнер обновлен успешно',
            'container': container.to_dict(),
            'location_status': location.status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления контейнера: {str(e)}'}), 500


@containers_bp.route('', methods=['POST'])
@jwt_required()
def create_container():
    """Создание нового контейнера"""
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['location_id', 'number']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        # Проверка существования площадки
        location = Location.query.get(data['location_id'])
        if not location:
            return jsonify({'error': 'Площадка не найдена'}), 404
        
        # Создание контейнера (UUID генерируется автоматически)
        container = Container(
            location_id=data['location_id'],
            number=int(data['number']),
            status=data.get('status', 'empty'),
            fill_level=int(data.get('fill_level', 0))
        )
        
        db.session.add(container)
        db.session.flush()
        
        # Обновление статуса площадки
        location.update_status()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Контейнер создан успешно',
            'container': container.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания контейнера: {str(e)}'}), 500


@containers_bp.route('/<string:container_id>', methods=['DELETE'])
@jwt_required()
def delete_container(container_id):
    """Удаление контейнера"""
    try:
        container = Container.query.get(container_id)
        
        if not container:
            return jsonify({'error': 'Контейнер не найден'}), 404
        
        location = container.location
        
        db.session.delete(container)
        
        # Обновление статуса площадки
        location.update_status()
        
        db.session.commit()
        
        return jsonify({'message': 'Контейнер удален успешно'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления контейнера: {str(e)}'}), 500

