#!/usr/bin/env python3
"""
Интегрированный мониторинг Telegram в основное приложение
"""
import asyncio
import threading
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from app import db
from models import Chat, Message as DBMessage
from datetime import datetime
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class IntegratedTelegramMonitor:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.bot = None
        self.dp = None
        self.monitoring_thread = None
        self.running = False
        
    def initialize_bot(self):
        """Инициализация бота"""
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не найден")
            return False
            
        try:
            self.bot = Bot(token=self.bot_token)
            self.dp = Dispatcher()
            self.register_handlers()
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {e}")
            return False
    
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
            from app import app
            
            with app.app_context():
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
                
                logger.info(f"Сообщение: {chat_title} от {full_name} (ID: {user_id})")
                
                # Проверяем существование чата
                chat = Chat.query.filter_by(id=message.chat.id).first()
                if not chat:
                    chat = Chat(
                        id=message.chat.id,
                        title=chat_title,
                        chat_type=message.chat.type,
                        is_active=True
                    )
                    db.session.add(chat)
                
                # Создаем сообщение
                db_message = DBMessage(
                    message_id=message.message_id,
                    chat_id=message.chat.id,
                    user_id=user_id,
                    username=username,
                    full_name=full_name,
                    text=message.text or "",
                    message_type=self.get_message_type(message),
                    is_team_member=is_team_member,
                    timestamp=datetime.fromtimestamp(message.date.timestamp())
                )
                
                db.session.add(db_message)
                db.session.commit()
                
                member_type = "команды" if is_team_member else "клиента"
                logger.info(f"Сохранено сообщение от {member_type}: {full_name}")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {e}")
            db.session.rollback()
    
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
    
    async def run_monitoring(self):
        """Запуск мониторинга в отдельном потоке"""
        try:
            logger.info("Запуск интегрированного Telegram мониторинга...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
    
    def start_monitoring_thread(self):
        """Запуск мониторинга в отдельном потоке"""
        if self.running:
            return
            
        if not self.initialize_bot():
            logger.error("Не удалось инициализировать бота")
            return
            
        self.running = True
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.run_monitoring())
            except Exception as e:
                logger.error(f"Ошибка в потоке мониторинга: {e}")
            finally:
                loop.close()
        
        self.monitoring_thread = threading.Thread(target=run_async, daemon=True)
        self.monitoring_thread.start()
        logger.info("Поток мониторинга запущен")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.running = False
        if self.bot:
            try:
                asyncio.run(self.bot.session.close())
            except:
                pass

# Глобальный экземпляр мониторинга
telegram_monitor = IntegratedTelegramMonitor()

def start_telegram_monitoring():
    """Функция для запуска мониторинга"""
    telegram_monitor.start_monitoring_thread()

def stop_telegram_monitoring():
    """Функция для остановки мониторинга"""
    telegram_monitor.stop_monitoring()