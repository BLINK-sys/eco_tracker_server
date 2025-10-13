# Развертывание EcoTracker Server на Render

Пошаговая инструкция по развертыванию серверной части на Render.com

## Шаг 1: Создание PostgreSQL базы данных

1. Войдите на [Render.com](https://render.com)
2. Нажмите **"New +"** → **"PostgreSQL"**
3. Заполните форму:
   - **Name**: `ecotracker-db` (или любое имя)
   - **Database**: `ecotracker`
   - **User**: оставьте по умолчанию
   - **Region**: выберите ближайший регион
   - **Plan**: выберите **Free**
4. Нажмите **"Create Database"**
5. Дождитесь создания БД (несколько минут)
6. Скопируйте **Internal Database URL** (в разделе "Connections")
   - Формат: `postgresql://user:password@host/database`
   - Этот URL будет использоваться в переменных окружения

## Шаг 2: Создание Web Service

1. На Render нажмите **"New +"** → **"Web Service"**
2. Подключите ваш GitHub репозиторий:
   - Выберите `eco_tracker_server` (или ваш репозиторий)
3. Заполните форму:
   - **Name**: `ecotracker-server`
   - **Region**: тот же регион, что и БД
   - **Branch**: `main`
   - **Root Directory**: оставьте пустым (или `ecotracker_server` если это монорепо)
   - **Runtime**: **Python 3**
   - **Build Command**: `chmod +x build.sh && ./build.sh`
   - **Start Command**: `gunicorn -c gunicorn_config.py wsgi:app`
   - **Plan**: выберите **Free**

## Шаг 3: Настройка переменных окружения

В разделе **"Environment Variables"** добавьте:

| Key | Value | Описание |
|-----|-------|----------|
| `FLASK_ENV` | `production` | Режим работы |
| `SECRET_KEY` | `your-random-secret-key-here` | Секретный ключ Flask (сгенерируйте случайную строку) |
| `JWT_SECRET_KEY` | `your-random-jwt-key-here` | Секретный ключ JWT (сгенерируйте случайную строку) |
| `DATABASE_URL` | `скопируйте Internal Database URL из шага 1` | URL PostgreSQL базы |
| `CORS_ORIGINS` | `https://your-frontend-url.onrender.com` | URL вашего фронтенда (можно указать несколько через запятую) |
| `PYTHON_VERSION` | `3.11.0` | Версия Python |

### Генерация секретных ключей:

Выполните в терминале:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Используйте вывод для `SECRET_KEY` и `JWT_SECRET_KEY`.

## Шаг 4: Деплой

1. Нажмите **"Create Web Service"**
2. Render автоматически начнет деплой
3. Дождитесь завершения (5-10 минут)
4. После успешного деплоя вы увидите статус **"Live"**
5. Ваш сервер будет доступен по URL: `https://ecotracker-server.onrender.com`

## Шаг 5: Проверка работы

Откройте в браузере:
```
https://ecotracker-server.onrender.com/
```

Вы должны увидеть:
```json
{
  "message": "EcoTracker API",
  "version": "1.0.0",
  "status": "running"
}
```

## Важные замечания

### Free plan особенности:
- ⚠️ Сервис "засыпает" после 15 минут неактивности
- ⚠️ Первый запрос после сна может занять 30-60 секунд
- ⚠️ БД бесплатно на 90 дней, затем удаляется

### Обновление кода:
- При пуше в `main` ветку Render автоматически перезапустит сервис
- Можно настроить автодеплой в настройках сервиса

### Логи:
- Доступны в разделе **"Logs"** на странице сервиса
- Полезно для отладки проблем

### База данных:
- Бэкапы доступны только на платных планах
- Для доступа к БД можно использовать External Database URL

## Подключение фронтенда

После деплоя сервера обновите переменные окружения фронтенда:

```env
VITE_API_URL=https://ecotracker-server.onrender.com/api
```

## Troubleshooting

### Проблема: Build failed
- Проверьте логи сборки
- Убедитесь, что `requirements.txt` корректен
- Проверьте права на выполнение `build.sh`

### Проблема: Application Error
- Проверьте логи приложения
- Убедитесь, что все переменные окружения установлены
- Проверьте правильность DATABASE_URL

### Проблема: WebSocket не работает
- Убедитесь, что используется eventlet worker
- Проверьте CORS_ORIGINS
- На бесплатном плане могут быть ограничения WebSocket

## Альтернативные команды

### Если используете другую версию Python:
```bash
# Build Command
pip install --upgrade pip && pip install -r requirements.txt && python init_db.py

# Start Command
gunicorn -c gunicorn_config.py wsgi:app
```

### Для отключения симулятора в продакшене:
Отредактируйте `app.py`:
```python
# Закомментируйте эти строки:
# if app.config['DEBUG']:
#     from sensor_simulator import start_sensor_simulator
#     start_sensor_simulator(app)
```

---

**Готово!** Ваш EcoTracker Server теперь работает на Render с PostgreSQL базой данных 🎉

