-- Добавление колонки last_full_at в таблицу locations
-- Запустить на Render через PostgreSQL console или локально

ALTER TABLE locations 
ADD COLUMN IF NOT EXISTS last_full_at TIMESTAMP;

-- Для существующих площадок со статусом 'full' установить текущее время
UPDATE locations 
SET last_full_at = CURRENT_TIMESTAMP 
WHERE status = 'full' AND last_full_at IS NULL;

