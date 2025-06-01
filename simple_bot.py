#!/usr/bin/env python3
"""
Simplified Telegram bot that saves messages directly to database
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config_manager import ConfigManager
from models import Chat, Message as MessageModel, db
from app import app
from team_member_linker import team_linker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleTelegramBot:
    """Simple Telegram bot that saves messages directly to database"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        self.config = ConfigManager()
        
        # Database setup
        self.engine = create_engine(os.getenv("DATABASE_URL"))
        self.Session = sessionmaker(bind=self.engine)
        
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
            
            # Try to link team member automatically if not already linked
            if username and user_id:
                team_linker.check_and_link_member(user_id, username, full_name)
            
            # Check if user is team member
            is_team_member = team_linker.is_team_member(user_id, username)
            
            # Save message to database
            with app.app_context():
                # Get or create chat
                chat = db.session.query(Chat).filter_by(id=message.chat.id).first()
                if not chat:
                    chat = Chat(
                        id=message.chat.id,
                        title=message.chat.title or "Private Chat",
                        chat_type=message.chat.type,
                        is_active=True
                    )
                    db.session.add(chat)
                
                # Create message record
                message_record = MessageModel(
                    message_id=message.message_id,
                    chat_id=message.chat.id,
                    user_id=user_id,
                    username=message.from_user.username if message.from_user else None,
                    full_name=message.from_user.full_name if message.from_user else "Unknown",
                    text=message.text or "",
                    message_type=self.get_message_type(message),
                    is_team_member=is_team_member,
                    timestamp=message.date,
                    processed_for_sentiment=False
                )
                
                db.session.add(message_record)
                db.session.commit()
                
                logger.info(f"Saved message from {message_record.full_name} in chat {chat.title}")
            
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
        logger.info("Starting Telegram bot monitoring...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error in bot polling: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop the bot monitoring"""
        logger.info("Stopping Telegram bot monitoring...")
        try:
            await self.bot.session.close()
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


async def main():
    """Main function to run the bot"""
    bot = SimpleTelegramBot()
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