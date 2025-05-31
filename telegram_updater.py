#!/usr/bin/env python3
"""
Встроенный обновлятор Telegram сообщений для веб-приложения
"""
import asyncio
import logging
import os
import requests
from datetime import datetime
from app import app, db
from models import Chat, Message
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class TelegramUpdater:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.last_update_id = 0
        
    def get_updates(self):
        """Получение обновлений от Telegram API"""
        if not self.bot_token:
            return []
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'limit': 10,
                'timeout': 1
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])
            
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}")
        
        return []
    
    def process_update(self, update):
        """Обработка одного обновления"""
        try:
            message = update.get('message')
            if not message:
                return False
                
            # Обновляем last_update_id
            self.last_update_id = max(self.last_update_id, update.get('update_id', 0))
            
            # Извлечение данных
            from_user = message.get('from', {})
            user_id = from_user.get('id', 0)
            username = from_user.get('username')
            first_name = from_user.get('first_name', '')
            last_name = from_user.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or "Unknown"
            
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            chat_type = chat.get('type', 'unknown')
            
            if chat_type == 'private':
                chat_title = "Private Chat"
            else:
                chat_title = chat.get('title', 'Unknown Chat')
            
            # Проверка участника команды
            is_team_member = self.config_manager.is_team_member(user_id)
            
            # Данные сообщения
            message_id = message.get('message_id')
            text = message.get('text', '')
            timestamp = datetime.fromtimestamp(message.get('date', 0))
            
            logger.info(f"Обновление: {chat_title} от {full_name}")
            
            with app.app_context():
                # Проверяем существование чата
                chat_obj = Chat.query.filter_by(id=chat_id).first()
                if not chat_obj:
                    chat_obj = Chat(
                        id=chat_id,
                        title=chat_title,
                        chat_type=chat_type,
                        is_active=True
                    )
                    db.session.add(chat_obj)
                
                # Проверяем, есть ли уже это сообщение
                existing_message = Message.query.filter_by(
                    message_id=message_id, 
                    chat_id=chat_id
                ).first()
                
                if not existing_message:
                    # Создаем новое сообщение
                    message_obj = Message(
                        message_id=message_id,
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        full_name=full_name,
                        text=text,
                        message_type="text" if text else "other",
                        is_team_member=is_team_member,
                        timestamp=timestamp
                    )
                    
                    db.session.add(message_obj)
                    db.session.commit()
                    
                    member_type = "команды" if is_team_member else "клиента"
                    logger.info(f"Новое сообщение от {member_type}: {full_name}")
                    return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки обновления: {e}")
            if 'db' in locals():
                db.session.rollback()
        
        return False
    
    def check_for_updates(self):
        """Проверка и обработка новых обновлений"""
        try:
            updates = self.get_updates()
            new_messages = 0
            
            for update in updates:
                if self.process_update(update):
                    new_messages += 1
            
            if new_messages > 0:
                logger.info(f"Обработано {new_messages} новых сообщений")
            
            return new_messages
            
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")
            return 0

# Глобальный экземпляр обновлятора
telegram_updater = TelegramUpdater()

def update_telegram_messages():
    """Функция для обновления сообщений Telegram"""
    return telegram_updater.check_for_updates()