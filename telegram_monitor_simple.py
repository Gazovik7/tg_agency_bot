#!/usr/bin/env python3
"""
Простой Telegram монитор для сохранения сообщений в базу данных
"""
import os
import asyncio
import logging
from datetime import datetime
import psycopg2
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot = None
dp = None
running = True

# Члены команды (из конфига)
TEAM_MEMBERS = {265739915}  # ID Ивана Смирнова

def get_db_connection():
    """Получение подключения к базе данных"""
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return None

async def save_message_to_db(message_data):
    """Сохранение сообщения в базу данных"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        # Сохраняем или обновляем чат
        cur.execute("""
            INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at) 
            VALUES (%s, %s, %s, true, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                title = EXCLUDED.title,
                updated_at = EXCLUDED.updated_at
        """, (
            message_data['chat_id'],
            message_data['chat_title'],
            message_data['chat_type'],
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        # Сохраняем сообщение
        cur.execute("""
            INSERT INTO messages (
                message_id, chat_id, user_id, username, full_name, text,
                message_type, is_team_member, timestamp, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            message_data['message_id'],
            message_data['chat_id'],
            message_data['user_id'],
            message_data['username'],
            message_data['full_name'],
            message_data['text'],
            message_data['message_type'],
            message_data['is_team_member'],
            message_data['timestamp'],
            datetime.utcnow()
        ))
        
        conn.commit()
        logger.info(f"Сохранено сообщение от {message_data['full_name']} ({'команда' if message_data['is_team_member'] else 'клиент'})")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

@dp.message()
async def handle_message(message: Message):
    """Обработка всех входящих сообщений"""
    try:
        # Извлекаем данные сообщения
        chat_id = message.chat.id
        user_id = message.from_user.id
        username = getattr(message.from_user, 'username', None)
        
        first_name = getattr(message.from_user, 'first_name', '') or ''
        last_name = getattr(message.from_user, 'last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()
        
        chat_title = getattr(message.chat, 'title', 'Private Chat')
        chat_type = message.chat.type
        
        text = message.text or message.caption or ""
        is_team_member = user_id in TEAM_MEMBERS
        timestamp = datetime.fromtimestamp(message.date.timestamp())
        
        # Определяем тип сообщения
        if message.text:
            message_type = 'text'
        elif message.photo:
            message_type = 'photo'
        elif message.document:
            message_type = 'document'
        elif message.voice:
            message_type = 'voice'
        elif message.video:
            message_type = 'video'
        else:
            message_type = 'other'
        
        # Подготавливаем данные для сохранения
        message_data = {
            'message_id': message.message_id,
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'full_name': full_name,
            'text': text,
            'message_type': message_type,
            'is_team_member': is_team_member,
            'timestamp': timestamp,
            'chat_title': chat_title,
            'chat_type': chat_type
        }
        
        # Сохраняем в базу данных
        await save_message_to_db(message_data)
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    global running
    logger.info("Получен сигнал завершения")
    running = False

async def main():
    """Основная функция"""
    global bot, dp, running
    
    # Проверяем наличие токена
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return
    
    # Устанавливаем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Инициализируем бота
        bot = Bot(token=token)
        dp = Dispatcher()
        
        # Регистрируем обработчик сообщений
        dp.message.register(handle_message)
        
        logger.info("Запуск Telegram мониторинга...")
        
        # Запускаем polling
        await dp.start_polling(bot, allowed_updates=['message'])
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
    finally:
        if bot:
            await bot.session.close()
        logger.info("Telegram мониторинг остановлен")

if __name__ == "__main__":
    asyncio.run(main())