"""
Симулятор датчиков контейнеров
Эмулирует поступление данных от реальных датчиков уровня заполнения
"""

import time
import random
import threading
from models import db, Container, Location
from socket_events import broadcast_container_update, has_active_connections, get_active_connections_count
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Импортируем FCM сервис (будет использоваться для мобильных пользователей)
try:
    from fcm_service import send_container_notification, send_location_notification
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    logger.warning('FCM service not available, mobile notifications will be disabled')

# Кэш последней отправки уведомления по площадке, чтобы избегать дублей
# location_id -> datetime(last_full_at)
last_notified_at_by_location = {}


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


def simulate_sensor_data(app):
    """
    Циклическая симуляция датчиков только для компании ТОО EcoTracker
    Распределение площадок по статусам:
    Стадия 1: 1 требует внимание, 1 частично, 1 пустая
    Стадия 2: 1 требует внимание, 2 частично
    Стадия 3: 2 требует внимание, 1 частично
    Стадия 4: 3 требует внимание
    Стадия 5: 3 пустые
    Стадия 6: 2 пустые, 1 частично
    Затем цикл повторяется
    """
    print("=" * 60)
    print("SENSOR SIMULATOR STARTED - ECOTRACKER LOCATIONS")
    print("6 stages cycle every 10 seconds")
    print("Getting company ID from database...")
    print("=" * 60)
    
    with app.app_context():
        logger.info('Sensor simulator starting - getting company ID...')
        
        # Получаем ID компании ТОО EcoTracker динамически
        from models import Company
        company = Company.query.filter_by(name='ТОО EcoTracker').first()
        
        if not company:
            logger.error('Company "ТОО EcoTracker" not found in database')
            print("[ERROR] Company 'ТОО EcoTracker' not found in database")
            return
        
        ECOTRACKER_COMPANY_ID = company.id
        logger.info(f'Sensor simulator found company ID: {ECOTRACKER_COMPANY_ID}')
        
        print(f"[OK] Found company: ТОО EcoTracker ({ECOTRACKER_COMPANY_ID})")
        print("Starting sensor simulation...")
        
        # НОВАЯ ЛОГИКА: Циклическое изменение уровня заполнения для каждой площадки
        # ЛОГИКА: Каждая площадка становится FULL ровно 1 раз за все циклы
        # Через один цикл: все пустые/частично заполненные
        # Через один цикл: ровно 1 площадка FULL (по очереди)
        
        # Определение стадий для КАЖДОЙ площадки индивидуально
        # Каждая площадка имеет 12 стадий (6 циклов × 2 стадии)
        # Стадии: 0,1,2,3,4,5,6,7,8,9,10,11
        # Циклы: 0,0,1,1,2,2,3,3,4,4,5,5
        # В каждом цикле: 1 стадия = пустая/частичная, 1 стадия = одна площадка FULL
        
        location_cycles = {
            # Площадка 0: FULL на стадии 2 (цикл 1)
            0: [0, 60, 100, 60, 0, 60, 0, 60, 0, 0, 60, 0],
            # Площадка 1: FULL на стадии 4 (цикл 2) 
            1: [60, 0, 60, 60, 100, 0, 0, 60, 0, 0, 60, 60],
            # Площадка 2: FULL на стадии 6 (цикл 3)
            2: [0, 60, 0, 60, 0, 0, 100, 0, 60, 60, 0, 60],
            # Площадка 3: FULL на стадии 8 (цикл 4)
            3: [0, 0, 0, 60, 0, 0, 0, 60, 100, 0, 60, 0],
            # Площадка 4: FULL на стадии 10 (цикл 5)
            4: [60, 0, 0, 0, 0, 0, 60, 60, 0, 0, 100, 0],
            # Площадка 5+: повторяем паттерн
            5: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            6: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            7: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        }
        
        current_stage = 0
        
        print("LOGIC: Каждая площадка становится FULL ровно 1 раз за 12 стадий")
        print("       Через один цикл: все пустые/частично заполненные")
        print("       Через один цикл: ровно 1 площадка FULL (по очереди)")
        
        while True:
            try:
                # Очищаем сессию перед каждой итерацией
                db.session.remove()
                
                # Проверяем, есть ли активные подключения для компании ТОО EcoTracker
                active_connections = get_active_connections_count(ECOTRACKER_COMPANY_ID)
                print(f"[SIMULATOR CHECK] Active WebSocket connections: {active_connections}")
                
                # Проверяем, есть ли мобильные пользователи (FCM токены)
                mobile_users_count = 0
                if FCM_AVAILABLE:
                    from models import User, FCMToken
                    # Получаем пользователей компании с FCM токенами
                    users_with_fcm = db.session.query(User).filter_by(
                        parent_company_id=ECOTRACKER_COMPANY_ID
                    ).join(FCMToken).count()
                    mobile_users_count = users_with_fcm
                    print(f"[SIMULATOR CHECK] Mobile users with FCM: {mobile_users_count}")
                else:
                    print(f"[SIMULATOR CHECK] FCM not available")
                
                # Если нет ни веб-пользователей, ни мобильных - переходим в режим ожидания
                if active_connections == 0 and mobile_users_count == 0:
                    print(f"\n[IDLE] No active users for EcoTracker company")
                    print(f"       WebSocket connections: {active_connections}, Mobile users: {mobile_users_count}")
                    print(f"       Waiting for users to connect... (checking every 10 seconds)")
                    time.sleep(10)
                    continue
                
                print(f"\n[ACTIVE] Users detected for EcoTracker:")
                print(f"         WebSocket connections: {active_connections}")
                print(f"         Mobile users (FCM): {mobile_users_count}")
                
                # Получаем только площадки компании ТОО EcoTracker
                ecotracker_locations = Location.query.filter_by(company_id=ECOTRACKER_COMPANY_ID).order_by(Location.name).all()
                
                if not ecotracker_locations:
                    print("No EcoTracker locations found, waiting...")
                    time.sleep(10)
                    continue
                
                stage_num = current_stage + 1
                
                print(f"\n{'='*60}")
                print(f"STAGE {stage_num}/12 - Updating {len(ecotracker_locations)} locations")
                print(f"{'='*60}")
                
                updated_count = 0
                locations_changed = {
                    'to_full': [],
                    'to_partial': [],
                    'to_empty': []
                }
                
                # Обновляем КАЖДУЮ площадку согласно её индивидуальному циклу
                for idx, location in enumerate(ecotracker_locations):
                    try:
                        # Получаем цикл для этой площадки (повторяем паттерн для площадок > 4)
                        cycle_pattern = location_cycles.get(idx % len(location_cycles), location_cycles[0])
                        target_fill_level = cycle_pattern[current_stage]
                        
                        # Определяем целевой статус
                        if target_fill_level == 0:
                            target_status = 'empty'
                        elif target_fill_level == 100:
                            target_status = 'full'
                        else:
                            target_status = 'partial'
                        
                        # Получаем контейнеры через явный запрос (избегаем lazy load)
                        location_containers = db.session.query(Container).filter_by(
                            location_id=location.id
                        ).all()
                        
                        if not location_containers:
                            continue
                        
                        # Проверяем, нужно ли обновлять контейнеры
                        containers_need_update = any(c.fill_level != target_fill_level for c in location_containers)
                        
                        if containers_need_update:
                            old_status = location.status
                            containers_updated = 0
                            
                            # Обновляем ВСЕ контейнеры площадки до одинакового уровня
                            # НО НЕ отправляем FCM уведомления для каждого контейнера
                            for container in location_containers:
                                if container.fill_level != target_fill_level:
                                    # Обновляем только fill_level и status, БЕЗ отправки FCM
                                    container.fill_level = target_fill_level
                                    
                                    # Автоматически определяем статус по уровню заполнения
                                    if target_fill_level == 0:
                                        container.status = 'empty'
                                    elif target_fill_level < 70:
                                        container.status = 'partial'
                                    else:
                                        container.status = 'full'
                                    
                                    containers_updated += 1
                            
                            # Commit изменений контейнеров
                            db.session.commit()
                            
                            # Получаем свежую площадку и обновляем её статус
                            updated_location = db.session.query(Location).filter_by(id=location.id).first()
                            if updated_location:
                                print(f"[STATUS UPDATE] {location.name}: обновляем статус площадки...")
                                updated_location.update_status()
                                db.session.commit()
                                new_status = updated_location.status
                                print(f"[STATUS UPDATE] {location.name}: статус в БД = {new_status}")
                            else:
                                new_status = target_status
                                print(f"[STATUS UPDATE] {location.name}: площадка не найдена, используем target_status = {target_status}")
                            
                            # КРИТИЧЕСКИ ВАЖНО: Получаем СВЕЖИЙ объект из БД после commit для FCM проверки
                            # Это гарантирует что мы проверяем актуальный статус
                            fresh_location_for_fcm = db.session.query(Location).filter_by(id=location.id).first()
                            
                            # Отправляем FCM уведомление ТОЛЬКО ОДИН РАЗ для площадки
                            # И ТОЛЬКО если статус действительно изменился на 'full'
                            if FCM_AVAILABLE and old_status != 'full' and new_status == 'full':
                                try:
                                    # Уникальный ID для отслеживания дублирования
                                    fcm_id = f"{location.id}_{int(time.time() * 1000)}"
                                    
                                    print(f"\n{'='*80}")
                                    print(f"[FCM CHECK] ПЛОЩАДКА {location.name}")
                                    print(f"[FCM CHECK] FCM_ID: {fcm_id}")
                                    print(f"[FCM CHECK] Переход статуса: {old_status} -> {new_status}")
                                    print(f"[FCM CHECK] location_id: {location.id}, company_id: {location.company_id}")
                                    
                                    # ТРЁХСТУПЕНЧАТАЯ ПРОВЕРКА перед отправкой FCM
                                    
                                    # Проверка 1: Свежий объект существует и статус = 'full'
                                    if not fresh_location_for_fcm:
                                        print(f"[FCM CHECK] ❌ БЛОК 1: fresh_location_for_fcm = None")
                                        print(f"{'='*80}\n")
                                        continue
                                    
                                    print(f"[FCM CHECK] ✅ БЛОК 1: fresh_location существует")
                                    print(f"[FCM CHECK]    Статус в БД: {fresh_location_for_fcm.status}")
                                    
                                    if fresh_location_for_fcm.status != 'full':
                                        print(f"[FCM CHECK] ❌ БЛОК 2: Статус в БД НЕ 'full' ({fresh_location_for_fcm.status}), отменяем FCM")
                                        print(f"{'='*80}\n")
                                        continue
                                    
                                    print(f"[FCM CHECK] ✅ БЛОК 2: Статус в БД = 'full'")
                                    
                                    # Проверка 2: Анти-дубль по last_full_at
                                    location_id_str = str(location.id)
                                    last_full_at = fresh_location_for_fcm.last_full_at
                                    last_sent = last_notified_at_by_location.get(location_id_str)
                                    
                                    print(f"[FCM CHECK] БЛОК 3: Проверка дублирования")
                                    print(f"[FCM CHECK]    last_full_at в БД: {last_full_at}")
                                    print(f"[FCM CHECK]    last_sent (кэш):  {last_sent}")
                                    
                                    if last_full_at is None:
                                        print(f"[FCM CHECK] ⚠️  last_full_at = None, но статус = 'full' (странно!)")
                                    elif last_sent is not None:
                                        # Сравниваем timestamps
                                        if last_full_at <= last_sent:
                                            print(f"[FCM CHECK] ❌ БЛОК 3: ДУБЛЬ ОБНАРУЖЕН!")
                                            print(f"[FCM CHECK]    {last_full_at} <= {last_sent}")
                                            print(f"[FCM CHECK]    FCM НЕ отправляем")
                                            print(f"{'='*80}\n")
                                            continue
                                        else:
                                            print(f"[FCM CHECK] ✅ БЛОК 3: last_full_at новее, можно отправлять")
                                    else:
                                        print(f"[FCM CHECK] ✅ БЛОК 3: Первая отправка для этой площадки (кэш пуст)")
                                    
                                    # ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ - ОТПРАВЛЯЕМ FCM
                                    print(f"[FCM SEND] 🚀 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ, ОТПРАВЛЯЕМ FCM")
                                    print(f"[FCM SEND] FCM_ID: {fcm_id}")
                                    
                                    send_location_notification(
                                        location_data={
                                            'id': str(location.id),
                                            'name': location.name,
                                            'status': 'full',
                                            'company_id': str(location.company_id)
                                        },
                                        location_updated_at=last_full_at
                                    )
                                    
                                    print(f"[FCM SEND] ✅ FCM_ID: {fcm_id} - Уведомление отправлено")
                                    
                                    # Обновляем кэш ТОЛЬКО после успешной отправки
                                    if last_full_at is not None:
                                        last_notified_at_by_location[location_id_str] = last_full_at
                                        print(f"[FCM SEND] 💾 Кэш обновлен: {location_id_str} -> {last_full_at}")
                                    
                                    print(f"{'='*80}\n")
                                    
                                except Exception as fcm_error:
                                    logger.error(f'Error sending FCM location notification: {fcm_error}')
                                    print(f"[FCM ERROR] ❌ {fcm_error}")
                                    print(f"{'='*80}\n")
                            elif FCM_AVAILABLE:
                                print(f"[FCM] ПЛОЩАДКА {location.name}: {old_status} -> {new_status}, FCM НЕ отправляем (условие не выполнено)")
                            
                            # Отправляем WebSocket обновления для каждого контейнера
                            # ТОЛЬКО после обновления статуса площадки
                            for container in location_containers:
                                if container.fill_level == target_fill_level:
                                    print(f"[BROADCAST] Container {container.id}: {container.fill_level}% -> company_{location.company_id}")
                                    # Используем свежую площадку для WebSocket (тот же объект что и для FCM)
                                    if fresh_location_for_fcm:
                                        broadcast_container_update(container, fresh_location_for_fcm)
                                    elif updated_location:
                                        broadcast_container_update(container, updated_location)
                                    else:
                                        broadcast_container_update(container, location)
                            
                            if containers_updated > 0:
                                print(f"  [{idx}] {location.name}: {old_status} -> {new_status} ({containers_updated} контейнеров -> {target_fill_level}%)")
                                
                                # Отслеживаем изменения статуса для статистики
                                if old_status != new_status:
                                    if new_status == 'full':
                                        locations_changed['to_full'].append(location.name)
                                    elif new_status == 'partial':
                                        locations_changed['to_partial'].append(location.name)
                                    elif new_status == 'empty':
                                        locations_changed['to_empty'].append(location.name)
                                
                                updated_count += containers_updated
                    
                    except Exception as e:
                        logger.error(f'Error updating location {location.id}: {str(e)}')
                        continue
                
                # Вывод статистики стадии
                print(f"\n[STAGE {stage_num} SUMMARY]")
                print(f"  Обновлено контейнеров: {updated_count}")
                if locations_changed['to_full']:
                    print(f"  Стали FULL ({len(locations_changed['to_full'])}): {', '.join(locations_changed['to_full'])}")
                if locations_changed['to_partial']:
                    print(f"  Стали PARTIAL ({len(locations_changed['to_partial'])}): {', '.join(locations_changed['to_partial'])}")
                if locations_changed['to_empty']:
                    print(f"  Стали EMPTY ({len(locations_changed['to_empty'])}): {', '.join(locations_changed['to_empty'])}")
                
                # Переходим к следующей стадии
                current_stage = (current_stage + 1) % 12
                print(f"\n⏭️  Next: Stage {current_stage + 1}/12")
                print("⏱️  Waiting 10 seconds before next stage...")
                
                # Пауза 10 секунд перед следующей стадией
                time.sleep(10)
                
            except Exception as e:
                logger.error(f'Error in sensor simulator: {str(e)}')
                print(f"[ERROR] Simulator error: {str(e)}")
                time.sleep(10)


def start_sensor_simulator(app):
    """Запускает симулятор датчиков в отдельном потоке"""
    print("\n>>> Starting sensor simulator...")
    simulator_thread = threading.Thread(target=simulate_sensor_data, args=(app,), daemon=True)
    simulator_thread.start()
    logger.info('Sensor simulator thread started')
    print("[OK] Sensor simulator thread started\n")

