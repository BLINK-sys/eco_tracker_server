from flask_socketio import emit, join_room, leave_room
from flask import request
from models import db, Container, Location
import logging

logger = logging.getLogger(__name__)

# Глобальный словарь для отслеживания активных подключений по компаниям
# company_id -> set of session IDs
active_company_connections = {}


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
        print(f"[DISCONNECT] Client {request.sid} disconnected")
        
        # Удаляем клиента из всех комнат компаний
        global active_company_connections
        removed_from_companies = []
        for company_id in list(active_company_connections.keys()):
            if request.sid in active_company_connections[company_id]:
                active_company_connections[company_id].remove(request.sid)
                removed_from_companies.append(company_id)
                logger.info(f'Removed {request.sid} from company {company_id} active connections')
                print(f"[DISCONNECT] Removed from company {company_id}")
                
                # Если больше нет подключений к этой компании, удаляем её
                if not active_company_connections[company_id]:
                    del active_company_connections[company_id]
                    logger.info(f'No active connections for company {company_id} - removed from tracking')
                    print(f"[DISCONNECT] Company {company_id} has no more active connections")
        
        if removed_from_companies:
            print(f"[DISCONNECT] Client removed from {len(removed_from_companies)} company room(s)")
        else:
            print(f"[DISCONNECT] Client {request.sid} was not in any company rooms")
    
    @socketio.on('join_company')
    def handle_join_company(data):
        """Клиент присоединяется к комнате компании для получения обновлений"""
        company_id = data.get('company_id')
        if company_id:
            join_room(f'company_{company_id}')
            
            # Отслеживаем активное подключение
            global active_company_connections
            if company_id not in active_company_connections:
                active_company_connections[company_id] = set()
                print(f"[JOIN] New company room created: {company_id}")
            
            active_company_connections[company_id].add(request.sid)
            
            logger.info(f'Client {request.sid} joined company room: {company_id}')
            logger.info(f'Active connections for company {company_id}: {len(active_company_connections[company_id])}')
            print(f"[JOIN] Client {request.sid} joined company {company_id}")
            print(f"[JOIN] Total active connections for company: {len(active_company_connections[company_id])}")
            emit('joined_company', {'company_id': company_id})
    
    @socketio.on('leave_company')
    def handle_leave_company(data):
        """Клиент покидает комнату компании"""
        company_id = data.get('company_id')
        if company_id:
            leave_room(f'company_{company_id}')
            
            # Удаляем из отслеживания
            global active_company_connections
            if company_id in active_company_connections:
                active_company_connections[company_id].discard(request.sid)
                if not active_company_connections[company_id]:
                    del active_company_connections[company_id]
            
            logger.info(f'Client {request.sid} left company room: {company_id}')


# Глобальная ссылка на socketio (будет установлена из app.py)
_socketio = None

def set_socketio(socketio_instance):
    """Устанавливает глобальную ссылку на socketio"""
    global _socketio
    _socketio = socketio_instance
    print("[OK] SocketIO instance registered in socket_events")


def has_active_connections(company_id):
    """
    Проверяет, есть ли активные WebSocket подключения для компании
    
    Args:
        company_id: ID компании
    
    Returns:
        bool: True если есть активные подключения, False в противном случае
    """
    global active_company_connections
    return company_id in active_company_connections and len(active_company_connections[company_id]) > 0


def get_active_companies():
    """
    Возвращает список ID компаний с активными подключениями
    
    Returns:
        list: список ID компаний
    """
    global active_company_connections
    return list(active_company_connections.keys())


def get_active_connections_count(company_id=None):
    """
    Возвращает количество активных подключений
    
    Args:
        company_id: ID компании (опционально). Если не указан, возвращает общее количество
    
    Returns:
        int: количество активных подключений
    """
    global active_company_connections
    if company_id:
        count = len(active_company_connections.get(company_id, set()))
        print(f"[CONNECTION CHECK] Company {company_id}: {count} connections")
        print(f"[CONNECTION CHECK] All companies: {list(active_company_connections.keys())}")
        return count
    else:
        total = sum(len(connections) for connections in active_company_connections.values())
        print(f"[CONNECTION CHECK] Total connections: {total}")
        return total


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
    
    # Проверяем, есть ли активные подключения для этой компании
    if not has_active_connections(location.company_id):
        # Не отправляем обновления, если никто не подключен
        logger.debug(f'No active connections for company {location.company_id}, skipping broadcast')
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
    print(f"            Active clients: {get_active_connections_count(location.company_id)}")
    
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
    
    # Проверяем, есть ли активные подключения для этой компании
    if not has_active_connections(location.company_id):
        logger.debug(f'No active connections for company {location.company_id}, skipping broadcast')
        return
    
    # Отправляем обновление только клиентам этой компании
    _socketio.emit(
        'location_updated',
        location.to_dict(),
        room=f'company_{location.company_id}'
    )
    
    logger.info(f'Broadcast location update to company {location.company_id}: {location.id}')

