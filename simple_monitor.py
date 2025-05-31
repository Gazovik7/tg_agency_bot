#!/usr/bin/env python3
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleMonitor:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.bot_token or not self.database_url:
            raise ValueError("Отсутствуют переменные окружения")
            
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        
        # База данных
        self.engine = create_engine(self.database_url)
        Session = sessionmaker(bind=self.engine)
        self.Session = Session
        
        self.running = True
        self.register_handlers()
        
    def register_handlers(self):
        @self.dp.message()
        async def handle_message(message: Message):
            try:
                await self.save_message(message)
            except Exception as e:
                logger.error(f"Ошибка: {e}")
    
    async def save_message(self, message: Message):
        user_id = message.from_user.id if message.from_user else 0
        username = message.from_user.username if message.from_user else None
        full_name = message.from_user.full_name if message.from_user else "Unknown"
        
        chat_title = "Private Chat" if message.chat.type == "private" else (message.chat.title or "Unknown")
        
        # Проверка участника команды (265739915 - ваш ID)
        is_team_member = user_id == 265739915
        
        logger.info(f"Сообщение: {chat_title} от {full_name}")
        
        session = self.Session()
        try:
            # Проверяем чат
            result = session.execute(text("SELECT id FROM chats WHERE id = :chat_id"), {"chat_id": message.chat.id}).fetchone()
            
            if not result:
                session.execute(text("""
                    INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at)
                    VALUES (:id, :title, :chat_type, :is_active, :created_at, :updated_at)
                """), {
                    "id": message.chat.id,
                    "title": chat_title,
                    "chat_type": message.chat.type,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
            
            # Сохраняем сообщение
            session.execute(text("""
                INSERT INTO messages (message_id, chat_id, user_id, username, full_name, text, 
                                    message_type, is_team_member, timestamp, created_at)
                VALUES (:message_id, :chat_id, :user_id, :username, :full_name, :text,
                        :message_type, :is_team_member, :timestamp, :created_at)
            """), {
                "message_id": message.message_id,
                "chat_id": message.chat.id,
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "text": message.text or "",
                "message_type": "text" if message.text else "other",
                "is_team_member": is_team_member,
                "timestamp": datetime.fromtimestamp(message.date.timestamp()),
                "created_at": datetime.utcnow()
            })
            
            session.commit()
            logger.info(f"Сохранено от {'команды' if is_team_member else 'клиента'}: {full_name}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка БД: {e}")
        finally:
            session.close()
    
    async def start(self):
        logger.info("Запуск простого мониторинга...")
        while self.running:
            try:
                await self.dp.start_polling(self.bot)
            except Exception as e:
                logger.error(f"Ошибка: {e}, перезапуск через 5 сек...")
                await asyncio.sleep(5)
                self.bot = Bot(token=self.bot_token)
                self.dp = Dispatcher()
                self.register_handlers()

monitor = None

def signal_handler(signum, frame):
    global monitor
    if monitor:
        monitor.running = False
    sys.exit(0)

async def main():
    global monitor
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor = SimpleMonitor()
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())