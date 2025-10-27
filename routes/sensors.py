from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Container, Location
from container_service import update_container_fill_level, update_location_containers
import random
import logging

logger = logging.getLogger(__name__)

sensors_bp = Blueprint('sensors', __name__)


@sensors_bp.route('/update', methods=['POST', 'OPTIONS'])
def sensor_update():
    """
    Endpoint для получения данных от датчиков IoT
    В реальной системе датчики будут отправлять данные сюда
    
    Формат данных:
    {
        "container_id": "uuid",
        "fill_level": 85,  // 0-100%
        "timestamp": "2024-01-01T12:00:00"
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data or 'container_id' not in data or 'fill_level' not in data:
            return jsonify({'error': 'Необходимы container_id и fill_level'}), 400
        
        container_id = data['container_id']
        fill_level = int(data['fill_level'])
        
        # Валидация уровня заполнения
        if fill_level < 0 or fill_level > 100:
            return jsonify({'error': 'fill_level должен быть от 0 до 100'}), 400
        
        # Обновляем контейнер (автоматически пересчитывается статус и отправляется через WebSocket)
        result = update_container_fill_level(container_id, fill_level)
        
        if not result:
            return jsonify({'error': 'Контейнер не найден'}), 404
        
        return jsonify({
            'message': 'Данные датчика обработаны',
            'container': result['container'],
            'location_status': result['location_status']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка обработки данных: {str(e)}'}), 500


@sensors_bp.route('/location-update', methods=['POST', 'OPTIONS'])
def location_sensor_update():
    """
    Основной endpoint для получения данных от датчиков по площадке
    Принимает данные о заполнении нескольких контейнеров одной площадки
    
    Формат данных:
    {
        "location_id": "uuid",
        "containers": [
            {
                "container_id": "uuid1",
                "fill_level": 85
            },
            {
                "container_id": "uuid2", 
                "fill_level": 45
            }
        ],
        "timestamp": "2024-01-01T12:00:00"  // опционально
    }
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Пытаемся получить JSON данные, даже если Content-Type не установлен правильно
        data = request.get_json(force=True, silent=True)
        
        # Если get_json не сработал, пробуем парсить вручную
        if not data:
            try:
                import json
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    data = json.loads(raw_data)
                    logger.info(f'Parsed JSON manually from raw data: {len(raw_data)} chars')
            except Exception as parse_error:
                logger.warning(f'Failed to parse JSON manually: {parse_error}')
        
        if not data:
            logger.error(f'No JSON data received. Content-Type: {request.content_type}, Raw data: {request.get_data(as_text=True)[:200]}')
            return jsonify({'error': 'Данные не предоставлены или неверный формат JSON'}), 400
            
        location_id = data.get('location_id')
        containers_data = data.get('containers', [])
        
        if not location_id:
            return jsonify({'error': 'Необходимо указать location_id'}), 400
            
        if not containers_data:
            return jsonify({'error': 'Необходимо указать данные контейнеров'}), 400
        
        # Валидация данных контейнеров
        for container_data in containers_data:
            if not isinstance(container_data, dict):
                return jsonify({'error': 'Неверный формат данных контейнера'}), 400
                
            if 'container_id' not in container_data or 'fill_level' not in container_data:
                return jsonify({'error': 'Каждый контейнер должен содержать container_id и fill_level'}), 400
                
            try:
                fill_level = int(container_data['fill_level'])
                if not (0 <= fill_level <= 100):
                    return jsonify({'error': f'fill_level должен быть от 0 до 100, получен: {fill_level}'}), 400
                container_data['fill_level'] = fill_level
            except (ValueError, TypeError):
                return jsonify({'error': f'fill_level должен быть числом, получен: {container_data["fill_level"]}'}), 400
        
        # Обновляем контейнеры площадки
        result = update_location_containers(location_id, containers_data)
        
        if not result['success']:
            return jsonify({'error': result.get('error', 'Ошибка обработки данных')}), 400
        
        response_data = {
            'message': 'Данные датчиков успешно обработаны',
            'location': result['location'],
            'updated_containers': result['updated_containers'],
            'total_updated': result['total_updated']
        }
        
        # Добавляем информацию об ошибках если есть
        if result.get('errors'):
            response_data['warnings'] = result['errors']
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f'Error in location sensor update: {str(e)}')
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@sensors_bp.route('/test-update/<string:container_id>', methods=['POST'])
def test_sensor_update(container_id):
    """
    Тестовый endpoint для симуляции данных датчика
    Используется для отладки
    """
    try:
        data = request.get_json() or {}
        fill_level = int(data.get('fill_level', random.randint(0, 100)))
        
        result = update_container_fill_level(container_id, fill_level)
        
        if not result:
            return jsonify({'error': 'Контейнер не найден'}), 404
        
        return jsonify({
            'message': 'Тестовое обновление выполнено',
            'container': result['container'],
            'location_status': result['location_status']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500

