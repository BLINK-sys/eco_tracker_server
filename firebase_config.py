"""
Конфигурация Firebase Admin SDK для отправки push-уведомлений
"""

import firebase_admin
from firebase_admin import credentials
import os
import json


def initialize_firebase():
    """
    Инициализация Firebase Admin SDK
    
    Способы настройки (в порядке приоритета):
    1. Переменная окружения FIREBASE_CREDENTIALS_JSON (JSON строка)
    2. Файл firebase-service-account.json в корне проекта
    3. Переменная окружения GOOGLE_APPLICATION_CREDENTIALS (путь к файлу)
    """
    try:
        # Проверяем, не инициализирован ли уже Firebase
        if firebase_admin._apps:
            print('[OK] Firebase already initialized')
            return True
        
        # Способ 1: JSON из переменной окружения
        firebase_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        if firebase_json:
            try:
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print('[OK] Firebase initialized from FIREBASE_CREDENTIALS_JSON')
                return True
            except json.JSONDecodeError as e:
                print(f'[ERROR] Failed to parse FIREBASE_CREDENTIALS_JSON: {e}')
        
        # Способ 2: Файл firebase-service-account.json
        json_file = 'firebase-service-account.json'
        if os.path.exists(json_file):
            cred = credentials.Certificate(json_file)
            firebase_admin.initialize_app(cred)
            print(f'[OK] Firebase initialized from file {json_file}')
            return True
        
        # Способ 3: GOOGLE_APPLICATION_CREDENTIALS
        google_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if google_creds and os.path.exists(google_creds):
            cred = credentials.Certificate(google_creds)
            firebase_admin.initialize_app(cred)
            print(f'[OK] Firebase initialized from GOOGLE_APPLICATION_CREDENTIALS')
            return True
        
        # Если ничего не найдено
        print('[WARNING] Firebase credentials not found')
        print('   Create firebase-service-account.json file')
        print('   Or set FIREBASE_CREDENTIALS_JSON environment variable')
        print('   FCM notifications will be disabled')
        return False
        
    except Exception as e:
        print(f'[ERROR] Firebase initialization failed: {e}')
        print('   FCM notifications will be disabled')
        return False


def is_firebase_available():
    """Проверяет, доступен ли Firebase"""
    return bool(firebase_admin._apps)

