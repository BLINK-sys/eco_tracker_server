-- Добавление колонки last_seen_at в таблицу fcm_tokens
-- Запустить на Render через PostgreSQL console или локально

ALTER TABLE fcm_tokens 
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Установить текущее время для существующих токенов
UPDATE fcm_tokens 
SET last_seen_at = CURRENT_TIMESTAMP 
WHERE last_seen_at IS NULL;

