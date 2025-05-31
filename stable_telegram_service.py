#!/usr/bin/env python3
"""
Стабильный сервис мониторинга Telegram
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from config_manager import ConfigManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class StableTelegramService:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден")
        if not self.database_url:
            raise ValueError("DATABASE_URL не найден")
            
        self.bot = Bot(token=self.bot_token)
        self.dp = Dispatcher()
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
    
    def get_db_connection(self):
        """Получение подключения к базе данных"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            return None
    
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
                
            # Проверка участника команды
            is_team_member = self.config_manager.is_team_member(user_id)
            
            logger.info(f"Получено сообщение: {chat_title} от {full_name} (ID: {user_id})")
            
            # Сохранение в базу данных
            conn = self.get_db_connection()
            if not conn:
                logger.error("Не удалось подключиться к базе данных")
                return
                
            try:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # Проверяем существование чата
                    cur.execute("SELECT id FROM chats WHERE id = %s", (message.chat.id,))
                    chat_exists = cur.fetchone()
                    
                    if not chat_exists:
                        # Создаем новый чат
                        cur.execute("""
                            INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            message.chat.id,
                            chat_title,
                            message.chat.type,
                            True,
                            datetime.utcnow(),
                            datetime.utcnow()
                        ))
                    
                    # Сохраняем сообщение
                    cur.execute("""
                        INSERT INTO messages (message_id, chat_id, user_id, username, full_name, text, 
                                            message_type, is_team_member, timestamp, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        message.message_id,
                        message.chat.id,
                        user_id,
                        username,
                        full_name,
                        message.text or "",
                        self.get_message_type(message),
                        is_team_member,
                        datetime.fromtimestamp(message.date.timestamp()),
                        datetime.utcnow()
                    ))
                    
                conn.commit()
                
                member_type = "команды" if is_team_member else "клиента"
                logger.info(f"Сохранено сообщение от {member_type}: {full_name}")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка сохранения в базу данных: {e}")
            finally:
                conn.close()
                
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
        logger.info("Запуск стабильного Telegram сервиса мониторинга...")
        
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

# Глобальная переменная для сервиса
service = None

def signal_handler(signum, frame):
    """Обработчик сигналов"""
    logger.info(f"Получен сигнал {signum}, остановка...")
    if service:
        asyncio.create_task(service.stop_monitoring())
    sys.exit(0)

async def main():
    """Главная функция"""
    global service
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        service = StableTelegramService()
        
        # Бесконечный цикл с автоперезапуском при ошибках
        while True:
            try:
                await service.start_monitoring()
            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")
                logger.info("Перезапуск через 5 секунд...")
                await asyncio.sleep(5)
                
                # Пересоздаем бот и диспетчер
                service.bot = Bot(token=service.bot_token)
                service.dp = Dispatcher()
                service.register_handlers()
                
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())