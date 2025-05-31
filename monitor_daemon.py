#!/usr/bin/env python3
"""
Простой демон для мониторинга Telegram сообщений
"""
import asyncio
import logging
import os
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config_manager import ConfigManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_daemon.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramDaemon:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
            
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
        
        # База данных
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL не найден в переменных окружения")
            
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.Session = Session
        
        self.running = True
        
        # Регистрация обработчиков
        self.register_handlers()
        
    def register_handlers(self):
        """Регистрация обработчиков сообщений"""
        @self.dp.message()
        async def handle_all_messages(message: Message):
            try:
                await self.process_message(message)
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
    
    async def process_message(self, message: Message):
        """Обработка входящего сообщения"""
        try:
            user_id = message.from_user.id if message.from_user else 0
            username = message.from_user.username if message.from_user else None
            full_name = message.from_user.full_name if message.from_user else "Unknown"
            
            # Определение типа чата
            chat_title = "Unknown Chat"
            if message.chat.type == "private":
                chat_title = "Private Chat"
            elif message.chat.title:
                chat_title = message.chat.title
                
            # Проверка, является ли пользователь участником команды
            is_team_member = self.config_manager.is_team_member(user_id)
            
            logger.info(f"Получено сообщение: {message.chat.type} '{chat_title}' от {full_name} (ID: {user_id})")
            
            # Сохранение в базу данных
            session = self.Session()
            try:
                # Проверяем существование чата
                chat_exists = session.execute(
                    text("SELECT id FROM chats WHERE id = :chat_id"),
                    {"chat_id": message.chat.id}
                ).fetchone()
                
                if not chat_exists:
                    # Создаем новый чат
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
                    "message_type": self.get_message_type(message),
                    "is_team_member": is_team_member,
                    "timestamp": datetime.fromtimestamp(message.date.timestamp()),
                    "created_at": datetime.utcnow()
                })
                
                session.commit()
                
                member_type = "команды" if is_team_member else "клиента"
                logger.info(f"Сохранено сообщение от {member_type}: {full_name}")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Ошибка сохранения сообщения: {e}")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
    
    def get_message_type(self, message: Message) -> str:
        """Определение типа сообщения"""
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
        else:
            return "other"
    
    async def start_monitoring(self):
        """Запуск мониторинга"""
        logger.info("Запуск Telegram демона мониторинга...")
        
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка запуска мониторинга: {e}")
            raise
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        logger.info("Остановка мониторинга...")
        self.running = False
        await self.bot.session.close()

# Глобальная переменная для демона
daemon = None

def signal_handler(signum, frame):
    """Обработчик сигналов"""
    logger.info(f"Получен сигнал {signum}, остановка...")
    if daemon:
        asyncio.create_task(daemon.stop_monitoring())
    sys.exit(0)

async def main():
    """Главная функция"""
    global daemon
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        daemon = TelegramDaemon()
        await daemon.start_monitoring()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())