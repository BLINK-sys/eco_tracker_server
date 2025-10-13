# EcoTracker Server

Серверная часть системы мониторинга контейнеров EcoTracker.

## Технологии

- **Flask** - веб-фреймворк
- **SQLAlchemy** - ORM для работы с БД
- **PostgreSQL** / SQLite - база данных
- **Flask-SocketIO** - WebSocket для real-time обновлений
- **Flask-JWT-Extended** - аутентификация через JWT токены

## Установка и запуск (локально)

### 1. Установка зависимостей

```bash
cd ecotracker_server
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Скопируйте `.env.example` в `.env`:
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
DATABASE_URL=sqlite:///ecotracker.db  # или PostgreSQL URL
CORS_ORIGINS=http://localhost:5173
```

### 3. Запуск сервера

```bash
python app.py
```

Сервер запустится на `http://localhost:5000`

## Структура проекта

```
ecotracker_server/
├── app.py                  # Главный файл приложения
├── config.py               # Конфигурация
├── models.py               # Модели базы данных
├── init_data.py            # Инициализация тестовых данных
├── sensor_simulator.py     # Симулятор датчиков
├── socket_events.py        # WebSocket события
├── wsgi.py                 # WSGI entry point для продакшена
├── requirements.txt        # Зависимости Python
├── routes/                 # Маршруты API
│   ├── auth.py            # Аутентификация
│   ├── users.py           # Управление пользователями
│   ├── companies.py       # Управление компаниями
│   ├── locations.py       # Управление площадками
│   ├── containers.py      # Управление контейнерами
│   ├── sensors.py         # Управление датчиками
│   └── reports.py         # Отчеты
└── instance/              # База данных SQLite (создается автоматически)
```

## API эндпоинты

### Аутентификация
- `POST /api/auth/login` - Вход
- `POST /api/auth/register` - Регистрация
- `GET /api/auth/me` - Получить текущего пользователя

### Пользователи
- `GET /api/users` - Список пользователей
- `POST /api/users` - Создать пользователя
- `GET /api/users/:id` - Получить пользователя
- `PUT /api/users/:id` - Обновить пользователя
- `DELETE /api/users/:id` - Удалить пользователя

### Площадки
- `GET /api/locations` - Список площадок
- `POST /api/locations` - Создать площадку
- `GET /api/locations/:id` - Получить площадку
- `PUT /api/locations/:id` - Обновить площадку
- `DELETE /api/locations/:id` - Удалить площадку

### Контейнеры
- `GET /api/containers` - Список контейнеров
- `POST /api/containers` - Создать контейнер
- `PUT /api/containers/:id` - Обновить контейнер
- `DELETE /api/containers/:id` - Удалить контейнер

### WebSocket события
- `container_updated` - Обновление контейнера
- `location_updated` - Обновление площадки
- `join_company` - Присоединиться к комнате компании
- `leave_company` - Покинуть комнату компании

## Работа с PostgreSQL локально

### Установка PostgreSQL

**Windows:**
1. Скачайте с [postgresql.org](https://www.postgresql.org/download/windows/)
2. Установите PostgreSQL
3. Запомните пароль для пользователя `postgres`

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql
```

### Создание базы данных

```bash
# Подключитесь к PostgreSQL
psql -U postgres

# Создайте базу данных
CREATE DATABASE ecotracker;

# Создайте пользователя (опционально)
CREATE USER ecotracker_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ecotracker TO ecotracker_user;

# Выход
\q
```

### Настройка подключения

Обновите `.env`:
```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ecotracker
# или
DATABASE_URL=postgresql://ecotracker_user:your_password@localhost:5432/ecotracker
```

## Симулятор датчиков

Симулятор автоматически запускается в режиме разработки и обновляет данные контейнеров каждые 10 секунд.

Для включения симулятора в продакшене добавьте переменную окружения:
```env
ENABLE_SIMULATOR=true
```

## Развертывание на Render

См. подробную инструкцию в [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)

Краткие шаги:
1. Создайте PostgreSQL базу на Render
2. Создайте Web Service
3. Настройте переменные окружения
4. Деплой!

## Тестовые данные

При первом запуске автоматически создаются:

**Компания:**
- ТОО EcoTracker

**Пользователи:**
- `bocan.anton@mail.ru` / `password123` (Владелец)
- `bocan.anton1@mail.ru` / `password123` (Оператор)

**Площадки:**
- МКР БАМ
- Проспект Аманбаева
- Рынок

Каждая площадка имеет 3 контейнера разных типов отходов.

## Разработка

### Создание новых моделей

1. Добавьте модель в `models.py`
2. Создайте миграцию (если используете Flask-Migrate)
3. Примените миграцию

### Создание новых API эндпоинтов

1. Создайте файл в `routes/`
2. Зарегистрируйте blueprint в `routes/__init__.py`
3. Добавьте необходимую логику и валидацию

### WebSocket события

Для отправки real-time обновлений используйте функции из `socket_events.py`:
- `broadcast_container_update(container, location)`
- `broadcast_location_update(location)`

## Лицензия

MIT

## Контакты

Разработчик: Anton Bocan
Email: bocan.anton@mail.ru

