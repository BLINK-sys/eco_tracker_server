#!/usr/bin/env python3
"""
Умный симулятор датчиков - работает только при активных соединениях
"""
import time
import random
import threading
from datetime import datetime
from models import db, Container, Location
import logging

logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания активных соединений
active_connections = 0
_socketio = None

def set_socketio(socketio_instance):
    """Устанавливает ссылку на SocketIO"""
    global _socketio
    _socketio = socketio_instance

def increment_connections():
    """Увеличивает счетчик активных соединений"""
    global active_connections
    active_connections += 1
    print(f"📡 Active connections: {active_connections}")

def decrement_connections():
    """Уменьшает счетчик активных соединений"""
    global active_connections
    active_connections = max(0, active_connections - 1)
    print(f"📡 Active connections: {active_connections}")

def has_active_connections():
    """Проверяет, есть ли активные WebSocket соединения"""
    return active_connections > 0

def simulate_smart_sensor_data(app):
    """Умный симулятор - работает только при активных соединениях"""
    global _socketio
    
    if not _socketio:
        print("❌ SocketIO not initialized")
        return
    
    print("🧠 Starting SMART sensor simulator...")
    print("   - Works only when clients are connected")
    print("   - Pauses when no active connections")
    
    # Этапы симуляции
    stages = [
        (1, 1, 1),  # 1 full, 1 partial, 1 empty
        (1, 2, 0),  # 1 full, 2 partial, 0 empty
        (2, 1, 0),  # 2 full, 1 partial, 0 empty
        (3, 0, 0),  # 3 full, 0 partial, 0 empty
        (0, 0, 3),  # 0 full, 0 partial, 3 empty
        (0, 1, 2),  # 0 full, 1 partial, 2 empty
    ]
    
    current_stage = 0
    
    while True:
        try:
            # Проверяем активные соединения
            if not has_active_connections():
                print("😴 No active connections - simulator sleeping...")
                time.sleep(30)  # Спим 30 секунд если нет соединений
                continue
            
            print(f"\n🎬 SIMULATOR ACTIVE - {active_connections} connections")
            
            # Получаем все локации
            with app.app_context():
                locations = Location.query.all()
                
            if not locations:
                print("❌ No locations found")
                time.sleep(60)
                continue
            
            # Выбираем текущую стадию
            full_count, partial_count, empty_count = stages[current_stage]
            current_stage = (current_stage + 1) % len(stages)
            
            print(f"\n============================================================")
            print(f"STAGE: {full_count} full, {partial_count} partial, {empty_count} empty")
            print(f"============================================================")
            
            # Обновляем контейнеры для каждой локации
            for i, location in enumerate(locations):
                with app.app_context():
                    containers = Container.query.filter_by(location_id=location.id).all()
                
                if not containers:
                    continue
                
                # Определяем уровень заполнения для этой локации
                if i < full_count:
                    fill_level = 100
                    status = "FULL"
                elif i < full_count + partial_count:
                    fill_level = 60
                    status = "PARTIAL"
                else:
                    fill_level = 0
                    status = "EMPTY"
                
                # Обновляем все контейнеры в локации
                for container in containers:
                    with app.app_context():
                        container.fill_level = fill_level
                        container.updated_at = datetime.utcnow()
                        db.session.commit()
                    
                    # Отправляем WebSocket событие
                    if _socketio:
                        update_data = {
                            'container_id': container.id,
                            'location_id': container.location_id,
                            'fill_level': fill_level,
                            'status': status,
                            'updated_at': container.updated_at.isoformat()
                        }
                        
                        room_name = f'company_{location.company_id}'
                        print(f"[BROADCAST] Sending 'container_updated' to room: {room_name}")
                        print(f"            Container: {container.id}, fill_level: {fill_level}%")
                        
                        _socketio.emit('container_updated', update_data, room=room_name)
                
                print(f"  Location: {location.name} -> {status}")
                print(f"       Updated {len(containers)} containers to {fill_level}%")
            
            print(f"[OK] Stage complete - Updated containers")
            print(f"Next: Stage {current_stage + 1}/6")
            
            # Ждем 2 минуты перед следующей стадией (только если есть соединения)
            if has_active_connections():
                print("⏰ Waiting 2 minutes before next stage...")
                time.sleep(120)  # 2 минуты
            else:
                print("😴 No connections - sleeping...")
                time.sleep(30)
                
        except Exception as e:
            logger.error(f'Error in smart simulator: {str(e)}')
            print(f"[ERROR] Smart simulator error: {str(e)}")
            time.sleep(60)

def start_smart_simulator(app):
    """Запускает умный симулятор датчиков"""
    print("\n>>> Starting SMART sensor simulator...")
    simulator_thread = threading.Thread(target=simulate_smart_sensor_data, args=(app,), daemon=True)
    simulator_thread.start()
    logger.info('Smart sensor simulator thread started')
    print("[OK] Smart sensor simulator thread started\n")
