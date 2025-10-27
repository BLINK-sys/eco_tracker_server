"""
Сервис для обновления данных контейнеров от реальных датчиков
Содержит логику обработки данных заполнения контейнеров
"""

from models import db, Container, Location
from socket_events import broadcast_container_update, has_active_connections, get_active_connections_count
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Импортируем FCM сервис для мобильных уведомлений
try:
    from fcm_service import send_container_notification, send_location_notification
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    logger.warning('FCM service not available, mobile notifications will be disabled')


def update_container_fill_level(container_id, new_fill_level):
    """
    Обновляет уровень заполнения контейнера и автоматически определяет статус
    
    Args:
        container_id: ID контейнера
        new_fill_level: новый уровень заполнения (0-100)
    
    Returns:
        dict: обновленные данные контейнера и площадки
    """
    try:
        # Удаляем старую сессию перед новым запросом (важно для gevent)
        db.session.remove()
        
        # Получаем контейнер в текущей сессии
        container = db.session.query(Container).filter_by(id=container_id).first()
        if not container:
            db.session.rollback()
            logger.warning(f'Container {container_id} not found')
            return None
        
        # Сохраняем старый статус ДО изменения
        old_status = container.status
        
        # Обновляем уровень заполнения
        container.fill_level = new_fill_level
        
        # Автоматически определяем статус по уровню заполнения
        if new_fill_level == 0:
            container.status = 'empty'
        elif new_fill_level < 70:
            container.status = 'partial'
        else:
            container.status = 'full'
        
        # Проверяем, изменился ли статус на 'full'
        status_changed_to_full = (old_status != 'full' and container.status == 'full')
        
        # Получаем location_id до обращения к relationship
        location_id = container.location_id
        company_id_for_log = None
        
        # Сначала commit изменений контейнера
        db.session.commit()
        
        # Теперь получаем площадку в свежей сессии и обновляем её статус
        location = db.session.query(Location).filter_by(id=location_id).first()
        if location:
            company_id_for_log = location.company_id
            
            # Сохраняем СТАРЫЙ статус площадки ДО пересчета
            old_location_status = location.status
            
            # Пересчитываем статус площадки
            location.update_status()
            
            # Проверяем, изменился ли статус ПЛОЩАДКИ на 'full'
            location_changed_to_full = (old_location_status != 'full' and location.status == 'full')
            
            # Логируем изменение статуса площадки
            if old_location_status != location.status:
                print(f"[LOCATION STATUS] {location.name}: {old_location_status} -> {location.status}")
            
            # Commit изменений площадки
            db.session.commit()
            
            # Обновляем объект контейнера после commit
            container = db.session.query(Container).filter_by(id=container_id).first()
            
            # Отправляем обновления
            if company_id_for_log:
                # 1. WebSocket для веб-пользователей (работает в реальном времени)
                print(f"[BROADCAST] Container {container.id}: {container.fill_level}% -> company_{company_id_for_log}")
                broadcast_container_update(container, location)
                
                # 2. FCM для мобильных пользователей (работает даже при закрытом приложении)
                # ОТПРАВЛЯЕМ ТОЛЬКО при изменении статуса ПЛОЩАДКИ на 'full'
                if FCM_AVAILABLE and location_changed_to_full:
                    try:
                        print(f"[FCM] ПЛОЩАДКА изменила статус на FULL: {old_location_status} -> {location.status}, отправляем уведомление")
                        print(f"[FCM] last_full_at: {location.last_full_at}")
                        send_location_notification(
                            location_data={
                                'id': str(location.id),
                                'name': location.name,
                                'status': location.status,
                                'company_id': str(location.company_id)
                            },
                            location_updated_at=location.last_full_at  # Передаем ТОЧНОЕ время когда стала full
                        )
                    except Exception as fcm_error:
                        logger.error(f'Error sending FCM location notification: {fcm_error}')
                elif FCM_AVAILABLE:
                    print(f"[FCM] Статус площадки: {old_location_status} -> {location.status}, FCM не отправляем")
            
            logger.info(f'Container {container_id} updated: fill_level={new_fill_level}%, status={container.status}')
            logger.info(f'Location {location.id} updated: status={location.status}')
            
            return {
                'container': container.to_dict(),
                'location_status': location.status
            }
        else:
            logger.warning(f'Location {location_id} not found for container {container_id}')
            return None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating container {container_id}: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        # Очищаем сессию после каждой операции
        db.session.remove()


def update_location_containers(location_id, containers_data):
    """
    Обновляет данные нескольких контейнеров одной площадки
    
    Args:
        location_id: ID площадки
        containers_data: список словарей [{"container_id": "uuid", "fill_level": 85}, ...]
    
    Returns:
        dict: результат обновления с данными площадки и контейнеров
    """
    try:
        # Проверяем существование площадки
        location = db.session.query(Location).filter_by(id=location_id).first()
        if not location:
            logger.warning(f'Location {location_id} not found')
            return {'success': False, 'error': 'Площадка не найдена'}
        
        results = []
        updated_containers = []
        errors = []
        
        # Обновляем каждый контейнер
        for container_data in containers_data:
            container_id = container_data.get('container_id')
            fill_level = container_data.get('fill_level')
            
            if not container_id or fill_level is None:
                errors.append(f'Неполные данные для контейнера: {container_data}')
                continue
                
            # Валидация уровня заполнения
            if not (0 <= fill_level <= 100):
                errors.append(f'Некорректный уровень заполнения {fill_level}% для контейнера {container_id}')
                continue
            
            # Проверяем что контейнер принадлежит указанной площадке
            container = db.session.query(Container).filter_by(
                id=container_id, 
                location_id=location_id
            ).first()
            
            if not container:
                errors.append(f'Контейнер {container_id} не найден на площадке {location_id}')
                continue
            
            # Обновляем контейнер
            result = update_container_fill_level(container_id, fill_level)
            if result:
                results.append(result)
                updated_containers.append({
                    'container_id': container_id,
                    'fill_level': fill_level,
                    'status': result['container']['status']
                })
            else:
                errors.append(f'Ошибка обновления контейнера {container_id}')
        
        # Получаем актуальный статус площадки после всех обновлений
        fresh_location = db.session.query(Location).filter_by(id=location_id).first()
        
        return {
            'success': True,
            'location': {
                'id': str(location_id),
                'name': fresh_location.name if fresh_location else location.name,
                'status': fresh_location.status if fresh_location else location.status,
                'company_id': str(fresh_location.company_id if fresh_location else location.company_id)
            },
            'updated_containers': updated_containers,
            'total_updated': len(updated_containers),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f'Error updating location containers: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': f'Ошибка обработки данных: {str(e)}'
        }
    finally:
        db.session.remove()
