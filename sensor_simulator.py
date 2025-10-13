"""
Симулятор датчиков контейнеров
Эмулирует поступление данных от реальных датчиков уровня заполнения
"""

import time
import random
import threading
from models import db, Container, Location
from socket_events import broadcast_container_update
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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
        container = Container.query.get(container_id)
        if not container:
            return None
        
        # Обновляем уровень заполнения
        container.fill_level = new_fill_level
        
        # Автоматически определяем статус по уровню заполнения
        if new_fill_level == 0:
            container.status = 'empty'
        elif new_fill_level < 70:
            container.status = 'partial'
        else:
            container.status = 'full'
        
        # Получаем площадку
        location = container.location
        
        # Пересчитываем статус площадки
        location.update_status()
        
        # Сохраняем изменения
        db.session.commit()
        
        # Отправляем обновление через WebSocket
        broadcast_container_update(container, location)
        
        logger.info(f'Container {container_id} updated: fill_level={new_fill_level}%, status={container.status}')
        logger.info(f'Location {location.id} updated: status={location.status}')
        
        return {
            'container': container.to_dict(),
            'location_status': location.status
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating container {container_id}: {str(e)}')
        return None


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
        
        # Определение стадий (распределение площадок по статусам)
        # [full_count, partial_count, empty_count]
        stages = [
            [1, 1, 1],  # Стадия 1: 1 требует внимание, 1 частично, 1 пустая
            [1, 2, 0],  # Стадия 2: 1 требует внимание, 2 частично
            [2, 1, 0],  # Стадия 3: 2 требует внимание, 1 частично
            [3, 0, 0],  # Стадия 4: 3 требует внимание
            [0, 0, 3],  # Стадия 5: 3 пустые
            [0, 1, 2],  # Стадия 6: 2 пустые, 1 частично
        ]
        
        current_stage = 0
        
        while True:
            try:
                # Получаем только площадки компании ТОО EcoTracker
                ecotracker_locations = Location.query.filter_by(company_id=ECOTRACKER_COMPANY_ID).all()
                
                if not ecotracker_locations:
                    print("No EcoTracker locations found, waiting...")
                    time.sleep(10)
                    continue
                
                # Если площадок меньше 3, пропускаем
                if len(ecotracker_locations) < 3:
                    print(f"Not enough locations ({len(ecotracker_locations)}), need at least 3")
                    time.sleep(10)
                    continue
                
                stage_distribution = stages[current_stage]
                stage_num = current_stage + 1
                full_count, partial_count, empty_count = stage_distribution
                
                print(f"\n{'='*60}")
                print(f"STAGE {stage_num}/6: {full_count} full, {partial_count} partial, {empty_count} empty")
                print(f"Updating EcoTracker locations...")
                print(f"Total locations: {len(ecotracker_locations)}")
                print(f"{'='*60}")
                
                updated_count = 0
                
                # Применяем распределение к площадкам
                for idx, location in enumerate(ecotracker_locations):
                    try:
                        # Определяем желаемый статус для этой площадки
                        if idx < full_count:
                            target_status = 'full'
                            target_fill_level = 100
                        elif idx < full_count + partial_count:
                            target_status = 'partial'
                            target_fill_level = 60
                        else:
                            target_status = 'empty'
                            target_fill_level = 0
                        
                        # Проверяем, нужно ли обновлять эту площадку
                        if location.status != target_status:
                            # Обновляем все контейнеры площадки до нужного уровня
                            containers_updated = 0
                            for container in location.containers:
                                if container.fill_level != target_fill_level:
                                    result = update_container_fill_level(container.id, target_fill_level)
                                    if result:
                                        containers_updated += 1
                            
                            if containers_updated > 0:
                                print(f"  Location: {location.name} -> {target_status.upper()}")
                                print(f"       Updated {containers_updated} containers to {target_fill_level}%")
                                updated_count += containers_updated
                    
                    except Exception as e:
                        logger.error(f'Error updating location {location.id}: {str(e)}')
                        continue
                
                print(f"\n[OK] Stage {stage_num} complete - Updated {updated_count} containers")
                
                # Переходим к следующей стадии
                current_stage = (current_stage + 1) % len(stages)
                next_stage_num = current_stage + 1
                next_distribution = stages[current_stage]
                
                print(f"Next: Stage {next_stage_num}/6 - {next_distribution[0]} full, {next_distribution[1]} partial, {next_distribution[2]} empty")
                print("\nWaiting 10 seconds before next stage...")
                
                # Пауза 30 секунд перед следующей стадией (уменьшаем нагрузку)
                time.sleep(30)
                
            except Exception as e:
                logger.error(f'Error in sensor simulator: {str(e)}')
                print(f"[ERROR] Simulator error: {str(e)}")
                time.sleep(30)


def start_sensor_simulator(app):
    """Запускает симулятор датчиков в отдельном потоке"""
    print("\n>>> Starting sensor simulator...")
    simulator_thread = threading.Thread(target=simulate_sensor_data, args=(app,), daemon=True)
    simulator_thread.start()
    logger.info('Sensor simulator thread started')
    print("[OK] Sensor simulator thread started\n")

