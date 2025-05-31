#!/usr/bin/env python3
"""
Simple Telegram bot to monitor messages
"""
import os
import asyncio
import logging
from datetime import datetime
import psycopg2
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
dp = Dispatcher()

# Team members (from config)
TEAM_MEMBERS = {265739915}  # Иван Смирнов

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(os.environ['DATABASE_URL'])

@dp.message()
async def handle_message(message: Message):
    """Handle all incoming messages"""
    try:
        # Get message data
        chat_id = message.chat.id
        user_id = message.from_user.id
        username = getattr(message.from_user, 'username', None)
        first_name = getattr(message.from_user, 'first_name', '')
        last_name = getattr(message.from_user, 'last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        
        chat_title = getattr(message.chat, 'title', 'Private Chat')
        chat_type = message.chat.type
        
        text = message.text or message.caption or ""
        is_team_member = user_id in TEAM_MEMBERS
        timestamp = datetime.fromtimestamp(message.date.timestamp())
        
        # Save to database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert or update chat
        cur.execute("""
            INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                title = EXCLUDED.title,
                updated_at = EXCLUDED.updated_at
        """, (chat_id, chat_title, chat_type, True, datetime.utcnow(), datetime.utcnow()))
        
        # Insert message
        cur.execute("""
            INSERT INTO messages (
                message_id, chat_id, user_id, username, full_name, text,
                message_type, is_team_member, timestamp, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            message.message_id, chat_id, user_id, username, full_name, text,
            'text', is_team_member, timestamp, datetime.utcnow()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Saved message from {full_name} ({'team' if is_team_member else 'client'}) in {chat_title}")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")

async def main():
    """Start bot"""
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())