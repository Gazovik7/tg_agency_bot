from app import app
import asyncio
import threading
import os
import logging
from datetime import datetime
import psycopg2
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot configuration
TEAM_MEMBERS = {265739915}  # Иван Смирнов
bot = None
dp = None

async def init_telegram_bot():
    """Initialize Telegram bot"""
    global bot, dp
    
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found")
        return False
    
    bot = Bot(token=token)
    dp = Dispatcher()
    
    @dp.message()
    async def handle_message(message: Message):
        """Handle all incoming messages"""
        try:
            # Extract message data
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
            
            # Save to database
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
            
            # Insert or update chat
            cur.execute("""
                INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at) 
                VALUES (%s, %s, %s, true, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    title = EXCLUDED.title,
                    updated_at = EXCLUDED.updated_at
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
            
            logger.info(f"Message saved: {full_name} ({'team' if is_team_member else 'client'}) in {chat_title}")
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
    
    logger.info("Telegram bot initialized")
    return True

async def start_telegram_polling():
    """Start Telegram polling in background"""
    if bot and dp:
        try:
            logger.info("Starting Telegram polling...")
            await dp.start_polling(bot, allowed_updates=['message'])
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")

def run_telegram_bot():
    """Run Telegram bot in separate thread"""
    async def telegram_worker():
        if await init_telegram_bot():
            await start_telegram_polling()
    
    # Create new event loop for this thread
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(telegram_worker())

# Start Telegram bot in background thread
telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
telegram_thread.start()
logger.info("Telegram monitoring started in background thread")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
