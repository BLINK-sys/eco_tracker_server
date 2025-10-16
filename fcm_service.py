"""
Сервис для отправки FCM уведомлений мобильным пользователям
WebSocket уведомления для веб-пользователей остаются без изменений
"""

from firebase_admin import messaging
from firebase_config import is_firebase_available
from models import db, FCMToken, User
import logging

logger = logging.getLogger(__name__)


def send_container_notification(container_data, location_data, container_updated_at=None):
    """
    Отправляет FCM уведомление о заполненном контейнере
    ТОЛЬКО мобильным пользователям (у которых есть FCM токены)
    И ТОЛЬКО если контейнер был обновлен ПОСЛЕ того, как пользователь свернул приложение
    Веб-пользователи получают уведомления через WebSocket
    
    Args:
        container_data: dict с данными контейнера (id, number, status, fill_level)
        location_data: dict с данными площадки (id, name, company_id)
        container_updated_at: datetime когда контейнер был обновлен (опционально)
    """
    if not is_firebase_available():
        logger.debug('Firebase недоступен, FCM уведомления отключены')
        return
    
    # Добавляем проверку только для заполненных контейнеров
    if container_data.get('status') != 'full':
        logger.debug(f'Контейнер {container_data.get("id")} не заполнен ({container_data.get("status")}), FCM уведомление не отправляется')
        return
    
    try:
        # Получаем всех пользователей компании
        company_id = location_data['company_id']
        users = User.query.filter_by(parent_company_id=company_id).all()
        
        if not users:
            logger.debug(f'Нет пользователей для компании {company_id}')
            return
        
        # Собираем FCM токены только тех пользователей, которые НЕ были активны после обновления контейнера
        fcm_tokens = []
        for user in users:
            for token_obj in user.fcm_tokens:
                # Если указано время обновления контейнера
                if container_updated_at:
                    print(f'[FCM CHECK] Пользователь: {user.email}')
                    print(f'            last_seen_at: {token_obj.last_seen_at}')
                    print(f'            updated_at: {container_updated_at}')
                    print(f'            Разница: {(container_updated_at - token_obj.last_seen_at).total_seconds()} сек')
                    
                    # Отправляем уведомление только если пользователь не был активен после обновления
                    if token_obj.last_seen_at < container_updated_at:
                        fcm_tokens.append(token_obj.token)
                        print(f'            ✅ ОТПРАВЛЯЕМ уведомление')
                        logger.info(f'📱 FCM: Пользователь {user.email} неактивен с {token_obj.last_seen_at}, отправляем уведомление')
                    else:
                        print(f'            ⏭️ ПРОПУСКАЕМ (пользователь был активен)')
                        logger.info(f'⏭️ FCM: Пользователь {user.email} был активен в {token_obj.last_seen_at}, пропускаем уведомление')
                else:
                    # Если время не указано, отправляем всем (старое поведение)
                    fcm_tokens.append(token_obj.token)
                    print(f'[FCM CHECK] Пользователь: {user.email} - время не указано, отправляем всем')
        
        if not fcm_tokens:
            logger.debug(f'Нет FCM токенов для отправки (все пользователи уже видели обновление)')
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
        
        # Пробуем отправить каждое уведомление отдельно
        success_count = 0
        for token in fcm_tokens:
            try:
                single_message = messaging.Message(
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
                    token=token,
                )
                response = messaging.send(single_message)
                logger.info(f'📱 FCM: Уведомление отправлено на токен {token[:20]}...: {response}')
                success_count += 1
            except Exception as token_error:
                logger.error(f'❌ Ошибка отправки на токен {token[:20]}...: {token_error}')
        
        logger.info(f'📱 FCM: Отправлено уведомлений: {success_count}/{len(fcm_tokens)}')
        
        return success_count
        
    except Exception as e:
        logger.error(f'❌ Ошибка отправки FCM уведомления: {e}')
        return 0


def send_location_notification(location_data, location_updated_at=None):
    """
    Отправляет FCM уведомление о заполненной площадке
    ТОЛЬКО мобильным пользователям, которые НЕ были активны после обновления
    
    Args:
        location_data: dict с данными площадки (id, name, status, company_id)
        location_updated_at: datetime когда площадка была обновлена (опционально)
    """
    if not is_firebase_available():
        logger.debug('Firebase недоступен, FCM уведомления отключены')
        return
    
    # Отправляем уведомления только для заполненных площадок
    if location_data.get('status') != 'full':
        logger.debug(f'Площадка {location_data.get("id")} не заполнена ({location_data.get("status")}), FCM уведомление не отправляется')
        return
    
    try:
        company_id = location_data['company_id']
        users = User.query.filter_by(parent_company_id=company_id).all()
        
        if not users:
            logger.debug(f'Нет пользователей для компании {company_id}')
            return
        
        # Собираем FCM токены только тех пользователей, которые НЕ были активны после обновления площадки
        # ВАЖНО: используем set для де-дупликации токенов (один пользователь может иметь несколько токенов)
        fcm_tokens_set = set()
        user_token_count = {}  # Для отладки
        
        for user in users:
            user_tokens_added = 0
            for token_obj in user.fcm_tokens:
                # Если указано время обновления площадки
                if location_updated_at:
                    print(f'[FCM LOCATION CHECK] Пользователь: {user.email}')
                    print(f'                     Токен: {token_obj.token[:20]}...')
                    print(f'                     last_seen_at: {token_obj.last_seen_at}')
                    print(f'                     updated_at: {location_updated_at}')
                    
                    if token_obj.last_seen_at and location_updated_at:
                        print(f'                     Разница: {(location_updated_at - token_obj.last_seen_at).total_seconds()} сек')
                    
                    # Отправляем уведомление только если пользователь не был активен после обновления
                    if token_obj.last_seen_at < location_updated_at:
                        if token_obj.token not in fcm_tokens_set:
                            fcm_tokens_set.add(token_obj.token)
                            user_tokens_added += 1
                            print(f'                     ✅ ОТПРАВЛЯЕМ уведомление о площадке')
                            logger.info(f'📱 FCM: Пользователь {user.email} неактивен, отправляем уведомление о площадке')
                        else:
                            print(f'                     ⚠️ ДУБЛЬ ТОКЕНА, уже добавлен ранее')
                    else:
                        print(f'                     ⏭️ ПРОПУСКАЕМ (пользователь был активен)')
                        logger.info(f'⏭️ FCM: Пользователь {user.email} был активен, пропускаем уведомление о площадке')
                else:
                    # Если время не указано, отправляем всем (старое поведение)
                    if token_obj.token not in fcm_tokens_set:
                        fcm_tokens_set.add(token_obj.token)
                        user_tokens_added += 1
                        print(f'[FCM LOCATION CHECK] Пользователь: {user.email} - время не указано, отправляем всем')
                    else:
                        print(f'[FCM LOCATION CHECK] Пользователь: {user.email} - ДУБЛЬ ТОКЕНА')
            
            if user_tokens_added > 0:
                user_token_count[user.email] = user_tokens_added
        
        # Конвертируем set в list для дальнейшей обработки
        fcm_tokens = list(fcm_tokens_set)
        
        if user_token_count:
            print(f'[FCM DEDUP] Токенов по пользователям: {user_token_count}')
            print(f'[FCM DEDUP] ИТОГО уникальных токенов: {len(fcm_tokens)}')
        
        if not fcm_tokens:
            logger.debug(f'Нет FCM токенов для отправки (все пользователи уже видели обновление площадки)')
            return
        
        status_text = 'заполнена'  # Всегда заполнена, т.к. проверяем выше
        
        title = f'Площадка {status_text}!'
        body = f'{location_data["name"]}: все контейнеры заполнены'
        
        # Отправляем индивидуально каждому токену
        import time
        fcm_call_id = f"LOCATION_{int(time.time() * 1000)}"  # Миллисекунды для уникальности
        
        logger.info(f'📱 FCM LOCATION: Отправка {len(fcm_tokens)} уведомлений о площадке...')
        print(f'[FCM LOCATION] CALL_ID: {fcm_call_id} - Отправляем {len(fcm_tokens)} уведомлений для площадки {location_data["name"]}')
        print(f'[FCM LOCATION] CALL_ID: {fcm_call_id} - Токены: {[token[:20] + "..." for token in fcm_tokens[:3]]}')  # Показываем первые 3 токена
        
        success_count = 0
        for i, token in enumerate(fcm_tokens):
            try:
                print(f'[FCM LOCATION] CALL_ID: {fcm_call_id} - Отправка {i+1}/{len(fcm_tokens)} на токен {token[:20]}...')
                single_message = messaging.Message(
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
                    token=token,
                )
                response = messaging.send(single_message)
                logger.info(f'📱 FCM LOCATION: Уведомление отправлено на токен {token[:20]}...: {response}')
                print(f'[FCM LOCATION] CALL_ID: {fcm_call_id} - ✅ Уведомление {i+1} отправлено: {response}')
                success_count += 1
            except Exception as token_error:
                logger.error(f'❌ Ошибка отправки на токен {token[:20]}...: {token_error}')
                print(f'[FCM LOCATION] CALL_ID: {fcm_call_id} - ❌ Ошибка отправки {i+1}: {token_error}')
        
        logger.info(f'📱 FCM LOCATION: Отправлено уведомлений о площадке: {success_count}/{len(fcm_tokens)}')
        print(f'[FCM LOCATION] CALL_ID: {fcm_call_id} - ИТОГО: {success_count}/{len(fcm_tokens)} уведомлений отправлено')
        
        return success_count
        
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

