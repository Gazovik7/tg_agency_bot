#!/usr/bin/env python3
"""
Standalone Telegram bot for message monitoring
"""
import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StandaloneTelegramBot:
    """Standalone Telegram bot that saves messages directly to database"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
            
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        
        # Database setup
        self.engine = create_engine(os.environ.get('DATABASE_URL'))
        Session = sessionmaker(bind=self.engine)
        self.Session = Session
        
        self.register_handlers()
        logger.info("Standalone Telegram bot initialized")

    def register_handlers(self):
        """Register message handlers"""
        
        @self.dp.message()
        async def handle_all_messages(message: Message):
            """Handle all incoming messages"""
            try:
                await self.process_message(message)
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def process_message(self, message: Message):
        """Process incoming message and save to database"""
        try:
            session = self.Session()
            
            # Get chat info
            chat_id = message.chat.id
            chat_title = getattr(message.chat, 'title', 'Private Chat')
            chat_type = message.chat.type
            
            # Get user info
            user_id = message.from_user.id
            username = getattr(message.from_user, 'username', None)
            full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
            
            # Check if user is team member
            is_team_member = await self.is_team_member(user_id)
            
            # Get message text and type
            text = message.text or message.caption or ""
            message_type = self.get_message_type(message)
            
            # Save chat if not exists
            chat_query = text("SELECT id FROM chats WHERE id = :chat_id")
            chat_exists = session.execute(chat_query, {"chat_id": chat_id}).fetchone()
            
            if not chat_exists:
                insert_chat = text("""
                    INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at) 
                    VALUES (:chat_id, :title, :chat_type, true, :now, :now)
                """)
                session.execute(insert_chat, {
                    "chat_id": chat_id,
                    "title": chat_title,
                    "chat_type": chat_type,
                    "now": datetime.utcnow()
                })
            
            # Save message
            insert_message = text("""
                INSERT INTO messages (
                    message_id, chat_id, user_id, username, full_name, text, 
                    message_type, is_team_member, timestamp, created_at
                ) VALUES (
                    :message_id, :chat_id, :user_id, :username, :full_name, :text,
                    :message_type, :is_team_member, :timestamp, :created_at
                )
            """)
            
            session.execute(insert_message, {
                "message_id": message.message_id,
                "chat_id": chat_id,
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "text": text,
                "message_type": message_type,
                "is_team_member": is_team_member,
                "timestamp": datetime.fromtimestamp(message.date.timestamp()),
                "created_at": datetime.utcnow()
            })
            
            session.commit()
            session.close()
            
            logger.info(f"Saved message from {full_name} in chat {chat_title}")
            
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()

    async def is_team_member(self, user_id: int) -> bool:
        """Check if user is a team member"""
        team_members = self.config_manager.get_team_members()
        return user_id in team_members

    def get_message_type(self, message: Message) -> str:
        """Determine message type"""
        if message.text:
            return 'text'
        elif message.photo:
            return 'photo'
        elif message.document:
            return 'document'
        elif message.voice:
            return 'voice'
        elif message.video:
            return 'video'
        elif message.sticker:
            return 'sticker'
        else:
            return 'other'

    async def start_monitoring(self):
        """Start the bot monitoring"""
        try:
            logger.info("Starting Telegram bot monitoring...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def stop_monitoring(self):
        """Stop the bot monitoring"""
        try:
            await self.bot.session.close()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

async def main():
    """Main function to run the bot"""
    bot = None
    try:
        bot = StandaloneTelegramBot()
        await bot.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        if bot:
            await bot.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())