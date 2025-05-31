#!/usr/bin/env python3
"""
Webhook обработчик для Telegram бота
"""
import logging
import os
from datetime import datetime
from flask import request, jsonify
from app import app, db
from models import Chat, Message
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
    def verify_webhook(self, request_data):
        """Проверка веб-хука"""
        # Простая проверка наличия обязательных полей
        return 'message' in request_data and 'update_id' in request_data
    
    def process_webhook_message(self, message_data):
        """Обработка сообщения из веб-хука"""
        try:
            message = message_data.get('message', {})
            if not message:
                return False
                
            # Извлечение данных пользователя
            from_user = message.get('from', {})
            user_id = from_user.get('id', 0)
            username = from_user.get('username')
            full_name = from_user.get('first_name', '') + ' ' + from_user.get('last_name', '')
            full_name = full_name.strip() or "Unknown"
            
            # Извлечение данных чата
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            chat_type = chat.get('type', 'unknown')
            
            # Определение названия чата
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
            
            logger.info(f"Webhook: {chat_title} от {full_name} (ID: {user_id})")
            
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
            
            # Создаем сообщение
            message_obj = Message(
                message_id=message_id,
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                full_name=full_name,
                text=text,
                message_type=self.get_message_type(message),
                is_team_member=is_team_member,
                timestamp=timestamp
            )
            
            db.session.add(message_obj)
            db.session.commit()
            
            member_type = "команды" if is_team_member else "клиента"
            logger.info(f"Webhook: Сохранено сообщение от {member_type}: {full_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки webhook сообщения: {e}")
            db.session.rollback()
            return False
    
    def get_message_type(self, message):
        """Определение типа сообщения"""
        if message.get('text'):
            return "text"
        elif message.get('photo'):
            return "photo"
        elif message.get('document'):
            return "document"
        elif message.get('voice'):
            return "voice"
        elif message.get('video'):
            return "video"
        else:
            return "other"

# Создаем глобальный экземпляр обработчика
webhook_handler = WebhookHandler()

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Endpoint для получения веб-хуков от Telegram"""
    try:
        request_data = request.get_json()
        
        if not request_data:
            logger.warning("Webhook: Пустые данные")
            return jsonify({'status': 'error', 'message': 'No data'}), 400
        
        if not webhook_handler.verify_webhook(request_data):
            logger.warning("Webhook: Неверный формат данных")
            return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
        
        # Обрабатываем сообщение
        success = webhook_handler.process_webhook_message(request_data)
        
        if success:
            return jsonify({'status': 'ok'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Processing failed'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка webhook endpoint: {e}")
        return jsonify({'status': 'error', 'message': 'Internal error'}), 500

@app.route('/webhook/status', methods=['GET'])
def webhook_status():
    """Статус веб-хука"""
    return jsonify({
        'status': 'active',
        'webhook_url': '/webhook/telegram',
        'bot_configured': bool(webhook_handler.bot_token)
    })