# 🚀 Быстрый старт FCM для EcoTracker

## 📋 Что вам нужно сделать (5 шагов)

### ✅ Шаг 1: Создать Firebase проект (2 минуты)

1. Открыть https://console.firebase.google.com/
2. Нажать "Add project" → ввести "EcoTracker" → создать
3. В проекте нажать на Android иконку
4. Package name: `com.example.ecotracker_mobile`
5. Скачать `google-services.json` → поместить в `ecotracker_mobile/android/app/`

### ✅ Шаг 2: Получить Service Account Key (1 минута)

1. В Firebase Console → ⚙️ Project Settings → Service Accounts
2. Нажать "Generate new private key"
3. Скачать JSON файл
4. **Для локальной разработки:**
   ```bash
   # Переименовать и поместить в корень ecotracker_server/
   mv ~/Downloads/ecotracker-xxx.json ecotracker_server/firebase-service-account.json
   ```

5. **Для Render (продакшен):**
   ```bash
   # Открыть файл и скопировать ВСЁ содержимое
   cat firebase-service-account.json
   
   # В Render Dashboard:
   # Environment → Add Variable
   # Name: FIREBASE_CREDENTIALS_JSON
   # Value: вставить скопированный JSON (весь объект)
   ```

### ✅ Шаг 3: Обновить Android конфигурацию (2 минуты)

#### `ecotracker_mobile/android/build.gradle`:
```gradle
buildscript {
    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.0'
        classpath 'org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.0'
        classpath 'com.google.gms:google-services:4.4.0'  // ← Добавить эту строку
    }
}
```

#### `ecotracker_mobile/android/app/build.gradle`:
```gradle
// В самом конце файла добавить:
apply plugin: 'com.google.gms.google-services'  // ← Добавить эту строку
```

### ✅ Шаг 4: Установить зависимости

#### Сервер:
```bash
cd ecotracker_server
pip install -r requirements.txt
```

#### Мобильное приложение:
```bash
cd ecotracker_mobile
flutter pub get
```

### ✅ Шаг 5: Применить миграции БД

```bash
cd ecotracker_server

# Создать миграцию
flask db migrate -m "Add FCMToken model"

# Применить
flask db upgrade
```

## 🧪 Тестирование

### 1. Запустить сервер:
```bash
cd ecotracker_server
python app.py
```

Вы должны увидеть:
```
✅ Firebase инициализирован из файла firebase-service-account.json
```

### 2. Запустить мобильное приложение:
```bash
cd ecotracker_mobile
flutter run
```

Вы должны увидеть:
```
✅ Firebase инициализирован
🔑 FCM Token: xxxxx...
✅ Firebase Cloud Messaging инициализирован
```

### 3. Залогиниться в приложении

Вы должны увидеть:
```
📤 Отправка FCM токена на сервер...
✅ FCM токен сохранен на сервере
✅ Подписались на уведомления компании
```

### 4. Проверить уведомления:

1. **Оставить приложение открытым** → уведомлений НЕТ (данные через WebSocket)
2. **Свернуть приложение** (Home кнопка) → дождаться симулятора → уведомление ✅
3. **Закрыть приложение** (смахнуть из недавних) → дождаться → уведомление ✅

## ❌ Troubleshooting

### Firebase не инициализируется:
```
❌ Ошибка инициализации Firebase: [Errno 2] No such file or directory: 'firebase-service-account.json'

Решение: Проверить что файл существует в корне ecotracker_server/
```

### FCM токен не сохраняется:
```
❌ Ошибка сохранения FCM токена: 401 Unauthorized

Решение: Проверить что JWT токен действителен
```

### Уведомления не приходят:
```
Проверить:
1. Приложение свернуто? (не открыто)
2. FCM токен сохранен на сервере?
3. Firebase инициализирован на сервере?
4. google-services.json в правильной папке?
```

## 📊 Проверка в БД

```sql
-- Проверить сохраненные FCM токены
SELECT u.email, f.token, f.device_info, f.created_at 
FROM fcm_tokens f 
JOIN users u ON f.user_id = u.id;
```

## 🎯 Готово!

Теперь ваше приложение работает как **WhatsApp** или **Telegram**:
- ✅ Уведомления при закрытом приложении
- ✅ Мгновенная доставка через Firebase
- ✅ WebSocket для веб-пользователей (без изменений)
- ✅ FCM для мобильных пользователей (новая функциональность)

🎉 Обе системы работают параллельно и не мешают друг другу!

