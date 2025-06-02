import asyncio
import logging
import os
from dotenv import load_dotenv
from pathlib import Path

# Настраиваем расширенное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Загружаем переменные окружения из файла .env
    env_path = Path('.') / '.env'
    logger.debug(f"Пытаемся загрузить .env из: {env_path.absolute()}")
    logger.debug(f"Файл .env существует: {env_path.exists()}")
    
    load_dotenv(dotenv_path=env_path)
    
    # Проверяем загрузку переменных
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    logger.debug(f"TELEGRAM_BOT_TOKEN загружен: {'Да' if bot_token else 'Нет'}")
    
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
except Exception as e:
    logger.error(f"Ошибка при инициализации: {str(e)}", exc_info=True)
    raise

import json
from datetime import datetime
from typing import Optional

import redis
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramMonitorBot:
    """Telegram bot for monitoring group chats"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        self.redis = None
        self.config = ConfigManager()
        
        # Register handlers
        self.register_handlers()
    
    async def init_redis(self):
        """Initialize Redis connection"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def register_handlers(self):
        """Register message handlers"""
        
        @self.dp.message()
        async def handle_all_messages(message: Message):
            """Handle all incoming messages"""
            try:
                # Only process group and supergroup messages
                if message.chat.type not in ['group', 'supergroup']:
                    return
                
                await self.process_message(message)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def process_message(self, message: Message):
        """Process incoming message and add to Redis queue"""
        try:
            # Determine if sender is team member
            is_team_member = await self.is_team_member(message.from_user.id)
            
            # Create message data
            message_data = {
                "message_id": message.message_id,
                "chat_id": message.chat.id,
                "chat_title": message.chat.title,
                "chat_type": message.chat.type,
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "full_name": message.from_user.full_name,
                "text": message.text or "",
                "message_type": self.get_message_type(message),
                "is_team_member": is_team_member,
                "timestamp": message.date.isoformat(),
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Add to Redis queue (sync operation)
            if self.redis:
                self.redis.lpush("message_queue", json.dumps(message_data))
            
            logger.info(f"Queued message from chat {message.chat.title} ({message.chat.id})")
            
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}")
    
    async def is_team_member(self, user_id: int) -> bool:
        """Check if user is a team member"""
        try:
            team_members = self.config.get_team_members()
            return user_id in team_members
        except Exception as e:
            logger.error(f"Error checking team member status: {e}")
            return False
    
    def get_message_type(self, message: Message) -> str:
        """Determine message type"""
        if message.text:
            return "text"
        elif message.photo:
            return "photo"
        elif message.document:
            return "document"
        elif message.video:
            return "video"
        elif message.audio:
            return "audio"
        elif message.voice:
            return "voice"
        elif message.sticker:
            return "sticker"
        else:
            return "other"
    
    async def start_monitoring(self):
        """Start the bot monitoring"""
        try:
            await self.init_redis()
            logger.info("Starting Telegram monitoring bot...")
            
            # Get bot info
            bot_info = await self.bot.get_me()
            logger.info(f"Bot started: @{bot_info.username}")
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop the bot monitoring"""
        try:
            if self.redis:
                await self.redis.close()
            await self.bot.session.close()
            logger.info("Bot monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


async def main():
    """Main function to run the bot"""
    bot = TelegramMonitorBot()
    try:
        await bot.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        await bot.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
