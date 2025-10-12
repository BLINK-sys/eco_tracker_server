from flask_socketio import emit, join_room, leave_room
from flask import request
from models import db, Container, Location
import logging

logger = logging.getLogger(__name__)


def register_socket_events(socketio):
    """Регистрация обработчиков WebSocket событий"""
    
    @socketio.on('connect')
    def handle_connect():
        """Обработчик подключения клиента"""
        logger.info(f'Client connected: {request.sid}')
        emit('connection_response', {'data': 'Connected to EcoTracker server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Обработчик отключения клиента"""
        logger.info(f'Client disconnected: {request.sid}')
    
    @socketio.on('join_company')
    def handle_join_company(data):
        """Клиент присоединяется к комнате компании для получения обновлений"""
        company_id = data.get('company_id')
        if company_id:
            join_room(f'company_{company_id}')
            logger.info(f'Client {request.sid} joined company room: {company_id}')
            emit('joined_company', {'company_id': company_id})
    
    @socketio.on('leave_company')
    def handle_leave_company(data):
        """Клиент покидает комнату компании"""
        company_id = data.get('company_id')
        if company_id:
            leave_room(f'company_{company_id}')
            logger.info(f'Client {request.sid} left company room: {company_id}')


# Глобальная ссылка на socketio (будет установлена из app.py)
_socketio = None

def set_socketio(socketio_instance):
    """Устанавливает глобальную ссылку на socketio"""
    global _socketio
    _socketio = socketio_instance
    print("[OK] SocketIO instance registered in socket_events")


def broadcast_container_update(container, location):
    """
    Отправляет обновление контейнера всем клиентам компании
    
    Args:
        container: обновленный контейнер
        location: площадка, к которой принадлежит контейнер
    """
    global _socketio
    
    if not _socketio:
        print("[WARNING] SocketIO not initialized!")
        return
    
    if not location.company_id:
        print(f"[WARNING] Location {location.id} has no company_id!")
        return
    
    update_data = {
        'container': container.to_dict(),
        'location': {
            'id': location.id,
            'status': location.status,
            'name': location.name
        }
    }
    
    room_name = f'company_{location.company_id}'
    
    print(f"[BROADCAST] Sending 'container_updated' to room: {room_name}")
    print(f"            Container: {container.id}, fill_level: {container.fill_level}%")
    
    # Отправляем обновление только клиентам этой компании
    _socketio.emit(
        'container_updated',
        update_data,
        room=room_name
    )
    
    logger.info(f'Broadcast container update to company {location.company_id}: {container.id}')


def broadcast_location_update(location):
    """
    Отправляет обновление площадки всем клиентам компании
    
    Args:
        location: обновленная площадка
    """
    global _socketio
    
    if not _socketio or not location.company_id:
        return
    
    # Отправляем обновление только клиентам этой компании
    _socketio.emit(
        'location_updated',
        location.to_dict(),
        room=f'company_{location.company_id}'
    )
    
    logger.info(f'Broadcast location update to company {location.company_id}: {location.id}')

