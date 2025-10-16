# 🔥 Настройка Firebase Cloud Messaging на сервере

## ✅ Что уже сделано

1. ✅ Добавлен `firebase-admin` в `requirements.txt`
2. ✅ Создана модель `FCMToken` в `models.py`
3. ✅ Создан `firebase_config.py` для инициализации Firebase
4. ✅ Создан `fcm_service.py` для отправки уведомлений
5. ✅ Добавлены API endpoints в `routes/fcm.py`:
   - `POST /api/fcm/token` - сохранить FCM токен
   - `DELETE /api/fcm/token` - удалить FCM токен
   - `GET /api/fcm/tokens` - получить токены пользователя
6. ✅ Интегрирован FCM в `sensor_simulator.py`
7. ✅ FCM работает **параллельно** с WebSocket (не мешает веб-пользователям)

## 📋 Что нужно сделать

### 1. Получить Firebase Service Account Key

1. Открыть [Firebase Console](https://console.firebase.google.com/)
2. Выбрать проект "EcoTracker"
3. Настройки проекта → Service Accounts
4. Нажать "Generate new private key"
5. Скачать JSON файл

### 2. Установить credentials (выберите один способ)

#### Способ 1: Файл (для локальной разработки)
```bash
# Сохранить JSON как firebase-service-account.json в корне проекта
cp ~/Downloads/ecotracker-xxx-firebase-adminsdk.json firebase-service-account.json
```

#### Способ 2: Переменная окружения (для Render)
```bash
# Скопировать содержимое JSON файла
cat firebase-service-account.json | pbcopy  # macOS
cat firebase-service-account.json | clip    # Windows

# В Render Dashboard:
# Environment Variables → Add Variable
# Имя: FIREBASE_CREDENTIALS_JSON
# Значение: вставить JSON (весь объект как строку)
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Применить миграции БД

```bash
# Создать миграцию для новой таблицы fcm_tokens
flask db migrate -m "Add FCMToken model"

# Применить миграцию
flask db upgrade
```

### 5. Запустить сервер

```bash
python app.py
```

Вы должны увидеть:
```
✅ Firebase инициализирован из файла firebase-service-account.json
```

## 🔍 Тестирование

### 1. Проверить инициализацию Firebase

```python
from firebase_config import is_firebase_available

if is_firebase_available():
    print('✅ Firebase готов к работе')
else:
    print('❌ Firebase не настроен')
```

### 2. Проверить API сохранения токена

```bash
# Получить JWT токен (залогиниться)
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ecotracker.kz", "password": "admin123"}'

# Сохранить FCM токен
curl -X POST http://localhost:5000/api/fcm/token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"token": "test_fcm_token_123"}'
```

### 3. Проверить отправку уведомлений

```python
from fcm_service import send_container_notification

# Отправить тестовое уведомление
send_container_notification(
    container_data={
        'id': 'test-id',
        'number': 1,
        'status': 'full',
        'fill_level': 100
    },
    location_data={
        'id': 'test-location',
        'name': 'Тестовая площадка',
        'company_id': 'your-company-id'
    }
)
```

## 📊 Как работает

### Веб-пользователи (браузер)
```
Сервер → WebSocket → Браузер (в реальном времени)
✅ Работает как раньше, без изменений
```

### Мобильные пользователи
```
Сервер → Firebase → Телефон (даже если приложение закрыто)
✅ Новая функциональность
```

### Оба канала работают одновременно:

```python
# В sensor_simulator.py
if company_id_for_log:
    # 1. WebSocket для веб-пользователей
    broadcast_container_update(container, location)
    
    # 2. FCM для мобильных пользователей
    if FCM_AVAILABLE:
        send_container_notification(container_data, location_data)
```

## 🔧 Структура FCM Token в БД

```sql
CREATE TABLE fcm_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    device_info VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 🚀 Деплой на Render

1. В Render Dashboard добавить переменную окружения:
   ```
   FIREBASE_CREDENTIALS_JSON = {"type":"service_account","project_id":...}
   ```

2. Push изменения на GitHub

3. Render автоматически:
   - Установит `firebase-admin`
   - Применит миграции
   - Инициализирует Firebase
   - Запустит сервер с FCM

## ⚠️ Важно

1. **Не коммитить** `firebase-service-account.json` в Git
2. **Удалять недействительные токены** автоматически (уже реализовано)
3. **Проверять доступность Firebase** перед отправкой
4. **WebSocket не трогать** - всё работает параллельно

## 📚 API Endpoints

### POST /api/fcm/token
Сохранить FCM токен пользователя
```json
Request:
{
    "token": "fcm_token_string",
    "device_info": "optional"
}

Response:
{
    "message": "FCM token saved successfully",
    "token_id": "uuid"
}
```

### DELETE /api/fcm/token
Удалить FCM токен (при выходе)
```json
Request:
{
    "token": "fcm_token_string"
}

Response:
{
    "message": "FCM token deleted successfully"
}
```

### GET /api/fcm/tokens
Получить все токены пользователя
```json
Response:
{
    "tokens": [...],
    "count": 2
}
```

## 🎯 Результат

✅ **Веб-пользователи** - получают уведомления через WebSocket (как раньше)  
✅ **Мобильные пользователи** - получают FCM уведомления (даже при закрытом приложении)  
✅ **Оба работают одновременно** без конфликтов

