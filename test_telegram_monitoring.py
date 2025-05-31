#!/usr/bin/env python3
"""
Test Telegram monitoring with direct database saving
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestTelegramBot:
    """Test Telegram bot for monitoring"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        
        # Database setup
        self.engine = create_engine(os.getenv("DATABASE_URL"))
        self.Session = sessionmaker(bind=self.engine)
        
        # Team member ID (your ID)
        self.team_member_id = 265739915
        
        # Register handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register message handlers"""
        
        @self.dp.message()
        async def handle_all_messages(message: Message):
            """Handle all incoming messages"""
            try:
                await self.process_message(message)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
    
    async def process_message(self, message: Message):
        """Process incoming message and save to database"""
        try:
            # Get user info
            user_id = message.from_user.id if message.from_user else 0
            username = message.from_user.username if message.from_user else None
            full_name = message.from_user.full_name if message.from_user else "Unknown"
            is_team_member = user_id == self.team_member_id
            
            # Save to database using raw SQL to avoid import issues
            session = self.Session()
            try:
                # Insert or update chat
                chat_query = text("""
                    INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at)
                    VALUES (:chat_id, :title, :chat_type, :is_active, :created_at, :updated_at)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        updated_at = EXCLUDED.updated_at
                """)
                
                session.execute(chat_query, {
                    'chat_id': message.chat.id,
                    'title': message.chat.title or 'Private Chat',
                    'chat_type': message.chat.type,
                    'is_active': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                })
                
                # Insert message
                message_query = text("""
                    INSERT INTO messages (
                        message_id, chat_id, user_id, username, full_name, text,
                        message_type, is_team_member, timestamp, created_at,
                        processed_for_sentiment
                    ) VALUES (
                        :message_id, :chat_id, :user_id, :username, :full_name, :text,
                        :message_type, :is_team_member, :timestamp, :created_at,
                        :processed_for_sentiment
                    )
                """)
                
                session.execute(message_query, {
                    'message_id': message.message_id,
                    'chat_id': message.chat.id,
                    'user_id': user_id,
                    'username': username,
                    'full_name': full_name,
                    'text': message.text or "",
                    'message_type': self.get_message_type(message),
                    'is_team_member': is_team_member,
                    'timestamp': message.date,
                    'created_at': datetime.utcnow(),
                    'processed_for_sentiment': False
                })
                
                session.commit()
                
                role = "команды" if is_team_member else "клиента"
                logger.info(f"✅ Сохранено сообщение от {role}: {full_name} в чате {message.chat.title}")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error saving to database: {e}")
            finally:
                session.close()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def get_message_type(self, message: Message) -> str:
        """Determine message type"""
        if message.text:
            return "text"
        elif message.photo:
            return "photo"
        elif message.document:
            return "document"
        elif message.voice:
            return "voice"
        elif message.video:
            return "video"
        elif message.sticker:
            return "sticker"
        else:
            return "other"
    
    async def start_monitoring(self):
        """Start the bot monitoring"""
        logger.info("🚀 Запуск мониторинга Telegram...")
        logger.info(f"👤 ID участника команды: {self.team_member_id}")
        logger.info("📱 Отправьте сообщение в чат с ботом для тестирования")
        
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error in bot polling: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop the bot monitoring"""
        logger.info("⏹️ Остановка мониторинга...")
        try:
            await self.bot.session.close()
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


async def main():
    """Main function"""
    bot = TestTelegramBot()
    try:
        await bot.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")
    finally:
        await bot.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())