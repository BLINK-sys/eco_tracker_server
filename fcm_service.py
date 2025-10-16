"""
Сервис для отправки FCM уведомлений мобильным пользователям
WebSocket уведомления для веб-пользователей остаются без изменений
"""

from firebase_admin import messaging
from firebase_config import is_firebase_available
from models import db, FCMToken, User
import logging

logger = logging.getLogger(__name__)


def send_container_notification(container_data, location_data):
    """
    Отправляет FCM уведомление о заполненном контейнере
    ТОЛЬКО мобильным пользователям (у которых есть FCM токены)
    Веб-пользователи получают уведомления через WebSocket
    
    Args:
        container_data: dict с данными контейнера (id, number, status, fill_level)
        location_data: dict с данными площадки (id, name, company_id)
    """
    if not is_firebase_available():
        logger.debug('Firebase недоступен, FCM уведомления отключены')
        return
    
    try:
        # Получаем всех пользователей компании
        company_id = location_data['company_id']
        users = User.query.filter_by(parent_company_id=company_id).all()
        
        if not users:
            logger.debug(f'Нет пользователей для компании {company_id}')
            return
        
        # Собираем FCM токены всех пользователей компании
        fcm_tokens = []
        for user in users:
            for token_obj in user.fcm_tokens:
                fcm_tokens.append(token_obj.token)
        
        if not fcm_tokens:
            logger.debug(f'Нет FCM токенов для компании {company_id}')
            return
        
        # Формируем текст уведомления
        status_text = {
            'full': 'заполнен',
            'partial': 'частично заполнен',
            'empty': 'пустой'
        }.get(container_data.get('status', 'unknown'), 'обновлен')
        
        title = 'Контейнер ' + status_text + '!'
        body = f'{location_data["name"]}: контейнер №{container_data["number"]} {status_text}'
        
        # Создаём уведомление
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                'location_id': str(location_data['id']),
                'location_name': location_data['name'],
                'container_id': str(container_data['id']),
                'container_number': str(container_data['number']),
                'status': container_data.get('status', 'unknown'),
                'fill_level': str(container_data.get('fill_level', 0)),
                'payload': 'container_updated',
            },
            tokens=fcm_tokens,
        )
        
        # Отправляем
        logger.info(f'📱 FCM: Отправка {len(fcm_tokens)} уведомлений...')
        logger.info(f'📱 FCM: Токены: {fcm_tokens[:2]}...')  # Показываем первые 2 токена
        response = messaging.send_multicast(message)
        logger.info(f'📱 FCM: Отправлено уведомлений: {response.success_count}/{len(fcm_tokens)}')
        
        # Удаляем недействительные токены
        if response.failure_count > 0:
            _remove_invalid_tokens(response, fcm_tokens)
        
        return response.success_count
        
    except Exception as e:
        logger.error(f'❌ Ошибка отправки FCM уведомления: {e}')
        return 0


def send_location_notification(location_data):
    """
    Отправляет FCM уведомление о заполненной площадке
    ТОЛЬКО мобильным пользователям
    
    Args:
        location_data: dict с данными площадки (id, name, status, company_id)
    """
    if not is_firebase_available():
        return
    
    try:
        company_id = location_data['company_id']
        users = User.query.filter_by(parent_company_id=company_id).all()
        
        fcm_tokens = []
        for user in users:
            for token_obj in user.fcm_tokens:
                fcm_tokens.append(token_obj.token)
        
        if not fcm_tokens:
            return
        
        status_text = {
            'full': 'заполнена',
            'partial': 'частично заполнена',
            'empty': 'пустая'
        }.get(location_data.get('status', 'unknown'), 'обновлена')
        
        title = f'Площадка {status_text}!'
        body = f'{location_data["name"]}: {status_text}'
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                'location_id': str(location_data['id']),
                'location_name': location_data['name'],
                'status': location_data.get('status', 'unknown'),
                'payload': 'location_updated',
            },
            tokens=fcm_tokens,
        )
        
        response = messaging.send_multicast(message)
        logger.info(f'📱 FCM: Отправлено уведомлений о площадке: {response.success_count}/{len(fcm_tokens)}')
        
        if response.failure_count > 0:
            _remove_invalid_tokens(response, fcm_tokens)
        
        return response.success_count
        
    except Exception as e:
        logger.error(f'❌ Ошибка отправки FCM уведомления о площадке: {e}')
        return 0


def send_to_company_topic(company_id, notification_data):
    """
    Отправляет уведомление на топик компании
    Все мобильные пользователи, подписанные на топик, получат уведомление
    
    Args:
        company_id: ID компании
        notification_data: dict с title, body, и опционально data
    """
    if not is_firebase_available():
        return
    
    try:
        topic = f'company_{company_id}'
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=notification_data['title'],
                body=notification_data['body'],
            ),
            data=notification_data.get('data', {}),
            topic=topic,
        )
        
        response = messaging.send(message)
        logger.info(f'📱 FCM: Уведомление отправлено на топик {topic}: {response}')
        return response
        
    except Exception as e:
        logger.error(f'❌ Ошибка отправки на топик: {e}')
        return None


def _remove_invalid_tokens(response, tokens):
    """
    Удаляет недействительные FCM токены из базы данных
    
    Args:
        response: MulticastMessage response от Firebase
        tokens: список токенов в том же порядке, что и в запросе
    """
    try:
        invalid_tokens = []
        for idx, send_response in enumerate(response.responses):
            if not send_response.success:
                # Проверяем код ошибки
                if send_response.exception:
                    error_code = getattr(send_response.exception, 'code', None)
                    # Удаляем только если токен недействителен или устройство отписалось
                    if error_code in ['invalid-registration-token', 'registration-token-not-registered']:
                        invalid_tokens.append(tokens[idx])
        
        if invalid_tokens:
            # Удаляем недействительные токены
            FCMToken.query.filter(FCMToken.token.in_(invalid_tokens)).delete(synchronize_session=False)
            db.session.commit()
            logger.info(f'🗑️ Удалено недействительных FCM токенов: {len(invalid_tokens)}')
            
    except Exception as e:
        logger.error(f'❌ Ошибка удаления недействительных токенов: {e}')
        db.session.rollback()

