#!/usr/bin/env python3
"""
Simple Telegram monitoring service
"""
import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TEAM_MEMBER_ID = 265739915  # Your Telegram ID
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

# Initialize bot and database
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@dp.message()
async def handle_message(message: Message):
    """Handle incoming messages"""
    try:
        user_id = message.from_user.id if message.from_user else 0
        username = message.from_user.username if message.from_user else None
        full_name = message.from_user.full_name if message.from_user else "Unknown"
        is_team_member = user_id == TEAM_MEMBER_ID
        
        session = Session()
        try:
            # Save chat
            chat_sql = text("""
                INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at)
                VALUES (:chat_id, :title, :chat_type, true, :now, :now)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    updated_at = EXCLUDED.updated_at
            """)
            
            session.execute(chat_sql, {
                'chat_id': message.chat.id,
                'title': message.chat.title or 'Private Chat',
                'chat_type': message.chat.type,
                'now': datetime.utcnow()
            })
            
            # Save message
            msg_sql = text("""
                INSERT INTO messages (
                    message_id, chat_id, user_id, username, full_name, text,
                    message_type, is_team_member, timestamp, created_at
                ) VALUES (
                    :message_id, :chat_id, :user_id, :username, :full_name, :text,
                    :message_type, :is_team_member, :timestamp, :created_at
                )
            """)
            
            session.execute(msg_sql, {
                'message_id': message.message_id,
                'chat_id': message.chat.id,
                'user_id': user_id,
                'username': username,
                'full_name': full_name,
                'text': message.text or "",
                'message_type': 'text' if message.text else 'other',
                'is_team_member': is_team_member,
                'timestamp': message.date,
                'created_at': datetime.utcnow()
            })
            
            session.commit()
            
            role = "команды" if is_team_member else "клиента"
            logger.info(f"Сохранено сообщение от {role}: {full_name}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Message processing error: {e}")

async def main():
    """Main function"""
    logger.info("Запуск Telegram мониторинга...")
    logger.info(f"ID участника команды: {TEAM_MEMBER_ID}")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Остановлено")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())