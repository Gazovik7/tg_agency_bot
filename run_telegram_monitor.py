#!/usr/bin/env python3
import asyncio
import os
import logging
from datetime import datetime
import psycopg2
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Team members
TEAM_MEMBERS = {265739915}

# Initialize bot
bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
dp = Dispatcher()

@dp.message()
async def handle_message(message: Message):
    try:
        # Extract message data
        chat_id = message.chat.id
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        chat_title = message.chat.title or "Private Chat"
        chat_type = message.chat.type
        text = message.text or ""
        is_team_member = user_id in TEAM_MEMBERS
        timestamp = datetime.fromtimestamp(message.date.timestamp())
        
        # Save to database
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        
        # Insert chat
        cur.execute("""
            INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at) 
            VALUES (%s, %s, %s, true, %s, %s)
            ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at
        """, (chat_id, chat_title, chat_type, datetime.utcnow(), datetime.utcnow()))
        
        # Insert message
        cur.execute("""
            INSERT INTO messages (
                message_id, chat_id, user_id, username, full_name, text,
                message_type, is_team_member, timestamp, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 'text', %s, %s, %s)
        """, (
            message.message_id, chat_id, user_id, username, full_name, text,
            is_team_member, timestamp, datetime.utcnow()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Message saved: {full_name} ({'team' if is_team_member else 'client'})")
        
    except Exception as e:
        logger.error(f"Error: {e}")

async def main():
    logger.info("Starting Telegram monitor...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())