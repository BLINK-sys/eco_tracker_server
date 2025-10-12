from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Container
from sensor_simulator import update_container_fill_level

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

